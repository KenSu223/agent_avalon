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


def eshift_chains(fams, frames, manifest, seed=4242):
    """chain per eligible family: target item + N_FILLER items from other families.
    Fillers are identical across the two arms of a family, which is all the paired design needs."""
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
        if not fr["eligible"] or fid not in conf:
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


def jobs_for(chains, frames, fams, dis, surp_local, seeds, ops=("O1", "O3"), slots=26):
    jobs = []
    for ci, (fid, ch) in enumerate(sorted(chains.items())):
        for arm in ("F+", "F-"):
            for si in seeds:
                for op in ops:
                    rid = f"es-{op}-{fid}-{'P' if arm=='F+' else 'M'}-s{si}"
                    cfg = dict(run_id=rid, op=op, model=MODEL, T=1.0, B=300, slots=slots,
                               chain_idx=ci, seed_idx=si, n_seeds=len(seeds),
                               rand_seed=5000 + si, K=K)
                    jobs.append({"chain": ch, "families": fams, "distractors": dis,
                                 "surprise_local": surp_local, "frame": frames[fid][arm],
                                 "cfg": cfg, "_arm": arm, "_family": fid})
    return jobs


if __name__ == "__main__":
    n_seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    slots = int(sys.argv[2]) if len(sys.argv) > 2 else 26
    fams = load_families()
    man = json.loads((RES / "manifest.json").read_text())
    fr = json.loads((RES / "frames.json").read_text())["frames"]
    dis = load_distractors()
    chains = eshift_chains(fams, fr, man)
    jobs = jobs_for(chains, fr, fams, dis, man["surprise_local"], list(range(n_seeds)), slots=slots)
    paid = [j for j in jobs if j["cfg"]["op"] == "O1"]
    print(f"E-SHIFT: {len(chains)} eligible families x 2 arms x {n_seeds} seeds x 2 operators "
          f"= {len(jobs)} trajectories")
    print(f"paid compactor calls: {len(paid)*(K+1)}  est "
          f"${estimate_cost(MODEL, len(paid)*(K+1), 1000, 420):.2f}")
    # record the arm/family mapping so the analysis never has to parse run ids
    (RES / "eshift_index.json").write_text(json.dumps(
        {j["cfg"]["run_id"]: {"arm": j["_arm"], "family_id": j["_family"],
                              "target_item": chains[j["_family"]]["target_item"],
                              "op": j["cfg"]["op"], "seed_idx": j["cfg"]["seed_idx"]}
         for j in jobs}, indent=1))
    run_many(jobs, RES / "chains_eshift.jsonl", workers=12, desc="eshift")
