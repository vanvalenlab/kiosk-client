from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
import os
import subprocess
import re

def selenium_stuff():
    opts = Options()
    opts.set_headless()
    assert opts.headless # Operating in headless mode
    browser = Firefox(options=opts)
    browser.get('http://' + str(os.environ['CLUSTER_ADDRESS']) + '/predict')
    submission_field = browser.find_element_by_css_selector('div.dropzoneCSS')
    submission_field.click()
    file_upload_box = browser.find_element_by_css_selector('input[type=\"file\"]')
    file_upload_box.send_keys('/conf/zip_files.zip')
    file_upload_box.submit() # unnecessary?
    browser.find_element_by_css_selector('.jss273 .jss252').click() # open up model menu
    browser.find_element_by_css_selector('.jss79:nth-child(7)').click() # select model
    browser.find_element_by_css_selector('.jss100').click() # submit

def main():
    with open("./cluster_address","r") as cluster_file:
        line = cluster_file.readline()
    cluster_address = re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', line)
    if cluster_address:
        os.environ['CLUSTER_ADDRESS'] = str(cluster_address)
        selenium_stuff()
    else:
        raise NameError("There doesn't appear to be an IP address in ./cluster_address.")

if __name__=='__main__':
    main()
