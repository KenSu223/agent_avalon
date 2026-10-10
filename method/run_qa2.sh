#!/bin/bash
# METHOD §10.5: QA2 replication -- re-run with saved contexts, then answer under pi_F / pi_F+R.
cd /home/ubuntu/agent_avalon/memory_prior
benchmark_audit/run_v2_qa2.sh
for s in raw_rag openhands aider mem0 anthropic_api gemini_cli langchain_summary neutral_roll codex llamaindex_facts_default mem0_v1; do
  if [ -s benchmark_audit/results_v2/rescore_mab_ruler_${s}_qa2.jsonl ]; then
    /home/ubuntu/llm_infra/fw-env/bin/python method/protocols.py mab_ruler_qa2 $s > method/logs/protocols_mab_ruler_qa2_$s.log 2>&1
    echo "$(date '+%T') qa2 $s $(tail -n 1 method/logs/protocols_mab_ruler_qa2_$s.log)" >> method/logs/run_qa2.log
  else
    echo "$(date '+%T') qa2 $s MISSING rescore output" >> method/logs/run_qa2.log
  fi
done
echo "QA2 DONE" >> method/logs/run_qa2.log
