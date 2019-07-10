# Copyright 2016-2019 The Van Valen Lab at the California Institute of
# Technology (Caltech), with support from the Paul Allen Family Foundation,
# Google, & National Institutes of Health (NIH) under Grant U24CA224309-01.
# All rights reserved.
#
# Licensed under a modified Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.github.com/vanvalenlab/kiosk-benchmarking/LICENSE
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

import json
import logging
import os

import dateutil.parser
import treq
from twisted.internet import defer, reactor
from twisted.internet import error as twisted_errors
from twisted.web import _newclient as twisted_client
from twisted.internet.task import deferLater


class Job(object):

    def __init__(self, host, filepath, model_name, model_version, **kwargs):
        self.logger = logging.getLogger(str(self.__class__.__name__))

        self.host = str(host)
        self.filepath = str(filepath)
        self.model_name = str(model_name)
        self.model_version = str(model_version)

        if not self.model_version.isdigit():
            raise ValueError('`model_version` must be a number, got ' +
                             self.model_version)

        self.preprocess = kwargs.get('preprocess', '')
        self.postprocess = kwargs.get('postprocess', '')
        self.upload_prefix = kwargs.get('upload_prefix', 'uploads')
        self.expire_time = int(kwargs.get('expire_time', 3600))
        self.update_interval = int(kwargs.get('update_interval', 10))
        self.original_name = kwargs.get('original_name', self.filepath)

        self.failed = False  # for error handling

        self.headers = {'Content-Type': ['application/json']}
        self.status = None
        self.job_id = None
        self.created_at = None
        self.finished_at = None
        self.postprocess_time = None
        self.prediction_time = None
        self.download_time = None
        self.upload_time = None
        self.output_url = None
        self._finished_statuses = {'done', 'failed'}

        self._http_errors = (
            twisted_client.ResponseNeverReceived,
            twisted_client.RequestTransmissionFailed,
            twisted_errors.ConnectBindError,
            twisted_errors.TimeoutError,
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

    def sleep(self, seconds):
        """Simple helper to delay asynchronously for some number of seconds."""
        return deferLater(reactor, seconds, lambda: None)

    def json(self):
        jsondata = {
            'input_file': self.original_name,
            'status': self.status,
            'download_url': self.output_url,
            'created_at': self.created_at,
            'finished_at': self.finished_at,
            'prediction_time': self.prediction_time,
            'postprocess_time': self.postprocess_time,
            'upload_time': self.upload_time,
            'download_time': self.download_time,
            'model': '{}:{}'.format(self.model_name, self.model_version),
            'postprocess': self.postprocess,
            'preprocess': self.preprocess,
            'job_id': self.job_id,
        }
        # make sure each value is a string.
        for x in jsondata:
            if x is None:
                jsondata[x] = ''
        return jsondata

    def _log_http_response(self, response):
        log = self.logger.debug if response.code == 200 else self.logger.warning
        log('%s %s - %s %s',
            response.request.method.decode(),
            response.request.absoluteURI.decode(),
            response.code, response.phrase.decode())

    @defer.inlineCallbacks
    def get_redis_value(self, field):
        host = '{}/api/redis'.format(self.host)
        payload = {'hash': self.job_id, 'key': field}

        retrying = True  # retry  loop to prevent stackoverflow
        while retrying:

            try:
                request = treq.post(host, json=payload, headers=self.headers)
                response = yield request  # Wait for the deferred request
            except self._http_errors as err:
                self.logger.error('Job `%s` encountered error while getting '
                                  'redis field %s: %s', self.job_id, field, err)
                yield self.sleep(self.update_interval)
                continue  # return to top of retry loop

            try:
                self._log_http_response(response)
                json_content = yield response.json()  # parse the JSON data
            except (json.decoder.JSONDecodeError, AttributeError) as err:
                self.logger.error('Job `%s` failed to parse JSON data from the'
                                  ' request: %s', self.job_id, err)
                yield self.sleep(self.update_interval)
                continue  # return to top of retry loop

            value = json_content.get('value')

            retrying = False  # success

        defer.returnValue(value)  # "return" the value

    @defer.inlineCallbacks
    def create(self):
        # Build a deferred request to the create API
        job_data = {
            'modelName': self.model_name,
            'modelVersion': self.model_version,
            'preprocessFunction': self.preprocess,
            'postprocessFunction': self.postprocess,
            'imageName': self.filepath,
            'uploadedName': os.path.join(self.upload_prefix, self.filepath),
        }
        host = '{}/api/predict'.format(self.host)

        retrying = True  # retry  loop to prevent stackoverflow
        while retrying:

            try:
                request = treq.post(host, json=job_data, headers=self.headers)
                response = yield request  # Wait for the deferred request
            except self._http_errors as err:
                self.logger.error('Encountered error in create(): %s,', err)
                yield self.sleep(self.update_interval)
                continue  # return to top of retry loop

            try:
                self._log_http_response(response)
                json_content = yield response.json()  # parse the JSON data
            except (json.decoder.JSONDecodeError, AttributeError) as err:
                self.logger.error('Job `%s` failed to parse JSON data from the'
                                  ' request: %s', self.job_id, err)
                yield self.sleep(self.update_interval)
                continue  # return to top of retry loop

            job_id = json_content.get('hash')
            self.logger.info('Job created with ID `%s`', job_id)
            retrying = False  # success

        defer.returnValue(job_id)  # "return" the value

    @defer.inlineCallbacks
    def monitor(self):
        while not self.is_done:

            yield self.sleep(self.update_interval)  # prevent 429s

            status = yield self.get_redis_value('status')

            if self.status != status:
                self.status = status
                self.logger.info('Job `%s` has new status `%s`',
                                 self.job_id, self.status)

        # job is_done, log and summarize
        self.logger.info('Job `%s` is finished with status `%s`.',
                         self.job_id, self.status)

        defer.returnValue(True)  # "return" the value

    @defer.inlineCallbacks
    def summarize(self):
        attributes = [
            'created_at',
            'finished_at',
            'prediction_time',
            'postprocess_time',
            'upload_time',
            'download_time',
            # 'total_jobs',
            'output_url',
        ]

        for name in attributes:
            retry = False
            value = None  # retry each request if the field is still null
            while value is None:
                if retry:
                    yield self.sleep(self.update_interval)  # prevent 429s

                try:
                    value = yield self.get_redis_value(name)
                    retry = value is None
                except self._http_errors as err:
                    self.logger.error('Job `%s` encountered error while '
                                      'summarizing %s: %s',
                                      self.job_id, name, err)
                    retry = True

            setattr(self, name, value)  # save the valid value to self

        defer.returnValue(True)  # "return" the value

    @defer.inlineCallbacks
    def expire(self):
        # build the expire API request
        host = '{}/api/redis/expire'.format(self.host)
        payload = {'hash': self.job_id, 'expireIn': self.expire_time}

        retrying = True  # retry  loop to prevent stackoverflow
        while retrying:

            try:
                request = treq.post(host, json=payload, headers=self.headers)
                response = yield request  # Wait for the deferred request
            except self._http_errors as err:
                self.logger.error('Job `%s` encountered error while trying to '
                                  'calling expire: %s', self.job_id, err)
                yield self.sleep(self.update_interval)
                continue  # return to top of retry loop

            try:
                self._log_http_response(response)
                json_content = yield response.json()  # parse the JSON data
            except (json.decoder.JSONDecodeError, AttributeError) as err:
                self.logger.error('Job `%s` failed to parse JSON data from the'
                                  ' request: %s', self.job_id, err)
                yield self.sleep(self.update_interval)
                continue  # return to top of retry loop

            value = json_content.get('value')

            if int(value) == 1:
                self.logger.info('Job `%s` will expire in %s seconds.',
                                 self.job_id, self.expire_time)
            else:
                self.logger.warning('Unexpected response from '
                                    '`EXPIRE %s`: `%s`', self.job_id, value)

            retrying = False  # success

        defer.returnValue(value)  # "return" the value

    @defer.inlineCallbacks
    def restart(self, delay=0):
        if not self.failed:
            self.logger.warning('Job `%s` was restarted but is not failed.',
                                self.job_id)

        self.failed = False  # reset failure mode to prevent further restarts

        if delay:
            yield self.sleep(delay)

        self.logger.info('Restarting failed job `%s`.', self.job_id)

        if self.job_id is None:  # never got started in the first place
            yield self.start()

        elif self.is_done:  # no need to monitor, skip straight to summarize
            yield self.summarize()

        else:  # job has begun but was not finished, monitor status
            yield self.monitor()

    @defer.inlineCallbacks
    def start(self, delay=0):

        if delay:
            yield self.sleep(delay) # delay the start if required

        try:
            self.job_id = yield self.create()

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
                self.logger.info('Job `%s` has final status `%s` and was '
                                 'completed in %s seconds. Download at `%s`.',
                                 self.job_id, self.status,
                                 diff.total_seconds(), self.output_url)

            yield self.sleep(self.update_interval)
            value = yield self.expire()

            defer.returnValue(value)

        except Exception as err:
            self.failed = True
            self.logger.error('Job `%s` encountered unexpected error in '
                              'job.start(): %s', self.job_id, err)
            defer.returnValue(False)
