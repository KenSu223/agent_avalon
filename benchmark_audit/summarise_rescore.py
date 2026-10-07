"""Re-scored memory systems on existing benchmarks, split by prior-answerability.

Prior-answerable item  = answered correctly closed-book (forced guess) by Qwen3-235B OR Llama-3.3-70B.
Prior-resistant item   = answered correctly by neither.
For each benchmark: per-system accuracy on all items / prior-resistant / prior-answerable, the ranks under each,
and the guess-corrected score (acc - g) / (1 - g), where g is the pooled closed-book forced accuracy of the same items.
"""
import json, glob, collections, sys
from pathlib import Path
R = Path(__file__).parent / "results"


def closed_book_sets():
    ans = collections.defaultdict(bool)
    for f in ("closed_book_qwen3-235b-a22b-2507.jsonl", "closed_book_llama3-3-70b-instruct.jsonl"):
        for l in open(R / f):
            r = json.loads(l)
            if r["proto"] == "forced" and r.get("correct"):
                ans[r["id"]] = True
    return ans


def spearman(a, b):
    ks = list(a)
    ra = {k: i for i, k in enumerate(sorted(ks, key=lambda k: -a[k]))}
    rb = {k: i for i, k in enumerate(sorted(ks, key=lambda k: -b[k]))}
    n = len(ks)
    d2 = sum((ra[k] - rb[k]) ** 2 for k in ks)
    return 1 - 6 * d2 / (n * (n * n - 1)) if n > 2 else float("nan")


def main():
    pa = closed_book_sets()
    for bench in ("locomo", "mab_ruler"):
        files = sorted(glob.glob(str(R / f"rescore_{bench}_*.jsonl")))
        files = [f for f in files if not f.endswith("_smoke.jsonl")]
        if not files:
            continue
        print(f"\n=== {bench} ===")
        res = {}
        for f in files:
            sysname = Path(f).stem.replace(f"rescore_{bench}_", "")
            rows = [json.loads(l) for l in open(f)]
            if bench == "locomo":
                rows = [r for r in rows if r["category"] != 5]
            else:
                rows = [r for r in rows if r.get("sub") == "ruler_qa1"]  # every system has QA1; QA2 only for some
            if not rows:
                print(f"  {sysname}: no rows (failed run) -- excluded")
                continue
            allr = [r for r in rows]
            resist = [r for r in rows if not pa[r["id"]]]
            answ = [r for r in rows if pa[r["id"]]]
            acc = lambda rs: sum(bool(r["correct"]) for r in rs) / len(rs) if rs else float("nan")
            res[sysname] = dict(all=acc(allr), resist=acc(resist), answ=acc(answ), n=len(allr), n_res=len(resist), n_ans=len(answ))
        n = next(iter(res.values()))
        print(f"items: {n['n']}  prior-resistant: {n['n_res']}  prior-answerable: {n['n_ans']} ({n['n_ans']/n['n']:.0%})")
        print(f"{'system':26s} {'all':>7s} {'resistant':>10s} {'answerable':>11s} {'rank all':>9s} {'rank resist':>12s}")
        ra = {k: i + 1 for i, k in enumerate(sorted(res, key=lambda k: -res[k]['all']))}
        rr = {k: i + 1 for i, k in enumerate(sorted(res, key=lambda k: -res[k]['resist']))}
        for k in sorted(res, key=lambda k: -res[k]["all"]):
            v = res[k]
            print(f"{k:26s} {v['all']:7.3f} {v['resist']:10.3f} {v['answ']:11.3f} {ra[k]:9d} {rr[k]:12d}")
        print(f"Spearman(rank all, rank resistant) = {spearman({k: v['all'] for k, v in res.items()}, {k: v['resist'] for k, v in res.items()}):.3f}")
        alls = [v["all"] for v in res.values()]; rs = [v["resist"] for v in res.values()]
        print(f"spread (max-min): all {max(alls)-min(alls):.3f}  resistant {max(rs)-min(rs):.3f}")


if __name__ == "__main__":
    main()
