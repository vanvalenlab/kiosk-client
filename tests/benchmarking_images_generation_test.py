# Tests for the file benchmarking_images_generation.py

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
