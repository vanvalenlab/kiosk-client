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

import json
import logging
import time
import timeit

import requests

from batch_api.settings import HOST, EXPIRE_TIME, HTTP_RETRY_BACKOFF, HTTP_RETRIES


def chunk(lst, chunk_size):
    """Break a single list into several lists of length `chunk_size`"""
    chunked = []
    for i in range(0, len(lst), chunk_size):
        chunked.append((lst[i: i + chunk_size]))
    return chunked


def _retry_post_wrapper(endpoint, payload):
    """Wraps a HTTP POST request in a retry loop"""
    logger = logging.getLogger('benchmark._retry_post_wrapper')
    for i in range(1, HTTP_RETRIES + 1):
        try:
            response = requests.post(endpoint, json=payload)
        except requests.exceptions.ConnectionError as err:
            if i == HTTP_RETRIES:
                raise err
            logger.warning('Encountered %s. Retrying %s/%s in %s seconds.',
                           err, i, HTTP_RETRIES, HTTP_RETRY_BACKOFF)
            time.sleep(HTTP_RETRY_BACKOFF)
            continue
        if response.status_code==504:
            logger.warning("504 error.")
            time.sleep(HTTP_RETRY_BACKOFF)
            continue
        elif response.status_code==200:
            break
    return response


def create_jobs(jobs):
    logger = logging.getLogger('benchmark.create_jobs')
    start = timeit.default_timer()
    endpoint = HOST + '/api/batch/predict'

    response = _retry_post_wrapper(endpoint, {'jobs': jobs})

    try:
        job_ids = response.json()['hashes']
    except (json.decoder.JSONDecodeError, KeyError) as err:
        logger.warning('Failed to create %s jobs with status %s: %s.',
                       len(jobs), response.status_code, err)
        job_ids = []
    if len(job_ids) != len(jobs):
        logger.warning('Tried to create %s jobs but only got back %s'
                       ' job IDs', len(jobs), len(job_ids))
    logger.debug('Created %s jobs in %s seconds.',
                 len(job_ids), timeit.default_timer() - start)
    return job_ids


def create_jobs_multi(pool, jobs, chunk_size):
    """Use a multiprocessing.Pool to call many create_jobs in parallel"""
    logger = logging.getLogger('benchmark.create_jobs_multi')
    start = timeit.default_timer()

    # chunk the list of jobs and upload in parallel, then flatten the results
    job_ids = pool.map(create_jobs, chunk(jobs, chunk_size))
    job_ids = [item for chunked in job_ids for item in chunked]

    logger.info('Created %s jobs in %s seconds.',
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
    except (json.decoder.JSONDecodeError, KeyError) as err:
        logger.warning('Failed to parse JSON response with status %s: %s.',
                       response.status_code, err)
        statuses = []

    for job_id, status in zip(job_ids, statuses):
        if status in {'done', 'failed'}:
            completed_jobs[job_id] = {'status': status}

    logger.debug('Found %s completed jobs in %s seconds.',
                 len(completed_jobs), timeit.default_timer() - start)

    return completed_jobs


def get_completed_jobs_multi(pool, job_ids, chunk_size):
    """Use a multiprocessing.Pool to call many get_completed_jobs in parallel"""
    logger = logging.getLogger('benchmark.get_completed_jobs_multi')
    start = timeit.default_timer()

    # chunk requests for status updates, then flatten results
    newly_completed = pool.map(get_completed_jobs, chunk(job_ids, chunk_size))
    newly_completed = dict(j for i in newly_completed for j in i.items())

    logger.debug('Found %s completed jobs in %s seconds.',
                 len(newly_completed), timeit.default_timer() - start)

    return newly_completed


def get_job_output_paths(job_ids):
    """Get the status of all job_ids"""
    logger = logging.getLogger('benchmark.get_completed_jobs')
    start = timeit.default_timer()

    completed_jobs = {}  # to match the job_id and the output path.

    endpoint = HOST + '/api/batch/redis'
    response = _retry_post_wrapper(endpoint, {
        'hashes': job_ids,
        'key': 'output_file_name'
    })

    try:
        outputs = response.json()['values']
    except (json.decoder.JSONDecodeError, KeyError) as err:
        logger.warning('Failed to parse JSON response with status %s: %s',
                       response.status_code, err)
        outputs = []

    for job_id, output in zip(job_ids, outputs):
        try:
            if output:
                completed_jobs[job_id] = {'output': output}
            else:
                logger.warning('`output_path` for job `%s` is `%s`',
                               job_id, output)
        except KeyError:
            logger.error('Job %s not found in completed jobs.', job_id)

    logger.debug('Found %s job output paths %s seconds.',
                 len(completed_jobs), timeit.default_timer() - start)

    return completed_jobs


def get_job_output_paths_multi(pool, job_ids, chunk_size):
    """Use a multiprocessing.Pool to call many get_job_output_paths in parallel"""
    logger = logging.getLogger('benchmark.get_job_output_paths_multi')
    start = timeit.default_timer()

    # chunk requests for output path, then flatten results
    outputs = pool.map(get_job_output_paths, chunk(job_ids, chunk_size))
    outputs = dict(j for i in outputs for j in i.items())
    logger.debug('Found %s job output paths in %s seconds.',
                 len(outputs), timeit.default_timer() - start)

    return outputs


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
    except (json.decoder.JSONDecodeError, KeyError) as err:
        logger.warning('Failed to expire job `%s`: %s', job_id, err)
        value = 0

    return value


def expire_job_multi(pool, job_ids):
    """Use a multiprocessing.Pool to call many expire_job in parallel"""
    logger = logging.getLogger('benchmark.expire_job_multi')
    start = timeit.default_timer()

    # chunk requests for expiration
    expired = pool.map(expire_job, job_ids)
    # expired = [item for chunked in expired for item in chunked]
    if not len(job_ids) == sum(expired):
        logger.warning('%s job not expired!', len(job_ids) - sum(expired))
    logger.info('%s jobs expired in %s seconds.',
                sum(expired), timeit.default_timer() - start)
    return expired
