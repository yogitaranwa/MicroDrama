#!/bin/bash
for i in 1 2 3 4; do
  python3 -u output/legacy/gen_arc.py && [ -f output/legacy/honesty_run/arc.json ] && exit 0
  echo "$(date +%H:%M:%S) arc attempt $i failed, retrying" >> output/legacy/honesty_arc.log
  sleep 20
done
exit 1
