#!/bin/sh
# runq.sh QUEUEFILE : each line "name|harness args". Runs them one after another (resumable), writing res/<name>.jsonl.
cd "$(dirname "$0")/.."
while IFS='|' read -r name args; do
  [ -z "$name" ] && continue
  python3 tools/harness.py --out res/$name.jsonl $args >/dev/null 2>res/$name.err
  echo "$name done $(date +%T)" >> res/queue.log
done < "$1"
