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
import time
import timeit
import logging
import logging.handlers
import multiprocessing
import argparse

from batching import settings
from batching.jobs import create_jobs_multi
from batching.jobs import get_completed_jobs_multi
from batching.jobs import expire_job_multi


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

    parser.add_argument('--pre', default='',
                        help='Name of pre-processing function, applied to the'
                             ' data before being passed to the model.')

    parser.add_argument('--post', default='watershed',
                        help='Name of post-processing function, applied to the'
                             ' output of the model.')

    return parser


def main():
    # create the request objects
    logger = logging.getLogger('benchmark')
    _ = timeit.default_timer()

    all_jobs = []
    model_name, model_version = ARGS.model.split(':')
    for _ in range(ARGS.count):
        all_jobs.append({
            'uploadedName': os.path.join(settings.UPLOAD_PREFIX, ARGS.file),
            'modelName': model_name,
            'modelVersion': model_version,
            'imageName': ARGS.file,
            'postprocessFunction':  ARGS.post,
            'preprocessFunction':  ARGS.pre,
        })

    logger.info('Created JSON payloads for %s jobs in %s seconds.',
                len(all_jobs), timeit.default_timer() - _)

    all_job_ids = create_jobs_multi(POOL, all_jobs, settings.MAX_JOBS)

    # monitor job_ids until they all have a `done` or `failed` status.
    _ = timeit.default_timer()
    completed_hashes = {}
    remaining_job_ids = copy.copy(all_job_ids)
    while len(completed_hashes) != len(all_jobs):
        try:
            new_hashes = get_completed_jobs_multi(
                POOL, remaining_job_ids, settings.MAX_JOBS)

            # update the `completed_hashes` with results newly completed jobs
            completed_hashes.update(new_hashes)
            # update remaining job ids, which are chunked next loop
            remaining_job_ids = list(set(remaining_job_ids) - set(new_hashes.keys()))

            logger.info('Found %s newly completed jobs. '
                        '%s of %s jobs are complete. '
                        'Sleeping for %s seconds.',
                        len(new_hashes), len(completed_hashes),
                        len(all_job_ids), settings.BACKOFF)

            if len(completed_hashes) != len(all_jobs):
                time.sleep(settings.BACKOFF)
        except Exception as err:
            logger.error('Encountered %s: %s', type(err).__name__, err)

    logger.info('All %s jobs are completed in %s seconds.',
                len(completed_hashes), timeit.default_timer() - _)

    # expire all the keys we added.
    all_expired = expire_job_multi(POOL, all_job_ids)

    logger.info('%s of %s jobs will expire in %s seconds.',
                sum(all_expired), len(all_job_ids), settings.EXPIRE_TIME)

    # analyze results
    logger.info('Benchmarking completed in %s seconds.',
                timeit.default_timer() - _)


if __name__ == '__main__':
    initialize_logger()

    # process the input
    ARGS = get_arg_parser().parse_args()

    # declare shared pool before calling main()
    # so each process has the same context
    POOL = multiprocessing.Pool()

    main()
