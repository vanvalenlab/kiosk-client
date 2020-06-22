# kiosk-client

[![Build Status](https://travis-ci.com/vanvalenlab/kiosk-client.svg?branch=master)](https://travis-ci.com/vanvalenlab/kiosk-client)
[![Coverage Status](https://coveralls.io/repos/github/vanvalenlab/kiosk-client/badge.svg?branch=master)](https://coveralls.io/github/vanvalenlab/kiosk-client?branch=master)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](/LICENSE)
[![PyPi](https://img.shields.io/pypi/v/kiosk_client.svg)](https://pypi.org/project/Kiosk-Client/)
[![Python Versions](https://img.shields.io/pypi/pyversions/kiosk_client.svg)](https://pypi.org/project/kiosk_client/)

`kiosk-client` is tool for interacting with the [DeepCell Kiosk](https://github.com/vanvalenlab/kiosk-console) in order to create and monitor deep learning image processing jobs. It uses the asynchronous HTTP client [treq](https://github.com/twisted/treq) and the [Kiosk-Frontend API](https://github.com/vanvalenlab/kiosk-frontend) to create and monitor many jobs at once. Once all jobs are completed, [costs are estimated](./docs/cost_computation_notes.md) by using the cluster's [Grafana API](https://grafana.com/docs/http_api/). An output file is then generated with statistics on each job's performance and resulting output files.

This repository is part of the [DeepCell Kiosk](https://github.com/vanvalenlab/kiosk-console). More information about the Kiosk project is available through [Read the Docs](https://deepcell-kiosk.readthedocs.io/en/master) and our [FAQ](http://www.deepcell.org/faq) page.

## Installation

### Install with `pip`

```bash
pip install kiosk_client
```

### Install from source

```bash
# clone the repository
git clone https://github.com/vanvalenlab/kiosk-client.git

# install the package
pip install kiosk-client
```

## Usage

The only thing necessary to use the CLI is the image file to process, the type of job, and the IP address or FQDN of the DeepCell Kiosk.

```bash
python -m kiosk_client path/to/image.png \
  --job-type segmentation \
  --host 123.456.789.012
```

It is also possible to override the default model and post-processing function for a given job type.

```bash
python -m kiosk_client path/to/image.png \
  --job-type segmentation \
  --host 123.456.789.012 \
  --model ModelName:0 \
  --post deep_watershed
```

### Benchmark Mode

The CLI can also be used to benchmark the cluster with high volume jobs.
It is a prerequisite that the the `FILE` exist in the `STORAGE_BUCKET` inside `UPLOAD_PREFIX` (e.g. `/uploads/image.png`).
There are also a number of other benchmarking options including `--upload-results` and `--calculate_cost`.
A new job is created every `START_DELAY` seconds up to `COUNT` jobs.
The upload time can be simulated by changing the start delay.

```bash
# from within the kiosk-client repository
python -m kiosk_client path/to/image.png \
  --job-type segmentation \
  --host 123.456.789.012 \
  --model ModelName:0 \
  --post deep_watershed \
  --start-delay 0.5 \
  --count 1000 \
  --calculate_cost \
  --upload-results
```

_It is easiest to run a benchmarking job from within the DeepCell Kiosk._

## Configuration

Each job can be configured using environmental variables in a `.env` file. Most of these environment variables can be overridden with command line options. Use `python benchmarking --help` for detailed list of options.

| Name | Description | Default Value |
| :--- | :--- | :--- |
| `JOB_TYPE` | **REQUIRED**: Name of job workflow. | `"segmentation"` |
| `API_HOST` | **REQUIRED**: Hostname and port for the *kiosk-frontend* API server. | `""` |
| `STORAGE_BUCKET` | Cloud storage bucket address (e.g. `"gs://bucket-name"`). Required if using `benchmark` mode and `upload-results`. | `""` |
| `MODEL` | Name and version of the model hosted by TensorFlow Serving (e.g. `"modelname:0"`). Overrides default model for the given `JOB_TYPE` | `"modelname:0"` |
| `SCALE` | Rescale data by this float value for model compatibility. | `1` |
| `LABEL` | Integer value of label type. | `""` |
| `PREPROCESS` | Name of the preprocessing function to use (e.g. `"normalize"`). | `""` |
| `POSTPROCESS` | Name of the postprocessing function to use (e.g. `"watershed"`). | `""` |
| `UPLOAD_PREFIX` | Prefix of upload directory in the cloud storage bucket. | `"/uploads"` |
| `UPDATE_INTERVAL` | Number of seconds a job should wait between sending status update requests to the server. | `10` |
| `START_DELAY` | Number of seconds between submitting each new job. This can be configured to simulate upload latency. | `0.05` |
| `MANAGER_REFRESH_RATE` | Number of seconds between completed job updates. | `10` |
| `EXPIRE_TIME` | Completed jobs are expired after this many seconds. | `3600` |
| `CONCURRENT_REQUESTS_PER_HOST` | Limit number of simultaneous requests to the server.  | `64` |
| `NUM_CYCLES` | Number of times to run the job. | `1` |
| `NUM_GPUS` | Number of GPUs used during the run. Used for logging. | `0` |
| `LOG_ENABLED` | Toggle for enabling/disabling logging. | `True` |
| `LOG_LEVEL` | Level of output for logging statements. | `"DEBUG"` |
| `LOG_FILE` | Filename of the log file. | `"benchmark.log"` |
| `GRAFANA_HOST` | Hostname of the Grafana server. | `"prometheus-operator-grafana"` |
| `GRAFANA_USER` | Username for the Grafana server. | `"admin"` |
| `GRAFANA_PASSWORD` | Password for the Grafana server. | `"prom-operator"` |


#### Google Cloud Authentication

When uploading to Google Cloud, you will need to [authenticate](https://cloud.google.com/docs/authentication/production) using the `GOOGLE_APPLICATION_CREDENTIALS` set to your service account JSON file.

## Contribute

We welcome contributions to the [kiosk-console](https://github.com/vanvalenlab/kiosk-console) and its associated projects. If you are interested, please refer to our [Developer Documentation](https://deepcell-kiosk.readthedocs.io/en/master/DEVELOPER.html), [Code of Conduct](https://github.com/vanvalenlab/kiosk-console/blob/master/CODE_OF_CONDUCT.md) and [Contributing Guidelines](https://github.com/vanvalenlab/kiosk-console/blob/master/CONTRIBUTING.md).

## License

This software is license under a modified Apache-2.0 license. See [LICENSE](/LICENSE) for full  details.

## Copyright

Copyright © 2018-2020 [The Van Valen Lab](http://www.vanvalen.caltech.edu/) at the California Institute of Technology (Caltech), with support from the Paul Allen Family Foundation, Google, & National Institutes of Health (NIH) under Grant U24CA224309-01.
All rights reserved.
