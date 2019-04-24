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
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import time
import shutil
from functools import partial
import subprocess
import argparse
import logging
from multiprocessing import Pool

# import skimage  # TODO: breaks docker image?
import numpy as np
from PIL import Image as pil_image


class ImageGenerator():
    def __init__(self, args):
        # configure logger
        self._configure_logger()

        # assign command line args
        self.number_of_images = args.number_of_images
        if not args.images_per_zip:
            self.images_per_zip = 1000
        else:
            self.images_per_zip = args.images_per_zip

        self.home_directory = args.home_directory
        if self.home_directory.endswith('/'):
            self.home_directory = self.home_directory[:-1]

        self.make_zips = args.generate_zips
        self.upload_bucket = args.upload_bucket
        self.upload_folder = args.upload_folder
        self.upload_address = 'gs://{}/{}'.format(
            self.upload_bucket, self.upload_folder)

    def _configure_logger(self):
        # Disable logging from Python modules.
        logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
        logging.getLogger(
            'selenium.webdriver.remote.remote_connection'
                ).setLevel(logging.WARNING)
        # Configure script's logging.
        self._logger = logging.getLogger('image_generation')
        self._logger.setLevel(logging.DEBUG)
        # Send logs to stdout so they can be read via Kubernetes.
        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        sh.setFormatter(formatter)
        self._logger.addHandler(sh)
        # Also send logs to a file for later inspection.
        fh = logging.FileHandler('image_generation.log')
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        self._logger.addHandler(fh)

    def potentially_sleep(self):
        # This is a trap for pods that are initialized without a number of images.
        # Just sit here and wait for the deployment to be destroyed and restarted.
        if self.number_of_images == 0:
            while True:
                self._logger.debug('SLEEP')
                time.sleep(10000)

    def _create_directories(self):
        directories = [
            'uncooked_images',
            'uncooked_zips',
            'zips',
            'current_images',
        ]
        for d in directories:
            if not os.path.isdir(os.path.join(self.home_directory, d)):
                os.makedirs(os.path.join(self.home_directory, d))

    def generate_files(self):
        # Are we making zip files, or just individual images?
        # Right now, this is also a proxy for whether we're uploading files
        # directly or using the web interface (zip=web).
        self._logger.info('Beginning image generation.')
        # Make necessary directories
        self._create_directories()
        if self.make_zips:
            self._generate_images_and_zips()
        else:
            filepath = self._lean_image_generation()
            self._lean_image_upload(filepath)
        self._logger.info('Finished image generation.')

    def _lean_image_generation(self):
        img_w = 1280
        img_h = 1080

        filepath = os.path.join(self.home_directory, 'image_0.png')

        # generate only one image
        bias = np.random.rand(img_w, img_h, 1) * 64
        variance = np.random.rand(img_w, img_h, 1) * (255 - 64)
        imarray = np.random.rand(img_w, img_h, 1) * variance + bias
        if filepath.lower().endswith('tif') or filepath.lower().endswith('tiff'):
            skimage.external.tifffileimsave(filepath, imarray[:, :, 0])
        else:
            img = self._array_to_img(
                imarray, data_format='channels_last', scale=False)
            img.save(filepath)
        return filepath

    def _lean_image_upload(self, filepath):
        # upload image
        image_name = 'image_0.png'
        upload_prefix = 'directupload_watershednuclearnofgbg41f16_0_watershed_0_'
        benchmarking = True
        if benchmarking:
            upload_prefix += 'benchmarking%sspecial_' % self.number_of_images
        upload_filename = upload_prefix + image_name
        upload_path = '%s/%s' % (self.upload_address, upload_filename)
        # TODO: use a google.cloud.storage function instead of subprocess
        subprocess.run(['gsutil', 'cp', filepath, upload_path])
        self._logger.debug('Uploaded %s to %s.', filepath, upload_path)

    def _generate_images_and_zips(self):
        """Generate (number_of_images) images and package them into a series of zip
        files, each containing no more than (images_per_zip) images.
        """
        # create worker pool for image generation
        num_cpus = 16  # optimized for 16 CPU setting
        worker_pool = Pool(processes=num_cpus)

        # initialize image generation parameters
        remaining_images = self.number_of_images
        last_image_zipped = 0
        zip_file_counter = 0

        # create partial function for divvying up jobs between worker_pool workers
        _image_generation_partial = partial(self._image_generation, self.home_directory)

        # Create images (images_per_zip) at a time and zip them as they're created.
        while remaining_images > 0:
            print('remaining: ', remaining_images)
            print('per_zip: ', self.images_per_zip)

            images_in_this_zip = min(remaining_images, self.images_per_zip)
            last_image_to_zip = last_image_zipped + images_in_this_zip
            image_number_range = range(last_image_zipped, last_image_to_zip)
            worker_pool.map(_image_generation_partial, image_number_range)
            self._make_zip_archive(
                last_image_to_zip, zip_file_counter, images_in_this_zip)
            remaining_images = remaining_images - images_in_this_zip
            last_image_zipped = last_image_to_zip
            zip_file_counter = zip_file_counter + 1

            print(remaining_images, ' images left to generate.')
            print(zip_file_counter, ' zip files created.')

    def _make_zip_archive(self, last_image_to_zip, zip_file_counter, \
            images_in_this_zip):
        image_numbers_to_zip = range(last_image_to_zip-images_in_this_zip, \
                last_image_to_zip)
        for image_number in image_numbers_to_zip:
            try:
                image_name = 'image_%s.png' % image_number
                src = os.path.join(self.home_directory, image_name)
                dst = os.path.join(
                    self.home_directory, 'current_images', image_name)
                shutil.move(src, dst)
            except FileNotFoundError:
                images_in_batch = image_number-last_image_to_zip + images_in_this_zip
                print('Only %s images found in last batch.' % images_in_batch)
                if images_in_batch == 0:
                    return 1
                else:
                    break
        shutil.make_archive(self.home_directory + '/uncooked_zips/zip_files' + \
            str(zip_file_counter), 'zip', \
            self.home_directory + '/current_images/')
        initial_location = self.home_directory + '/uncooked_zips/zip_files' + \
            str(zip_file_counter) + '.zip'
        final_location = self.home_directory + '/zips/zip_files' + \
            str(zip_file_counter) + '.zip'
        shutil.move(initial_location, final_location)
        for image_number in image_numbers_to_zip:
            try:
                image_name = 'image_%s.png' % image_number
                os.remove(os.path.join(
                    self.home_directory, 'current_images', image_name))
            except FileNotFoundError:
                images_in_batch = image_number-last_image_to_zip+images_in_this_zip
                print('Only %s images removed from last batch.' % images_in_batch)

                if images_in_batch == 0:
                    return 1
                else:
                    break
        return 0

    def _image_generation(self, home_directory, file_num):
        image_name = 'image_%s.png' % file_num
        file_path = os.path.join(home_directory, 'uncooked_images', image_name)
        self._write_image(file_path, 1280, 1080)
        shutil.move(file_path, os.path.join(home_directory, image_name))

    # this function is originally from
    # https://github.com/vanvalenlab/deepcell-tf/blob/master/tests/deepcell/utils/io_utils_test.py
    def _write_image(self, filepath, img_w=30, img_h=30):
        bias = np.random.rand(img_w, img_h, 1) * 64
        variance = np.random.rand(img_w, img_h, 1) * (255 - 64)
        imarray = np.random.rand(img_w, img_h, 1) * variance + bias
        if filepath.lower().endswith('tif') or filepath.lower().endswith('tiff'):
            skimage.external.tifffileimsave(filepath, imarray[:, :, 0])
        else:
            img = self._array_to_img(
                imarray, data_format='channels_last', scale=False)
            img.save(filepath)

    # this function is modified from
    # https://github.com/tensorflow/tensorflow/blob/r1.5/tensorflow/python/keras/_impl/keras/preprocessing/image.py
    def _array_to_img(self, x, data_format=None, scale=True):
        """Converts a 3D Numpy array to a PIL Image instance.
        Arguments:
            x: Input Numpy array.
            data_format: Image data format.
            scale: Whether to rescale image values
                to be within [0, 255].
        Returns:
            A PIL Image instance.
        Raises:
            ImportError: if PIL is not available.
            ValueError: if invalid `x` or `data_format` is passed.
        """
        if pil_image is None:
            raise ImportError('Could not import PIL.Image. '
                              'The use of `array_to_img` requires PIL.')
        FLOAT_X = 'float32'
        x = np.asarray(x, dtype=FLOAT_X)
        if x.ndim != 3:
            raise ValueError('Expected image array to have rank 3 (single image). '
                             'Got array with shape:', x.shape)

        IMAGE_DATA_FORMAT = 'channels_last'
        if data_format is None:
            data_format = IMAGE_DATA_FORMAT
        if data_format not in {'channels_first', 'channels_last'}:
            raise ValueError('Invalid data_format:', data_format)

        # Original Numpy array x has format (height, width, channel)
        # or (channel, height, width)
        # but target PIL image has format (width, height, channel)
        if data_format == 'channels_first':
            x = x.transpose(1, 2, 0)
        if scale:
            x = x + max(-np.min(x), 0)
            x_max = np.max(x)
            if x_max != 0:
                x /= x_max
            x *= 255
        if x.shape[2] == 3:
            # RGB
            return pil_image.fromarray(x.astype('uint8'), 'RGB')
        elif x.shape[2] == 1:
            # grayscale
            return pil_image.fromarray(x[:, :, 0].astype('uint8'), 'L')
        else:
            raise ValueError('Unsupported channel number: ', x.shape[2])

if __name__ == '__main__':
    # parse command line args
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'home_directory',
        help='directory to save generated images in')
    parser.add_argument(
        'number_of_images',
        help='number of images to generate', type=int)
    parser.add_argument(
        '-z', '--generate_zips',
        help='do you want to generate zip files for web upload',
        action='store_true')
    parser.add_argument(
        '-i', '--images_per_zip',
        help='number of images_per zip file', type=int)
    parser.add_argument('--upload_bucket', help='bucket for direct uploading')
    parser.add_argument('--upload_folder', help='folder in upload bucket')
    args = parser.parse_args()

    ig = ImageGenerator(args)
    ig.potentially_sleep()
    ig.generate_files()
