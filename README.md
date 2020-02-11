# kiosk-benchmarking

[![Build Status](https://travis-ci.com/vanvalenlab/kiosk-benchmarking.svg?branch=master)](https://travis-ci.com/vanvalenlab/kiosk-benchmarking)
[![Coverage Status](https://coveralls.io/repos/github/vanvalenlab/kiosk-benchmarking/badge.svg?branch=master)](https://coveralls.io/github/vanvalenlab/kiosk-benchmarking?branch=master)

`kiosk-benchmarking` is tool for interacting with the [Kiosk](https://github.com/vanvalenlab/kiosk) in order to create and monitor deep learning image processing jobs. It uses the asynchronous HTTP client [treq](https://github.com/twisted/treq) and the [Kiosk-Frontend API](https://github.com/vanvalenlab/kiosk-frontend) to create and monitor many jobs at once. Once all jobs are completed, [costs are estimated](./docs/cost_computation_notes.md) by using the cluster's [Grafana API](https://grafana.com/docs/http_api/). An output file is then generated with statistics on each job's performance and resulting output files.

## Getting started

First, clone the git repository and install the required dependencies.

```bash
# clone the repository
git clone https://github.com/vanvalenlab/kiosk-benchmarking.git

# move into the new repository directory
cd kiosk-benchmarking

# install the requirements
pip install -r requirements.txt
```

## Usage Examples

Benchmarking can be run in 2 different modes: `benchmark` and `upload`.

### Benchmark Mode

```bash
# from within the kiosk-benchmarking repository
python benchmarking benchmark --file image_to_process.png  --count 100
```

`benchmark` mode will create a new job every `START_DELAY` seconds up to `COUNT` jobs. Each job is monitored and when all jobs are finished, the stats are summarized, cost is estimated, and the output file is uploaded to the `STORAGE_BUCKET`.  The `FILE` is expected to be inside the bucket in the `UPLOAD_PREFIX` directory (`/uploads` by default) and can be either a single image or a zip file of images. The upload time can be simulated by changing the start delay.

### Upload Mode

```bash
# from within the kiosk-benchmarking repository
python benchmarking upload --file local_file_to_upload.png
```

`upload` mode is designed for batch processing local files.  The `FILE` path is checked for any zip or image files, each is uploaded and monitored.  When all jobs are finished, the stats are summarized, cost is estimated, and the output file is uploaded to the `STORAGE_BUCKET`.

## Environmental Variables

Each job can be configured using environmental variables in a `.env` file.

| Name                 | Description                    | Required |
| :------------------- | :----------------------------- | :------- |
| `API_HOST`             | Hostname and port for the *kiosk-frontend* API server | True |
| `STORAGE_BUCKET`       | Cloud storage bucket address (e.g. *gs://bucket-name*) | True |
| `MODEL`                | Name and version of the model hosted by TensorFlow Serving (e.g. *modelname:0*) | True |
| `PREPROCESS`           | Name of the preprocessing function to use (e.g. *normalize*) | False |
| `POSTPROCESS`          | Name of the postprocessing function to use (e.g. *watershed*). | False |
| `UPDATE_INTERVAL`      | Number of seconds a job should wait between sending status update requests to the server. (defaults to 10) | False |
| `START_DELAY`          | Number of seconds between submitting each new job. This can be configured to simulate upload latency. (defaults to .05) | False |
| `MANAGER_REFRESH_RATE` | Number of seconds between completed job updates. (defaults to 10) | False |
| `EXPIRE_TIME`          | Completed jobs are expired after this many seconds. (defaults to 600) | False |
| `CONCURRENT_REQUESTS_PER_HOST` | Limit number of simultaneous requests to the server. (default 64) | False |
| `UPLOAD_PREFIX` | Prefix of upload directory in the cloud storage bucket. (default `/uploads`) | False |
| `GRAFANA_HOST`         | Hostname of the Grafana server.  | True |
| `GRAFANA_USER`         | Username for the Grafana server. | True |
| `GRAFANA_PASSWORD`     | Password for the Grafana server. | True |

#### Google Cloud Authentication

When uploading to Google Cloud, you will need to [authenticate](https://cloud.google.com/docs/authentication/production) using the `GOOGLE_APPLICATION_CREDENTIALS` set to your service account JSON file.
