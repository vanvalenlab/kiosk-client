#!/bin/bash

for (( i=0; i<${NUM_CYCLES}; i++ ))
do
  python -m kiosk_client \
    $FILE \
    --job-type=$JOB_TYPE \
    --host=$API_HOST \
    --model=${MODEL:=""} \
    --pre=${PREPROCESS:=""} \
    --post=${POSTPROCESS:=""} \
    --start-delay=${START_DELAY:=0.5} \
    --update-interval=${UPDATE_INTERVAL:=10} \
    --refresh-rate=${MANAGER_REFRESH_RATE:=10} \
    --expire-time=${EXPIRE_TIME:=3600} \
    --upload-prefix=${UPLOAD_PREFIX:=uploads} \
    --log-level=${LOG_LEVEL:="DEBUG"} \
    --benchmark \
    --storage-bucket=${STORAGE_BUCKET:=""} \
    --count=${COUNT:=1} \
    --upload-results \
    --calculate-cost \
    --no-download-results \
  && \
  sleep ${CYCLE_INTERVAL:="1h"}
done

sleep 7d
