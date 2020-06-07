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
"""Utility files for batch file processing"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os

from PIL import Image

from twisted.internet import reactor
from twisted.internet.task import deferLater


def get_download_path():
    """Returns the default downloads path for linux or windows.
    https://stackoverflow.com/a/48706260
    """
    if os.name == 'nt':
        # pylint: disable=E0401,C0415
        import winreg
        k = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
        downloads_guid = '{374DE290-123F-4565-9164-39C4925E467B}'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, k) as key:
            location = winreg.QueryValueEx(key, downloads_guid)[0]
        return location
    location = os.path.join(os.path.expanduser('~'), 'Downloads')
    while not os.path.exists(location):
        location = os.path.abspath(os.path.join(location, '..'))
    return location


def strip_bucket_prefix(prefix):
    """Remove any leading or trailing "/" characters."""
    return '/'.join(x for x in prefix.split('/') if x)


def sleep(seconds):
    """Simple helper to delay asynchronously for some number of seconds."""
    return deferLater(reactor, seconds, lambda: None)


def is_image_file(filepath):
    """Returns True if the file is an image file, otherwise False"""
    try:
        with Image.open(filepath) as im:
            im.verify()
        return True
    except:  # pylint: disable=bare-except
        return False


def iter_image_files(path, include_archives=True):
    archive_extensions = {'.zip'}
    if os.path.isfile(path):
        _, ext = os.path.splitext(path.lower())
        if ext in archive_extensions and include_archives:
            yield path
        elif is_image_file(path):
            yield path

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
