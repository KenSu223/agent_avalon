"""Summarise V3: retained / flipped / dropped by condition x generation x version (C vs I)."""
import json, sys, collections, random
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "framework_study/results"
items = {json.loads(l)["id"]: json.loads(l) for l in open(ROOT / "framework_study/stimuli/items.jsonl")}
rows = [json.loads(l) for l in open(RES / "v3_coded.jsonl")]


def rates(rs):
    n = len(rs)
    c = collections.Counter(r["label"] for r in rs)
    return n, {k: c[k] / n for k in ("RETAINED", "FLIPPED", "DROPPED", "DISAGREE", "UNPARSED")}


def boot_diff(a, b, key, n=2000, seed=0):
    """bootstrap CI over note sets for rate(a)-rate(b)."""
    rng = random.Random(seed)
    sets = sorted({r["set"] for r in a + b})
    def rate(rs):
        return sum(r["label"] == key for r in rs) / max(1, len(rs))
    by_a = collections.defaultdict(list); by_b = collections.defaultdict(list)
    for r in a: by_a[r["set"]].append(r)
    for r in b: by_b[r["set"]].append(r)
    ds = []
    for _ in range(n):
        s = [rng.choice(sets) for _ in sets]
        aa = [r for x in s for r in by_a[x]]; bb = [r for x in s for r in by_b[x]]
        ds.append(rate(aa) - rate(bb))
    ds.sort()
    return rate(a) - rate(b), ds[int(0.025 * n)], ds[int(0.975 * n)]


if __name__ == "__main__":
    conds = ["narrative-retell", "narrative-gist", "list-retell"]
    print("judge agreement:", round(sum(r["label"] != "DISAGREE" for r in rows) / len(rows), 3))
    for c in conds:
        print(f"\n=== {c} ===")
        print(f"{'gen':>3} | {'C: ret  flip  drop':>20} | {'I: ret  flip  drop':>20}")
        for g in range(0, 7):
            out = []
            for v in ("C", "I"):
                n, r = rates([x for x in rows if x["cond"] == c and x["gen"] == g and x["version"] == v])
                out.append(f"{r['RETAINED']:.2f} {r['FLIPPED']:.2f} {r['DROPPED']:.2f}")
            print(f"{g:>3} | {out[0]:>20} | {out[1]:>20}")
        last = [x for x in rows if x["cond"] == c and x["gen"] == 6]
        I = [x for x in last if x["version"] == "I"]; C = [x for x in last if x["version"] == "C"]
        for key in ("FLIPPED", "DROPPED", "RETAINED"):
            d, lo, hi = boot_diff(I, C, key)
            print(f"   gen6 I-C {key:8s}: {d:+.3f}  95% CI [{lo:+.3f}, {hi:+.3f}]")
        for tag, pred in (("normative", lambda i: items[i]["normative"]), ("descriptive", lambda i: not items[i]["normative"] and items[i]["type"] != "preference"),
                          ("preference", lambda i: items[i]["type"] == "preference")):
            Ii = [x for x in I if pred(x["item"])]; Cc = [x for x in C if pred(x["item"])]
            if Ii and Cc:
                print(f"   gen6 {tag:11s} I flip {rates(Ii)[1]['FLIPPED']:.2f} (n={len(Ii)})  C flip {rates(Cc)[1]['FLIPPED']:.2f}   I drop {rates(Ii)[1]['DROPPED']:.2f}  C drop {rates(Cc)[1]['DROPPED']:.2f}")
    # which I items get regularised
    flips = collections.Counter(); tot = collections.Counter()
    for x in rows:
        if x["version"] == "I" and x["gen"] == 6:
            tot[x["item"]] += 1; flips[x["item"]] += x["label"] == "FLIPPED"
    print("\nI-items most often regularised at gen 6 (all conditions):")
    for iid, k in flips.most_common(15):
        print(f"  {iid} {k}/{tot[iid]}  {items[iid]['I']['clause'][:80]}")
