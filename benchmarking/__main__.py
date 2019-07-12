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
"""Use the kiosk-frontend API to create and monitor image processing jobs"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import logging
import logging.handlers
import os
import sys

from twisted.internet import reactor

from benchmarking import manager
from benchmarking import settings


def get_arg_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument('mode', choices=['benchmark', 'upload'],
                        help='Benchmarking mode.  `benchmark` for data that '
                             'already exists in the bucket, `upload` to upload'
                             'a local file/directory and process them all.')

    parser.add_argument('-f', '--file', required=True,
                        help='File to process in many duplicated jobs. '
                             '(Must exist in the cloud storage bucket.)')

    parser.add_argument('-c', '--count', default=10, type=int,
                        help='Number of times to process the given file.')

    parser.add_argument('-L', '--log-level', default=settings.LOG_LEVEL,
                        choices=('DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'),
                        help='log level (default: DEBUG)')

    parser.add_argument('--upload', action='store_true',
                        help='If provided, uploads the file before creating '
                             'a new job.')

    return parser


def initialize_logger(log_level):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(fmt=settings.LOG_FORMAT)

    console = logging.StreamHandler(stream=sys.stdout)
    console.setFormatter(formatter)

    fh = logging.handlers.RotatingFileHandler(
        filename=os.path.join(settings.LOG_DIR, 'benchmarking.log'),
        maxBytes=10000000,
        backupCount=1)
    fh.setFormatter(formatter)

    console.setLevel(getattr(logging, log_level))
    fh.setLevel(getattr(logging, log_level))

    logger.addHandler(console)
    logger.addHandler(fh)


if __name__ == '__main__':
    args = get_arg_parser().parse_args()

    if settings.LOG_ENABLED:
        initialize_logger(log_level=args.log_level)

    mgr_kwargs = {
        'host': settings.HOST,
        'model_name': settings.MODEL_NAME,
        'model_version': settings.MODEL_VERSION,
        'update_interval': settings.UPDATE_INTERVAL,
        'start_delay': settings.START_DELAY,
        'refresh_rate': settings.MANAGER_REFRESH_RATE,
        'postprocess': settings.POSTPROCESS,
        'preprocess': settings.PREPROCESS,
        'upload_prefix': settings.UPLOAD_PREFIX,
    }

    if args.mode == 'benchmark':
        mgr_kwargs['upload'] = args.upload
        mgr = manager.BenchmarkingJobManager(**mgr_kwargs)
        mgr.run(filepath=args.file, count=args.count)

    elif args.mode == 'upload':
        mgr = manager.BatchProcessingJobManager(**mgr_kwargs)
        if not os.path.exists(args.file):
            raise FileNotFoundError('%s could not be found.' % args.file)
        mgr.run(filepath=args.file)

    reactor.run()  # pylint: disable=E1101
