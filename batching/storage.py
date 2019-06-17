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
"""Storage Interface to upload / download files from / to the cloud"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import time
import timeit

import os
import logging

import boto3
from google.cloud import storage as google_storage
from google.cloud import exceptions as google_exceptions

from batching import settings
from batching.settings import DOWNLOAD_DIR


class StorageException(Exception):
    """Custom Exception for the Storage classes"""
    pass


def get_client(cloud_provider):
    """Returns the Storage Client appropriate for the cloud provider
    # Arguments:
        cloud_provider: Indicates which cloud platform (AWS vs GKE)
    # Returns:
        storage_client: Client for interacting with the cloud.
    """
    cloud_provider = str(cloud_provider).lower()
    logger = logging.getLogger('storage.get_client')
    if cloud_provider == 'aws':
        storage_client = S3Storage(settings.AWS_S3_BUCKET)
    elif cloud_provider == 'gke':
        storage_client = GoogleStorage(settings.GCLOUD_STORAGE_BUCKET)
    else:
        errmsg = 'Bad value for CLOUD_PROVIDER: %s'
        logger.error(errmsg, cloud_provider)
        raise ValueError(errmsg % cloud_provider)
    return storage_client


class Storage(object):
    """General class to interact with cloud storage buckets.
    Supported cloud stroage provider will have child class implementations.

    Args:
        bucket: cloud storage bucket name
        download_dir: path to local directory to save downloaded files
    """

    def __init__(self, bucket, download_dir=DOWNLOAD_DIR, backoff=1.5):
        self.bucket = bucket
        self.download_dir = download_dir
        self.output_dir = 'output'
        self.backoff = backoff
        self.logger = logging.getLogger(str(self.__class__.__name__))

    def get_storage_client(self):
        """Returns the storage API client"""
        raise NotImplementedError

    def get_download_path(self, filepath, download_dir=None):
        """Get local filepath for soon-to-be downloaded file.

        Args:
            filepath: key of file in cloud storage to download
            download_dir: path to directory to save file

        Returns:
            dest: local path to downloaded file
        """
        if download_dir is None:
            download_dir = self.download_dir
        no_upload_dir = os.path.join(*(filepath.split(os.path.sep)[1:]))
        dest = os.path.join(download_dir, no_upload_dir)
        if not os.path.isdir(os.path.dirname(dest)):
            os.makedirs(os.path.dirname(dest))
        return dest

    def download(self, filepath, download_dir):
        """Download a  file from the cloud storage bucket.

        Args:
            filepath: key of file in cloud storage to download
            download_dir: path to directory to save file

        Returns:
            dest: local path to downloaded file
        """
        raise NotImplementedError

    def upload(self, filepath, subdir=None):
        """Upload a file to the cloud storage bucket.

        Args:
            filepath: local path to file to upload

        Returns:
            dest: key of uploaded file in cloud storage
        """
        raise NotImplementedError


class GoogleStorage(Storage):
    """Interact with Google Cloud Storage buckets.

    Args:
        bucket: cloud storage bucket name
        download_dir: path to local directory to save downloaded files
    """

    def __init__(self, bucket, download_dir=DOWNLOAD_DIR, backoff=1.5):
        super(GoogleStorage, self).__init__(bucket, download_dir, backoff)
        self.bucket_url = 'www.googleapis.com/storage/v1/b/{}/o'.format(bucket)

    def get_storage_client(self):
        """Returns the storage API client"""
        return google_storage.Client()

    def get_public_url(self, filepath):
        """Get the public URL to download the file.

        Args:
            filepath: key to file in cloud storage

        Returns:
            url: Public URL to download the file
        """
        client = self.get_storage_client()
        bucket = client.get_bucket(self.bucket)
        blob = bucket.blob(filepath)
        blob.make_public()
        return blob.public_url

    def upload(self, filepath, subdir=None):
        """Upload a file to the cloud storage bucket.

        Args:
            filepath: local path to file to upload

        Returns:
            dest: key of uploaded file in cloud storage
        """
        start = timeit.default_timer()
        client = self.get_storage_client()
        self.logger.debug('Uploading %s to bucket %s.', filepath, self.bucket)
        retrying = True
        while retrying:
            try:
                dest = os.path.basename(filepath)
                if subdir:
                    if str(subdir).startswith('/'):
                        subdir = subdir[1:]
                    dest = os.path.join(subdir, dest)
                dest = os.path.join(self.output_dir, dest)
                bucket = client.get_bucket(self.bucket)
                blob = bucket.blob(dest)
                blob.upload_from_filename(filepath, predefined_acl='publicRead')
                self.logger.debug('Uploaded %s to bucket %s in %s seconds.',
                                  filepath, self.bucket,
                                  timeit.default_timer() - start)
                retrying = False
                return dest, blob.public_url
            except google_exceptions.TooManyRequests as err:
                self.logger.warning('Encountered %s: %s.  Backing off for %s '
                                    'seconds...', type(err).__name__, err,
                                    self.backoff)
                time.sleep(self.backoff)
                retrying = True  # Unneccessary but explicit
            except Exception as err:
                retrying = False
                self.logger.error('Encountered %s: %s while uploading %s.',
                                  type(err).__name__, err, filepath)
                raise err

    def download(self, filepath, download_dir=None):
        """Download a  file from the cloud storage bucket.

        Args:
            filepath: key of file in cloud storage to download
            download_dir: path to directory to save file

        Returns:
            dest: local path to downloaded file
        """
        client = self.get_storage_client()
        dest = self.get_download_path(filepath, download_dir)
        self.logger.debug('Downloading %s to %s.', filepath, dest)
        retrying = True
        while retrying:
            try:
                start = timeit.default_timer()
                blob = client.get_bucket(self.bucket).blob(filepath)
                blob.download_to_filename(dest)
                self.logger.debug('Downloaded %s from bucket %s in %s seconds.',
                                  dest, self.bucket,
                                  timeit.default_timer() - start)
                return dest
            except google_exceptions.TooManyRequests as err:
                self.logger.warning('Encountered %s: %s.  Backing off for %s '
                                    'seconds and...', type(err).__name__, err,
                                    self.backoff)
                time.sleep(self.backoff)
                retrying = True  # Unneccessary but explicit
            except Exception as err:
                retrying = False
                self.logger.error('Encountered %s: %s while downloading %s.',
                                  type(err).__name__, err, filepath)
                raise err


class S3Storage(Storage):
    """Interact with Amazon S3 buckets.

    Args:
        bucket: cloud storage bucket name
        download_dir: path to local directory to save downloaded files
    """

    def __init__(self, bucket, download_dir=DOWNLOAD_DIR, backoff=1.5):
        super(S3Storage, self).__init__(bucket, download_dir, backoff)
        self.bucket_url = 's3.amazonaws.com/{}'.format(bucket)

    def get_storage_client(self):
        """Returns the storage API client"""
        return boto3.client(
            's3',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

    def get_public_url(self, filepath):
        """Get the public URL to download the file.

        Args:
            filepath: key to file in cloud storage

        Returns:
            url: Public URL to download the file
        """
        return 'https://{url}/{obj}'.format(url=self.bucket_url, obj=filepath)

    def upload(self, filepath, subdir=None):
        """Upload a file to the cloud storage bucket.

        Args:
            filepath: local path to file to upload

        Returns:
            dest: key of uploaded file in cloud storage
        """
        start = timeit.default_timer()
        client = self.get_storage_client()
        dest = os.path.basename(filepath)
        if subdir:
            if str(subdir).startswith('/'):
                subdir = subdir[1:]
            dest = os.path.join(subdir, dest)
        dest = os.path.join(self.output_dir, dest)
        self.logger.debug('Uploading %s to bucket %s.', filepath, self.bucket)
        try:
            client.upload_file(filepath, self.bucket, dest)
            self.logger.debug('Uploaded %s to bucket %s in %s seconds.',
                              filepath, self.bucket,
                              timeit.default_timer() - start)
            return dest, self.get_public_url(dest)
        except Exception as err:
            self.logger.error('Encountered %s: %s while uploading %s.',
                              type(err).__name__, err, filepath)
            raise err

    def download(self, filepath, download_dir=None):
        """Download a  file from the cloud storage bucket.

        Args:
            filepath: key of file in cloud storage to download
            download_dir: path to directory to save file

        Returns:
            dest: local path to downloaded file
        """
        start = timeit.default_timer()
        client = self.get_storage_client()
        # Bucket keys shouldn't start with "/"
        if filepath.startswith('/'):
            filepath = filepath[1:]

        dest = self.get_download_path(filepath, download_dir)
        self.logger.debug('Downloading %s to %s.', filepath, dest)
        try:
            client.download_file(self.bucket, filepath, dest)
            self.logger.debug('Downloaded %s from bucket %s in %s seconds.',
                              dest, self.bucket, timeit.default_timer() - start)
            return dest
        except Exception as err:
            self.logger.error('Encountered %s: %s while downloading %s.',
                              type(err).__name__, err, filepath)
            raise err
