#!/bin/bash
# Step 4 main runs (STEP4_DESIGN.md v1.0): 9 systems x 2 families x 192 users, checkpoints 0,4,12; then probes.
cd /home/ubuntu/agent_avalon/memory_prior/framework_study/src
FW=/home/ubuntu/llm_infra/fw-env/bin/python; V1=/home/ubuntu/llm_infra/mem0v1-env/bin/python; NE=/home/ubuntu/llm_infra/nemori-env/bin/python
mkdir -p ../logs/step4
one() {  # $1 python  $2 system  $3 family
  local M=qwen.qwen3-235b-a22b-2507-v1:0; [ $3 = llama ] && M=meta.llama3-3-70b-instruct-v1:0
  $1 run_framework.py $2 --model $M --users 192 --workers 6 --v2 --checkpoints 0,4,12 --tag s4$3 > ../logs/step4/run_${2}_$3.log 2>&1
  $FW probe.py ../results/snapshots_${2}_s4$3.jsonl --answer-model $M > ../logs/step4/probe_${2}_$3.log 2>&1
  echo "$(date '+%F %T') $2 $3 run: $(tail -n 1 ../logs/step4/run_${2}_$3.log) | probe: $(tail -n 1 ../logs/step4/probe_${2}_$3.log | cut -c1-80)" >> ../logs/step4/all.log
}
for fam in qwen llama; do
  for s in raw_history codex aider anthropic_api neutral_roll mem0 llamaindex_facts; do one $FW $s $fam & done
  one $V1 mem0_v1 $fam &
  one $NE nemori $fam &
done
wait
echo "$(date '+%F %T') ALL DONE" >> ../logs/step4/all.log
