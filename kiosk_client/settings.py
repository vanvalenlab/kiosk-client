# Copyright 2016-2018 The Van Valen Lab at the California Institute of
# Technology (Caltech), with support from the Paul Allen Family Foundation,
# Google, & National Institutes of Health (NIH) under Grant U24CA224309-01.
# All rights reserved.
#
# Licensed under a modified Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.github.com/vanvalenlab/kiosk-client/LICENSE
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
"""Constants and environment variables"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import errno
import os

from decouple import config

from kiosk_client.utils import get_download_path


NUM_GPUS = config('NUM_GPUS', cast=int, default=0)

# Google credentials
STORAGE_BUCKET = config('STORAGE_BUCKET', default='')

# Batch API Host (IP Address or FQDN)
HOST = config('API_HOST', cast=str, default='')
if not any(HOST.lower().startswith(x) for x in ('http://', 'https://')):
    HOST = 'http://{}'.format(HOST)

# Grafana resources for cost estimation
GRAFANA_HOST = config('GRAFANA_HOST', default='prometheus-operator-grafana')
GRAFANA_USER = config('GRAFANA_USER', default='admin')
GRAFANA_PASSWORD = config('GRAFANA_PASSWORD', default='prom-operator')

# TensorFlow Servable
MODEL = config('MODEL', default='')

# Job Type
JOB_TYPE = config('JOB_TYPE', default='segmentation')
SCALE = config('SCALE', default='')  # detect scale automatically if empty
LABEL = config('LABEL', default='')   # detect data type automatically if empty

# Pre- and Post-Processing functions
PREPROCESS = config('PREPROCESS', default='')
POSTPROCESS = config('POSTPROCESS', default='')

# How frequently Jobs update their statuses
UPDATE_INTERVAL = config('UPDATE_INTERVAL', default=10, cast=float)

# Time to wait between starting jobs (for staggering redis entries)
START_DELAY = config('START_DELAY', default=0.05, cast=float)

# Time interval between Manager status checks
MANAGER_REFRESH_RATE = config('MANAGER_REFRESH_RATE', default=10, cast=float)

# Time in seconds to expire the completed jobs.
EXPIRE_TIME = config('EXPIRE_TIME', default=3600, cast=int)

# Name of upload folder in storage bucket.
UPLOAD_PREFIX = config('UPLOAD_PREFIX', default='uploads', cast=str)

# HTTP Settings
CONCURRENT_REQUESTS_PER_HOST = config('CONCURRENT_REQUESTS_PER_HOST',
                                      default=64, cast=int)

# Application directories
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOAD_DIR = os.path.join(ROOT_DIR, 'download')
OUTPUT_DIR = get_download_path()
LOG_DIR = os.path.join(ROOT_DIR, 'logs')

# Log settings
LOG_ENABLED = config('LOG_ENABLED', default=True, cast=bool)
LOG_FORMAT = '[%(asctime)s]:[%(levelname)s]:[%(name)s]: %(message)s'
LOG_LEVEL = config('LOG_LEVEL', cast=str, default='DEBUG')
LOG_FILE = config('LOG_FILE', default='benchmark.log')
LOG_FILE = os.path.join(LOG_DIR, LOG_FILE)

# Overwrite directories with environment variabls
DOWNLOAD_DIR = config('DOWNLOAD_DIR', default=DOWNLOAD_DIR)
OUTPUT_DIR = config('OUTPUT_DIR', default=OUTPUT_DIR)
LOG_DIR = config('LOG_DIR', default=LOG_DIR)

for d in (DOWNLOAD_DIR, OUTPUT_DIR, LOG_DIR):
    try:
        os.makedirs(d)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
