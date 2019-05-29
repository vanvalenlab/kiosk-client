#!/bin/sh

python benchmark.py \
  --file $FILE \
  --count $COUNT \
  --model $MODEL \
  --host $API_HOST \
  --post $POSTPROCESS
