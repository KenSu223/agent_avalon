#!/bin/bash
# Re-run of Mem0 on MemoryAgentBench QA2: the first run was killed by the proxy restart (2026-10-11 00:21, "Connection error").
cd /home/ubuntu/agent_avalon/memory_prior/benchmark_audit
FW=/home/ubuntu/llm_infra/fw-env/bin/python
$FW rescore.py mem0 mab_ruler --workers 5 --save-ctx --mab-only qa2 > logs_v2/rescore_mab_ruler_qa2_mem0_rerun.log 2>&1
echo "$(date '+%F %T') mab_ruler_qa2 mem0 RERUN $(tail -n 1 logs_v2/rescore_mab_ruler_qa2_mem0_rerun.log)" >> logs_v2/all_qa2.log
cd .. && $FW method/protocols.py mab_ruler_qa2 mem0 > method/logs/protocols_mab_ruler_qa2_mem0.log 2>&1
echo "$(date '+%T') qa2 mem0 (rerun) $(tail -n 1 method/logs/protocols_mab_ruler_qa2_mem0.log)" >> method/logs/run_qa2.log
