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
        self.refresh_rate = int(kwargs.get('refresh_rate', 2))
        self.status_update_interval = kwargs.get('status_update_interval', 10)
        self.start_delay = kwargs.get('start_delay', .1)
        self.headers = {'Content-Type': ['application/json']}
        self.started_at = None

    def make_job(self, filepath):
        return Job(filepath=filepath,
                   host=self.host,
                   model_name=self.model_name,
                   model_version=self.model_version,
                   postprocess=self.postprocess,
                   status_update_interval=self.status_update_interval,
                   upload_prefix=self.upload_prefix)

    def start_jobs(self, job_index=0):
        if job_index == 0:
            self.logger.info('Creating %s jobs', len(self.all_jobs))

        if job_index < len(self.all_jobs):
            job = self.all_jobs[job_index]
            job.create()
            return reactor.callLater(self.start_delay, self.start_jobs, job_index + 1)

        self.logger.info('All %s jobs created', len(self.all_jobs))
        return reactor.callLater(self.start_delay, self.check_benchmarking_status)

    def benchmark(self, filepath, count):
        self.started_at = timeit.default_timer()
        self.logger.info('Benchmarking %s jobs of file `%s`', count, filepath)

        for _ in range(count):
            job = self.make_job(filepath)
            self.all_jobs.append(job)

        return reactor.callLater(self.start_delay, self.start_jobs, 0)

    def check_benchmarking_status(self):
        complete = sum(j.is_done for j in self.all_jobs)
        self.logger.info('%s of %s jobs complete', complete, len(self.all_jobs))

        if complete == len(self.all_jobs):
            return reactor.callLater(self.refresh_rate, self.summarize)

        return reactor.callLater(self.refresh_rate, self.check_benchmarking_status)

    def summarize(self):
        self.logger.info('Finished %s jobs in %s seconds',
                         len(self.all_jobs),
                         timeit.default_timer() - self.started_at)
        statuses = {}
        for j in self.all_jobs:
            if j.status not in statuses:
                statuses[j.status] = 1
            else:
                statuses[j.status] += 1

        for k, v in statuses.items():
            self.logger.info('%s = %s', k, v)

        reactor.stop()
