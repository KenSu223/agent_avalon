"""Capacity-matched prior-blind control (free: no model calls)."""
import json, sys
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from stimuli import load_families, ROOT
from run_chains import run_many, load_distractors
RES = ROOT / "results"
if __name__ == "__main__":
    fams = load_families(); man = json.loads((RES/"manifest.json").read_text()); dis = load_distractors()
    jobs = []
    for ci, ch in enumerate(man["confirmatory_manifest"]["chains"]):
        for si in range(3):
            jobs.append({"chain": ch, "families": fams, "distractors": dis,
                         "surprise_local": man["surprise_local"],
                         "cfg": dict(run_id=f"cf-O3W-{ch['chain_id']}-s{si}", op="O3W",
                                     model="qwen.qwen3-235b-a22b-2507-v1:0", T=1.0, B=150,
                                     chain_idx=ci, seed_idx=si, n_seeds=3, rand_seed=2000+si, K=20)})
    print(f"{len(jobs)} free O3W trajectories")
    run_many(jobs, RES / "chains_o3w.jsonl", workers=8, desc="o3w")
