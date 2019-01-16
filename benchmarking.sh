
### setup ###
#system setup

function kiosk_prep() {
  # prepping kiosk
  apk update && apk upgrade && apk add build-base jpeg-dev python3-dev zlib-dev
  rm /usr/bin/python && ln -s /usr/bin/python3 /usr/bin/python && ln -s /usr/bin/pip3 /usr/bin/pip
  pip install --upgrade pip && pip install numpy pillow
}

function environmental_setup() {
  # create benchmarking variables
  export BENCHMARKING_PU_TYPE_AND_NUMBER=$(echo $BENCHMARK_TYPE | cut -f2 -d',' | sed 's/-/ /')
  export BENCHMARKING_PU_TYPE=$(echo $BENCHMARKING_PU_TYPE_AND_NUMBER | cut -f2 -d' ')
  export img_num=$(echo $BENCHMARK_TYPE | grep -o '[0-9]\+-image' | grep -o '[0-9]\+')
  export BENCHMARK_MODEL="HeLa_S3_watershed"
  export BENCHMARK_MODEL_VERSION="0"
  export BENCHMARK_POSTPROCESSING="watershed"
  export BENCHMARK_CUTS="0"
  
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
  echo "Number of images: $img_num"
  echo "Deepcell model: $BENCHMARK_MODEL"
  echo "Deepcell Model Version: $BENCHMARK_MODEL_VERSION"
  echo "Deepcell postprocessing: $BENCHMARK_POSTPROCESSING"
  echo "Image cuts: $BENCHMARK_CUTS"
  sleep 10
}

function image_generation() {
  # image generation
  python ./benchmarking_images_generation.py $img_num
}

function preliminary_benchmarking_output() {
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

### benchmarking ###

function cluster_creation() {
# cluster creation
echo "$(date): cluster creation begins" >> benchmarks.txt
make create
echo "$(date): cluster creation completed" >> benchmarks.txt
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

# download all results
## not sure how to implement this

function destroy_cluster() {
# destroy cluster
echo "Checking active nodes again: $(kubectl get nodes | grep Ready | wc -l)"
echo "$(date): cluster destruction begins" >> benchmarks.txt
make destroy
echo "$(date): cluster destruction completed" >> benchmarks.txt
# upload benchmarks.txt to bucket
if [ "$CLOUD_PROVIDER" = "gke" ]; then
    gsutil cp benchmarks.txt gs://$GKE_BUCKET/$BENCHMARK_TYPE
elif [ "$CLOUD_PROVIDER" = "aws" ]; then
    aws s3 cp benchmarks.txt s3://$AWS_S3_BUCKET/$BENCHMARK_TYPE
fi
}


function main() {
  kiosk_prep
  environmental_setup
  image_generation
  preliminary_benchmarking_output
  cluster_creation
  file_upload
  wait_for_gpu
  wait_for_jobs_to_process
  destroy_cluster
}

main
