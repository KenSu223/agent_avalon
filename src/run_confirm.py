"""B4/B7 (M4): the confirmatory main chains over the full operator lattice."""
import json, sys
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from infra.llm import estimate_cost
from stimuli import load_families, ROOT
from run_chains import run_many, load_distractors

RES = ROOT / "results"
MODEL = "qwen.qwen3-235b-a22b-2507-v1:0"
K = 20
PAID = {"O1", "O2", "O4", "O5", "O6", "O6-random", "O6-low"}


def jobs_for(man, fams, dis, surp_local, ops, seeds, B, T, slots):
    jobs = []
    for ci, ch in enumerate(man["confirmatory_manifest"]["chains"]):
        for si in seeds:
            for op in ops:
                rid = f"cf-{op}-{ch['chain_id']}-s{si}"
                jobs.append({"chain": ch, "families": fams, "distractors": dis,
                             "surprise_local": surp_local,
                             "cfg": dict(run_id=rid, op=op, model=MODEL, T=T, B=B, slots=slots,
                                         chain_idx=ci, seed_idx=si, n_seeds=len(seeds),
                                         rand_seed=2000 + si, K=K)})
    return jobs


if __name__ == "__main__":
    cfgf = json.loads((RES / "FROZEN_PROTOCOL.json").read_text())
    ops = cfgf.get("operators", ["O1", "O2", "O3", "O4", "O5", "O6", "O6-random", "O6-low", "O7"])
    seeds = list(range(cfgf["n_seeds"]))
    fams = load_families()
    man = json.loads((RES / "manifest.json").read_text())
    dis = load_distractors()
    jobs = jobs_for(man, fams, dis, man["surprise_local"], ops, seeds,
                    cfgf["B"], cfgf["T"], cfgf["slots"])
    paid = [j for j in jobs if j["cfg"]["op"] in PAID]
    print(f"confirmatory: {len(jobs)} trajectories, {len(paid)} paid, "
          f"{len(paid)*(K+1)} compactor calls, est "
          f"${estimate_cost(MODEL, len(paid)*(K+1), 1000, 420):.2f}")
    run_many(jobs, RES / "chains_confirm.jsonl", workers=12, desc="confirm")
