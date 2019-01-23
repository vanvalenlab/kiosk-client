# Tests for the file benchmarking_images_generation.py

import benchmarking_images_generation as big

import os
import glob
import math
import getpass


def test__make_zip_archive():
    # Set parameters
    images_to_create = 10
    images_per_zip = 10
    number_of_zips = math.ceil(images_to_create / images_per_zip)
    home_directory = "/home/travis"  # for Travis CI tests

    # Make necessary directories
    os.chmod(home_directory, 0o771)
    if not os.path.isdir(home_directory + "/uncooked_zips"):
        os.makedirs(home_directory + "/uncooked_zips")
    if not os.path.isdir(home_directory + "/zips"):
        os.makedirs(home_directory + "/zips")
    if not os.path.isdir(home_directory + "/current_images"):
        os.makedirs(home_directory + "/current_images")

    # Execute relevant function
    big._make_zip_archive(images_to_create, 0, images_per_zip, home_directory)

    # Check for existence of files
    list_of_images = glob.glob(home_directory + "/*.png")
    assert len(list_of_images) == images_to_create
    for img_num in range(images_to_create):
        image_name = home_directory + "/image_" + int(img_num) + ".png"
        assert image_name in list_of_images
    list_of_zips = glob.glob("/conf/zips/zip_files*.zip")
    for zip_number in range(number_of_zips):
        zip_name = home_directory + "/zip_files" + int(zip_number) + ".zip"
        assert zip_name in list_of_zips
