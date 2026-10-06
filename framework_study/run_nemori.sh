#!/bin/bash
cd /home/ubuntu/agent_avalon/memory_prior/framework_study
NE=/home/ubuntu/llm_infra/nemori-env/bin/python
FW=/home/ubuntu/llm_infra/fw-env/bin/python
$NE src/run_framework.py nemori --users 43 --distract 12 --workers 4 > logs/run_nemori.log 2>&1
$FW src/probe.py results/snapshots_nemori.jsonl > logs/probe_nemori.log 2>&1
echo "$(date '+%F %T') nemori done $(tail -n 1 logs/run_nemori.log) | $(tail -n 1 logs/probe_nemori.log)" >> logs/run_all.log
