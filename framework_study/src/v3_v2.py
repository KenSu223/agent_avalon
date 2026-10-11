"""V3 Bartlett positive control for the expanded item set (STEP3_DESIGN.md §3): validates the material as a whole,
not an inclusion gate.

Subset: 120 final items (rule / procedure / preference only: neutral items have no schema, updates are two-stage),
stratified by type in proportion to the final set, seed 0. Everything else is the original V3 unchanged
(v3_reproduction.py): 30 note sets x 8 items, 3 conditions (narrative-retell, narrative-gist, list-retell),
6 generations, Qwen3-235B at T=1, memory-state coding by gpt-oss-120b and gemma-3-27b.
Pre-registered prediction: I -> C (regularisation toward the schema) exceeds C -> I, as in the original V3.
Outputs: framework_study/results/v3_v2_chains.json, v3_v2_coded.jsonl, v3_v2_summary.txt
"""
import json, random, collections, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "framework_study/src")); sys.path.insert(0, str(ROOT / "framework_study/stimuli"))
import v3_reproduction as V3
from infra.llm import budget

OUT = ROOT / "framework_study/results"
N_SUBSET = 120


def subset():
    final = [json.loads(l) for l in open(ROOT / "framework_study/stimuli/items_v2_final.jsonl")]
    pool = [x for x in final if x["type"] in ("rule", "procedure", "preference")]
    rng = random.Random(0)
    by = collections.defaultdict(list)
    for x in pool:
        by[x["type"]].append(x)
    alloc = {t: round(N_SUBSET * len(v) / len(pool)) for t, v in by.items()}
    while sum(alloc.values()) != N_SUBSET:
        t = max(alloc, key=lambda k: len(by[k]) - alloc[k]) if sum(alloc.values()) < N_SUBSET else max(alloc, key=alloc.get)
        alloc[t] += 1 if sum(alloc.values()) < N_SUBSET else -1
    return [x for t, v in by.items() for x in rng.sample(v, alloc[t])]


def summarise(rows):
    lines = []
    for cond in ("narrative-retell", "narrative-gist", "list-retell"):
        rs = [r for r in rows if r["cond"] == cond and r["gen"] >= 1]
        ic = [r for r in rs if r["version"] == "I"]; cc = [r for r in rs if r["version"] == "C"]
        rate = lambda s, lab: sum(r["label"] == lab for r in s) / max(1, len(s))
        sets = sorted({r["set"] for r in rs})
        rng = random.Random(0)
        by = collections.defaultdict(list)
        for r in rs:
            by[r["set"]].append(r)
        ds = []
        for _ in range(2000):
            samp = [r for s in (rng.choice(sets) for _ in sets) for r in by[s]]
            ds.append(rate([r for r in samp if r["version"] == "I"], "FLIPPED") - rate([r for r in samp if r["version"] == "C"], "FLIPPED"))
        ds.sort()
        lines.append(f"{cond:17s} I->C {rate(ic, 'FLIPPED'):.3f}  C->I {rate(cc, 'FLIPPED'):.3f}  difference {rate(ic, 'FLIPPED') - rate(cc, 'FLIPPED'):+.3f} "
                     f"[{ds[50]:+.3f},{ds[1949]:+.3f}]  dropped I {rate(ic, 'DROPPED'):.3f} C {rate(cc, 'DROPPED'):.3f}  "
                     f"judge agreement {1 - rate(rs, 'DISAGREE'):.3f}")
    return "\n".join(lines)


def main():
    sub = subset()
    V3.ITEMS = sub                      # make_sets / chat_transcript / list_transcript / code all read V3.ITEMS
    sets = V3.make_sets(seed=0)
    state = V3.run_chains(sets)
    json.dump({"items": [x["id"] for x in sub], "sets": sets, "state": {f"{c}|{s}": h for (c, s), h in state.items()}},
              open(OUT / "v3_v2_chains.json", "w"))
    rows = V3.code(sets, state)
    with open(OUT / "v3_v2_coded.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    text = summarise(rows)
    (OUT / "v3_v2_summary.txt").write_text(text + "\n")
    print(text); print("spent", budget()["spent_usd"])


if __name__ == "__main__":
    main()
