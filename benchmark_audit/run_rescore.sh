#!/bin/bash
# Re-score memory systems on LoCoMo and MemoryAgentBench ruler QA. Four chains in parallel.
cd /home/ubuntu/agent_avalon/memory_prior/benchmark_audit
FW=/home/ubuntu/llm_infra/fw-env/bin/python
V1=/home/ubuntu/llm_infra/mem0v1-env/bin/python
run() { $1 rescore.py $2 $3 --workers 5 > logs/rescore_$3_$2.log 2>&1; echo "$(date '+%F %T') $3 $2 $(tail -n 1 logs/rescore_$3_$2.log)" >> logs/rescore_all.log; }
mkdir -p logs
( for s in raw_rag codex openhands; do run $FW $s locomo; run $FW $s mab_ruler; done ) &
( for s in mem0 aider anthropic_api; do run $FW $s locomo; run $FW $s mab_ruler; done ) &
( for s in langmem gemini_cli langchain_summary; do run $FW $s locomo; run $FW $s mab_ruler; done ) &
( for s in llamaindex_facts_default neutral_roll; do run $FW $s locomo; run $FW $s mab_ruler; done; run $V1 mem0_v1 locomo; run $V1 mem0_v1 mab_ruler ) &
wait
echo "$(date '+%F %T') ALL DONE" >> logs/rescore_all.log
