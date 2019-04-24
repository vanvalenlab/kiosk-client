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
"""Tests for the file benchmarking_images_generation.py"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import benchmarking_images_generation as big

import os
import glob
import math
import getpass
import shutil


def test_generate_images_and_zips():
    # Set parameters
    images_to_create = 10
    images_per_zip = 10
    number_of_zips = math.ceil(images_to_create / images_per_zip)
    home_directory = "/home/travis"  # for Travis CI tests

    # Make necessary directories
    os.chmod(home_directory, 0o771)
    big.create_directories(home_directory)

    # Execute relevant function
    big.generate_images_and_zips(images_to_create, images_per_zip,
                                 home_directory)

    # Check for existence of files
    list_of_images = glob.glob(home_directory + "/image_*.png")
    assert len(list_of_images) == images_to_create
    for img_num in range(images_to_create):
        image_name = home_directory + "/image_" + str(img_num) + ".png"
        assert image_name in list_of_images
    list_of_zips = glob.glob(home_directory + "/zips/zip_files*.zip")
    for zip_number in range(number_of_zips):
        zip_name = home_directory + "/zips/zip_files" + str(zip_number) + ".zip"
        assert zip_name in list_of_zips
