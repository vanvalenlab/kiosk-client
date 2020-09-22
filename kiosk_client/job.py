# Copyright 2016-2020 The Van Valen Lab at the California Institute of
# Technology (Caltech), with support from the Paul Allen Family Foundation,
# Google, & National Institutes of Health (NIH) under Grant U24CA224309-01.
# All rights reserved.
#
# Licensed under a modified Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.github.com/vanvalenlab/kiosk-client/LICENSE
#
# The Work provided may be used for non-commercial academic purposes only.
# For any other use of the Work, including commercial use, please contact:
# vanvalenlab@gmail.com
#
# Neither the name of Caltech nor the names of its contributors may be used
# to endorse or promote products derived from this software without specific
# prior written permission.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""Job class using Twisted to create and monitor itself asynchronously"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
import os
import timeit

import dateutil.parser
import treq
from twisted.internet import defer
from twisted.internet import error as twisted_errors
from twisted.web import _newclient as twisted_client

from kiosk_client.utils import sleep, strip_bucket_prefix, get_download_path


class Job(object):

    def __init__(self, host, filepath, model_name, model_version, **kwargs):
        """Creates and tracks a DeepCell Kiosk job, recording various summary data.

        Args:
            host (str): public IP address of the DeepCell Kiosk cluster.
            filepath (str): The filepath of the file to be processed.
            model_name (str): Name of servable model.
            model_version (int): Version of servable model.
            kwargs (dict): Optional keyword arguments.
        """
        self.logger = logging.getLogger(str(self.__class__.__name__))

        self.host = str(host)
        self.filepath = str(filepath)
        self.model_name = str(model_name)
        self.model_version = str(model_version)
        self.job_type = str(kwargs.get('job_type', 'segmentation'))

        data_scale = str(kwargs.get('data_scale', ''))
        if data_scale:
            try:
                data_scale = float(data_scale)
            except ValueError:
                raise ValueError('data_scale must be a number.')
        self.data_scale = data_scale

        data_label = str(kwargs.get('data_label', ''))
        if data_label:
            try:
                data_label = int(data_label)
            except ValueError:
                raise ValueError('data_label must be an integer.')
        self.data_label = data_label

        if self.model_version and not self.model_version.isdigit():
            raise ValueError('`model_version` must be a number, got ' +
                             self.model_version)

        self.preprocess = kwargs.get('preprocess', '')
        self.postprocess = kwargs.get('postprocess', '')
        self.upload_prefix = kwargs.get('upload_prefix', 'uploads')
        self.upload_prefix = strip_bucket_prefix(self.upload_prefix)
        self.expire_time = int(kwargs.get('expire_time', 3600))
        self.update_interval = int(kwargs.get('update_interval', 10))
        self.original_name = kwargs.get('original_name', self.filepath)
        self.download_results = kwargs.get('download_results', False)

        self.output_dir = kwargs.get('output_dir', get_download_path())
        if not os.path.isdir(self.output_dir):
            raise ValueError('Invalid value for output_dir,'
                             ' %s is not a directory.' % self.output_dir)
        if not os.access(self.output_dir, os.W_OK):
            raise ValueError('Invalid value for output_dir,'
                             ' %s is not writable.' % self.output_dir)

        self.failed = False  # for error handling
        self.is_expired = False

        self.headers = {
            'Content-Type': ['application/json'],
            'Connection': 'close',
        }

        # summary data
        self.status = None
        self.job_id = None
        self.created_at = None
        self.finished_at = None
        self.postprocess_time = None
        self.prediction_time = None
        self.download_time = None
        self.upload_time = None
        self.output_url = None
        self.total_jobs = None
        self.total_time = None
        self.reason = None
        self.children_upload_time = None
        self.cleanup_time = None
        self.predict_retries = None
        self._finished_statuses = {'done', 'failed'}

        self.pool = kwargs.get('pool')

        self.sleep = sleep  # allow monkey-patch

        self._http_errors = (
            twisted_client.ResponseNeverReceived,
            twisted_client.RequestTransmissionFailed,
            twisted_errors.ConnectBindError,
            twisted_errors.TimeoutError,
            twisted_errors.ConnectError,
            twisted_errors.ConnectionRefusedError,
        )

    @property
    def is_done(self):
        return self.status in self._finished_statuses

    @property
    def is_summarized(self):
        if self.status == 'failed':
            return True
        summaries = (self.created_at, self.finished_at, self.output_url)
        is_summarized = all(x is not None for x in summaries)
        return is_summarized and self.is_done

    def json(self):

        def _float(x):
            if isinstance(x, list):
                return [_float(y) for y in x]
            try:
                return float(x)
            except:  # pylint: disable=bare-except
                return x

        return {
            'input_file': self.original_name,
            'status': self.status,
            'total_time': _float(self.total_time),
            'total_jobs': _float(self.total_jobs),
            'download_url': self.output_url,
            'created_at': self.created_at,
            'finished_at': self.finished_at,
            'prediction_time': _float(self.prediction_time),
            'postprocess_time': _float(self.postprocess_time),
            'upload_time': _float(self.upload_time),
            'download_time': _float(self.download_time),
            'predict_retries': _float(self.predict_retries),
            'cleanup_time': _float(self.cleanup_time),
            'children_upload_time': _float(self.children_upload_time),
            'model': '{}:{}'.format(self.model_name, self.model_version),
            'postprocess': self.postprocess,
            'preprocess': self.preprocess,
            'reason': self.reason,
            'job_id': self.job_id,
        }

    def _log_http_response(self, response, created_at):
        log = self.logger.debug if response.code == 200 else self.logger.warning
        log('%s %s - %s %s - took %ss',
            response.request.method.decode(),
            response.request.absoluteURI.decode(),
            response.code, response.phrase.decode(),
            timeit.default_timer() - created_at)

    def _make_post_request(self, host, **kwargs):
        req_kwargs = {
            'headers': kwargs.get('headers', self.headers),
            'pool': kwargs.get('pool', self.pool),
        }

        # The name of the payload dictates the type of encoding and headers.
        payload_names = {'data', 'json', 'files'}
        for pn in payload_names:
            if pn in kwargs:
                req_kwargs[pn] = kwargs[pn]

        return treq.post(host, **req_kwargs)

    @defer.inlineCallbacks
    def _retry_post_request_wrapper(self, host, name='REDIS', **kwargs):
        retrying = True  # retry loop to prevent stackoverflow
        while retrying:
            created_at = timeit.default_timer()
            try:
                request = self._make_post_request(host, **kwargs)
                response = yield request  # Wait for the deferred request
            except self._http_errors as err:
                self.logger.warning('[%s]: Encountered %s during %s: %s',
                                    self.job_id, type(err).__name__, name, err)
                yield self.sleep(self.update_interval)
                continue  # return to top of retry loop

            try:
                self._log_http_response(response, created_at)
                json_content = yield response.json()  # parse the JSON data
            except (ValueError, AttributeError) as err:
                self.logger.error('[%s]: Failed to parse %s response as JSON '
                                  'due to %s: %s', self.job_id, name,
                                  type(err).__name__, err)
                yield self.sleep(self.update_interval)
                continue  # return to top of retry loop

            retrying = False  # success

        defer.returnValue(json_content)  # "return" the value

    @defer.inlineCallbacks
    def upload_file(self):
        host = '{}/api/upload'.format(self.host)
        name = 'UPLOAD {}'.format(self.filepath)
        with open(self.filepath, 'rb') as f:
            payload = {'file': (self.filepath, f)}
            response = yield self._retry_post_request_wrapper(
                host, name, files=payload, headers=self.headers)
        uploaded_path = response.get('uploadedName')
        defer.returnValue(uploaded_path)  # "return" the value

    @defer.inlineCallbacks
    def get_redis_value(self, field):
        host = '{}/api/redis'.format(self.host)
        payload = {'hash': self.job_id, 'key': field}
        name = 'REDIS HGET {}'.format(field)
        response = yield self._retry_post_request_wrapper(host, name,
                                                          json=payload)
        value = response.get('value')
        defer.returnValue(value)  # "return" the value

    @defer.inlineCallbacks
    def create(self):
        # Build a deferred request to the create API
        # See https://tinyurl.com/u3qs9om for expected POST data
        job_data = {
            'modelName': self.model_name,
            'modelVersion': self.model_version,
            'preprocessFunction': self.preprocess,
            'postprocessFunction': self.postprocess,
            'imageName': self.filepath,
            'jobType': self.job_type,
            'dataRescale': self.data_scale,
            'dataLabel': self.data_label,
            'uploadedName': os.path.join(self.upload_prefix, self.filepath),
        }
        host = '{}/api/predict'.format(self.host)
        name = 'REDIS CREATE'
        response = yield self._retry_post_request_wrapper(host, name,
                                                          json=job_data)

        job_id = response.get('hash')

        if job_id is not None:
            self.logger.debug('[%s]: Successfully created.', job_id)
        else:
            self.logger.error('Create response JSON is invalid: %s', response)

        defer.returnValue(job_id)  # "return" the value

    @defer.inlineCallbacks
    def monitor(self):
        while not self.is_done:

            yield self.sleep(self.update_interval)  # prevent 429s

            status = yield self.get_redis_value('status')

            if self.status != status:
                self.status = status
                self.logger.info('[%s]: Found new %sstatus `%s`.', self.job_id,
                                 'final ' if self.is_done else '', self.status)

        defer.returnValue(self.is_done)  # "return" the value

    @defer.inlineCallbacks
    def summarize(self):
        summary_attributes = (
            'created_at',
            'finished_at',
            'reason',
            'output_url',
        )
        attributes = (
            'prediction_time',
            'predict_retries',
            'postprocess_time',
            'upload_time',
            'download_time',
            'children_upload_time',
            'cleanup_time',
            'total_jobs',
            'total_time',
        )
        # get the string values
        for name in summary_attributes:
            value = yield self.get_redis_value(name)
            setattr(self, name, value)  # save the valid value to self

        # get the numerical values and parse into list if required
        for name in attributes:
            value = yield self.get_redis_value(name)
            value = str(value).split(',')
            if len(value) == 1:
                value = value[0]
            setattr(self, name, value)  # save the valid value to self

        defer.returnValue(self.is_summarized)  # "return" the value

    @defer.inlineCallbacks
    def expire(self):
        host = '{}/api/redis/expire'.format(self.host)
        payload = {'hash': self.job_id, 'expireIn': self.expire_time}
        name = 'REDIS EXPIRE'
        response = yield self._retry_post_request_wrapper(host, name,
                                                          json=payload)
        value = response.get('value')
        defer.returnValue(value)  # "return" the value

    @defer.inlineCallbacks
    def download_output(self):
        start = timeit.default_timer()
        basename = self.output_url.split('/')[-1]
        dest = os.path.join(self.output_dir, basename)
        self.logger.info('[%s]: Downloading output file %s to %s.',
                         self.job_id, self.output_url, dest)
        name = 'DOWNLOAD RESULTS'
        retrying = True  # retry loop to prevent stackoverflow
        while retrying:
            try:
                request = treq.get(self.output_url, unbuffered=True)
                response = yield request
            except self._http_errors as err:
                self.logger.warning('[%s]: Encountered %s during %s: %s',
                                    self.job_id, type(err).__name__, name, err)
                yield self.sleep(self.update_interval)
                continue  # return to top of retry loop
            retrying = False  # success

        with open(dest, 'wb') as outfile:
            yield response.collect(outfile.write)

        self.logger.info('Saved output file: "%s" in %s s.',
                         dest, timeit.default_timer() - start)

        defer.returnValue(dest)

    @defer.inlineCallbacks
    def restart(self, delay=0):
        if not self.failed:
            self.logger.warning('[%s]: Restarting but not failed.', self.job_id)

        self.failed = False  # reset failure mode to prevent further restarts

        if delay:
            yield self.sleep(delay)

        self.logger.debug('[%s]: Restarting failed job.', self.job_id)

        if self.job_id is None:  # never got started in the first place
            result = yield self.start()

        elif self.is_done:  # no need to monitor, skip straight to summarize
            result = yield self.summarize()

        else:  # job has begun but was not finished, monitor status
            result = yield self.monitor()

        defer.returnValue(result)

    @defer.inlineCallbacks
    def start(self, delay=0, upload=False):

        if delay:  # delay the start if required
            yield self.sleep(delay)

        if upload:
            uploaded_path = yield self.upload_file()
            self.filepath = os.path.relpath(uploaded_path, self.upload_prefix)

        try:
            self.job_id = yield self.create()
            assert self.job_id is not None, 'Create did not return a job ID'

            success = yield self.monitor()
            assert success, 'Monitor did not have a successful return vaue'

            success = yield self.summarize()
            assert success, 'Summarize did not have a successful return vaue'

            if self.status == 'done' and self.is_summarized:
                # TODO: `dateutil` deprecated by python 3.7 `fromisoformat`
                # created_at = datetime.datetime.fromisoformat(created_at)
                # finished_at = datetime.datetime.fromisoformat(finished_at)
                created_at = dateutil.parser.parse(self.created_at)
                finished_at = dateutil.parser.parse(self.finished_at)
                diff = finished_at - created_at
                self.logger.info('[%s]: Finished in %s seconds with status '
                                 '`%s`. Download at `%s`.',
                                 self.job_id, diff.total_seconds(),
                                 self.status, self.output_url)

                if self.download_results:
                    success = yield self.download_output()

            elif self.status == 'failed':
                reason = yield self.get_redis_value('reason')
                self.logger.warning('[%s]: Found final status `%s`: %s',
                                    self.job_id, self.status, reason)

            else:
                raise ValueError('Job %s was about to expire with status %s' %
                                 (self.job_id, self.status))

            yield self.sleep(self.update_interval)
            value = yield self.expire()

            assert value == 1, 'Failed to expire key %s' % self.job_id
            self.is_expired = True

            defer.returnValue(value)

        except Exception as err:
            self.failed = True
            self.logger.error('[%s]: Encountered unexpected error in '
                              'job.start(): %s', self.job_id, err)
            defer.returnValue(False)
