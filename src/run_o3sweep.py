"""Extended O3 slot sweep (no model calls) to calibrate the prior-blind control at the frozen
operating point. The control must sit in a measurable retention range or a null gradient in it
would be uninformative; A3's non-degeneracy requirement takes precedence over word-matching."""
import json, sys
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from stimuli import load_families, ROOT
from run_chains import run_many, load_distractors

RES = ROOT / "results"
if __name__ == "__main__":
    fams = load_families()
    man = json.loads((RES / "manifest.json").read_text())
    dis = load_distractors()
    jobs = []
    for slots in (56, 60, 64, 68):
        for ci, ch in enumerate(man["dev_manifest"]["chains"]):
            for si in (0, 1):
                jobs.append({"chain": ch, "families": fams, "distractors": dis,
                             "surprise_local": man["surprise_local"],
                             "cfg": dict(run_id=f"dev-O3-s{slots}-{ch['chain_id']}-s{si}", op="O3",
                                         model="qwen.qwen3-235b-a22b-2507-v1:0", T=1.0, B=150,
                                         slots=slots, chain_idx=ci, seed_idx=si, n_seeds=2,
                                         rand_seed=1000 + si, K=20)})
    print(f"{len(jobs)} free O3 trajectories")
    run_many(jobs, RES / "chains_o3sweep2.jsonl", workers=8, desc="o3")
