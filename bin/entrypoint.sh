#!/bin/sh

python -m benchmarking \
  --file $FILE \
  --count $COUNT \
  --model $MODEL \
  --host $API_HOST \
  --post $POSTPROCESS
