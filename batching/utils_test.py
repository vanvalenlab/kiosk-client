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
"""Tests for utility functions"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import tempfile

from PIL import Image
import pytest

from batching import utils


class TestUtils(object):

    def test_is_image_file(self):
        with tempfile.TemporaryDirectory() as tempdir:
            # Test valid image
            valid_image = os.path.join(tempdir, 'image.png')
            img = Image.new('RGB', (800, 1280), (255, 255, 255))
            img.save(valid_image, 'PNG')
            assert utils.is_image_file(valid_image)

            # Test invalid image
            invalid_image = os.path.join(tempdir, 'bad_image.png')
            with open(invalid_image, 'w') as f:
                f.write('line1')
            assert not utils.is_image_file(invalid_image)

            # Test image file does not exist
            missing_image = os.path.join(tempdir, 'nofile.png')
            assert not utils.is_image_file(missing_image)

    def test_iter_image_files(self):
        pass
