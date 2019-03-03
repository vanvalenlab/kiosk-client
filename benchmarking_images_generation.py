import os
import sys
import time
import numpy as np
from multiprocessing import Pool
from PIL import Image as pil_image
import shutil
from functools import partial
import subprocess
import argparse

# this function is originally from
# https://github.com/vanvalenlab/deepcell-tf/blob/master/tests/deepcell/utils/io_utils_test.py
def _write_image(filepath, img_w=30, img_h=30):
    bias = np.random.rand(img_w, img_h, 1) * 64
    variance = np.random.rand(img_w, img_h, 1) * (255 - 64)
    imarray = np.random.rand(img_w, img_h, 1) * variance + bias
    if filepath.lower().endswith('tif') or filepath.lower().endswith('tiff'):
        tiff.imsave(filepath, imarray[:, :, 0])
    else:
        img = array_to_img(imarray, scale=False, data_format='channels_last')
        img.save(filepath)

# this function is originally from
# https://github.com/tensorflow/tensorflow/blob/r1.5/tensorflow/python/keras/_impl/keras/preprocessing/image.py
def array_to_img(x, data_format=None, scale=True):
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
    x = np.asarray(x, dtype=floatx())
    if x.ndim != 3:
        raise ValueError('Expected image array to have rank 3 (single image). '
                       'Got array with shape:', x.shape)
  
    if data_format is None:
        data_format = image_data_format()
    if data_format not in {'channels_first', 'channels_last'}:
        raise ValueError('Invalid data_format:', data_format)
  
    # Original Numpy array x has format (height, width, channel)
    # or (channel, height, width)
    # but target PIL image has format (width, height, channel)
    if data_format == 'channels_first':
        x = x.transpose(1, 2, 0)
    if scale:
        x = x + max(-np.min(x), 0)  # pylint: disable=g-no-augmented-assignment
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

# the following two functions are originally from
# https://github.com/keras-team/keras/blob/master/keras/backend/common.py
_FLOATX = 'float32'
def floatx():
    """Returns the default float type, as a string.
    (e.g. 'float16', 'float32', 'float64').
    # Returns
        String, the current default float type.
    # Example
    ```python
        >>> keras.backend.floatx()
        'float32'
    ```
    """
    return _FLOATX

_IMAGE_DATA_FORMAT = 'channels_last'
def image_data_format():
    """Returns the default image data format convention.
    # Returns
        A string, either `'channels_first'` or `'channels_last'`
    # Example
    ```python
        >>> keras.backend.image_data_format()
        'channels_first'
    ```
    """
    return _IMAGE_DATA_FORMAT

def _image_generation(home_directory, file_num):
    image_name = "image_" + str(file_num) + ".png"
    file_path = home_directory + "/uncooked_images/" + image_name
    _write_image(file_path,1280,1080)
    shutil.move(home_directory + "/uncooked_images/" + image_name, \
            home_directory + "/" + image_name)

def make_zip_files( img_num, images_per_zip, home_directory ):
    remaining_images = img_num
    last_image_zipped = 0
    zip_file_counter = 0

    while remaining_images > images_per_zip:
        last_image_zipped = last_image_zipped + images_per_zip
        _make_zip_archive(last_image_zipped, zip_file_counter, \
                images_per_zip, home_directory)
        remaining_images = remaining_images - images_per_zip
        zip_file_counter = zip_file_counter + 1
    #zip any remaining files
    last_image_zipped = last_image_zipped + images_per_zip
    _make_zip_archive(last_image_zipped, zip_file_counter, \
            images_per_zip, home_directory)

def _make_zip_archive( last_image_to_zip, zip_file_counter, \
        images_in_this_zip, home_directory ):
    image_numbers_to_zip = range(last_image_to_zip-images_in_this_zip, \
            last_image_to_zip)
    for image_number in image_numbers_to_zip:
        try:
            image_name = "image_" + str(image_number) + ".png"
            shutil.move(home_directory + "/"+image_name, \
                    home_directory + "/current_images/"+image_name)
        except FileNotFoundError:
            images_in_batch = image_number-last_image_to_zip+images_in_this_zip
            print("Only " + str(images_in_batch) + \
                    " images found in last batch.")
            if images_in_batch == 0:
                return 1
            else:
                break
    shutil.make_archive(home_directory + "/uncooked_zips/zip_files" + \
            str(zip_file_counter), "zip", \
            home_directory + "/current_images/")
    initial_location = home_directory + "/uncooked_zips/zip_files" + \
            str(zip_file_counter) + ".zip"
    final_location = home_directory + "/zips/zip_files" + \
            str(zip_file_counter) + ".zip"
    shutil.move( initial_location, final_location)
    for image_number in image_numbers_to_zip:
        try:
            image_name = "image_" + str(image_number) + ".png"
            os.remove(home_directory + "/current_images/" + image_name)
        except FileNotFoundError:
            images_in_batch = image_number-last_image_to_zip+images_in_this_zip
            print("Only " + str(images_in_batch) + \
                    " images removed from last batch.")
            if images_in_batch == 0:
                return 1
            else:
                break
    return 0

def _direct_image_uploads(last_image_to_zip, zip_file_counter, \
        images_in_this_zip, home_directory, upload_address):
    image_numbers_to_upload = range(last_image_to_zip-images_in_this_zip, \
            last_image_to_zip)
    for image_number in image_numbers_to_upload:
        try:
            image_name = "image_" + str(image_number) + ".png"
            image_path = home_directory + "/" + image_name
            upload_filename = "directupload_" + \
                    "watershednuclearnofgbg41f16_0_watershed_0_" + image_name
            upload_path = upload_address + "/" + upload_filename
            subprocess.run(["gsutil", "-m", "cp", image_path, upload_path])
            os.remove(image_path)
        except FileNotFoundError:
            images_in_batch = image_number-last_image_to_zip+images_in_this_zip
            print("Only " + str(images_in_batch) + \
                    " images found in last batch.")
            if images_in_batch == 0:
                return 1
            else:
                break
    return 0

def _lean_image_generation(home_directory):
    img_w = 1280
    img_h = 1080
    filepath = home_directory + "/image_1.png"

    # generate only one image
    bias = np.random.rand(img_w, img_h, 1) * 64
    variance = np.random.rand(img_w, img_h, 1) * (255 - 64)
    imarray = np.random.rand(img_w, img_h, 1) * variance + bias
    if filepath.lower().endswith('tif') or filepath.lower().endswith('tiff'):
        tiff.imsave(filepath, imarray[:, :, 0])
    else:
        img = array_to_img(imarray, scale=False, data_format='channels_last')
        img.save(filepath)
    return filepath
    
def _lean_image_uploads(filepath, number_of_images, home_directory, upload_address):
    # upload first image, which is stored locally
    first_image_name = "image_0.png"
    first_upload_filename = "directupload_" + \
            "watershednuclearnofgbg41f16_0_watershed_0_" + first_image_name
    first_upload_path = upload_address + "/" + first_upload_filename
    subprocess.run(["gsutil", "cp", filepath, first_upload_path])
    # make a ton of copies of that original image in the bucket itself
    # since the goal here is benchmarking, we are implicitly assuming that
    # no component in our prediction pipeline uses caching. The only one 
    # that might right now is tensorflow-serving, but I don't think it does.
    previous_upload_path = first_upload_path
    for img_num in range(1,number_of_images):
        image_name = "image_" + str(img_num) + ".png"
        upload_filename = "directupload_" + \
                "watershednuclearnofgbg41f16_0_watershed_0_" + image_name
        upload_path = upload_address + "/" + upload_filename
        ig_logger.debug("Copying " + previous_upload_path + " to " + upload_path)
        subprocess.run(["gsutil", "cp", previous_upload_path, upload_path])
        previous_upload_path = upload_path

def _lean_upploads_arithmetic(filepath, number_of_images, home_directory, upload_address):
    # upload first image, which is stored locally
    first_image_name = "image_0.png"
    first_upload_filename = "directupload_" + \
            "watershednuclearnofgbg41f16_0_watershed_0_" + first_image_name
    first_upload_path = upload_address + "/" + first_upload_filename
    subprocess.run(["gsutil", "cp", filepath, first_upload_path])
    # Make a ton of copies of that original image in the bucket itself.
    # Since the goal here is benchmarking, we are implicitly assuming that
    # no component in our prediction pipeline uses caching. The only one 
    # that might right now is tensorflow-serving, but I don't think it does.
    previous_upload_path = first_upload_path
    for img_num in range(1,number_of_images):
        # keeping in mind that img_num is essentially how many entries we have available for copying,
        # we can minimize the number of gsutil calls we need by using every available entry every time

        image_name = "image_" + str(img_num) + ".png"
        upload_filename = "directupload_" + \
                "watershednuclearnofgbg41f16_0_watershed_0_" + image_name
        upload_path = upload_address + "/" + upload_filename
        ig_logger.debug("Copying " + previous_upload_path + " to " + upload_path)
        subprocess.run(["gsutil", "cp", previous_upload_path, upload_path])
        previous_upload_path = upload_path


def generate_images_and_zips(number_of_images, images_per_zip, home_directory,
                             make_zips, upload_address, ig_logger):
    """Generate (number_of_images) images and package them into a series of zip
    files, each containing no more than (images_per_zip) images.
    """
    # create worker pool for image generation
    worker_pool = Pool(processes=16) # optimized for 16 CPU setting

    # initialize image generation parameters
    remaining_images = number_of_images
    last_image_zipped = 0
    zip_file_counter = 0

    if make_zips:
        # create partial function for divvying up jobs between worker_pool workers
        _image_generation_partial = partial(_image_generation, home_directory)

        # Create images (images_per_zip) at a time and zip them as they're created.
        while remaining_images > 0:
            print("remaining: " + str(remaining_images))
            print("per_zip: " + str(images_per_zip))
            images_in_this_zip = min(remaining_images, images_per_zip)
            last_image_to_zip = last_image_zipped + images_in_this_zip
            image_number_range = range(last_image_zipped, last_image_to_zip)
            worker_pool.map(_image_generation_partial, image_number_range)
            if make_zips:
                _make_zip_archive(last_image_to_zip, zip_file_counter, \
                        images_in_this_zip, home_directory)
            else:
                _direct_image_uploads(last_image_to_zip, zip_file_counter,
                    images_in_this_zip, home_directory, upload_address)
            remaining_images = remaining_images - images_in_this_zip
            last_image_zipped = last_image_to_zip
            zip_file_counter = zip_file_counter + 1
            #print("")
            #print(str(remaining_images) + " images left to generate.")
            print(str(zip_file_counter) + " zip files created.")
            #print("")
    else:
        filepath = _lean_image_generation(home_directory)
        _lean_image_uploads(filepath, number_of_images, home_directory, 
                upload_address, ig_logger)

def create_directories(home_directory):
    if not os.path.isdir(home_directory + "/uncooked_images"):
        os.makedirs(home_directory + "/uncooked_images")
    if not os.path.isdir(home_directory + "/uncooked_zips"):
        os.makedirs(home_directory + "/uncooked_zips")
    if not os.path.isdir(home_directory + "/zips"):
        os.makedirs(home_directory + "/zips")
    if not os.path.isdir(home_directory + "/current_images"):
        os.makedirs(home_directory + "/current_images")

if __name__=='__main__':
    # parse command line args
    parser = argparse.ArgumentParser()
    parser.add_argument("home_directory",
            help="directory to save generated images in")
    parser.add_argument("number_of_images",
            help="number of images to generate", type=int)
    parser.add_argument("-z", "--generate_zips",
            help="do you want to generate zip files for web upload",
            action="store_true")
    parser.add_argument("-i", "--images_per_zip",
            help="number of images_per zip file", type=int)
    parser.add_argument("--upload_bucket", help="bucket for direct uploading")
    parser.add_argument("--upload_folder", help="folder in upload bucket")
    args = parser.parse_args()
    # assign command line args
    number_of_images = args.number_of_images
    images_per_zip = args.images_per_zip
    if not images_per_zip:
        images_per_zip = 1000
    home_directory = args.home_directory
    if home_directory.endswith('/'):
        home_directory = home_directory[:-1]
    make_zips = args.generate_zips
    upload_bucket = args.upload_bucket
    upload_folder = args.upload_folder
    upload_address = "gs://" + upload_bucket + "/" + upload_folder

    # Configure logging
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
    logging.getLogger("selenium.webdriver.remote.remote_connection"
            ).setLevel(logging.WARNING)
    ig_logger = logging.getLogger('image_generation')
    ig_logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler('image_generation.log')
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ig_logger.addHandler(fh)
    
    # This is a trap for pods that are initialized without a number of images.
    # Just sit here and wait for the deployment to be destroyed and restarted.
    if number_of_images==0:
        while True:
            time.sleep(10000)

    # Make necessary directories
    create_directories(home_directory)

    # All current deepcell models to date use inputs of size 1080x1280,
    # so we're going to be using those dimensions.
    print("Beginning image generation.")
    print(time.time())
    generate_images_and_zips(number_of_images, images_per_zip, home_directory,
                             make_zips, upload_address, ig_logger)
    print(time.time())
    print("Finished image generation.")
