from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
import os
import subprocess
import re
import time

def selenium_stuff():
    opts = Options()
    opts.binary_location = '/usr/lib/chromium-browser/chromium-browser'
    opts.add_argument("--no-sandbox")
    opts.set_headless()
    assert opts.headless # Operating in headless mode
    browser = Chrome("/usr/lib/chromium-browser/chromedriver", options=opts)
    browser.get('http://' + str(os.environ['CLUSTER_ADDRESS']) + '/predict')
    submission_field = browser.find_element_by_css_selector('div.dropzoneCSS')
    submission_field.click()
    file_upload_box = browser.find_element_by_css_selector( \
            'input[type=\"file\"]')
    file_upload_box.send_keys('/zip_files.zip')
    file_upload_box.submit() # unnecessary?
    # wait for image to upload
    wait_seconds = 300
    for i in range(wait_seconds):
        try:
            browser.find_element_by_css_selector('.uploadedImage')
            break
        except:
            if i % 5 == 0:
                print("Waited for " + str(i) + " seconds so far."
            time.sleep(1)
    # set model name
    model_selector = browser.find_element_by_css_selector( \
            '#model-placeholder')
    browser.execute_script( \
            'arguments[0].setAttribute("value"' + \
            ',"watershed_nuclear_nofgbg_41_f16");', \
            model_selector)
    # set model version
    model_version_selector = browser.find_element_by_css_selector( \
            '#version-placeholder')
    browser.execute_script( \
            'arguments[0].setAttribute("value","0");', \
            model_version_selector)
    # set post-processing protocol
    postprocess_selector = browser.find_element_by_css_selector( \
            '#postprocess-placeholder')
    browser.execute_script( \
            'arguments[0].setAttribute("value","watershed");', \
            postprocess_selector)
    # submit
    browser.find_element_by_css_selector('#submitButton' \
            ).send_keys('\n')
    # due to an eccentricity with chromedriver, it's necessary to use "send_keys()" above, instead of "click()"

def main():
    cluster_address = os.environ['CLUSTER_ADDRESS']
    if cluster_address!="NA":
        selenium_stuff()
    else:
        raise ValueError("There doesn't appear to be an IP address in the " \
                "CLUSTER_ADDRESS environmental variable.")

if __name__=='__main__':
    main()
