"""Round-1 reviewer fixes: per-judge estimates, worst-case bounds for unresolved cases,
missingness by operator/frame, the direct O6 vs O6-random paired contrast, dose-response in
pp-over-IQR, and clustered inference for the preference contrast."""
import json, statistics, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
import numpy as np
from stimuli import ROOT, DEV_FACTS
import analysis as A
import analyse_eshift as E
RES = ROOT / "results"
out = {}


# ---------- C1 per judge, and worst-case bounds on the unresolved cases
def c1_variants():
    rows = A.load_rows("eshift")
    index = json.loads((RES / "eshift_index.json").read_text())
    elig = set(json.loads((RES / "frames.json").read_text())["eligible"])
    pw = json.loads((RES / "power.json").read_text())
    sesoi = pw["operative_sesoi"]
    res = {"sesoi": sesoi}

    def run(label, relabel):
        rs = []
        for r in rows:
            r = dict(r)
            r["label"] = relabel(r)
            rs.append(r)
        pf = {f: v for f, v in E.paired_differences(rs, index, "O1", 10, "confirmatory").items()
              if f in elig}
        if not pf:
            return
        b = A.family_paired_bootstrap(pf, n_boot=4000)
        res[label] = {"mean": float(np.mean(b)), "ci95": A.ci(b), "n_families": len(pf)}

    run("primary", lambda r: r["label"])
    run("judge1_only", lambda r: (r["judge1"] or r["regex_label"]) if r["needs_judge"] else r["regex_label"])
    run("judge2_only", lambda r: (r["judge2"] or r["regex_label"]) if r["needs_judge"] else r["regex_label"])
    # worst case FOR the hypothesis: unresolved in F+ counted as DROPPED, in F- as RETAINED
    idx = index
    def worst_against(r):
        if r["label"] != A.UNRESOLVED:
            return r["label"]
        arm = idx.get(r["run_id"], {}).get("arm")
        return A.DROPPED if arm == "F+" else A.RETAINED
    def worst_for(r):
        if r["label"] != A.UNRESOLVED:
            return r["label"]
        arm = idx.get(r["run_id"], {}).get("arm")
        return A.RETAINED if arm == "F+" else A.DROPPED
    run("unresolved_worst_against_H", worst_against)
    run("unresolved_worst_for_H", worst_for)
    n_unres = sum(1 for r in rows if r["label"] == A.UNRESOLVED)
    res["n_unresolved"] = n_unres
    res["n_rows"] = len(rows)
    res["unresolved_rate"] = n_unres / len(rows)
    # unresolved rate by arm, to show it is not differential
    by = Counter((idx.get(r["run_id"], {}).get("arm"), r["label"] == A.UNRESOLVED) for r in rows)
    res["unresolved_by_arm"] = {
        arm: by[(arm, True)] / max(1, by[(arm, True)] + by[(arm, False)]) for arm in ("F+", "F-")}
    return res


# ---------- missingness / protocol compliance by operator
def protocol():
    recs = [json.loads(l) for l in (RES / "chains_confirm.jsonl").read_text().splitlines() if l.strip()]
    by = defaultdict(lambda: {"trim": [], "retry": [], "w": []})
    for r in recs:
        d = by[r["op"]]
        d["trim"].append(r["n_hard_trimmed"]); d["retry"].append(r["n_budget_retries"])
        d["w"].extend(s["words"] for s in r["snapshots"])
    rows = A.attach(A.load_rows("confirm"), json.loads((RES / "manifest.json").read_text()))
    n_by, unres_by = Counter(), Counter()
    for r in rows:
        if r["k"] == 10:
            n_by[r["op"]] += 1
            unres_by[r["op"]] += int(r["label"] == A.UNRESOLVED)
    return {op: {"hard_trims_per_traj": statistics.mean(d["trim"]),
                 "budget_retries_per_traj": statistics.mean(d["retry"]),
                 "mean_stored_words": statistics.mean(d["w"]),
                 "n_k10": n_by[op], "unresolved_k10": unres_by[op],
                 "unresolved_rate_k10": unres_by[op] / max(1, n_by[op])}
            for op, d in sorted(by.items())}


# ---------- direct paired operator contrasts, including O6 vs O6-random and O3W
def contrasts():
    man = json.loads((RES / "manifest.json").read_text())
    rows = A.attach(A.load_rows("confirm"), man)
    p = RES / "coded_o3w.jsonl"
    if p.exists():
        rows += A.attach(A.load_rows("o3w"), man)
    k10 = [r for r in rows if r["k"] == 10 and r["label"] != A.UNRESOLVED]
    ops = sorted({r["op"] for r in k10})

    def stat(s):
        d = {}
        for op in ops:
            v = [r["retained"] for r in s if r["op"] == op]
            d[op] = 100 * statistics.mean(v) if v else float("nan")
        return d
    boot = A.crossed_bootstrap(k10, stat, n_boot=2000)
    point = stat(k10)
    res = {"levels": {op: {"retention": point[op],
                           "ci95": A.ci([b[op] for b in boot if op in b and not np.isnan(b[op])]),
                           "n": sum(1 for r in k10 if r["op"] == op)} for op in ops}}
    pairs = [("O6", "O6-random"), ("O6", "O6-low"), ("O4", "O5"), ("O3", "O1"), ("O4", "O1"),
             ("O5", "O1"), ("O3W", "O1"), ("O3W", "O3")]
    res["paired"] = {}
    for a, b in pairs:
        if a not in ops or b not in ops:
            continue
        d = [x[a] - x[b] for x in boot if a in x and b in x and not (np.isnan(x[a]) or np.isnan(x[b]))]
        if d:
            c = A.ci(d)
            res["paired"][f"{a}_minus_{b}"] = {"point": point[a] - point[b], "ci95": c,
                                               "excludes_zero": bool(c[0] > 0 or c[1] < 0)}
    return res


# ---------- dose-response expressed over the IQR, with its CI
def dose():
    cf = json.loads((RES / "confirm_result_confirm.json").read_text())
    iqr = cf["iqr_surprise"]
    o1 = cf["C2_slope_O1_pp_per_logodds"]
    o3 = cf["C3_slope_O3_pp_per_logodds"]
    return {"iqr_logodds": iqr,
            "O1_pp_over_iqr": {"point": o1["point"]*iqr,
                               "ci95": [o1["ci95"][0]*iqr, o1["ci95"][1]*iqr]},
            "O3_pp_over_iqr": {"point": o3["point"]*iqr,
                               "ci95": [o3["ci95"][0]*iqr, o3["ci95"][1]*iqr]}}


# ---------- preferences: clustered over preference families, baseline-adjusted
def prefs(n_boot=5000, seed=5):
    mem = [json.loads(l) for l in (RES / "pref_memory.jsonl").read_text().splitlines() if l.strip()]
    beh = [json.loads(l) for l in (RES / "pref_behaviour.jsonl").read_text().splitlines() if l.strip()]
    defr = defaultdict(list)
    for r in beh:
        if r["cond"] == "C":
            defr[(r["family_id"], r["level"])].append(1.0 if r["complied"] else 0.0)
    dev = {k: 1 - statistics.mean(v) for k, v in defr.items()}
    byfam = defaultdict(list)
    for r in mem:
        d = dev.get((r["family_id"], r["level"]))
        if d is None:
            continue
        byfam[r["family_id"]].append({"k": r["k"], "nd": d >= 0.5,
                                      "stored": 1.0 if r["stored"] else 0.0})
    import random
    rng = random.Random(seed)
    fams = sorted(byfam)

    def gap(sample_fams, k):
        nd = [x["stored"] for f in sample_fams for x in byfam[f] if x["k"] == k and x["nd"]]
        dd = [x["stored"] for f in sample_fams for x in byfam[f] if x["k"] == k and not x["nd"]]
        if not nd or not dd:
            return None
        return 100 * (statistics.mean(nd) - statistics.mean(dd))
    pt20, pt0 = gap(fams, 20), gap(fams, 0)
    bs_raw, bs_adj = [], []
    for _ in range(n_boot):
        s = [rng.choice(fams) for _ in fams]
        g20, g0 = gap(s, 20), gap(s, 0)
        if g20 is not None and g0 is not None:
            bs_raw.append(g20); bs_adj.append(g20 - g0)
    return {"n_preference_families": len(fams),
            "gap_k0_pp": pt0, "gap_k20_pp": pt20,
            "gap_k20_ci95": A.ci(bs_raw), "baseline_adjusted_pp": pt20 - pt0,
            "baseline_adjusted_ci95": A.ci(bs_adj),
            "note": "cluster bootstrap over preference families; the k=0 gap is the pre-existing "
                    "difference and is subtracted in the adjusted contrast"}


if __name__ == "__main__":
    out["C1_variants"] = c1_variants()
    out["protocol_by_operator"] = protocol()
    out["contrasts"] = contrasts()
    out["dose_over_iqr"] = dose()
    out["preferences"] = prefs()
    (RES / "sensitivity.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))


def operator_per_judge(n_boot=1500):
    """Reviewer round 1, weakness 5: recompute the headline operator contrast under each judge."""
    man = json.loads((RES / "manifest.json").read_text())
    rows = A.attach(A.load_rows("confirm"), man)
    res = {}
    for label, relabel in (
        ("primary", lambda r: r["label"]),
        ("judge1_only", lambda r: (r["judge1"] or r["regex_label"]) if r["needs_judge"] else r["regex_label"]),
        ("judge2_only", lambda r: (r["judge2"] or r["regex_label"]) if r["needs_judge"] else r["regex_label"]),
        ("agreement_only", lambda r: r["label"]),
    ):
        rs = []
        for r in rows:
            r = dict(r)
            r["label"] = relabel(r)
            if label == "agreement_only" and r["label"] == A.UNRESOLVED:
                continue
            r["retained"] = 1.0 if r["label"] == A.RETAINED else 0.0
            rs.append(r)
        k10 = [r for r in rs if r["k"] == 10 and r["label"] != A.UNRESOLVED]
        def stat(s):
            d = {}
            for op in ("O1", "O4", "O5", "O3"):
                v = [r["retained"] for r in s if r["op"] == op]
                d[op] = 100 * statistics.mean(v) if v else float("nan")
            return d
        boot = A.crossed_bootstrap(k10, stat, n_boot=n_boot)
        pt = stat(k10)
        res[label] = {}
        for op in ("O4", "O5", "O3"):
            d = [b[op] - b["O1"] for b in boot if op in b and "O1" in b
                 and not (np.isnan(b[op]) or np.isnan(b["O1"]))]
            res[label][f"{op}_minus_O1"] = {"point": pt[op] - pt["O1"], "ci95": A.ci(d) if d else None}
        res[label]["O1_retention"] = pt["O1"]
    return res
