# Copyright 2016-2021 The Van Valen Lab at the California Institute of
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
# ==============================================================================
import os

from codecs import open

from setuptools import setup
from setuptools import find_packages


here = os.path.abspath(os.path.dirname(__file__))


about = {}
with open(os.path.join(here, 'kiosk_client', '__version__.py'), 'r', 'utf-8') as f:
    exec(f.read(), about)


with open(os.path.join(here, 'README.md'), 'r', 'utf-8') as f:
    readme = f.read()


setup(name=about['__title__'],
      version=about['__version__'],
      description=about['__description__'],
      author=about['__author__'],
      author_email=about['__author_email__'],
      url=about['__url__'],
      license=about['__license__'],
      download_url='{}/tarball/{}'.format(
          about['__url__'], about['__version__']),
      python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*",
      install_requires=['google-cloud-storage',
                        'Pillow',
                        'python-decouple',
                        'python-dateutil',
                        'treq==20.9.0'],
      extras_require={
          'tests': ['pytest<6',
                    'pytest-twisted',
                    'pytest-pep8',
                    'pytest-cov',
                    'pytest-mock']},
      packages=find_packages(),
      long_description=readme,
      long_description_content_type='text/markdown',
      classifiers=[
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8'])
