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
"""Manager class used to create and manage jobs"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
import timeit

from twisted.internet import reactor

from batching.job import Job


class JobManager(object):

    def __init__(self, host, model_name, model_version, **kwargs):
        self.logger = logging.getLogger(str(self.__class__.__name__))
        self.all_jobs = []

        host = str(host)
        if not any(host.startswith(x) for x in ('http://', 'https://')):
            host = 'http://{}'.format(host)

        self.host = host
        self.model_name = model_name
        self.model_version = model_version

        self.preprocess = kwargs.get('preprocess', '')
        self.postprocess = kwargs.get('postprocess', '')
        self.upload_prefix = kwargs.get('upload_prefix', 'uploads')
        self.refresh_rate = int(kwargs.get('refresh_rate', 10))
        self.update_interval = kwargs.get('update_interval', 10)
        self.start_delay = kwargs.get('start_delay', 0)
        self.headers = {'Content-Type': ['application/json']}
        self.created_at = timeit.default_timer()

    def delay(self, delay_seconds, cb, *args, **kwargs):
        """Wrapper around `reactor.callLater`"""
        # pylint: disable=E1101
        return reactor.callLater(delay_seconds, cb, *args, **kwargs)

    def make_job(self, filepath, original_name=None):
        if not original_name:
            original_name = filepath
        return Job(filepath=filepath,
                   host=self.host,
                   model_name=self.model_name,
                   model_version=self.model_version,
                   postprocess=self.postprocess,
                   update_interval=self.update_interval,
                   upload_prefix=self.upload_prefix,
                   original_name=original_name)

    def check_job_status(self):
        complete = sum(j.is_done for j in self.all_jobs)
        self.logger.info('%s of %s jobs complete', complete, len(self.all_jobs))

        if complete == len(self.all_jobs):
            return self.delay(self.refresh_rate, self.summarize)

        return self.delay(self.refresh_rate, self.check_job_status)

    def summarize(self):
        self.logger.info('Finished %s jobs in %s seconds', len(self.all_jobs),
                         timeit.default_timer() - self.created_at)
        statuses = {}
        for j in self.all_jobs:
            if j.status not in statuses:
                statuses[j.status] = 1
            else:
                statuses[j.status] += 1

        for k, v in statuses.items():
            self.logger.info('%s = %s', k, v)

        reactor.stop()  # pylint: disable=E1101

    def run_job(self, *args, **kwargs):
        raise NotImplementedError


class BenchmarkingJobManager(JobManager):

    def run_job(self, filepath, count):  # pylint: disable=W0221
        self.logger.info('Benchmarking %s jobs of file `%s`', count, filepath)

        for _ in range(count):
            job = self.make_job(filepath)
            self.all_jobs.append(job)
            self.delay(self.start_delay, job.create)

        return self.delay(self.start_delay, self.check_job_status)

