import os

try:
    upload_method = os.environ['UPLOAD_METHOD']
except KeyError:
    logging.error("The UPLOAD_METHOD evnironmental variable is not set.")
if upload_method == "web":
    try:
        images_per_zip = int(os.environ['IMAGES_PER_ZIP'])
        img_num = int(os.environ['IMG_NUM'])
        # rounding up
        zips = int(img_num / images_per_zip) + ((img_num % images_per_zip) > 0)
    except KeyError:
        pass
if upload_method == "direct":
    pass
else:
    logging.error("Set UPLOAD_METHOD environmental variable.")
benchmarking_pu_type_and_number = os.environ['BENCHMARKING_PU_TYPE_AND_NUMBER']
gpu_num = benchmarking_pu_type_and_number.split(" ")[0]
image_directory = "/conf/data"

with open("summary.txt", "a") as summary_file:
    summary_file.write("Processing unit type: ")
