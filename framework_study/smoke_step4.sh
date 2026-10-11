#!/bin/bash
# Step 4 smoke test: 2 users per system and family, tag smoke_*; measures cost and library robustness under Llama.
cd /home/ubuntu/agent_avalon/memory_prior/framework_study/src
FW=/home/ubuntu/llm_infra/fw-env/bin/python; V1=/home/ubuntu/llm_infra/mem0v1-env/bin/python; NE=/home/ubuntu/llm_infra/nemori-env/bin/python
mkdir -p ../logs/step4
for fam in qwen llama; do
  M=qwen.qwen3-235b-a22b-2507-v1:0; [ $fam = llama ] && M=meta.llama3-3-70b-instruct-v1:0
  for s in raw_history codex aider anthropic_api neutral_roll mem0 llamaindex_facts; do
    $FW run_framework.py $s --model $M --users 2 --workers 2 --v2 --checkpoints 0,4,12 --tag smoke_$fam > ../logs/step4/smoke_${s}_$fam.log 2>&1 &
  done
  $V1 run_framework.py mem0_v1 --model $M --users 2 --workers 2 --v2 --checkpoints 0,4,12 --tag smoke_$fam > ../logs/step4/smoke_mem0_v1_$fam.log 2>&1 &
  $NE run_framework.py nemori --model $M --users 2 --workers 2 --v2 --checkpoints 0,4,12 --tag smoke_$fam > ../logs/step4/smoke_nemori_$fam.log 2>&1 &
done
wait
echo SMOKE DONE
