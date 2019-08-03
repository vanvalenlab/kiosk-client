#!/bin/bash

for (( i=0; i<${NUM_CYCLES}; i++ ))
do
  python -m benchmarking \
    benchmark \
    --file $FILE \
    --count $COUNT \
    --log-level ${LOG_LEVEL:="DEBUG"} \
  && \
  sleep 1h
done

sleep 7d
