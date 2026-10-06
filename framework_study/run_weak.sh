#!/bin/bash
# Weak-compactor replication: product replicas driven by local Qwen3-8B (vLLM); probes unchanged (Qwen3-235B answers, same judges).
cd /home/ubuntu/agent_avalon/memory_prior/framework_study
FW=/home/ubuntu/llm_infra/fw-env/bin/python
run() {
  $FW src/run_framework.py $1 --model local:qwen3-8b --users 43 --distract 12 --workers 8 --tag weak8b > logs/run_$1_weak8b.log 2>&1
  $FW src/probe.py results/snapshots_$1_weak8b.jsonl > logs/probe_$1_weak8b.log 2>&1
  echo "$(date '+%F %T') $1 (weak8b) done $(tail -n 1 logs/run_$1_weak8b.log) | $(tail -n 1 logs/probe_$1_weak8b.log)" >> logs/run_all.log
}
( for f in neutral_roll codex aider gemini_cli; do run $f; done ) &
( for f in openhands anthropic_api langchain_summary; do run $f; done ) &
wait
echo "$(date '+%F %T') WEAK DONE" >> logs/run_all.log
