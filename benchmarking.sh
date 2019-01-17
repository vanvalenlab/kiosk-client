function image_generation() {
# image generation
python ./benchmarking_images_generation.py $IMG_NUM
}

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
  touch benchmarks.txt
  echo " " >> benchmarks.txt
  echo " " >> benchmarks.txt
  echo "$BENCHMARK_TYPE" >> benchmarks.txt
  echo " " >> benchmarks.txt
  echo "Processing Unit Type: $BENCHMARKING_PU_TYPE" >> benchmarks.txt
  echo "Processing Units and Number: $BENCHMARKING_PU_TYPE_AND_NUMBER" >> benchmarks.txt
  if [ "$BENCHMARKING_PU_TYPE" = "GPU" ]; then
      echo "If GPU, GPU type: $GPU_TYPE" >> benchmarks.txt
  else
      echo "CPU type unknown." >> benchmarks.txt
  fi
  echo "Number of images: $img_num" >> benchmarks.txt
  echo "Deepcell model: $BENCHMARK_MODEL" >> benchmarks.txt
  echo "Deepcell Model Version: $BENCHMARK_MODEL_VERSION" >> benchmarks.txt
  echo "Deepcell postprocessing: $BENCHMARK_POSTPROCESSING" >> benchmarks.txt
  echo "Image cuts: $BENCHMARK_CUTS" >> benchmarks.txt
  echo " " >> benchmarks.txt
}

function file_upload() {
  kubens deepcell
  ## new upload method
  wget https://github.com/mozilla/geckodriver/releases/download/v0.23.0/geckodriver-v0.23.0-linux64.tar.gz
  tar xvfz geckodriver-v0.23.0-linux64.tar.gz
  mv ./geckodriver /usr/local/bin
  echo http://nl.alpinelinux.org/alpine/edge/testing >> /etc/apk/repositories
  echo http://dl-3.alpinelinux.org/alpine/edge/main >> /etc/apk/repositories
  #apk add icu-libs
  apk add firefox
  pip install selenium
  python ./file_upload.py
  echo "$(date): data upload completed" >> benchmarks.txt
}

function wait_for_gpu() {
  # wait for GPU creation
  echo "$(date): GPU requisition begins" >> benchmarks.txt
  kubens deepcell
  while true; do
      sleep 1
      if [ $(kubectl get pods | grep -E "tf-serving.+Running" | wc -l) -gt 0 ]; then
          echo "$(date)"
          echo "Active pods:"
          echo "$(kubectl get pods)"
          break
      else
          echo "$(date): tf-serving pod status: $(kubectl get pods | grep tf-serving)"
      fi
  done
  echo "$(date): GPU requisition completed" >> benchmarks.txt
  echo " " >> benchmarks.txt
}

function wait_for_jobs_to_process() {
  # wait for all jobs to be processed
  echo "$(date): image processing begins" >> benchmarks.txt
  echo "Initial number of GPU nodes: $(kubectl get nodes | grep gpu | wc -l)" >> benchmarks.txt
  while true; do
      echo $(kubectl exec redis-master-0 -- redis-cli --eval hgetmultiple.lua)
      if [ "$(kubectl exec redis-master-0 -- redis-cli --eval hgetmultiple.lua)" -eq "0" ]; then
          break
      fi
      sleep 3
  done
  echo "Final number of GPU nodes: $(kubectl get nodes | grep gpu | wc -l)" >> benchmarks.txt
  echo "$(date): image processing completed" >> benchmarks.txt
  echo " " >> benchmarks.txt
}

function main() {
  image_generation
  preliminary_benchmarking_output
  file_upload
  wait_for_gpu
  wait_for_jobs_to_process
}

main
