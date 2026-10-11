#!/bin/bash
# Step 4 repair: users that failed because Bedrock throttled Llama (HTTP 429) are re-run (run_framework resumes and
# skips completed users), at low concurrency, until every run has all 192 users; then the snapshots are re-probed
# (already-probed rows come from the cache). Waits for run_step4.sh to finish first.
cd /home/ubuntu/agent_avalon/memory_prior/framework_study/src
FW=/home/ubuntu/llm_infra/fw-env/bin/python; V1=/home/ubuntu/llm_infra/mem0v1-env/bin/python; NE=/home/ubuntu/llm_infra/nemori-env/bin/python
until grep -q "ALL DONE" ../logs/step4/all.log 2>/dev/null; do sleep 60; done
users() { [ -f ../results/snapshots_$1_s4$2.jsonl ] && python3 -c "import json;print(len({json.loads(l)['user'] for l in open('../results/snapshots_$1_s4$2.jsonl')}))" || echo 0; }
py() { case $1 in mem0_v1) echo $V1;; nemori) echo $NE;; *) echo $FW;; esac; }
for attempt in 1 2 3 4; do
  todo=""
  for fam in qwen llama; do for s in raw_history codex aider anthropic_api neutral_roll mem0 llamaindex_facts mem0_v1 nemori; do
    [ "$(users $s $fam)" -lt 192 ] && todo="$todo $s:$fam"
  done; done
  echo "$(date '+%F %T') attempt $attempt todo:$todo" >> ../logs/step4/repair.log
  [ -z "$todo" ] && break
  # at most 3 runs at a time, 3 workers each, to stay under the Llama token-rate limit
  n=0
  for job in $todo; do
    s=${job%%:*}; fam=${job##*:}; M=qwen.qwen3-235b-a22b-2507-v1:0; [ $fam = llama ] && M=meta.llama3-3-70b-instruct-v1:0
    $(py $s) run_framework.py $s --model $M --users 192 --workers 3 --v2 --checkpoints 0,4,12 --tag s4$fam >> ../logs/step4/repair_${s}_$fam.log 2>&1 &
    n=$((n+1)); [ $((n % 3)) -eq 0 ] && wait
  done
  wait
done
for fam in qwen llama; do for s in raw_history codex aider anthropic_api neutral_roll mem0 llamaindex_facts mem0_v1 nemori; do
  M=qwen.qwen3-235b-a22b-2507-v1:0; [ $fam = llama ] && M=meta.llama3-3-70b-instruct-v1:0
  echo "$(date '+%F %T') $s $fam users $(users $s $fam)" >> ../logs/step4/repair.log
  $FW probe.py ../results/snapshots_${s}_s4$fam.jsonl --answer-model $M > ../logs/step4/reprobe_${s}_$fam.log 2>&1
done; done
echo "$(date '+%F %T') REPAIR DONE" >> ../logs/step4/repair.log
