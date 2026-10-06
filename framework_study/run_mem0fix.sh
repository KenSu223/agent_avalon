#!/bin/bash
cd /home/ubuntu/agent_avalon/memory_prior/framework_study
FW=/home/ubuntu/llm_infra/fw-env/bin/python
$FW src/run_framework.py mem0 --users 43 --distract 12 --workers 5 > logs/run_mem0.log 2>&1
$FW src/probe.py results/snapshots_mem0.jsonl > logs/probe_mem0.log 2>&1
echo "$(date '+%F %T') mem0 (uncapped get_all) done $(tail -n 1 logs/run_mem0.log) | $(tail -n 1 logs/probe_mem0.log)" >> logs/run_all.log
