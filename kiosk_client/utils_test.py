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
"""Tests for utility functions"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import random
import zipfile

from PIL import Image
import pytest

from kiosk_client import utils


class TestUtils(object):

    def test_get_download_path(self):
        download_dir = utils.get_download_path()
        assert os.path.isdir(download_dir)

    def test_is_image_file(self, tmpdir):
        # Test valid image
        tmpdir = str(tmpdir)
        valid_image = os.path.join(tmpdir, 'image.png')
        img = Image.new('RGB', (800, 1280), (255, 255, 255))
        img.save(valid_image, 'PNG')
        assert utils.is_image_file(valid_image)

        # Test invalid image
        invalid_image = os.path.join(tmpdir, 'bad_image.png')
        with open(invalid_image, 'w') as f:
            f.write('line1')
        assert not utils.is_image_file(invalid_image)

        # Test image file does not exist
        missing_image = os.path.join(tmpdir, 'nofile.png')
        assert not utils.is_image_file(missing_image)

    def test_iter_image_files(self, tmpdir):
        # test image files
        tmpdir = str(tmpdir)
        num = random.randint(1, 5)
        imagename = lambda x: 'image%s.png' % x

        valid_images = []
        for i in range(num):
            valid_image = os.path.join(tmpdir, imagename(i))
            img = Image.new('RGB', (800, 1280), (255, 255, 255))
            img.save(valid_image, 'PNG')
            valid_images.append(valid_image)

        # only image files exist
        results = utils.iter_image_files(tmpdir, include_archives=True)
        assert set(list(results)) == set(valid_images)

        # create a new zip file of all the valid images
        zippath = os.path.join(tmpdir, 'test.zip')
        z = zipfile.ZipFile(zippath, 'w', zipfile.ZIP_DEFLATED)
        z.close()

        # turn off include_archives, should not see the zip file
        results = utils.iter_image_files(tmpdir, include_archives=False)
        assert set(list(results)) == set(valid_images)

        # with include_archives, zipfile should be in results
        results = utils.iter_image_files(tmpdir, include_archives=True)
        assert set(list(results)) == set(valid_images).union({zippath})

        # test single file paths
        results = utils.iter_image_files(zippath, include_archives=True)
        assert set(list(results)) == set((zippath,))
        results = utils.iter_image_files(zippath, include_archives=False)
        assert set(list(results)) == set()
        results = utils.iter_image_files(valid_images[0])
        assert set(list(results)) == set((valid_images[0],))

    def test_strip_bucket_prefix(self):
        names = [
            'uploads',
            'uploads/with/subdir',
        ]
        fmt_strings = [
            '/{}',  # leading "/"
            '{}/',  # trailing "/"
            '/{}/',  # both leading and trailing "/"
            '{}',  # nothing
        ]
        for name in names:
            for fmt_string in fmt_strings:
                prefix = fmt_string.format(name)
                assert name == utils.strip_bucket_prefix(prefix)

        name = '/duplicate/leading/and/trailing/'
        stripped = utils.strip_bucket_prefix(name)
        assert name[1:-1] == stripped
