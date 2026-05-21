#!/usr/bin/env bash
set -u
cd /Users/jameswatson/Dropbox/GIT/claude-video
LOG=tasks/watch_batch.log
: > "$LOG"
i=0
total=$(wc -l < tasks/top10_apify.txt | tr -d ' ')
while IFS= read -r url <&3; do
  [[ -z "$url" ]] && continue
  i=$((i+1))
  echo "[$(date '+%H:%M:%S')] START $i/$total $url" | tee -a "$LOG"
  if python3 scripts/watch.py "$url" --save-dir outputs/rxpert/ < /dev/null >> "$LOG" 2>&1; then
    echo "[$(date '+%H:%M:%S')] OK    $i/$total $url" | tee -a "$LOG"
  else
    rc=$?
    echo "[$(date '+%H:%M:%S')] FAIL  $i/$total $url (exit $rc)" | tee -a "$LOG"
  fi
done 3< tasks/top10_apify.txt
echo "[$(date '+%H:%M:%S')] BATCH DONE" | tee -a "$LOG"
