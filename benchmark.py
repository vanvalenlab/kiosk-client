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
import signal
import logging
import logging.handlers
import multiprocessing
import argparse

import requests


class GracefulDeath:
    """Catch signals to allow graceful shutdown.

    Adapted from: https://stackoverflow.com/questions/18499497
    """

    def __init__(self):
        self.signum = None
        self.kill_now = False
        self.logger = logging.getLogger(str(self.__class__.__name__))
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)

    def handle_signal(self, signum, frame):  # pylint: disable=unused-argument
        self.signum = signum
        self.kill_now = True
        self.logger.debug('Received signal `%s` and frame `%s`', signum, frame)


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

    parser.add_argument('-x', '--expire-time', default=600, type=int,
                        help='Time in seconds to expire the completed jobs.')

    parser.add_argument('-r', '--retries', default=3, type=int,
                        help='Number of times to retry an HTTP ConnectionError')

    parser.add_argument('--retry-backoff', default=1, type=int,
                        help='Time to wait between HTTP retries')

    return parser


def chunk(lst, chunk_size):
    """Break a single list into several lists of length `chunk_size`"""
    chunked = []
    for i in range(0, len(lst), chunk_size):
        chunked.append((lst[i: i + chunk_size]))
    return chunked


def _retry_post_wrapper(endpoint, payload):
    """Wraps a HTTP POST request in a retry loop"""
    logger = logging.getLogger('benchmark._retry_post_wrapper')
    for i in range(1, RETRY_COUNT + 1):
        try:
            response = requests.post(endpoint, json=payload)
            break
        except requests.exceptions.ConnectionError as err:
            if i == RETRY_COUNT:
                raise err
            logger.warning('Encountered %s. Retrying %s/%s in %s seconds.',
                           err, i, RETRY_COUNT, RETRY_BACKOFF)
            time.sleep(RETRY_BACKOFF)
    return response


def create_jobs(jobs):
    logger = logging.getLogger('benchmark.create_jobs')
    start = timeit.default_timer()
    endpoint = HOST + '/api/batch/predict'

    response = _retry_post_wrapper(endpoint, {'jobs': jobs})

    job_ids = response.json()['hashes']
    if len(job_ids) != len(jobs):
        logger.warning('Tried to create %s jobs but only got back %s'
                       ' job IDs', len(jobs), len(job_ids))
    logger.debug('Created %s jobs in %s seconds.',
                 len(job_ids), timeit.default_timer() - start)
    return job_ids


def create_jobs_multi(jobs, chunk_size):
    """Use a multiprocessing.Pool to call many create_jobs in parallel"""
    logger = logging.getLogger('benchmark.create_jobs_multi')
    start = timeit.default_timer()

    # chunk the list of jobs and upload in parallel, then flatten the results
    job_ids = POOL.map(create_jobs, chunk(jobs, chunk_size))
    job_ids = [item for chunked in job_ids for item in chunked]

    logger.info('Uploaded %s jobs in %s seconds.',
                len(job_ids), timeit.default_timer() - start)

    return job_ids


def get_completed_jobs(job_ids):
    """Get the status of all job_ids"""
    logger = logging.getLogger('benchmark.get_completed_jobs')
    start = timeit.default_timer()

    completed_jobs = {}  # dict to track key and status

    endpoint = HOST + '/api/batch/status'
    response = _retry_post_wrapper(endpoint, {'hashes': job_ids})
    try:
        statuses = response.json()['statuses']
    except json.decoder.JSONDecodeError as err:
        self.logger.warning('Failed to parse JSON response with status %s',
                            response.status_code)
        statuses = []

    for job_id, status in zip(job_ids, statuses):
        if status in {'done', 'failed'}:
            completed_jobs[job_id] = {'status': status}

    logger.debug('Found %s completed jobs in %s seconds.',
                 len(completed_jobs), timeit.default_timer() - start)

    return completed_jobs


def get_completed_jobs_multi(job_ids, chunk_size):
    """Use a multiprocessing.Pool to call many get_completed_jobs in parallel"""
    logger = logging.getLogger('benchmark.get_completed_jobs_multi')
    start = timeit.default_timer()

    # chunk requests for status updates, then flatten results
    newly_completed = POOL.map(get_completed_jobs, chunk(job_ids, chunk_size))
    newly_completed = dict(j for i in newly_completed for j in i.items())

    logger.debug('Found %s completed jobs in %s seconds.',
                 len(newly_completed), timeit.default_timer() - start)

    return newly_completed


def expire_job(job_id):
    """Expire the Redis key `job_id` in `expire_seconds`"""
    logger = logging.getLogger('benchmark.expire_job')
    start = timeit.default_timer()

    endpoint = HOST + '/api/redis/expire'
    payload = {'hash': job_id, 'expireIn': EXPIRE_TIME}
    response = _retry_post_wrapper(endpoint, payload)

    if response.status_code != 200:
        logger.warning('Failed to expire job `%s`', job_id)
    else:
        logger.debug('Expired job %s in %s seconds.',
                     job_id, timeit.default_timer() - start)
    try:
        value = int(response.json()['value'])
    except json.decoder.JSONDecodeError:
        value = 0

    return value


def expire_job_multi(job_ids):
    """Use a multiprocessing.Pool to call many expire_job in parallel"""
    logger = logging.getLogger('benchmark.expire_job_multi')
    start = timeit.default_timer()

    # chunk requests for expiration
    expired = POOL.map(expire_job, job_ids)
    # expired = [item for chunked in expired for item in chunked]
    if not len(job_ids) == sum(expired):
        logger.warning('%s job not expired!', len(job_ids) - sum(expired))
    logger.info('%s jobs expired in %s seconds.',
                sum(expired), timeit.default_timer() - start)
    return expired


def main():
    # create the request objects
    logger = logging.getLogger('benchmark')
    _ = timeit.default_timer()

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

    logger.info('Created JSON payloads for %s jobs in %s seconds.',
                len(all_jobs), timeit.default_timer() - _)

    all_job_ids = create_jobs_multi(all_jobs, MAX_JOBS)

    # monitor job_ids until they all have a `done` or `failed` status.
    _ = timeit.default_timer()
    completed_hashes = {}
    remaining_job_ids = copy.copy(all_job_ids)
    while len(completed_hashes) != len(all_jobs):
        try:
            new_hashes = get_completed_jobs_multi(remaining_job_ids, MAX_JOBS)

            # update the `completed_hashes` with results newly completed jobs
            completed_hashes.update(new_hashes)
            # update remaining job ids, which are chunked next loop
            remaining_job_ids = list(set(remaining_job_ids) - set(new_hashes.keys()))

            logger.info('Found %s newly completed jobs. '
                        '%s of %s jobs are complete. '
                        'Sleeping for %s seconds.',
                        len(new_hashes), len(completed_hashes),
                        len(all_job_ids), ARGS.backoff)

            if len(completed_hashes) != len(all_jobs):
                time.sleep(ARGS.backoff)
        except Exception as err:
            logger.error('Encountered %s: %s', type(err).__name__, err)


        if SIGNAL_HANDLER.kill_now:
            break

    # all jobs are finished
    if SIGNAL_HANDLER.kill_now:
        logger.info('Gracefully exiting. Expiring hashes.')
    else:
        logger.info('All %s jobs are completed in %s seconds.',
                    len(completed_hashes), timeit.default_timer() - _)

    # expire all the keys we added.
    all_expired = expire_job_multi(all_job_ids)

    logger.info('%s of %s jobs will expire in %s seconds.',
                sum(all_expired), len(all_job_ids), EXPIRE_TIME)

    # analyze results
    logger.info('Benchmarking completed in %s seconds.',
                timeit.default_timer() - _)


if __name__ == '__main__':
    initialize_logger()

    SIGNAL_HANDLER = GracefulDeath()

    # process the input
    ARGS = get_arg_parser().parse_args()

    # set up shared constant values
    MAX_JOBS = 100  # maximum number of jobs per request
    EXPIRE_TIME = ARGS.expire_time
    RETRY_COUNT = ARGS.retries
    RETRY_BACKOFF = ARGS.retry_backoff

    if not ARGS.host.startswith('http://'):
        HOST = 'http://{}'.format(ARGS.host)
    else:
        HOST = ARGS.host

    # declare shared pool before calling main()
    # so each process has the same context
    POOL = multiprocessing.Pool()

    main()
