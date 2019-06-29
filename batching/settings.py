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

import multiprocessing
import os

from decouple import config


# remove leading/trailing "/"s from cloud bucket folder names
_strip = lambda x: '/'.join(y for y in x.split('/') if y)

MAX_JOBS = 100  # maximum number of jobs per API request

# Debug Mode
DEBUG = config('DEBUG', cast=bool, default=False)

# Cloud storage
CLOUD_PROVIDER = config('CLOUD_PROVIDER', cast=str, default='gke').lower()

# AWS credentials
AWS_REGION = config('AWS_REGION', default='us-east-1')
AWS_S3_BUCKET = config('AWS_S3_BUCKET', default='')
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')

# Google credentials
GCLOUD_STORAGE_BUCKET = config('GKE_BUCKET', default='')

# Batch API Host (IP Address or FQDN)
HOST = config('API_HOST', cast=str, default='')
if not any(HOST.lower().startswith(x) for x in ('http://', 'https://')):
    HOST = 'http://{}'.format(HOST)

# Time to wait between HTTP requests.
BACKOFF = config('BACKOFF', default=1, cast=int)

# Number of times to retry an HTTP ConnectionError
HTTP_RETRIES = config('HTTP_RETRIES', default=3, cast=int)

# Time to wait between HTTP retries
HTTP_RETRY_BACKOFF = config('HTTP_RETRY_BACKOFF', default=3, cast=int)

# Time in seconds to expire the completed jobs.
EXPIRE_TIME = config('EXPIRE_TIME', default=600, cast=int)

# Name of upload folder in storage bucket.
UPLOAD_PREFIX = config('UPLOAD_PREFIX', default='uploads', cast=str)

# Application directories
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOAD_DIR = os.path.join(ROOT_DIR, 'download')

# Overwrite directories with environment variabls
DOWNLOAD_DIR = config('DOWNLOAD_DIR', default=DOWNLOAD_DIR)

POOL = multiprocessing.Pool()
