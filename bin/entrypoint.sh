#!/bin/bash

python benchmark.py \
  --file $FILE \
  --count $COUNT \
  --model $MODEL \
  --host $API_HOST \
  --backoff $BACKOFF \
  --post $POSTPROCESS \
  --upload-prefix $UPLOAD_PREFIX \
  --retries $RETRY_COUNT \
  --retry-backoff $RETRY_BACKOFF \
  --expire-time $EXPIRE_TIME
