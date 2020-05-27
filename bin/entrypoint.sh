#!/bin/bash

for (( i=0; i<${NUM_CYCLES}; i++ ))
do
  python -m benchmarking \
    benchmark \
    $FILE \
    --job-type $JOB_TYPE \
    --model $MODEL \
    --host $HOST \
    --storage-bucket $STORAGE_BUCKET \
    --count $COUNT \
    --preprocess $PREPROCESS \
    --postprocess $POSTPROCESS \
    --upload-results \
    --start-delay $START_DELAY \
    --update-interval $UPDATE_INTERVAL \
    --refresh-rate $MANAGER_REFRESH_RATE \
    --expire-time $EXPIRE_TIME \
    --upload-prefix $UPLOAD_PREFIX \
    --log-level ${LOG_LEVEL:="DEBUG"} \
  && \
  sleep ${CYCLE_INTERVAL:="1h"}
done

sleep 7d
