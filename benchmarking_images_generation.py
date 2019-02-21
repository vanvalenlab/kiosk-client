import os
import sys
import time
import numpy as np
from multiprocessing import Pool
from PIL import Image as pil_image
import shutil
from functools import partial

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
    file_path = home_directory + "/image_" + str(file_num) + ".png"
    _write_image(file_path,1280,1080)

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

def generate_images_and_zips(number_of_images, images_per_zip, home_directory):
    """Generate (number_of_images) images and package them into a series of zip
    files, each containing no more than (images_per_zip) images.
    """
    # create worker pool for image generation
    worker_pool = Pool(processes=16) # optimized for 16 CPU setting

    # initialize image generation parameters
    remaining_images = number_of_images
    last_image_zipped = 0
    zip_file_counter = 0

    # create partial function for divvying up jobs between worker_pool workers
    _image_generation_partial = partial(_image_generation, home_directory)

    # Create images (images_per_zip) at a time and zip them as they're created.
    while remaining_images > 0:
        images_in_this_zip = min(remaining_images, images_per_zip)
        last_image_to_zip = last_image_zipped + images_in_this_zip
        image_number_range = range(last_image_zipped, last_image_to_zip)
        worker_pool.map(_image_generation_partial, image_number_range)
        _make_zip_archive(last_image_to_zip, zip_file_counter, \
                images_in_this_zip, home_directory)
        remaining_images = remaining_images - images_in_this_zip
        last_image_zipped = last_image_to_zip
        zip_file_counter = zip_file_counter + 1
        #print("")
        #print(str(remaining_images) + " images left to generate.")
        print(str(zip_file_counter) + " zip files created.")
        #print("")

def create_directories(home_directory):
    if not os.path.isdir(home_directory + "/uncooked_zips"):
        os.makedirs(home_directory + "/uncooked_zips")
    if not os.path.isdir(home_directory + "/zips"):
        os.makedirs(home_directory + "/zips")
    if not os.path.isdir(home_directory + "/current_images"):
        os.makedirs(home_directory + "/current_images")

if __name__=='__main__':
    # parse command line args
    number_of_images = int(sys.argv[1])
    images_per_zip = int(sys.argv[2])
    home_directory = str(sys.argv[3])
    if home_directory.endswith('/'):
        home_directory = home_directory[:-1]

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
    generate_images_and_zips(number_of_images, images_per_zip, home_directory)
    print(time.time())
    print("Finished image generation.")
