"""E-SHIFT (B3): the decisive causal test.

One trajectory per (family, arm, seed). The chain holds that family's TARGET item plus a fixed set
of filler items drawn from other families. Across the two arms of a family, everything is identical
-- the target sentence, its value, its position, the fillers, the distractors, the seed -- except a
single value-free role sentence at the top of the seeding session.

The same chains are also run under O3 (COPY-RAND) as a free frame control: O3 cannot condition on
the frame, so an arm difference there would expose residual interference rather than a prior effect.
"""
import json, random, sys
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from infra.llm import estimate_cost
from stimuli import load_families, ROOT
from run_chains import run_many, load_distractors

RES = ROOT / "results"
MODEL = "qwen.qwen3-235b-a22b-2507-v1:0"
N_FILLER = 18
K = 20


def eshift_chains(fams, frames, manifest, seed=4242, split="confirmatory"):
    """chain per eligible family: target item + N_FILLER items from other families.
    Fillers are identical across the two arms of a family, which is all the paired design needs."""
    # target families come from `split`; FILLERS always come from the confirmatory pool so that a
    # dev-stage variance estimate never changes what the confirmatory chains look like
    tgt_pool = {f["family_id"] for f in fams if f["split"] == split and f["kind"] == "mundane"}
    conf = {f["family_id"] for f in fams if f["split"] == "confirmatory" and f["kind"] == "mundane"}
    rng = random.Random(seed)
    pool_by_fam = {}
    for f in fams:
        if f["family_id"] in conf:
            pool_by_fam[f["family_id"]] = [
                {"family_id": f["family_id"], "level": lv["level"], "kind": "mundane",
                 "item_id": f"{f['family_id']}L{lv['level']}"} for lv in f["levels"]]
    out = {}
    for fid, fr in frames.items():
        if not fr["eligible"] or fid not in tgt_pool:
            continue
        target = {"family_id": fid, "level": fr["target_level"], "kind": "mundane",
                  "item_id": f"{fid}L{fr['target_level']}"}
        others = sorted(x for x in conf if x != fid)
        r = random.Random(hash(fid) % 10**6)
        r.shuffle(others)
        fillers = [r.choice(pool_by_fam[o]) for o in others[:N_FILLER]]
        items = fillers[:]
        pos = r.randrange(len(items) + 1)          # target position, fixed across arms
        items.insert(pos, target)
        out[fid] = {"chain_id": f"E-{fid}", "items": items, "target_item": target["item_id"],
                    "target_pos": pos}
    return out


def jobs_for(chains, frames, fams, dis, surp_local, seeds, ops=("O1", "O3"), slots=26,
             B=300, T=1.0):
    jobs = []
    for ci, (fid, ch) in enumerate(sorted(chains.items())):
        for arm in ("F+", "F-"):
            for si in seeds:
                for op in ops:
                    rid = f"es-{op}-{fid}-{'P' if arm=='F+' else 'M'}-s{si}"
                    cfg = dict(run_id=rid, op=op, model=MODEL, T=T, B=B, slots=slots,
                               chain_idx=ci, seed_idx=si, n_seeds=len(seeds),
                               rand_seed=5000 + si, K=K)
                    jobs.append({"chain": ch, "families": fams, "distractors": dis,
                                 "surprise_local": surp_local, "frame": frames[fid][arm],
                                 "cfg": cfg, "_arm": arm, "_family": fid})
    return jobs


if __name__ == "__main__":
    split = sys.argv[1] if len(sys.argv) > 1 else "confirmatory"
    n_seeds = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    slots = int(sys.argv[3]) if len(sys.argv) > 3 else 26
    B = int(sys.argv[4]) if len(sys.argv) > 4 else 300
    T = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
    tag = "eshift" if split == "confirmatory" else "eshift_dev"
    fams = load_families()
    man = json.loads((RES / "manifest.json").read_text())
    fr = json.loads((RES / "frames.json").read_text())["frames"]
    dis = load_distractors()
    chains = eshift_chains(fams, fr, man, split=split)
    jobs = jobs_for(chains, fr, fams, dis, man["surprise_local"], list(range(n_seeds)),
                    slots=slots, B=B, T=T)
    for j in jobs:
        j["cfg"]["run_id"] = f"{tag}-" + j["cfg"]["run_id"]
    paid = [j for j in jobs if j["cfg"]["op"] == "O1"]
    print(f"E-SHIFT [{split}]: {len(chains)} eligible families x 2 arms x {n_seeds} seeds "
          f"x 2 operators = {len(jobs)} trajectories (B={B}, T={T}, slots={slots})")
    print(f"paid compactor calls: {len(paid)*(K+1)}  est "
          f"${estimate_cost(MODEL, len(paid)*(K+1), 1000, 420):.2f}")
    # record the arm/family mapping so the analysis never has to parse run ids
    idx_path = RES / ("eshift_index.json" if split == "confirmatory" else "eshift_dev_index.json")
    idx_path.write_text(json.dumps(
        {j["cfg"]["run_id"]: {"arm": j["_arm"], "family_id": j["_family"],
                              "target_item": chains[j["_family"]]["target_item"],
                              "op": j["cfg"]["op"], "seed_idx": j["cfg"]["seed_idx"]}
         for j in jobs}, indent=1))
    run_many(jobs, RES / f"chains_{tag}.jsonl", workers=16, desc=tag)
