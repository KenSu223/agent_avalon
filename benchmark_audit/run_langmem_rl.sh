#!/bin/bash
# PLAN item 5c: LangMem with recursion_limit=100 on MemoryAgentBench RULER QA1 and QA2 (saved contexts), then pi_F / pi_F+R.
cd /home/ubuntu/agent_avalon/memory_prior/benchmark_audit
FW=/home/ubuntu/llm_infra/fw-env/bin/python
mkdir -p logs_v2
$FW rescore.py langmem_rl100 mab_ruler --workers 1 --save-ctx --mab-only qa1 > logs_v2/rescore_mab_ruler_langmem_rl100.log 2>&1 &
$FW rescore.py langmem_rl100 mab_ruler --workers 1 --save-ctx --mab-only qa2 > logs_v2/rescore_mab_ruler_qa2_langmem_rl100.log 2>&1 &
wait
cd ..
$FW method/protocols.py mab_ruler langmem_rl100 > method/logs/protocols_mab_ruler_langmem_rl100.log 2>&1
$FW method/protocols.py mab_ruler_qa2 langmem_rl100 > method/logs/protocols_mab_ruler_qa2_langmem_rl100.log 2>&1
echo "$(date '+%F %T') LANGMEM_RL DONE qa1: $(tail -n 1 benchmark_audit/logs_v2/rescore_mab_ruler_langmem_rl100.log) | qa2: $(tail -n 1 benchmark_audit/logs_v2/rescore_mab_ruler_qa2_langmem_rl100.log)" >> benchmark_audit/logs_v2/langmem_rl.log
