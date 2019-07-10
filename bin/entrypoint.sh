#!/bin/sh

python -m benchmarking \
  benchmark \
  --file $FILE \
  --count $COUNT \
  --log-level ${LOG_LEVEL:="DEBUG"}
