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
"""Tests for API Storage classes"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import tempfile

from google.cloud.exceptions import TooManyRequests

import pytest

from redis_consumer import storage
from redis_consumer import utils


class DummyGoogleClient(object):
    public_url = 'public-url'
    fail_tolerance = 2
    fail_count = 0

    def get_bucket(self, *_, **__):
        return self

    def blob(self, *_, **__):
        return self

    def make_public(self, *_, **__):
        return self

    def upload_from_filename(self, dest, **_):
        if self.fail_count < self.fail_tolerance:
            self.fail_count += 1
            raise TooManyRequests('thrown-on-purpose')
        assert os.path.exists(dest)

    def download_to_filename(self, dest, **_):
        if self.fail_count < self.fail_tolerance:
            self.fail_count += 1
            raise TooManyRequests('thrown-on-purpose')
        assert dest.endswith('/test/file.txt')


class DummyS3Client(object):
    def download_file(self, bucket, path, dest, **_):
        assert path.startswith('test')

    def upload_file(self, path, bucket, dest, **_):
        assert os.path.exists(path)


def test_get_client():
    aws = storage.get_client('aws')
    AWS = storage.get_client('AWS')
    assert isinstance(aws, type(AWS))

    # TODO: set GCLOUD env vars to test this
    # with pytest.raises(OSError):
    gke = storage.get_client('gke')
    GKE = storage.get_client('GKE')
    assert isinstance(gke, type(GKE))

    with pytest.raises(ValueError):
        _ = storage.get_client('bad_value')


class TestStorage(object):

    def test_get_download_path(self):
        with utils.get_tempdir() as tempdir:
            bucket = 'test-bucket'
            stg_cls = storage.Storage
            # monkey-patch the storage client function
            stg_cls.get_storage_client = lambda *x: True
            stg = stg_cls(bucket, tempdir)
            filekey = 'upload_dir/key/to.zip'
            path = stg.get_download_path(filekey, tempdir)
            path2 = stg.get_download_path(filekey)
            assert path == path2
            assert str(path).startswith(tempdir)
            assert str(path).endswith(filekey.replace('upload_dir/', ''))


class TestGoogleStorage(object):

    def test_get_public_url(self):
        with utils.get_tempdir() as tempdir:
            bucket = 'test-bucket'
            stg_cls = storage.GoogleStorage
            stg_cls.get_storage_client = DummyGoogleClient
            stg = stg_cls(bucket, tempdir, backoff=0)
            url = stg.get_public_url('test')
            assert url == 'public-url'

    def test_upload(self):
        with utils.get_tempdir() as tempdir:
            with tempfile.NamedTemporaryFile(dir=tempdir) as temp:
                bucket = 'test-bucket'
                stg_cls = storage.GoogleStorage
                stg_cls.get_storage_client = DummyGoogleClient
                stg = stg_cls(bucket, tempdir, backoff=0)

                # test succesful upload
                dest, url = stg.upload(temp.name)
                assert dest == 'output/{}'.format(os.path.basename(temp.name))

                # test succesful upload with subdir
                subdir = '/abc'
                dest, url = stg.upload(temp.name, subdir=subdir)
                assert dest == 'output{}/{}'.format(
                    subdir, os.path.basename(temp.name))

                # test failed upload
                with pytest.raises(Exception):
                    # self._client raises, but so does storage.upload
                    dest, url = stg.upload('file-does-not-exist')

    def test_download(self):
        remote_file = '/test/file.txt'
        with utils.get_tempdir() as tempdir:
            bucket = 'test-bucket'
            stg_cls = storage.GoogleStorage
            stg_cls.get_storage_client = DummyGoogleClient
            stg = stg_cls(bucket, tempdir, backoff=0)

            # test succesful download
            dest = stg.download(remote_file, tempdir)
            assert dest == stg.get_download_path(remote_file, tempdir)

            # test failed download
            with pytest.raises(Exception):
                # self._client raises, but so does storage.download
                dest = stg.download('bad/file.txt', tempdir)


class TestS3Storage(object):

    def test_get_public_url(self):
        with utils.get_tempdir() as tempdir:
            bucket = 'test-bucket'
            stg = storage.S3Storage(bucket, tempdir)
            url = stg.get_public_url('test')
            assert url == 'https://{}/{}'.format(stg.bucket_url, 'test')

    def test_upload(self):
        with utils.get_tempdir() as tempdir:
            with tempfile.NamedTemporaryFile(dir=tempdir) as temp:
                bucket = 'test-bucket'
                stg = storage.S3Storage(bucket, tempdir)

                # monkey path client functions
                stg.get_storage_client = DummyS3Client

                # test succesful upload
                dest, url = stg.upload(temp.name)
                assert dest == 'output/{}'.format(os.path.basename(temp.name))

                # test succesful upload with subdir
                subdir = '/abc'
                dest, url = stg.upload(temp.name, subdir=subdir)
                assert dest == 'output{}/{}'.format(
                    subdir, os.path.basename(temp.name))

                # test failed upload
                with pytest.raises(Exception):
                    # self._client raises, but so does storage.upload
                    dest, url = stg.upload('file-does-not-exist')

    def test_download(self):
        remote_file = '/test/file.txt'
        with utils.get_tempdir() as tempdir:
            bucket = 'test-bucket'
            stg = storage.S3Storage(bucket, tempdir)

            # monkey path client functions
            stg.get_storage_client = DummyS3Client

            # test succesful download
            dest = stg.download(remote_file, tempdir)
            assert dest == stg.get_download_path(remote_file[1:], tempdir)

            # test failed download
            with pytest.raises(Exception):
                # self._client raises, but so does storage.download
                dest = stg.download('bad/file.txt', tempdir)
