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
import time
import glob
import sys
import logging

from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.common.keys import Keys


class ZipFilesAllUploadedError(Exception):
    pass


def selenium_stuff(zip_file_path, max_wait_seconds):
    opts = Options()
    opts.binary_location = '/usr/lib/chromium-browser/chromium-browser'
    opts.add_argument("--no-sandbox")
    opts.set_headless()
    assert opts.headless # Operating in headless mode
    browser = Chrome("/usr/lib/chromium-browser/chromedriver", options=opts)
            #service_log_path="/dev/null")
    browser.get('http://' + str(os.environ['CLUSTER_ADDRESS']) + '/predict')
    time.sleep(20)
    # upload zip file
    try:
        file_upload_box = browser.find_element_by_css_selector( \
                'input[name=imageUploadInput]')
    except (NoSuchElementException, WebDriverException) as e:
        print("Page failed to load. Trying again later.")
        return 1
    file_upload_box.send_keys(zip_file_path)
    # wait for image to finish uploading
    for i in range(max_wait_seconds):
        try:
            browser.find_element_by_css_selector('.uploadedImage')
            print(str(zip_file_path) + " uploaded in " + str(i) + " seconds")
            break
        except (NoSuchElementException, WebDriverException) as e:
            time.sleep(1)
            # If we've failed for the last time...
            if i == (max_wait_seconds - 1):
                return 1
    # set model name, which will automatically set model version and
    # post-processing protocol
    try:
        model_selector_wrapper = browser.find_element_by_css_selector( \
            'div[aria-pressed="false"][role="button"][aria-haspopup="true"]')
    except (NoSuchElementException, WebDriverException) as e:
        print("Page failed to load. Trying again later.")
        return 1
    model_selector_wrapper.click()
    time.sleep(1)
    try:
        model_popup_element = browser.find_element_by_css_selector( \
            'li[role="option"][data-value="watershed_nuclear_nofgbg_41_f16"]')
    except (NoSuchElementException, WebDriverException) as e:
        print("Page failed to load. Trying again later.")
        return 1
    model_popup_element.click()
    time.sleep(1)
    # Click submit button
    try:
        browser.find_element_by_css_selector('#submitButtonWrapper' \
            ).click()
    except (NoSuchElementException, WebDriverException) as e:
        print("Page failed to load. Trying again later.")
        return 1
    time.sleep(1)
    # Remove zip file to save on hard drive space
    os.remove(zip_file_path)
    return 0

def get_list_of_zip_files():
    list_of_zip_files = glob.glob("/conf/data/zips/*.zip")
    return list_of_zip_files

def main():
    # Parse command line argument
    number_of_expected_zips = int(sys.argv[1])

    # Configure logging
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
    logging.getLogger(
        "selenium.webdriver.remote.remote_connection").setLevel(
            logging.WARNING)
    fu_logger = logging.getLogger('file_upload')
    fu_logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler('file_upload.log')
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    fu_logger.addHandler(fh)

    # Initialize variables
    cluster_address = os.environ['CLUSTER_ADDRESS']
    max_wait_seconds = 120

    if cluster_address != "NA":
        list_of_previously_uploaded_zip_files = []
        while True:
            if len(list_of_previously_uploaded_zip_files) \
                    < number_of_expected_zips:
                list_of_zip_files = get_list_of_zip_files()
                if len(list_of_zip_files) > 0:
                    for zip_file in list_of_zip_files:
                        if zip_file in list_of_previously_uploaded_zip_files:
                            pass
                        else:
                            selenium_success = selenium_stuff(
                                zip_file,
                                max_wait_seconds)
                            if selenium_success == 0:
                                fu_logger.debug('Successfully uploaded %s.',
                                                zip_file)
                                list_of_previously_uploaded_zip_files.\
                                        append(zip_file)
                                try:
                                    os.remove(zip_file)
                                    fu_logger.debug('Successfully deleted %s.',
                                                    zip_file)
                                except FileNotFoundError:
                                    fu_logger.debug('Could not find %s.',
                                                    zip_file)
                else:
                    time.sleep(10)
            else:
                # All zip files have been added to the list of uploaded zips.
                break
                # raise ZipFilesAllUploadedError("Where'd they all go????")
    else:
        raise ValueError("There doesn't appear to be an IP address in "
                         "the CLUSTER_ADDRESS environmental variable.")

if __name__ == '__main__':
    main()
