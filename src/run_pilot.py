"""M2: the dev pilot. Selects the operating point and discharges amendments A1 and A3.

Runs ONLY on dev families (F01-F12). Nothing here touches a confirmatory family.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from infra.llm import estimate_cost
from stimuli import load_families, ROOT
from run_chains import run_many, load_distractors

RES = ROOT / "results"
MODEL = "qwen.qwen3-235b-a22b-2507-v1:0"
K = 20
SEEDS = [0, 1]


def jobs_for(man, fams, dis, surp_local):
    out = []
    chains = man["dev_manifest"]["chains"]
    # --- O1 operating-point sweep: budget x temperature
    for B in (150, 300, 600):
        for T in (0.0, 1.0):
            for ci, ch in enumerate(chains):
                for si in SEEDS:
                    rid = f"dev-O1-B{B}-T{T}-{ch['chain_id']}-s{si}"
                    out.append({"chain": ch, "families": fams, "distractors": dis,
                                "surprise_local": surp_local,
                                "cfg": dict(run_id=rid, op="O1", model=MODEL, T=T, B=B,
                                            chain_idx=ci, seed_idx=si, n_seeds=len(SEEDS),
                                            rand_seed=1000 + si, K=K)})
    # --- O7 access ceiling (free, no model calls)
    for ci, ch in enumerate(chains):
        for si in SEEDS:
            out.append({"chain": ch, "families": fams, "distractors": dis,
                        "surprise_local": surp_local,
                        "cfg": dict(run_id=f"dev-O7-{ch['chain_id']}-s{si}", op="O7", model=MODEL,
                                    T=1.0, B=300, chain_idx=ci, seed_idx=si, n_seeds=len(SEEDS),
                                    rand_seed=1000 + si, K=K)})
    # --- O3 slot sweep for amendment A3 (free, no model calls)
    for slots in (10, 14, 18, 22, 26, 30, 34, 40):
        for ci, ch in enumerate(chains):
            for si in SEEDS:
                out.append({"chain": ch, "families": fams, "distractors": dis,
                            "surprise_local": surp_local,
                            "cfg": dict(run_id=f"dev-O3-s{slots}-{ch['chain_id']}-s{si}", op="O3",
                                        model=MODEL, T=1.0, B=300, slots=slots, chain_idx=ci,
                                        seed_idx=si, n_seeds=len(SEEDS), rand_seed=1000 + si, K=K)})
    return out


if __name__ == "__main__":
    fams = load_families()
    man = json.loads((RES / "manifest.json").read_text())
    dis = load_distractors()
    surp_local = man["surprise_local"]
    jobs = jobs_for(man, fams, dis, surp_local)
    n_llm = sum(1 for j in jobs if j["cfg"]["op"] in ("O1", "O2", "O4", "O5") or
                j["cfg"]["op"].startswith("O6"))
    print(f"{len(jobs)} trajectories ({n_llm} use the compactor), K={K}")
    print(f"est compactor calls: {n_llm*(K+1)}  est cost "
          f"${estimate_cost(MODEL, n_llm*(K+1), 1000, 420):.2f}")
    run_many(jobs, RES / "chains_dev.jsonl", workers=10, desc="dev")
