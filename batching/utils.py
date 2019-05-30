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
"""Utility files for batch file processing"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os

from PIL import Image


def is_image_file(filepath):
    """Returns True if the file is an image file, otherwise False"""
    try:
        with Image.open(filepath) as im:
            im.verify()
        return True
    except:  # pylint: disable=W0702
        return False


def iter_image_files(path, include_archives=True):
    archive_extensions = {'.zip',}
    for (dirpath, _, filenames) in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            # process all zip images
            _, ext = os.path.splitext(filepath.lower())
            if ext in archive_extensions and include_archives:
                yield filepath

            # process all images
            elif is_image_file(filepath):
                yield filepath
