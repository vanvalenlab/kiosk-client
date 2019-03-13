#!/bin/bash

function preliminary_benchmarking_output() {
  # benchmarking variable examination
  echo "$BENCHMARK_TYPE"
  echo " "
  echo "Processing Unit Type: '$BENCHMARKING_PU_TYPE'"
  echo "Processing Units and Number: $BENCHMARKING_PU_TYPE_AND_NUMBER"
  if [ "$BENCHMARKING_PU_TYPE" = "GPU" ]; then
      echo "If GPU, GPU type: $GPU_TYPE"
  else
      echo "CPU type unknown."
  fi  
  echo "Number of images: $IMG_NUM"
  echo "Deepcell model: $BENCHMARK_MODEL"
  echo "Deepcell Model Version: $BENCHMARK_MODEL_VERSION"
  echo "Deepcell postprocessing: $BENCHMARK_POSTPROCESSING"
  echo "Image cuts: $BENCHMARK_CUTS"

  # benchmark file creation
  touch benchmarking.log
  echo " " >> benchmarking.log
  echo " " >> benchmarking.log
  echo "$BENCHMARK_TYPE" >> benchmarking.log
  echo " " >> benchmarking.log
  echo "Processing Unit Type: $BENCHMARKING_PU_TYPE" >> benchmarking.log
  echo "Processing Units and Number: $BENCHMARKING_PU_TYPE_AND_NUMBER" >> benchmarking.log
  if [ "$BENCHMARKING_PU_TYPE" = "GPU" ]; then
      echo "If GPU, GPU type: $GPU_TYPE" >> benchmarking.log
  else
      echo "CPU type unknown." >> benchmarking.log
  fi
  echo "Number of images: $IMG_NUM" >> benchmarking.log
  echo "Images per zip file: $IMAGES_PER_ZIP" >> benchmarking.log
  echo "Number of zip files: $ZIPS" >> benchmarking.log
  echo "Deepcell model: $BENCHMARK_MODEL" >> benchmarking.log
  echo "Deepcell Model Version: $BENCHMARK_MODEL_VERSION" >> benchmarking.log
  echo "Deepcell postprocessing: $BENCHMARK_POSTPROCESSING" >> benchmarking.log
  echo "Image cuts: $BENCHMARK_CUTS" >> benchmarking.log
  echo " " >> benchmarking.log
}

function image_generation_and_file_upload() {
  # We're going to run the image generation script in the background (hence the
  # ampersand), and the file upload script in the foregoround. The expectation 
  # is that the file upload script should not terminate before the image
  # generation script, since it's waiting for the image generator to produce 
  # a set number of zip files.
  # Arguments to benchmarking_images_generation.py are 
  # (number of images to generate) and (number of images per zip file).
  if [ "$UPLOAD_METHOD" = "web" ]; then
    echo "$UPLOAD_METHOD is \"web\""
    unbuffer python3 ./benchmarking_images_generation.py $IMAGE_DIRECTORY $IMG_NUM --generate_zips --images_per_zip $IMAGES_PER_ZIP &
    # Argument to file_uplaod_web.py is (total number of zip files to upload).
    unbuffer python3 ./file_upload_web.py $ZIPS &
    unbuffer python3 ./redis_polling.py $UPLOAD_METHOD $ZIPS zip_results.txt
  else
    echo "$UPLOAD_METHOD is not \"web\""
    # benchmarking_images_generation currently uploads directly when --generate_zips isn't specified,
    # so we're not calling another upload script explicitly
    unbuffer python3 ./benchmarking_images_generation.py $IMAGE_DIRECTORY $IMG_NUM --upload_bucket $BUCKET --upload_folder $BUCKET_FOLDER &
    unbuffer python3 ./redis_polling.py $UPLOAD_METHOD $IMG_NUM zip_results.txt
  fi
  echo " " >> zip_results.txt
  echo "number of images: $IMG_NUM" >> zip_results.txt
  echo "number of GPUs: $GPU_NUM" >> zip_results.txt
  echo "All data analyzed."
  #echo "$(date): data generation and upload completed" >> benchmarking.log
}

function main() {
  # check variable logic
  if [ "$UPLOAD_METHOD" = "direct" ]; then
      :
  elif [ "$UPLOAD_METHOD" = "web" ]; then 
      if [ -n "$IMAGES_PER_ZIP" ]; then
          # the following expression is constructed to ensure rounding up of remainder
          ZIPS=$(( ($IMG_NUM + $IMAGES_PER_ZIP - 1)/$IMAGES_PER_ZIP )) 
      else
          touch benchmarking.log
          echo "" > benchmarking.log
          echo "UPLOAD_METHOD = web, but IMAGES_PER_ZIP is not set." > benchmarking.log
          echo "Set it with the -z command line option." > benchmarking.log
          echo "" > benchmarking.log
          exit 1
      fi
  else
      touch benchmarking.log
      echo "" > benchmarking.log
      echo "UPLOAD_METHOD is not set." > benchmarking.log
      echo "Set it with the -u command line option." > benchmarking.log
      echo "" > benchmarking.log
      exit 1
  fi

  # define necessary variables
  GPU_NUM=$([[ "${BENCHMARKING_PU_TYPE_AND_NUMBER}" =~ ([0-9]+) ]] && echo "${BASH_REMATCH[1]}")
  IMAGE_DIRECTORY=/conf/data

  echo "$IMAGES_PER_ZIP"
  echo "$ZIPS"
  # execute functions
  preliminary_benchmarking_output
  image_generation_and_file_upload
}

main
# the following is to prevent the pod from restarting
while :; do
    echo "$(date): sleeping"
    sleep 5d
done
