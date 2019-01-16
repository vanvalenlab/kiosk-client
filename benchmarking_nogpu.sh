touch benchmarks.txt

# cluster creation
echo "$(date): cluster creation begins" >> benchmarks.txt
make create
echo "$(date): cluster creation completed" >> benchmarks.txt
echo " " >> benchmarks.txt

#upload all data and write entries to REDIS database
echo "$(date): data upload begins" >> benchmarks.txt
kubens deepcell
if [ "$CLOUD_PROVIDER" = "gke" ]; then
    gsutil cp /conf/data/* gs://$GKE_BUCKET/uploads/
elif [ "$CLOUD_PROVIDER" = "aws" ]; then
    aws s3 cp /conf/data/* s3://$AWS_S3_BUCKET/uploads/
fi
for file in $(ls -p /conf/data | grep -v /); do
    kubectl exec redis-master-0 redis-cli hmset predict_$file url https://storage.googleapis.com/deepcell-output/uploads/$file file_name uploads/$file model_name HeLa_S3_deepcell model_version 0 postprocess_function deepcell cuts 0 status new
done
echo "$(date): data upload completed" >> benchmarks.txt
echo " " >> benchmarks.txt

# wait for GPU creation
echo "$(date): GPU requisition begins" >> benchmarks.txt
while true; do
    sleep 1
    if [ $(kubectl get nodes | grep Ready | wc -l) -gt 3 ]; then
        break
    else
        echo "$(date): Ready nodes: $(kubectl get nodes | grep Ready | wc -l)"
    fi
done
echo "$(date): GPU requisition completed" >> benchmarks.txt
echo " " >> benchmarks.txt

# wait for all jobs to be processed
echo "$(date): image processing begins" >> benchmarks.txt
while true; do
    broken_for_loop=0
    for file in $(ls -p /conf/data | grep -v /); do
        if [ $(kubectl exec redis-master-0 redis-cli hgetall predict_$file | grep done | wc -l) -lt 1 ]; then
            echo "$(date)"
            echo "$(kubectl exec redis-master-0 redis-cli hgetall predict_$file)"
            echo " "
            broken_for_loop=1
            break
        fi
    done
    if [ "$broken_for_loop" = "0" ]; then
        break # the for loop completed without hitting break, so we'll break out of the while loop
    fi
    sleep 1
done
echo "$(date): image processing completed" >> benchmarks.txt
echo " " >> benchmarks.txt

# download all results
## not sure how to implement this

# destroy cluster
echo "$(date): cluster destruction begins" >> benchmarks.txt
make destroy
echo "$(date): cluster destruction completed" >> benchmarks.txt
# upload benchmarks.txt to bucket
if [ "$CLOUD_PROVIDER" = "gke" ]; then
    gsutil cp benchmarks.txt gs://$GKE_BUCKET/$BENCHMARK_TYPE
elif [ "$CLOUD_PROVIDER" = "aws" ]; then
    aws s3 cp benchmarks.txt s3://$AWS_S3_BUCKET/$BENCHMARK_TYPE
fi
