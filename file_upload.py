from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
import os
import subprocess
import re

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
    file_upload_box = browser.find_element_by_css_selector('input[type=\"file\"]')
    file_upload_box.send_keys('/zip_files.zip')
    file_upload_box.submit() # unnecessary?
    browser.find_element_by_css_selector('.jss273 .jss252').click() # open up model menu
    browser.find_element_by_css_selector('.jss79:nth-child(7)').click() # select model
    browser.find_element_by_css_selector('.jss100').click() # submit

def main():
    cluster_address = os.environ['CLUSTER_ADDRESS']
    if cluster_address!="NA":
        selenium_stuff()
    else:
        raise ValueError("There doesn't appear to be an IP address in the " \
                "CLUSTER_ADDRESS environmental variable.")

if __name__=='__main__':
    main()
