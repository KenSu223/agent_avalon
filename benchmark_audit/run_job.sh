#!/bin/bash
# $1 env (fw|v1) $2 system $3 bench
cd /home/ubuntu/agent_avalon/memory_prior/benchmark_audit
PY=/home/ubuntu/llm_infra/fw-env/bin/python; [ "$1" = v1 ] && PY=/home/ubuntu/llm_infra/mem0v1-env/bin/python
EXTRA=""; [ "$3" = mab_ruler ] && EXTRA="--mab-only qa1"
# skip if the same job is already running (avoids duplicate writers to one result file)
if ps -eo args | grep -v grep | grep -q "rescore.py $2 $3"; then echo "$(date '+%F %T') $3 $2 skipped (already running)" >> logs/rescore_all.log; exit 0; fi
$PY rescore.py $2 $3 --workers 5 $EXTRA > logs/rescore_$3_$2.log 2>&1
echo "$(date '+%F %T') $3 $2 $(tail -n 1 logs/rescore_$3_$2.log)" >> logs/rescore_all.log
