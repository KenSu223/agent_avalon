#!/bin/bash
# METHOD §10.5: MemoryAgentBench RULER-QA2 replication, 11 systems, saved contexts -> results_v2/rescore_mab_ruler_<s>_qa2.jsonl
cd /home/ubuntu/agent_avalon/memory_prior/benchmark_audit
FW=/home/ubuntu/llm_infra/fw-env/bin/python
V1=/home/ubuntu/llm_infra/mem0v1-env/bin/python
mkdir -p logs_v2
run() {
  $1 rescore.py $2 mab_ruler --workers 5 --save-ctx --mab-only qa2 > logs_v2/rescore_mab_ruler_qa2_$2.log 2>&1
  echo "$(date '+%F %T') mab_ruler_qa2 $2 $(tail -n 1 logs_v2/rescore_mab_ruler_qa2_$2.log)" >> logs_v2/all_qa2.log
}
( for s in raw_rag openhands aider; do run $FW $s; done ) &
( for s in mem0 anthropic_api gemini_cli; do run $FW $s; done ) &
( for s in langchain_summary neutral_roll codex; do run $FW $s; done ) &
( run $FW llamaindex_facts_default; run $V1 mem0_v1 ) &
wait
echo "$(date '+%F %T') ALL DONE" >> logs_v2/all_qa2.log
