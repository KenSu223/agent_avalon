"""B8 diagnostics: a second strong family, a small local model, and temperature.

A null is only worth much if it is not specific to one model or one decoding setting.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from infra.llm import estimate_cost
from stimuli import load_families, ROOT
from run_chains import run_many, load_distractors

RES = ROOT / "results"
K = 20
OPS = ["O1", "O3", "O4", "O5"]
SEEDS = [0, 1]


def jobs_for(man, fams, dis, surp_local, model, tag, T=1.0, B=150, slots=60, ops=OPS):
    out = []
    for ci, ch in enumerate(man["confirmatory_manifest"]["chains"]):
        for si in SEEDS:
            for op in ops:
                out.append({"chain": ch, "families": fams, "distractors": dis,
                            "surprise_local": surp_local,
                            "cfg": dict(run_id=f"{tag}-{op}-{ch['chain_id']}-s{si}", op=op,
                                        model=model, T=T, B=B, slots=slots, chain_idx=ci,
                                        seed_idx=si, n_seeds=len(SEEDS), rand_seed=3000 + si, K=K)})
    return out


if __name__ == "__main__":
    which = sys.argv[1]
    fams = load_families()
    man = json.loads((RES / "manifest.json").read_text())
    dis = load_distractors()
    sl = man["surprise_local"]
    if which == "llama":
        jobs = jobs_for(man, fams, dis, sl, "meta.llama3-3-70b-instruct-v1:0", "lla")
        out = "chains_diag_llama.jsonl"
    elif which == "local":
        jobs = jobs_for(man, fams, dis, sl, "local:qwen3-8b", "loc")
        out = "chains_diag_local.jsonl"
    elif which == "temp":
        jobs = []
        for T in (0.0, 1.3):
            jobs += jobs_for(man, fams, dis, sl, "qwen.qwen3-235b-a22b-2507-v1:0",
                             f"tmp{T}", T=T, ops=["O1", "O3"])
        out = "chains_diag_temp.jsonl"
    else:
        raise SystemExit("usage: run_diag.py llama|local|temp")
    paid = [j for j in jobs if j["cfg"]["op"] != "O3" and not j["cfg"]["model"].startswith("local")]
    print(f"{which}: {len(jobs)} trajectories, {len(paid)} paid, {len(paid)*(K+1)} calls, est "
          f"${estimate_cost(jobs[0]['cfg']['model'], len(paid)*(K+1), 1000, 420):.2f}")
    run_many(jobs, RES / out, workers=12, desc=which)
