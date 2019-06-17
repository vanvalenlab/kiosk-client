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
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import time
import pickle
import logging
import argparse

import redis
import dateutil.parser


class RedisPoller():
    def __init__(self, args):
        # assign parsed command line args
        self.upload_method = args.upload_method
        self.expected_zip_keys = args.total_keys
        self.output_file = args.output_file

        # define necessary variables
        self.pickle_file_name = 'zip_file_summary.pkl'
        self.relevant_entries = {}

        # connect to Redis database
        self.redis_connection = redis.StrictRedis(
            host=os.getenv('REDIS_HOST', 'redis-master'),
            port=os.getenv('REDIS_PORT', '6379'),
            db=0)

        # configure logging
        self._configure_logger()

    def _configure_logger(self):
        self._logger = logging.getLogger('redis-polling')
        self._logger.setLevel(logging.DEBUG)
        # Send logs to stdout so they can be read via Kubernetes.
        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        sh.setFormatter(formatter)
        self._logger.addHandler(sh)
        # Also send logs to a file for later inspection.
        fh = logging.FileHandler('redis-polling.log')
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        self._logger.addHandler(fh)

    def _redis_keys(self, search_string='*'):
        self._logger.info('Getting all Redis keys matching `%s`.',
                          search_string)
        while True:
            try:
                redis_keys = self.redis_connection.keys(search_string)
                break
            except (redis.exceptions.ConnectionError,
                    redis.exceptions.ResponseError) as err:
                # For some reason, we're unable to connect to Redis right now.
                # Keep trying until we can.
                self._logger.warning('Trouble connecting to Redis. Retrying.'
                                     '\n%s: %s', type(err).__name__, err)
                time.sleep(5)
        self._logger.info('Got all Redis keys matching `%s`.', search_string)
        return redis_keys

    def _redis_hgetall(self, key):
        while True:
            try:
                key_values = self.redis_connection.hgetall(key)
                break
            except (redis.exceptions.ConnectionError,
                    redis.exceptions.ResponseError) as err:
                # For some reason, we're unable to connect to Redis right now.
                # Keep trying until we can.
                self._logger.warning('Trouble connecting to Redis. Retrying.'
                                     '\n%s: %s', type(err).__name__, err)
                time.sleep(5)
        return key_values

    def _add_to_relevant_entries(self):
        if self.upload_method == 'web':
            redis_keys = self._redis_keys('predict_zip*')
        elif self.upload_method == 'direct':
            redis_keys = self._redis_keys('predict*directupload*')
        for new_key in redis_keys:
            if new_key not in self.relevant_entries:
                self.relevant_entries[new_key] = {}
        self._logger.info('Number of relevant Redis entries:%s ',
                          len(self.relevant_entries))

    def _gather_redis_data(self):
        # Start tracking any new relevant entries in the Redis database.
        self._add_to_relevant_entries()

        # Check for updates to relevant keys in Redis.
        # Ultimately, we just want a "timestamp_upload" and a
        # "timestamp_output" for each key in the database.
        all_done = False
        while not all_done:
            # log prettification
            self._logger.info('')
            # Assuming that all data is in relevant_entries.
            # (Probably a false assumption.)
            all_done = True
            # See whether all current entries have both pieces of data. If
            # either piece is missing from any entry, our database is
            # incomplete and we need to re-run the loop.
            incomplete_entries = 0
            start_key = b'created_at'
            end_key = b'finished_at'
            for entry in self.relevant_entries:
                values = self.relevant_entries[entry].keys()

                if start_key not in values or end_key not in values:
                    entry_info = self._redis_hgetall(entry)

                    if all_done:
                        # Log first entry which is incomplete at info level.
                        self._logger.info('Data incomplete for %s, and '
                                          'possibly others.', entry)
                        all_done = False
                    else:
                        # Log all other incomplete entries at debug level.
                        self._logger.debug('Data also incomplete for %s.',
                                           entry)

                    incomplete_entries += 1

                    for key in (start_key, end_key):
                        if key not in values and key in entry_info:
                            self.relevant_entries[entry][key] = entry_info[key]
                            self._logger.debug('Updated key `%s`: `%s` = `%s`',
                                               entry, key, entry_info[key])

            # Check to see that the database has enough entries. If there are
            # too few, then we'll need to gather more and then re-run the loop
            # to fill them in.
            self._logger.info('There are %s incomplete entries.',
                              incomplete_entries)

            if len(self.relevant_entries) < self.expected_zip_keys:
                all_done = False
                self._logger.info('Not enough entries in database yet. We only'
                                  ' have %s.', len(self.relevant_entries))
                self._add_to_relevant_entries()

            if not all_done:
                time.sleep(5)

        # The database is complete, so write everything to a file for a record.
        with open(self.pickle_file_name, 'wb') as summary_file:
            pickle.dump(self.relevant_entries, summary_file)

        self._logger.info('Whoa, all fields have been filled out and '
                          'everything has been written to %s!',
                          self.pickle_file_name)

    def _analyze_redis_data(self):
        # organize data
        start_key = b'created_at'
        end_key = b'finished_at'

        start_times = []
        finish_times = []

        for entry in self.relevant_entries:
            values = self.relevant_entries[entry]
            started = dateutil.parser.parse(values[start_key])
            finished = dateutil.parser.parse(values[end_key])

            start_times.append(started)
            finish_times.append(finished)

        first_ts = min(start_times)
        all_uploaded_ts = max(start_times)
        final_ts = max(finish_times)

        upload_time = (all_uploaded_ts - first_ts).total_seconds()
        total_time = (final_ts - first_ts).total_seconds()

        with open(self.output_file, 'a') as f:
            # first, record to file
            print('First redis key uploaded at %s' % first_ts, file=f)
            print('All redis keys uploaded at %s' % all_uploaded_ts, file=f)
            print('Redis keys were populated in %s minutes.' % \
                  str(upload_time / 60), file=f)
            print('', file=f)
            print('Data processing began at %s.' % first_ts, file=f)
            print('Data processing ended at %s.' % final_ts, file=f)
            print('Data processing took %s minutes.' % \
                  str(total_time / 60), file=f)

        # then, record to stdout
        self._logger.info('')
        self._logger.info('Successfully processed %s entries!')
        self._logger.info('Data upload took %s minutes.', upload_time / 60)
        self._logger.info('Data processing took %s minutes.', total_time / 60)
        self._logger.info('')
        self._logger.info('Done!')

    def watch_redis(self):
        # start gathering data
        self._gather_redis_data()
        self._analyze_redis_data()

if __name__ == '__main__':
    # parse command line args
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'upload_method',
        help='which method was used to upload the files?',
        choices=['web', 'direct'])
    parser.add_argument(
        'total_keys',
        help='how many files did we upload?',
        type=int)
    parser.add_argument('output_file', help='output file for results')
    args = parser.parse_args()

    # Create RedisPoller object and tell it to watch Redis.
    rp = RedisPoller(args)
    rp.watch_redis()
