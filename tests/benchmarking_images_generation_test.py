# Tests for the file benchmarking_images_generation.py

import benchmarking_images_generation as big

import os
import glob
import math


def test__make_zip_archive():
    # Make necessary directories
    if not os.path.isdir("/conf/data/uncooked_zips"):
        os.makedirs("/conf/data/uncooked_zips")
    if not os.path.isdir("/conf/data/zips"):
        os.makedirs("/conf/data/zips")
    if not os.path.isdir("/conf/data/current_images"):
        os.makedirs("/conf/data/current_images")

    # Set parameters
    images_to_create = 10
    images_per_zip = 10
    number_of_zips = math.ceil(images_to_create / images_per_zip)
    # Execute relevant function
    big._make_zip_archive(images_to_create, 0, images_per_zip)

    # Check for existence of files
    list_of_images = glob.glob("/conf/data/*.png")
    assert len(list_of_images) == images_to_create
    for img_num in range(images_to_create):
        image_name = "/conf/data/image_" + int(img_num) + ".png"
        assert image_name in list_of_images
    list_of_zips = glob.glob("/conf/zips/zip_files*.zip")
    for zip_number in range(number_of_zips):
        zip_name = "/conf/data/zip_files" + int(zip_number) + ".zip"
        assert zip_name in list_of_zips
