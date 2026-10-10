#!/bin/bash
# Step 2.3 (PLAN.md): re-run every system with saved contexts (results_v2/). Deterministic systems hit the cache.
# LoCoMo: 12 systems. MemoryAgentBench: RULER-QA1 only, 11 systems (langmem fails there, loose end 5).
cd /home/ubuntu/agent_avalon/memory_prior/benchmark_audit
FW=/home/ubuntu/llm_infra/fw-env/bin/python
V1=/home/ubuntu/llm_infra/mem0v1-env/bin/python
mkdir -p logs_v2
run() {
  local extra=""; [ "$3" = mab_ruler ] && extra="--mab-only qa1"
  $1 rescore.py $2 $3 --workers 5 --save-ctx $extra > logs_v2/rescore_$3_$2.log 2>&1
  echo "$(date '+%F %T') $3 $2 $(tail -n 1 logs_v2/rescore_$3_$2.log)" >> logs_v2/all.log
}
( for s in raw_rag openhands aider; do run $FW $s locomo; run $FW $s mab_ruler; done ) &
( for s in mem0 anthropic_api gemini_cli; do run $FW $s locomo; run $FW $s mab_ruler; done ) &
( run $FW langmem locomo; for s in langchain_summary neutral_roll; do run $FW $s locomo; run $FW $s mab_ruler; done ) &
( run $FW llamaindex_facts_default locomo; run $FW llamaindex_facts_default mab_ruler; run $FW codex mab_ruler; run $V1 mem0_v1 locomo; run $V1 mem0_v1 mab_ruler ) &
wait
echo "$(date '+%F %T') ALL DONE" >> logs_v2/all.log
