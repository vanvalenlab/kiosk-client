# Copyright 2016-2018 The Van Valen Lab at the California Institute of
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
"""Constants and environment variables"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import errno
import os

from decouple import config


# remove leading/trailing "/"s from cloud bucket folder names
_strip = lambda x: '/'.join(y for y in x.split('/') if y)

# Debug Mode
DEBUG = config('DEBUG', cast=bool, default=False)

# Google credentials
GCLOUD_STORAGE_BUCKET = config('GCLOUD_STORAGE_BUCKET', default='')

# Batch API Host (IP Address or FQDN)
HOST = config('API_HOST', cast=str, default='')
if not any(HOST.lower().startswith(x) for x in ('http://', 'https://')):
    HOST = 'http://{}'.format(HOST)

# TensorFlow Servable
MODEL_NAME, MODEL_VERSION = config('MODEL', default='HeLaS3watershed:2').split(':')

# Pre- and Post-Processing functions
PREPROCESS = config('PREPROCESS', default='')
POSTPROCESS = config('POSTPROCESS', default='watershed')

# How frequently Jobs update their statuses
UPDATE_INTERVAL = config('UPDATE_INTERVAL', default=10, cast=float)

# Time to wait between starting jobs (for staggering redis entries)
START_DELAY = config('START_DELAY', default=1, cast=float)

# Time interval between Manager status checks
MANAGER_REFRESH_RATE = config('MANAGER_REFRESH_RATE', default=10, cast=float)

# Bucket prefix to upload all folders
UPLOAD_PREFIX = config('UPLOAD_PREFIX', default='uploads')

# Time in seconds to expire the completed jobs.
EXPIRE_TIME = config('EXPIRE_TIME', default=600, cast=int)

# Name of upload folder in storage bucket.
UPLOAD_PREFIX = _strip(config('UPLOAD_PREFIX', default='uploads', cast=str))

# Application directories
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOAD_DIR = os.path.join(ROOT_DIR, 'download')
OUTPUT_DIR = os.path.join(ROOT_DIR, 'output')

# Overwrite directories with environment variabls
DOWNLOAD_DIR = config('DOWNLOAD_DIR', default=DOWNLOAD_DIR)
OUTPUT_DIR = config('OUTPUT_DIR', default=OUTPUT_DIR)

for d in (DOWNLOAD_DIR, OUTPUT_DIR):
    try:
        os.makedirs(d)
    except OSError as exc:  # Guard against race condition
        if exc.errno != errno.EEXIST:
            raise
