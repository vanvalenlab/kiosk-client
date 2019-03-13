import os
import sys
import time
import pickle
import logging
import argparse
import redis
from redis import StrictRedis
from redis.exceptions import ConnectionError

class RedisPoller():
    def __init__(self, args):
        # assign parsed command line args
        self.upload_method = args.upload_method
        self.expected_zip_keys = args.total_keys
        self.output_file = args.output_file

        # read in environmental variables
        self.redis_host = os.getenv('REDIS_HOST', "redis-master")
        self.redis_port = os.getenv('REDIS_PORT', "6379")

        # define necessary variables
        self.pickle_file_name = 'zip_file_summary.pkl'
        self.relevant_entries = {}

        # connect to Redis database
        self.redis_connection = StrictRedis(host=self.redis_host,
                port=self.redis_port, db=0)

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

    def _redis_keys(self, search_string = "*"):
        self._logger.info("Getting all Redis keys matching \"" +
                search_string + "\".")
        while True:
            try:
                redis_keys = self.redis_connection.keys(search_string)
                break
            except ConnectionError as err:
                # For some reason, we're unable to connect to Redis right now.
                # Keep trying until we can.
                self._logger.warn("Trouble connecting to Redis. Retrying." +
                        "\n%s: %s", type(err).__name__, err)
                time.sleep(5)
        self._logger.info("Got all Redis keys matching \"" +
                search_string + "\".")
        return redis_keys

    def _redis_hgetall(self, key):
        while True:
            try:
                key_values = self.redis_connection.hgetall(key)
                break
            except ConnectionError as err:
                # For some reason, we're unable to connect to Redis right now.
                # Keep trying until we can.
                self._logger.warn("Trouble connecting to Redis. Retrying." +
                        "\n%s: %s", type(err).__name__, err)
                time.sleep(5)
        return key_values

    def _add_to_relevant_entries(self):
        if self.upload_method=="web":
            redis_keys = self._redis_keys('predict_zip*')
        elif self.upload_method=="direct":
            redis_keys = self._redis_keys('predict*directupload*')
        for new_key in redis_keys:
            if new_key not in self.relevant_entries:
                self.relevant_entries[new_key] = {}
        self._logger.info("Number of relevant Redis entries: " +
                str(len(self.relevant_entries)))

    def _gather_redis_data(self):
        # Start tracking any new relevant entries in the Redis database.
        self._add_to_relevant_entries()

        # Check for updates to relevant keys in Redis.
        # Ultimately, we just want a "timestamp_upload" and a
        # "timestamp_output" for each key in the database.
        all_done = False
        while not all_done:
            # log prettification
            self._logger.info("")
            # Assuming that all data is in relevant_entries.
            # (Probably a false assumption.)
            all_done = True
            # See whether all current entries have both pieces of data. If
            # either piece is missing from any entry, our database is
            # incomplete and we need to re-run the loop.
            incomplete_entries = 0
            for entry in self.relevant_entries.keys():
                if (b'timestamp_upload'
                        not in self.relevant_entries[entry].keys()) or \
                        (b'timestamp_output'
                                not in self.relevant_entries[entry].keys()):
                    if all_done:
                        # Log first entry which is incomplete at info level.
                        self._logger.info("Data incomplete for " + str(entry)
                                + ", and possibly others.")
                        all_done = False
                    else:
                        # Log all other incomplete entries at debug level.
                        self._logger.debug("Data also incomplete for " \
                                + str(entry) + ".")
                    incomplete_entries += 1
                    entry_info = self._redis_hgetall(entry)
                    if (b'timestamp_upload'
                            not in self.relevant_entries[entry].keys()) \
                            and (b'timestamp_upload' in entry_info.keys()):
                        self.relevant_entries[entry][b'timestamp_upload'] = \
                                entry_info[b'timestamp_upload']
                        self._logger.debug("Wrote upload timestamp for " +
                                str(entry) + ".")
                        self._logger.debug("Value is " +
                                str(entry_info[b'timestamp_upload']))
                    if (b'timestamp_output' not in
                            self.relevant_entries[entry].keys()) \
                            and (b'timestamp_output' in entry_info.keys()):
                        self.relevant_entries[entry][b'timestamp_output'] = \
                                entry_info[b'timestamp_output']
                        self._logger.debug("Wrote output timestamp for " +
                                str(entry) + ".")
                        self._logger.debug("Value is " +
                                str(entry_info[b'timestamp_output']))
            # Check to see that the database has enough entries. If there are
            # too few, then we'll need to gather more and then re-run the loop
            # to fill them in.
            self._logger.info("There are %s incomplete entries.",
                    incomplete_entries)
            if len(self.relevant_entries) < self.expected_zip_keys:
                all_done = False
                self._logger.info("Not enough entries in database yet. " +
                        "We only have %s.", len(self.relevant_entries))
                self._add_to_relevant_entries()
            if not all_done:
                time.sleep(5)

        # The database is complete, so write everything to a file for a record.
        with open(self.pickle_file_name,'wb') as summary_file:
            pickle.dump(self.relevant_entries, summary_file)
        self._logger.info("Whoa, all fields have been filled out and " +
                "everything has been written to " +
                self.pickle_file_name + "!")

    def _analyze_redis_data(self):
        # organize data
        upload_times = []
        for entry in self.relevant_entries:
            upload_time = float(
                    self.relevant_entries[entry][b'timestamp_upload'])
            upload_times.append(upload_time)
        beginning_of_upload = min(upload_times)
        end_of_upload = max(upload_times)
        upload_time = end_of_upload - beginning_of_upload
        processing_times = []
        for entry in self.relevant_entries:
            processing_time = float(
                    self.relevant_entries[entry][b'timestamp_output'])
            processing_times.append(processing_time)
        end_of_processing = max(processing_times)
        processing_time = end_of_processing - beginning_of_upload
        # convert from milliseconds to minutes
        upload_time_minutes = (upload_time / 1000) / 60
        processing_time_minutes = (processing_time / 1000) / 60

        # report data
        self._report_data(upload_time_minutes, processing_time_minutes,
                    beginning_of_upload, end_of_upload, end_of_processing)

    def _report_data(self, upload_time_minutes, processing_time_minutes,
                    beginning_of_upload, end_of_upload, end_of_processing):
        with open(self.output_file, 'a') as appendices:
            # first, record to file
            print("Data upload began (approximately) at " +
                    str(beginning_of_upload), file=appendices)
            print("Data upload ended at " + str(end_of_upload),
                    file=appendices)
            print("Data upload took, in total " + str(upload_time_minutes) +
                    " minutes.", file=appendices)
            print("", file=appendices)
            print("Data processing began at " + str(beginning_of_upload),
                    file=appendices)
            print("Data processing ended at " + str(end_of_processing),
                    file=appendices)
            print("Data processing took, in total " +
                    str(processing_time_minutes) + " minutes.",
                    file=appendices)
            # then, record to stdout
            self._logger.info("")
            self._logger.info("Data upload took, in total " +
                    str(upload_time_minutes) + " minutes.")
            self._logger.info("Data processing took, in total " +
                    str(processing_time_minutes) + " minutes.")
            self._logger.info("Data analysis analyzed.")

    def watch_redis(self):
        # start gathering data
        self._gather_redis_data()
        self._analyze_redis_data()

if __name__=='__main__':
    # parse command line args
    parser = argparse.ArgumentParser()
    parser.add_argument("upload_method",
            help="which method was used to upload the files?",
            choices=["web", "direct"])
    parser.add_argument("total_keys", help="how many files did we upload?",
            type=int)
    parser.add_argument("output_file", help="output file for results")
    args = parser.parse_args()

    # Create RedisPoller object and tell it to watch Redis.
    rp = RedisPoller(args)
    rp.watch_redis()
