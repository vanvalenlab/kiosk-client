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
import timeit

import dateutil.parser
import treq
from twisted.internet import defer, reactor


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

        self.headers = {'Content-Type': ['application/json']}
        self.status = None
        self.job_id = None
        self.created_at = None
        self.finished_at = None
        self.output_url = None
        self._finished_statuses = {'done', 'failed'}

    @property
    def is_done(self):
        return self.status in self._finished_statuses

    @property
    def is_summarized(self):
        summaries = (self.created_at, self.finished_at, self.output_url)
        is_summarized = all(x is not None for x in summaries)
        return is_summarized and self.is_done

    def delayed(self, args, cb):
        # pylint: disable=E1101
        return reactor.callLater(self.update_interval, cb, args)

    def parse_json_response(self, response):
        L = self.logger.debug if response.code == 200 else self.logger.warning
        L('%s %s - %s %s',
          response.request.method.decode(),
          response.request.absoluteURI.decode(),
          response.code, response.phrase.decode())

        if response.code != 200:
            d = defer.Deferred()
            d.addErrback(self.log_error, response)
            return d

        return treq.json_content(response)

    def get_redis_value(self, field):
        host = '{}/api/redis'.format(self.host)
        body = json.dumps({'hash': self.job_id, 'key': field}).encode('ascii')
        d = treq.post(host, body, headers=self.headers)
        d.addCallback(self.parse_json_response)
        return d

    def handle_expire(self, json_response):
        value = json_response.get('value')
        try:
            if int(value):
                self.logger.info('Job `%s` will expire with a return value '
                                 'of `%s`.', self.job_id, value)
            else:
                self.logger.warning('Job `%s` failed to expire with a return '
                                    'value of `%s`', self.job_id, value)
        except Exception as err:
            self.logger.error('Encountered %s while trying to parse expire '
                              'JSON response: %s', err, json_response)

    def expire(self):
        host = '{}/api/expire'.format(self.host)
        payload = {'hash': self.job_id, 'expireIn': self.expire_time}
        body = json.dumps(payload).encode('ascii')
        d = treq.post(host, body, headers=self.headers)
        d.addCallback(self.parse_json_response)
        d.addCallback(self.handle_expire)
        return d

    def summarize(self, response=None, name=None):
        attributes = ['created_at', 'finished_at', 'output_url']
        if response is None:  # the first time `summarize` is called
            d = self.get_redis_value(attributes[0])
            d.addCallback(self.summarize, attributes[0])
            return d

        index = attributes.index(name)

        # update the property
        setattr(self, name, response.get('value'))
        # If the property is still None, try updating it again
        if getattr(self, name) is None and self.status != 'failed':
            self.logger.info('Job `%s` has null value for %s, retrying',
                             self.job_id, name)
            d = self.get_redis_value(name)
            d.addCallback(self.delayed, name, self.summarize)
            return d

        # move on to the next property to update
        if index < len(attributes) - 1:
            d = self.get_redis_value(attributes[index + 1])
            d.addCallback(self.summarize, attributes[index + 1])
            return d

        if self.status == 'done':
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

        # all summary data fetched, expire the key
        d = self.expire()
        d.addCallback(self.handle_expire)
        return d


    def monitor(self, json_response):
        # First monitor call will be from create response
        if self.job_id is None:
            self.job_id = json_response.get('hash')
            self.logger.info('Job created with hash `%s`', self.job_id)

        status = json_response.get('value')
        if self.status != status:
            self.status = status
            self.logger.info('Hash `%s` has new status `%s`',
                             self.job_id, self.status)

        if self.is_done:
            self.logger.info('Hash `%s` is finished', self.job_id)
            return self.summarize()

        d = self.get_redis_value('status')
        d.addCallback(self.delayed, self.monitor)
        return d

    def log_error(self, failure):
        self.logger.error(failure)

    def create(self):
        job_data = {
            'modelName': self.model_name,
            'modelVersion': self.model_version,
            'preprocessFunction': self.preprocess,
            'postprocessFunction': self.postprocess,
            'imageName': self.filepath,
            'uploadedName': os.path.join(self.upload_prefix, self.filepath),
        }
        host = '{}/api/predict'.format(self.host)
        body = json.dumps(job_data).encode('ascii')
        d = treq.post(host, body, headers=self.headers)
        d.addCallback(self.parse_json_response)
        d.addCallback(self.monitor)
        d.addErrback(self.log_error)
        return d
