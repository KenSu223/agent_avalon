"""End-to-end smoke test: one short trajectory per operator, coded with the regex pass only."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from stimuli import load_families, build_chains, render, world
from run_chains import run_trajectory, load_distractors
import coder

fams = load_families()
dis = load_distractors()
man = build_chains(fams, restarts=300)
chain = man["chains"][0]
famd = {f["family_id"]: f for f in fams}

MODEL = "qwen.qwen3-235b-a22b-2507-v1:0"
surprise_local = {it["item_id"]: float(it["level"]) for it in chain["items"]}

for op in ["O1", "O2", "O3", "O5", "O6", "O7"]:
    cfg = dict(run_id=f"smoke-{op}", op=op, model=MODEL, T=1.0, B=300, slots=12,
               chain_idx=0, seed_idx=0, n_seeds=3, rand_seed=1, K=3)
    t0 = time.time()
    rec = run_trajectory(chain, fams, dis, cfg, surprise_local)
    w = rec["world"]
    labs = {}
    last = rec["snapshots"][-1]
    for it in rec["items"]:
        f = famd[it["family_id"]]
        item = {"level": it["level"], "attribute_rendered": render(f["attribute_regex"], w),
                "sentence_rendered": "", "question_rendered": ""}
        lab, dest, nj, ev = coder.code_regex(last["notes"], item, f)
        labs[lab] = labs.get(lab, 0) + 1
    pin_ok = ""
    if rec.get("pins"):
        kept = sum(1 for p in rec["pins"] if p in last["notes"])
        pin_ok = f" pins={kept}/{len(rec['pins'])}"
    print(f"{op}: {time.time()-t0:5.0f}s  ${rec['cost_usd']:.4f}  stored_words@k3={last['words']:4d} "
          f"trim={rec['n_hard_trimmed']} retry={rec['n_budget_retries']}{pin_ok}  labels={labs}")
    if op == "O1":
        print("   --- M_3 notes (first 400 chars) ---")
        print("   " + last["notes"][:400].replace("\n", "\n   "))
