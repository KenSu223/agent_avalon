#!/bin/bash
# Run every framework (43 users, 12 distractor sessions) and probe the snapshots. Three batches in parallel.
cd /home/ubuntu/agent_avalon/memory_prior/framework_study
FW=/home/ubuntu/llm_infra/fw-env/bin/python
V1=/home/ubuntu/llm_infra/mem0v1-env/bin/python
run() {  # $1 python, $2 framework
  $1 src/run_framework.py $2 --users 43 --distract 12 --workers 5 > logs/run_$2.log 2>&1
  $FW src/probe.py results/snapshots_$2.jsonl > logs/probe_$2.log 2>&1
  echo "$(date '+%F %T') $2 done $(tail -n 1 logs/run_$2.log) | $(tail -n 1 logs/probe_$2.log)" >> logs/run_all.log
}
( for f in raw_history neutral_roll codex openhands; do run $FW $f; done ) &
( for f in aider gemini_cli anthropic_api langchain_summary; do run $FW $f; done ) &
( for f in mem0 langmem llamaindex_facts; do run $FW $f; done; run $V1 mem0_v1 ) &
wait
echo "$(date '+%F %T') ALL DONE" >> logs/run_all.log
