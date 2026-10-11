"""V1 prior strength of the weak compactor (Llama-3.1-8B) on the step-4 subset S4, exactly as validate_v2.py V1
(20 forced-choice draws, T=1). Output: results/validation_v2_llama3-1-8b-instruct.json  (STEP5B_DESIGN.md §2)"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "framework_study/src"))
import validate_v2 as G
from sessions_v2 import S4
from infra.llm import batch_chat, budget
from validate import parse, ask, WORLD

M = "meta.llama3-1-8b-instruct-v1:0"
items = [x for x in S4 if x["type"] != "neutral"]
reqs, meta = [], []
for x in items:
    pre = G.V1_PREFIX_PREF if x["type"] == "preference" else G.V1_PREFIX
    for order in (0, 1):
        for s in range(10):
            reqs.append(dict(model=M, messages=[{"role": "system", "content": WORLD}, {"role": "user", "content": pre + ask(x["question"], x["options"], order)}],
                             temperature=1.0, sample_idx=s * 2 + order, max_tokens=12))
            meta.append(x)
res = batch_chat(reqs, workers=16, desc="V1 weak")
out = {}
for x, r in zip(meta, res):
    a = parse((r or {}).get("text", "") or "", x["options"])
    d = out.setdefault(x["id"], {"C": 0, "I": 0, "none": 0})
    d["C" if a == x["C"]["answer"] else "I" if a == x["I"]["answer"] else "none"] += 1
for d in out.values():
    n = d["C"] + d["I"]; d["p_congruent"] = d["C"] / n if n else None
(ROOT / "framework_study/results/validation_v2_llama3-1-8b-instruct.json").write_text(json.dumps({"model": M, "V1": out}, indent=1))
strong = sum(1 for d in out.values() if (d["p_congruent"] or 0) >= 0.8)
print(f"{len(out)} items, strong prior (>= 0.8) for {strong}; spent {budget()['spent_usd']:.2f}")
