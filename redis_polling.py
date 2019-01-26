import os
import time
import pickle
import redis

def main():
    # read in environmental variables
    redis_host = os.environ['REDIS_MASTER_SERVICE_HOST']
    redis_port = os.environ['REDIS_MASTER_SERVICE_PORT']

    r = redis.Redis(host=redis_host, port=redis_port, db=0)

    zip_results = {}
    zip_keys = r.keys('predict_zip*')

    for zip_key in zip_keys:
        zip_results[zip_key] = {}

    # check for updates to zip_files in Redis
    # ultimately, we just want an "timestamp_upload" and an "timestamp_output"
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
                if (b'timestamp_output' not in zip_results[zip_file].keys()) \
                        and (b'timestamp_output' in zip_file_info.keys()):
                    zip_results[zip_file][b'timestamp_output'] = \
                            zip_file_info[b'timestamp_output']
            time.sleep(10)

    # Write everything to a file.
    with open('zip_file_summary.pkl','wb') as zip_summary_file:
        pickle.dump(zip_results, zip_summary_file)
    print("Whoa, all fields have been filled out and it has been written to " +
            "a file!")

if __name__=='__main__':
    main()
