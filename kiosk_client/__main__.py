# Copyright 2016-2020 The Van Valen Lab at the California Institute of
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

from kiosk_client import manager
from kiosk_client import settings


def valid_filepath(parser, arg):
    """File validation for argparsing.

    https://stackoverflow.com/a/11541450
    """
    if not os.path.exists(arg):
        # Argparse uses the ArgumentTypeError to give a rejection message like:
        # error: argument input: x does not exist
        raise argparse.ArgumentTypeError('{0} does not exist'.format(arg))
    return arg


def get_arg_parser():
    parser = argparse.ArgumentParser(
        prog='kiosk_client',
        description='The Kiosk-Client is a Command Line Interface (CLI) for '
                    'interacting with the DeepCell Kiosk.'
    )

    # Job definition
    parser.add_argument('file', type=str, metavar="FILE",
                        help='File to process in many duplicated jobs. '
                             '(Must exist in the cloud storage bucket if '
                             'using benchmark mode.)')

    parser.add_argument('--benchmark', action='store_true',
                        help='Benchmarking mode. Manage COUNT simulated jobs. '
                             'The FILE must exist in the STORAGE_BUCKET.')

    parser.add_argument('-j', '--job-type', type=str, required=True,
                        help='Type of job (name of Redis work queue).')

    parser.add_argument('-t', '--host', type=str, required=True,
                        help='IP or FQDN of the DeepCell Kiosk API.')

    parser.add_argument('-m', '--model', type=str,
                        default=settings.MODEL,
                        help='Name and version of model hosted by TensorFlow '
                             'Serving. Overrides the default model defined by '
                             'the JOB_TYPE.')

    parser.add_argument('-b', '--storage-bucket', type=str,
                        default=settings.STORAGE_BUCKET,
                        help='Cloud storage bucket (e.g. gs://storage-bucket).'
                             'Only required if using `--upload-results`.')

    parser.add_argument('-c', '--count', default=1, type=int,
                        help='Number of times to process the given file. '
                             'Only used in `benchmark` mode.')

    parser.add_argument('--pre', '--preprocess', type=str,
                        default=settings.PREPROCESS,
                        help='Preprocessing function to use before model '
                             'prediction. Overrides default preprocessing '
                             'function for the JOB_TYPE.')

    parser.add_argument('--post', '--postprocess', type=str,
                        default=settings.POSTPROCESS,
                        help='Postprocessing function to use after model '
                             'prediction. Overrides default postprocessing '
                             'function for the JOB_TYPE.')

    parser.add_argument('-s', '--scale', type=str,
                        default=settings.SCALE,
                        help='Scale of the data. Data will be scaled up or '
                             'for the best model compatibility.')

    parser.add_argument('-l', '--label', type=str,
                        default=settings.LABEL, choices=['', '0', '1', '2'],
                        help='Data type (e.g. nuclear, cytoplasmic, etc.).')

    parser.add_argument('-U', '--upload', action='store_true',
                        help='If provided, uploads the file before creating '
                             'a new job. '
                             '(Only applicable in `benchmark` mode.)')

    parser.add_argument('--upload-results', action='store_true',
                        help='Upload the final output file to the bucket.')

    parser.add_argument('--no-download-results', action='store_true',
                        help='Upload the final output file to the bucket.')

    parser.add_argument('--calculate-cost', action='store_true',
                        help='Use the Grafana API to calculate the cost of '
                             'the job.')

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

    parser.add_argument('--output-dir', default=settings.OUTPUT_DIR,
                        help='Directory to save the job output.')

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

    logging.getLogger('PIL').setLevel(logging.INFO)


if __name__ == '__main__':
    args = get_arg_parser().parse_args()

    if settings.LOG_ENABLED:
        initialize_logger(log_level=args.log_level)

    if args.scale:  # optional, but if provided should be a float
        try:
            args.scale = float(args.scale)
        except ValueError:
            raise argparse.ArgumentTypeError(
                '{0} is not a float'.format(args.scale))

    mgr_kwargs = {
        'host': args.host,
        'model': args.model,
        'job_type': args.job_type,
        'update_interval': args.update_interval,
        'start_delay': args.start_delay,
        'refresh_rate': args.refresh_rate,
        'postprocess': args.post,
        'preprocess': args.pre,
        'upload_prefix': args.upload_prefix,
        'expire_time': args.expire_time,
        'data_scale': args.scale,
        'data_label': args.label,
        'storage_bucket': args.storage_bucket,
        'upload_results': args.upload_results,
        'calculate_cost': args.calculate_cost,
        'download_results': not args.no_download_results,
        'output_dir': args.output_dir,
    }

    if not os.path.exists(args.file) and not args.benchmark and args.upload:
        raise FileNotFoundError('%s could not be found.' % args.file)

    if args.benchmark:
        mgr = manager.BenchmarkingJobManager(**mgr_kwargs)
        mgr.run(filepath=args.file, count=args.count, upload=args.upload)

    else:
        mgr = manager.BatchProcessingJobManager(**mgr_kwargs)
        mgr.run(filepath=args.file)

    reactor.run()  # pylint: disable=E1101
