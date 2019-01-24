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
    # ultimately, we just want an "upload_timestamp" and an "output_timestamp"
    all_done = 0
    while all_done == 0:
        all_done = 1
        for zip_file in zip_results.keys():
            if (b'upload_timestamp' not in zip_results[zip_file].keys()) or \
                    (b'output_timestamp' not in zip_results[zip_file].keys()):
                all_done = 0
                zip_file_info = r.hgetall(zip_file)
                if (b'upload_timestamp' not in zip_results[zip_file].keys()) \
                        and (b'upload_timestamp' in zip_file_info.keys()):
                    zip_results[zip_file][b'upload_timestamp'] = \
                            zip_file_info[b'upload_timestamp']
                if (b'output_timestamp' not in zip_results[zip_file].keys()) \
                        and (b'output_timestamp' in zip_file_info.keys()):
                    zip_results[zip_file][b'output_timestamp'] = \
                            zip_file_info[b'output_timestamp']
            time.sleep(10)

    # Write everything to a file.
    with open('zip_file_summary.pkl','wb') as zip_summary_file:
        pickle.dump(zip_results, zip_summary_file)
    print("Whoa, all fields have been filled out and it has been written to " +
            "a file!")

if __name__=='__main__':
    main()
