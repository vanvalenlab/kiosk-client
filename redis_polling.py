import os
import sys
import time
import pickle
import logging
import redis

def add_keys_to_zip_results(redis_database, zip_results):
    zip_keys = redis_database.keys('predict_zip*')
    for zip_key in zip_keys:
        if zip_key not in zip_results:
            zip_results[zip_key] = {}
    return zip_results

def gather_redis_data(expected_zip_keys, pickle_file_name, rp_logger):
    # read in environmental variables
    redis_host = os.environ['REDIS_MASTER_SERVICE_HOST']
    redis_port = os.environ['REDIS_MASTER_SERVICE_PORT']

    # connect to Redis database
    r = redis.Redis(host=redis_host, port=redis_port, db=0)

    # zip_results will contain information about entries to the Redis database
    zip_results = {}
    zip_results = add_keys_to_zip_results(r, zip_results)

    # Check for updates to zip_files in Redis.
    # Ultimately, we just want an "timestamp_upload" and an "timestamp_output"
    # for each zip file in the database.
    all_done = 0
    while all_done == 0:
        all_done = 1
        for zip_file in zip_results.keys():
            if (b'timestamp_upload' not in zip_results[zip_file].keys()) or \
                    (b'timestamp_output' not in zip_results[zip_file].keys()):
                all_done = 0
                zip_file_info = r.hgetall(zip_file)
                if (b'timestamp_upload' not in zip_results[zip_file].keys()) \
                        and (b'timestamp_upload' in zip_file_info.keys()):
                    zip_results[zip_file][b'timestamp_upload'] = \
                            zip_file_info[b'timestamp_upload']
                    rp_logger.debug("Wrote upload timestamp for " + 
                            str(zip_file) + ".")
                if (b'timestamp_output' not in zip_results[zip_file].keys()) \
                        and (b'timestamp_output' in zip_file_info.keys()):
                    zip_results[zip_file][b'timestamp_output'] = \
                            zip_file_info[b'timestamp_output']
                    rp_logger.debug("Wrote output timestamp for " + 
                            str(zip_file) + ".")
        if len(zip_results) < expected_zip_keys:
            all_done = 0
            zip_results = add_keys_to_zip_results(r, zip_results)
        if all_done == 0:
            time.sleep(5)

    # Write everything to a file.
    with open(pickle_file_name,'wb') as zip_summary_file:
        pickle.dump(zip_results, zip_summary_file)
    print("Whoa, all fields have been filled out and it has been written to " +
            "a file!")

def analyze_redis_data(pickle_file_name, output_file):
    # import data
    with open(pickle_file_name,'rb') as zip_summary_file:
        zip_results = pickle.load(zip_summary_file)

    # organize data
    upload_times = []
    for zip_record in zip_results:
        upload_times.append(float(zip_results[zip_record][b'timestamp_upload']))
    beginning_of_upload = min(upload_times)
    end_of_upload = max(upload_times)
    upload_time = end_of_upload - beginning_of_upload
    processing_times = []
    for zip_record in zip_results:
        processing_times.append(float(zip_results[zip_record][b'timestamp_output']))
    end_of_processing = max(processing_times)
    processing_time = end_of_processing - beginning_of_upload
    # convert from milliseconds to minutes
    upload_time_minutes = (upload_time / 1000) / 60
    processing_time_minutes = (processing_time / 1000) / 60

    # report data
    report_data(output_file, upload_time_minutes, processing_time_minutes, 
                beginning_of_upload, end_of_upload, end_of_processing)

def report_data(output_file, upload_time_minutes, processing_time_minutes,
                beginning_of_upload, end_of_upload, end_of_processing):
    with open(output_file, 'a') as appendices:
        # first, record to file
        print("Data upload began (approximately) at " +
                str(beginning_of_upload), file=appendices)
        print("Data upload ended at " + str(end_of_upload), file=appendices)
        print("Data upload took, in total " + str(upload_time_minutes) + 
                " minutes.", file=appendices)
        print("", file=appendices)
        print("Data processing began at " + str(beginning_of_upload), 
                file=appendices)
        print("Data processing ended at " + str(end_of_processing), 
                file=appendices)
        print("Data processing took, in total " + 
                str(processing_time_minutes) + " minutes.", file=appendices)
        # then, record to stdout
        print("")
        print("Data upload took, in total " + str(upload_time_minutes) + 
                " minutes.")
        print("Data processing took, in total " + 
                str(processing_time_minutes) + " minutes.")
        print("Data analysis analyzed.")

def main(expected_zip_keys, output_file):
    # Logging
    rp_logger = logging.getLogger('redis_polling')
    rp_logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler('redis_polling.log')
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    rp_logger.addHandler(fh)

    pickle_file_name = 'zip_file_summary.pkl'
    gather_redis_data(expected_zip_keys, pickle_file_name, rp_logger)
    analyze_redis_data(pickle_file_name, output_file)

if __name__=='__main__':

    expected_zip_keys = int(sys.argv[1])
    output_file = str(sys.argv[2])
    main(expected_zip_keys, output_file)
