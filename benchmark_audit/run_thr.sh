#!/bin/bash
# METHOD §10.6: threshold-triggered compaction (T = 64k estimated tokens) for the 7 compaction systems on
# MemoryAgentBench QA1 + QA2, and the uncompacted full history on LoCoMo; then pi_F / pi_F+R answering.
cd /home/ubuntu/agent_avalon/memory_prior
FW=/home/ubuntu/llm_infra/fw-env/bin/python
mkdir -p benchmark_audit/logs_v2 method/logs
one() {  # $1 system
  cd /home/ubuntu/agent_avalon/memory_prior/benchmark_audit
  $FW rescore.py $1 mab_ruler --workers 1 --save-ctx --mab-only qa1 > logs_v2/rescore_mab_ruler_$1.log 2>&1
  echo "$(date '+%F %T') thr qa1 $1 $(tail -n 1 logs_v2/rescore_mab_ruler_$1.log)" >> logs_v2/all_thr.log
  $FW rescore.py $1 mab_ruler --workers 1 --save-ctx --mab-only qa2 > logs_v2/rescore_mab_ruler_qa2_$1.log 2>&1
  echo "$(date '+%F %T') thr qa2 $1 $(tail -n 1 logs_v2/rescore_mab_ruler_qa2_$1.log)" >> logs_v2/all_thr.log
  cd /home/ubuntu/agent_avalon/memory_prior
  $FW method/protocols.py mab_ruler $1 > method/logs/protocols_mab_ruler_$1.log 2>&1
  $FW method/protocols.py mab_ruler_qa2 $1 > method/logs/protocols_mab_ruler_qa2_$1.log 2>&1
  echo "$(date '+%F %T') thr protocols $1 $(tail -n 1 method/logs/protocols_mab_ruler_$1.log) || $(tail -n 1 method/logs/protocols_mab_ruler_qa2_$1.log)" >> benchmark_audit/logs_v2/all_thr.log
}
for s in codex openhands aider gemini_cli anthropic_api langchain_summary neutral_roll; do one "$s@thr64k" & done
( cd benchmark_audit && $FW rescore.py full_history locomo --workers 5 --save-ctx > logs_v2/rescore_locomo_full_history.log 2>&1
  echo "$(date '+%F %T') full_history locomo $(tail -n 1 logs_v2/rescore_locomo_full_history.log)" >> logs_v2/all_thr.log
  cd .. && $FW method/protocols.py locomo full_history > method/logs/protocols_locomo_full_history.log 2>&1
  echo "$(date '+%F %T') full_history protocols $(tail -n 1 method/logs/protocols_locomo_full_history.log)" >> benchmark_audit/logs_v2/all_thr.log ) &
wait
echo "$(date '+%F %T') ALL DONE" >> benchmark_audit/logs_v2/all_thr.log
