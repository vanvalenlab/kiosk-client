# Copyright 2016-2020 The Van Valen Lab at the California Institute of
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

    # Job definition
    parser.add_argument('file', required=True,
                        help='File to process in many duplicated jobs. '
                             '(Must exist in the cloud storage bucket.)')

    parser.add_argument('mode', choices=['benchmark', 'upload'],
                        help='Benchmarking mode.  `benchmark` for data that '
                             'already exists in the bucket, `upload` to upload'
                             'a local file/directory and process them all.')

    parser.add_argument('-j', '--job-type', type=str,
                        default=settings.JOB_TYPE,
                        help='Type of job (name of Redis work queue).')

    parser.add_argument('-m', '--model', type=str,
                        default=settings.MODEL,
                        help='Name and version of model hosted by TensorFlow '
                             'Serving.')

    parser.add_argument('-t', '--host', type=str,
                        default=settings.HOST,
                        help='IP or FQDN of the DeepCell Kiosk API.')

    parser.add_argument('-b', '--storage-bucket', type=str,
                        default=settings.STORAGE_BUCKET,
                        help='Cloud storage bucket (e.g. gs://storage-bucket).')

    parser.add_argument('-c', '--count', default=1, type=int,
                        help='Number of times to process the given file.')

    parser.add_argument('--pre', '--preprocess', type=str,
                        default=settings.PREPROCESS,
                        help='Number of times to process the given file.')

    parser.add_argument('--post', '--postprocess', type=str,
                        default=settings.POSTPROCESS,
                        help='Number of times to process the given file.')

    parser.add_argument('-s', '--scale', type=float,
                        default=settings.SCALE,
                        help='Scale of the data. Data will be scaled up or '
                             'for the best model compatibility.')

    parser.add_argument('-l', '--label', type=str,
                        default=settings.LABEL, choices=['', '0', '1', '2'],
                        help='Data type (e.g. nuclear, cytoplasmic, etc.).')

    parser.add_argument('-U', '--upload', action='store_true',
                        help='If provided, uploads the file before creating '
                             'a new job.')

    parser.add_argument('--upload-results', action='store_true',
                        help='Upload the final output file to the bucket.')

    # Timing / interval settings
    parser.add_argument('--start-delay', type=float,
                        default=settings.START_DELAY,
                        help='Time between each job creation '
                             '(0.5s is a typical file upload time).')

    parser.add_argument('--update-interval', type=float,
                        default=settings.UPDATE_INTERVAL,
                        help='Seconds between each job status refresh.')

    parser.add_argument('--refresh-rate', type=float,
                        default=settings.MANAGER_REFRESH_RATE,
                        help='Seconds between each manager status check.')

    parser.add_argument('-x', '--expire-time', type=float,
                        default=settings.EXPIRE_TIME,
                        help='Finished jobs expire after this many seconds.')

    # Logging options
    parser.add_argument('-L', '--log-level', default=settings.LOG_LEVEL,
                        choices=('DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'),
                        help='Only log the given level and above.')

    # optional arguments
    parser.add_argument('--upload-prefix', type=str,
                        default=settings.UPLOAD_PREFIX,
                        help='Maximum number of connections to the Kiosk.')

    return parser


def initialize_logger(log_level):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    log_level = getattr(logging, log_level)

    formatter = logging.Formatter(fmt=settings.LOG_FORMAT)

    console = logging.StreamHandler(stream=sys.stdout)
    console.setFormatter(formatter)
    console.setLevel(log_level)
    logger.addHandler(console)

    fh = logging.handlers.RotatingFileHandler(
        filename=settings.LOG_FILE,
        maxBytes=10000000,
        backupCount=1)
    fh.setFormatter(formatter)
    fh.setLevel(log_level)
    logger.addHandler(fh)


if __name__ == '__main__':
    args = get_arg_parser().parse_args()

    if settings.LOG_ENABLED:
        initialize_logger(log_level=args.log_level)

    mgr_kwargs = {
        'host': args.host,
        'model': args.model,
        'job_type': args.job_type,
        'update_interval': args.update_interval,
        'start_delay': args.start_delay,
        'refresh_rate': args.refresh_rate,
        'postprocess': args.postprocess,
        'preprocess': args.preprocess,
        'upload_prefix': args.upload_prefix,
        'expire_time': args.expire_time,
        'upload_results': args.upload_results,
        'data_scale': args.scale,
        'data_label': args.label,
    }

    if not os.path.exists(args.file) and (args.mode == 'upload' or args.upload):
        raise FileNotFoundError('%s could not be found.' % args.file)

    if args.mode == 'benchmark':
        mgr = manager.BenchmarkingJobManager(**mgr_kwargs)
        mgr.run(filepath=args.file, count=args.count, upload=args.upload)

    elif args.mode == 'upload':
        mgr = manager.BatchProcessingJobManager(**mgr_kwargs)
        mgr.run(filepath=args.file)

    reactor.run()  # pylint: disable=E1101
