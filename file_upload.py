from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.common.keys import Keys
import os
import subprocess
import re
import time
import glob
import sys

class ZipFilesAllUploadedError(Exception):
    pass

def selenium_stuff( zip_file_path, max_wait_seconds ):
    opts = Options()
    opts.binary_location = '/usr/lib/chromium-browser/chromium-browser'
    opts.add_argument("--no-sandbox")
    opts.set_headless()
    assert opts.headless # Operating in headless mode
    browser = Chrome("/usr/lib/chromium-browser/chromedriver", options=opts)
    browser.get('http://' + str(os.environ['CLUSTER_ADDRESS']) + '/predict')
    time.sleep(20)
    # upload zip file
    try:
        file_upload_box = browser.find_element_by_css_selector( \
                'input[name=imageUploadInput]')
    except (NoSuchElementException, WebDriverException) as e:
        print("Page failed to load. Trying again later.")
        return 1
    file_upload_box.send_keys( zip_file_path )
    # wait for image to finish uploading
    for i in range(max_wait_seconds):
        try:
            browser.find_element_by_css_selector('.uploadedImage')
            print("Image uploaded!")
            break
        except (NoSuchElementException, WebDriverException) as e:
            if i%5==0:
                print("Waited for " + str(i) + " seconds so far.")
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

    # Initialize variables
    cluster_address = os.environ['CLUSTER_ADDRESS']
    max_wait_seconds = 120

    if cluster_address!="NA":
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
                            if selenium_success==0:
                                print("Successfully uploaded " + \
                                        str(zip_file) + ".")
                                list_of_previously_uploaded_zip_files.\
                                        append(zip_file)
                                os.remove(zip_file)
                else:
                    time.sleep(10)
            else:
                raise ZipFilesAllUploadedError("Where'd they all go????")
    else:
        raise ValueError("There doesn't appear to be an IP address in " \
                "the CLUSTER_ADDRESS environmental variable.")

if __name__=='__main__':
    main()
