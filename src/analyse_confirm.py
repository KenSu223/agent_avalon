"""C2/C3/C4/C5/C6: the confirmatory main-chain analysis."""
import json, statistics, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
import numpy as np
from stimuli import ROOT
import analysis as A

RES = ROOT / "results"
PRIMARY_K = 10
SESOI_O3 = 5.0          # equivalence margin in percentage points, over the IQR surprise contrast


def iqr_contrast(rows):
    s = sorted(r["surprise"] for r in rows)
    return s[int(0.75 * len(s))] - s[int(0.25 * len(s))]


def run(tag="confirm", n_boot=2000):
    man = json.loads((RES / "manifest.json").read_text())
    rows = A.attach(A.load_rows(tag), man)
    k10 = [r for r in rows if r["k"] == PRIMARY_K and r["label"] != A.UNRESOLVED]
    mund = [r for r in k10 if r["kind"] == "mundane"]
    iqr = iqr_contrast(mund)

    out = {"n_rows": len(rows), "n_k10": len(k10), "n_mundane_k10": len(mund),
           "iqr_surprise": iqr, "primary_k": PRIMARY_K,
           "unresolved_rate": sum(1 for r in rows if r["label"] == A.UNRESOLVED) / max(1, len(rows))}

    # ---- C2 / C3 / C4: per-operator slope, from a family-FE linear probability model
    pair = [r for r in mund if r["op"] in ("O1", "O3")]
    point = A.lpm(pair, interact_ops=["O1", "O3"])
    boot = A.crossed_bootstrap(pair, lambda s: A.lpm(s, interact_ops=["O1", "O3"]), n_boot=n_boot)
    def dist(key):
        return [b[key] for b in boot if key in b]
    out["C2_slope_O1_pp_per_logodds"] = {"point": point.get("slope_O1"),
                                         "ci95": A.ci(dist("slope_O1")),
                                         "pp_over_iqr": point.get("slope_O1", 0) * iqr}
    out["C3_slope_O3_pp_per_logodds"] = {"point": point.get("slope_O3"),
                                         "ci95": A.ci(dist("slope_O3"))}
    inter_key = [k for k in point if k.startswith("interaction_")]
    if inter_key:
        kk = inter_key[0]
        out["C3_interaction"] = {"key": kk, "point": point[kk], "ci95": A.ci(dist(kk))}
    # equivalence on the control slope, expressed in pp over the IQR contrast
    o3_pp = [b["slope_O3"] * iqr for b in boot if "slope_O3" in b]
    out["C3_O3_equivalence"] = A.tost(o3_pp, SESOI_O3)
    out["C3_O3_equivalence"]["units"] = "pp of retention across the interquartile surprise contrast"

    # ---- C4: every operator's slope, same model, same bootstrap
    allops = A.lpm(mund)
    ball = A.crossed_bootstrap(mund, A.lpm, n_boot=max(400, n_boot // 3))
    out["C4_slopes_by_operator"] = {}
    for k in sorted(x for x in allops if x.startswith("slope_")):
        d = [b[k] for b in ball if k in b]
        out["C4_slopes_by_operator"][k.replace("slope_", "")] = {
            "point": allops[k], "ci95": A.ci(d) if d else None,
            "pp_over_iqr": allops[k] * iqr}

    # ---- retention by operator and tercile, for the figure and the adequacy check
    s = sorted(r["surprise"] for r in mund)
    t1, t2 = s[len(s)//3], s[2*len(s)//3]
    by = defaultdict(lambda: [[], [], []])
    for r in mund:
        g = 0 if r["surprise"] <= t1 else (1 if r["surprise"] <= t2 else 2)
        by[r["op"]][g].append(r["retained"])
    out["retention_by_operator_tercile"] = {
        op: {"low": 100*statistics.mean(g[0]) if g[0] else None,
             "mid": 100*statistics.mean(g[1]) if g[1] else None,
             "high": 100*statistics.mean(g[2]) if g[2] else None,
             "gap_low_minus_high": (100*statistics.mean(g[0]) - 100*statistics.mean(g[2]))
                                   if g[0] and g[2] else None,
             "n": sum(len(x) for x in g)}
        for op, g in sorted(by.items())}

    # ---- C5: direction of replacement
    d = A.direction([r for r in rows if r["op"] in ("O1", "O4", "O5") and r["kind"] == "mundane"], man)
    out["C5_direction"] = {k: v for k, v in d.items() if not k.startswith("_")}

    # ---- C6: value-level kernel, held-out trajectories
    runs = sorted({r["run_id"] for r in rows if r["op"] == "O1"})
    half = set(runs[::2])
    tr = [r for r in rows if r["op"] == "O1" and r["run_id"] in half]
    te = [r for r in rows if r["op"] == "O1" and r["run_id"] not in half]
    if tr and te:
        out["C6_kernel"] = A.kernel_predict(tr, te, man)

    # ---- C7: mitigation ladder
    mit = {}
    for op in ("O1", "O5", "O6", "O6-random", "O6-low"):
        hi = [r["retained"] for r in mund if r["op"] == op and r["surprise"] > t2]
        lo = [r["retained"] for r in mund if r["op"] == op and r["surprise"] <= t1]
        if hi:
            mit[op] = {"high_surprise_retention": 100*statistics.mean(hi),
                       "low_surprise_retention": 100*statistics.mean(lo) if lo else None,
                       "n_high": len(hi)}
    out["C7_mitigation"] = mit
    return out


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else "confirm"
    r = run(tag)
    (RES / f"confirm_result_{tag}.json").write_text(json.dumps(r, indent=1, default=float))
    print(json.dumps({k: v for k, v in r.items() if k.startswith(("C2", "C3", "n_", "iqr"))},
                     indent=1, default=float))
    print("\nretention by operator and surprise tercile (k=10):")
    for op, v in r["retention_by_operator_tercile"].items():
        print(f"  {op:<10} low {v['low']:>6.1f}  mid {v['mid'] or 0:>6.1f}  high {v['high']:>6.1f}"
              f"   gap {v['gap_low_minus_high']:>+6.1f} pp   n={v['n']}")
