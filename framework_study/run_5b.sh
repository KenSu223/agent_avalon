#!/bin/bash
# Loose end 5b (STEP5B_DESIGN.md): weak compactor Llama-3.1-8B, 4 systems x 96 users, checkpoints 0,2,4,8,12; probes by Qwen3-235B.
cd /home/ubuntu/agent_avalon/memory_prior/framework_study/src
FW=/home/ubuntu/llm_infra/fw-env/bin/python; M=meta.llama3-1-8b-instruct-v1:0
mkdir -p ../logs/step5b
for s in neutral_roll codex anthropic_api llamaindex_facts; do
  ( $FW run_framework.py $s --model $M --users 96 --workers 4 --v2 --checkpoints 0,2,4,8,12 --tag s4weak > ../logs/step5b/run_$s.log 2>&1
    $FW probe.py ../results/snapshots_${s}_s4weak.jsonl --answer-model qwen.qwen3-235b-a22b-2507-v1:0 > ../logs/step5b/probe_$s.log 2>&1
    echo "$(date '+%T') $s $(tail -n 1 ../logs/step5b/run_$s.log) | $(tail -n 1 ../logs/step5b/probe_$s.log | cut -c1-60)" >> ../logs/step5b/all.log ) &
done
wait; echo "$(date '+%T') ALL DONE" >> ../logs/step5b/all.log
