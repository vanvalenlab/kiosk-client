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

import argparse
import copy
import json
import logging
import logging.handlers
import multiprocessing
import os
import time
import timeit
import sys

from batching import settings
from batching import storage
from batching.jobs import create_jobs_multi
from batching.jobs import get_completed_jobs_multi
from batching.jobs import expire_job_multi
from batching.utils import iter_image_files


def initialize_logger(debug_mode=True):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('[%(asctime)s]:[%(levelname)s]:[%(name)s]: %(message)s')
    console = logging.StreamHandler(stream=sys.stdout)
    console.setFormatter(formatter)

    fh = logging.handlers.RotatingFileHandler(
        filename='batch_process.log',
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
                        help='Path to file/directory to upload and process.')

    parser.add_argument('-s', '--host', required=True,
                        help='Hostname of the Frontend/Batch API (e.g. '
                             'localhost:1234).')

    parser.add_argument('-m', '--model', required=True,
                        help='model name and version (e.g. inception:0).')

    parser.add_argument('--pre', default='',
                        help='Name of pre-processing function, applied to the'
                             ' data before being passed to the model.')

    parser.add_argument('--post', default='watershed',
                        help='Name of post-processing function, applied to the'
                             ' output of the model.')

    return parser


def prepare_jobs(filename, model, pre='', post=''):
    logger = logging.getLogger('benchmark.prepare_jobs')
    start = timeit.default_timer()
    storage_client = storage.get_client(settings.CLOUD_PROVIDER)
    model_name, model_version = model.split(':')

    all_jobs = []
    for f in iter_image_files(filename):
        # upload file
        relpath = os.path.relpath(f, filename)
        subdir = os.path.dirname(relpath)

        uploaded_name, _ = storage_client.upload(f, subdir)

        job = {
            'uploadedName': uploaded_name,
            'modelName': model_name,
            'modelVersion': model_version,
            'imageName': relpath,
            'postprocessFunction':  post,
            'preprocessFunction':  pre,
        }
        all_jobs.append(job)

    logger.info('Uploaded %s files and created JSON payloads in %s seconds.',
                len(all_jobs), timeit.default_timer() - start)
    logger.debug('JSON Payload: %s', json.dumps(all_jobs, indent=4))
    return all_jobs


def main():
    start = timeit.default_timer()
    logger = logging.getLogger('benchmark')
    pool = multiprocessing.Pool()  # Create the shared pool

    # create the request objects
    all_jobs = prepare_jobs(ARGS.file, ARGS.model, ARGS.pre, ARGS.post)

    # send the requests to the batch create API
    all_job_ids = create_jobs_multi(pool, all_jobs, settings.MAX_JOBS)

    # monitor job_ids until they all have a `done` or `failed` status.
    completed_hashes = {}
    remaining_job_ids = copy.copy(all_job_ids)
    while len(completed_hashes) != len(all_jobs):
        try:
            new_hashes = get_completed_jobs_multi(
                pool, remaining_job_ids, settings.MAX_JOBS)

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
                len(completed_hashes), timeit.default_timer() - start)

    # expire all the keys we added.
    all_expired = expire_job_multi(pool, all_job_ids)

    logger.info('%s of %s jobs will expire in %s seconds.',
                sum(all_expired), len(all_job_ids), settings.EXPIRE_TIME)

    # analyze results
    logger.info('Benchmarking completed in %s seconds.',
                timeit.default_timer() - start)


if __name__ == '__main__':
    initialize_logger()

    # process the input
    ARGS = get_arg_parser().parse_args()

    # declare shared pool before calling main()
    # so each process has the same context

    main()
