import os
import sys
import time
import numpy as np
from multiprocessing import Pool
from PIL import Image as pil_image
import shutil

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

def _image_generation(file_num):
    file_path = "/conf/data/image_" + str(file_num) + ".png"
    _write_image(file_path,1280,1080)

def make_zip_files( img_num ):
    """Package all images into a series of zip files,
    each containing no more than 1000 images.

    """
    remaining_images = img_num
    last_image_zipped = 0
    zip_file_counter = 0

    while remaining_images > 1000:
        last_image_zipped = last_image_zipped + 1000
        _make_zip_archive(last_image_zipped, zip_file_counter)
        remaining_images = remaining_images - 1000
        zip_file_counter = zip_file_counter + 1
    #zip any remaining files
    last_image_zipped = last_image_zipped + 1000
    _make_zip_archive(last_image_zipped, zip_file_counter)


def _make_zip_archive( last_image_zipped, zip_file_counter ):
        image_numbers_to_zip = range(last_image_zipped-1000, last_image_zipped)
        for image_number in image_numbers_to_zip:
            try:
                image_name = "image_" + str(image_number) + ".png"
                shutil.move("/conf/data/"+image_name, \
                        "/conf/data/current_images/"+image_name)
            except FileNotFoundError:
                print("Only " + str(image_number-1) + \
                        " images found in last batch.")
                break
        shutil.make_archive( "/conf/data/zips/zip_files" + \
                str(zip_file_counter), "zip", \
                "/conf/data/current_images/")
        for image_number in image_numbers_to_zip:
            try:
                image_name = "image_" + str(image_number) + ".png"
                shutil.move("/conf/data/current_images/"+image_name, \
                        "/conf/data/"+image_name)
            except FileNotFoundError:
                print("Only " + str(image_number-1) + \
                        " images found in last batch.")
                break



if __name__=='__main__':
    # parse command line args
    img_num = int(sys.argv[1])

    if not os.path.isdir("/conf/data/zips"):
        os.makedirs("/conf/data/zips")
    if not os.path.isdir("/conf/data/current_images"):
        os.makedirs("/conf/data/current_images")
    # the two images I've been using for the HeLa_S3_Deepcell model have been 1280x1080
    print("Beginning image generation.")
    print(time.time())
    worker_pool = Pool(processes=16) # optimized for 16 CPU setting
    inputs = range( img_num )
    worker_pool.map( _image_generation, inputs )
    make_zip_files(img_num)
    print(time.time())
    print("Finished image generation.")
