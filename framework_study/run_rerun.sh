#!/bin/bash
cd /home/ubuntu/agent_avalon/memory_prior/framework_study
FW=/home/ubuntu/llm_infra/fw-env/bin/python
for f in mem0 langmem; do
  $FW src/run_framework.py $f --users 43 --distract 12 --workers 5 > logs/run_$f.log 2>&1
  $FW src/probe.py results/snapshots_$f.jsonl > logs/probe_$f.log 2>&1
  echo "$(date '+%F %T') $f (rerun) done $(tail -n 1 logs/run_$f.log) | $(tail -n 1 logs/probe_$f.log)" >> logs/run_all.log
done
