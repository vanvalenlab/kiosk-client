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
"""Use the /batch/ API to create and monitor many image processing jobs"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import copy
import json
import time
import timeit
import logging
import logging.handlers
import argparse

import requests


def initialize_logger(debug_mode=True):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('[%(asctime)s]:[%(levelname)s]:[%(name)s]: %(message)s')
    console = logging.StreamHandler(stream=sys.stdout)
    console.setFormatter(formatter)

    fh = logging.handlers.RotatingFileHandler(
        filename='benchmark.log',
        maxBytes=10000000,
        backupCount=10)
    fh.setFormatter(formatter)

    if debug_mode:
        console.setLevel(logging.DEBUG)
    else:
        console.setLevel(logging.INFO)
    fh.setLevel(logging.DEBUG)

    logger.addHandler(console)
    logger.addHandler(fh)


def get_arg_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument('-f', '--file', required=True,
                        help='File to process in many duplicated jobs. '
                             '(Must exist in the cloud storage bucket.)')

    parser.add_argument('-m', '--model', required=True,
                        help='model name and version (e.g. inception:0).')

    parser.add_argument('-s', '--host', required=True,
                        help='Hostname of the Frontend/Batch API (e.g. '
                             'localhost:1234).')

    parser.add_argument('-c', '--count', default='1', type=int,
                        help='number of times to enter file as a job.')

    parser.add_argument('--upload-prefix', default='uploads',
                        help='Name of upload folder in storage bucket.')

    parser.add_argument('--pre', default='',
                        help='Name of pre-processing function, applied to the'
                             ' data before being passed to the model.')

    parser.add_argument('--post', default='watershed',
                        help='Name of post-processing function, applied to the'
                             ' output of the model.')

    parser.add_argument('-b', '--backoff', default=1, type=int,
                        help='Time to wait between HTTP requests.')

    return parser


if __name__ == '__main__':
    START = timeit.default_timer()
    initialize_logger()

    _logger = logging.getLogger('benchmark')

    # process the input
    ARGS = get_arg_parser().parse_args()

    if not ARGS.host.startswith('http://'):
        host = 'http://{}'.format(ARGS.host)
    else:
        host = ARGS.host

    # create the request objects
    start = timeit.default_timer()
    all_jobs = []
    model_name, model_version = ARGS.model.split(':')
    for _ in range(ARGS.count):
        all_jobs.append({
            'uploadedName': os.path.join(ARGS.upload_prefix, ARGS.file),
            'modelName': model_name,
            'modelVersion': model_version,
            'imageName': ARGS.file,
            'postprocessFunction':  ARGS.post,
            'preprocessFunction':  ARGS.pre,
        })
    _logger.info('Created JSON payloads for %s jobs in %s seconds.',
                 len(all_jobs), timeit.default_timer() - start)

    # create all of the jobs by sending API requests
    start = timeit.default_timer()
    all_job_ids = []
    max_jobs = 100
    for i in range(0, len(all_jobs), max_jobs):
        payload = {'jobs': all_jobs[i: i + max_jobs]}
        response = requests.post(host + '/api/batch/predict', json=payload)
        all_job_ids.extend(response.json()['hashes'])
        # if there are are more job_ids to upload, sleep
        if all_jobs[i + max_jobs + 1:]:
            time.sleep(ARGS.backoff)

    _logger.debug('Got hashes: %s', all_job_ids)
    _logger.info('Uploaded %s jobs in %s seconds.',
                 len(all_job_ids), timeit.default_timer() - start)

    # monitor job_ids until they all have a `done` or `failed` status.
    start = timeit.default_timer()
    completed_hashes = {}
    remaining_job_ids = copy.copy(all_job_ids)
    while len(completed_hashes) != len(all_jobs):
        # using temp dict for easier set differences at the end of the loop
        newly_completed_hashes = {}

        for i in range(0, len(remaining_job_ids), max_jobs):
            job_ids = remaining_job_ids[i: i + max_jobs]

            payload = {'hashes': job_ids}

            response = requests.post(host + '/api/batch/status', json=payload)
            statuses = response.json()['statuses']

            time.sleep(ARGS.backoff)

            for job_id, status in zip(job_ids, statuses):
                if status in {'done', 'failed'}:
                    newly_completed_hashes[job_id] = {'status': status}

            _logger.info('Jobs completed: %s',
                         json.dumps(newly_completed_hashes, indent=4))

        completed_hashes.update(newly_completed_hashes)
        remaining_job_ids = list(set(remaining_job_ids) - set(newly_completed_hashes.keys()))

    _logger.info('All %s jobs are completed in %s seconds.',
                 len(completed_hashes), timeit.default_timer() - start)

    # all jobs are finished, analyze results

    _logger.info('Benchmarking completed in %s seconds.',
                 timeit.default_timer() - START)
