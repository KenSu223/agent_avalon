"""Operator contrasts on overall retention at k=10, with the two-way crossed cluster bootstrap.

This is where the positive finding lives once the surprise gradient turns out to be flat: O4 rewrites
under the SAME budget with the SAME model but never reads its own previous memory, so O4 - O1
isolates the cost of iterating on your own summary.
"""
import json, statistics, sys
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
import numpy as np
from stimuli import ROOT
import analysis as A

RES = ROOT / "results"
K = 10


def retention(rows, op):
    v = [r["retained"] for r in rows if r["op"] == op]
    return 100 * statistics.mean(v) if v else float("nan")


def main(n_boot=2000):
    man = json.loads((RES / "manifest.json").read_text())
    rows = A.attach(A.load_rows("confirm"), man)
    k10 = [r for r in rows if r["k"] == K and r["label"] != A.UNRESOLVED]
    ops = sorted({r["op"] for r in k10})

    def stat(sample):
        return {op: retention(sample, op) for op in ops}
    boot = A.crossed_bootstrap(k10, stat, n_boot=n_boot)

    point = stat(k10)
    out = {"k": K, "levels": {}, "contrasts": {}}
    for op in ops:
        d = [b[op] for b in boot if op in b and not np.isnan(b[op])]
        out["levels"][op] = {"retention": point[op], "ci95": A.ci(d) if d else None,
                             "n": sum(1 for r in k10 if r["op"] == op)}
    for op in ops:
        if op == "O1":
            continue
        d = [b[op] - b["O1"] for b in boot if op in b and "O1" in b]
        out["contrasts"][f"{op}_minus_O1"] = {
            "point": point[op] - point["O1"], "ci95": A.ci(d) if d else None,
            "excludes_zero": bool(d and (A.ci(d)[0] > 0 or A.ci(d)[1] < 0))}
    # survival curve by operator
    curve = {}
    for op in ops:
        curve[op] = {}
        for k in sorted({r["k"] for r in rows}):
            v = [r["retained"] for r in rows
                 if r["op"] == op and r["k"] == k and r["label"] != A.UNRESOLVED]
            curve[op][k] = 100 * statistics.mean(v) if v else None
    out["curves"] = curve
    (RES / "operator_contrasts.json").write_text(json.dumps(out, indent=1, default=float))

    print(f"retention at k={K} (%), with two-way crossed cluster bootstrap CIs")
    for op in ops:
        v = out["levels"][op]
        c = out["contrasts"].get(f"{op}_minus_O1")
        extra = (f"   vs O1: {c['point']:+6.1f} CI95 [{c['ci95'][0]:+.1f},{c['ci95'][1]:+.1f}]"
                 f"{'  *' if c['excludes_zero'] else ''}") if c else ""
        print(f"  {op:<11}{v['retention']:>6.1f}  CI95 [{v['ci95'][0]:.1f},{v['ci95'][1]:.1f}]"
              f"  n={v['n']}{extra}")
    print("\nretention curve by operator:")
    ks = sorted(curve["O1"])
    print(f"  {'op':<11}" + "".join(f"{k:>7}" for k in ks))
    for op in ops:
        print(f"  {op:<11}" + "".join(f"{(curve[op][k] or 0):>7.1f}" for k in ks))


if __name__ == "__main__":
    main()
