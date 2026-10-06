"""C1: the frozen four-outcome decision rule for E-SHIFT (amendment A2)."""
import json, statistics, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
import numpy as np
from stimuli import ROOT, DEV_FACTS
import analysis as A

RES = ROOT / "results"


def paired_differences(rows, index, op="O1", k=10, split="confirmatory"):
    """family -> [per-seed paired difference in percentage points]."""
    by = defaultdict(dict)                      # (family, seed) -> {arm: retained}
    for r in rows:
        meta = index.get(r["run_id"])
        if not meta or meta["op"] != op or r["k"] != k:
            continue
        if r["item_id"] != meta["target_item"]:
            continue
        in_dev = meta["family_id"] in DEV_FACTS
        if (split == "confirmatory" and in_dev) or (split == "dev" and not in_dev):
            continue
        if r["label"] == A.UNRESOLVED:
            continue
        by[(meta["family_id"], meta["seed_idx"])][meta["arm"]] = \
            1.0 if r["label"] == A.RETAINED else 0.0
    per_family = defaultdict(list)
    for (fid, si), arms in by.items():
        if "F+" in arms and "F-" in arms:
            per_family[fid].append(100.0 * (arms["F+"] - arms["F-"]))
    return dict(per_family)


def run(split="confirmatory", sesoi=8.0, n_boot=10000):
    rows = A.load_rows("eshift")
    index = json.loads((RES / "eshift_index.json").read_text())
    frames = json.loads((RES / "frames.json").read_text())
    elig = set(frames["eligible"])

    out = {}
    for pop, keep in (("eligible_only", lambda f: f in elig), ("ITT", lambda f: True)):
        pf = {f: v for f, v in paired_differences(rows, index, "O1", 10, split).items() if keep(f)}
        if not pf:
            out[pop] = {"n_families": 0}
            continue
        boot = A.family_paired_bootstrap(pf, n_boot=n_boot)
        dec = A.decision_C1(boot, sesoi)
        dec["n_families"] = len(pf)
        dec["n_seed_blocks"] = sum(len(v) for v in pf.values())
        dec["per_family_mean"] = {f: statistics.mean(v) for f, v in pf.items()}
        out[pop] = dec

    # O3 frame control: O3 cannot condition on the frame, so an arm difference there would mean
    # residual interference rather than a prior effect.
    pf3 = {f: v for f, v in paired_differences(rows, index, "O3", 10, split).items() if f in elig}
    if pf3:
        b3 = A.family_paired_bootstrap(pf3, n_boot=n_boot)
        t3 = A.tost(b3, 5.0)
        out["frame_control_O3"] = {"mean": float(np.mean(b3)), "ci95": A.ci(b3),
                                   "equivalence_margin_pp": 5.0, **t3,
                                   "n_families": len(pf3),
                                   "flag_residual_interference": not t3["equivalent"]}
    primary = out.get("eligible_only", {})
    itt = out.get("ITT", {})
    if primary.get("decision") and itt.get("decision"):
        agree = (np.sign(primary["mean"]) == np.sign(itt["mean"]))
        out["itt_agreement"] = {"same_direction": bool(agree),
                                "note": "C1 is declared inconclusive if ITT and eligible-only "
                                        "disagree in direction or decision"}
        if not agree:
            out["eligible_only"]["decision"] = "INCONCLUSIVE"
            out["eligible_only"]["reason"] = "ITT disagrees in direction"
    return out


if __name__ == "__main__":
    split = sys.argv[1] if len(sys.argv) > 1 else "confirmatory"
    sesoi = float(sys.argv[2]) if len(sys.argv) > 2 else 8.0
    res = run(split, sesoi)
    (RES / f"eshift_result_{split}.json").write_text(json.dumps(res, indent=1, default=float))
    p = res.get("eligible_only", {})
    print(f"E-SHIFT ({split}), SESOI {sesoi} pp")
    if p.get("n_families"):
        print(f"  families {p['n_families']}, seed blocks {p['n_seed_blocks']}")
        print(f"  mean paired difference  {p['mean']:+.2f} pp")
        print(f"  95% CI  [{p['ci95'][0]:+.2f}, {p['ci95'][1]:+.2f}]")
        print(f"  90% CI  [{p['ci90'][0]:+.2f}, {p['ci90'][1]:+.2f}]")
        print(f"  DECISION: {p['decision']}")
    i = res.get("ITT", {})
    if i.get("n_families"):
        print(f"  ITT: {i['mean']:+.2f} pp over {i['n_families']} families -> {i['decision']}")
    c = res.get("frame_control_O3")
    if c:
        print(f"  O3 frame control: {c['mean']:+.2f} pp, equivalent to 0 within +/-5pp: "
              f"{c['equivalent']}")
