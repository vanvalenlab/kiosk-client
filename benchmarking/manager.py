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

import json
import logging
import os
import timeit
import uuid

from twisted.internet import reactor
from google.cloud import storage as google_storage

from benchmarking.job import Job
from benchmarking.utils import iter_image_files
from benchmarking import settings


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
            return self.summarize()  # no need for a delay here

        return self.delay(self.refresh_rate, self.check_job_status)

    def summarize(self):
        self.logger.info('Finished %s jobs in %s seconds', len(self.all_jobs),
                         timeit.default_timer() - self.created_at)
        jsondata = [j.json() for j in self.all_jobs]

        output_filepath = os.path.join(
            settings.OUTPUT_DIR,
            '{}.json'.format(uuid.uuid4().hex))

        with open(output_filepath, 'w') as jsonfile:
            json.dump(jsondata, jsonfile, indent=4)

            self.logger.info('Wrote job data as JSON to %s', output_filepath)

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


class BatchProcessingJobManager(JobManager):

    def run_job(self, filepath):  # pylint: disable=W0221
        self.logger.info('Benchmarking all image/zip files in `%s`', filepath)

        storage_client = google_storage.Client()

        for f in iter_image_files(filepath):

            self.logger.debug('Uploading %s', f)
            _, ext = os.path.splitext(f)
            dest = '{}{}'.format(uuid.uuid4().hex, ext)

            bucket = storage_client.get_bucket(settings.GCLOUD_STORAGE_BUCKET)
            blob = bucket.blob(os.path.join(self.upload_prefix, dest))
            blob.upload_from_filename(f, predefined_acl='publicRead')

            # uploaded_name = 'output/a/mibi_nuclear_2.tif'
            job = self.make_job(dest, original_name=f)
            self.all_jobs.append(job)
            self.delay(self.start_delay, job.create)

        return self.delay(self.start_delay, self.check_job_status)
