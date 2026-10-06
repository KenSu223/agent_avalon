"""C1: the frozen four-outcome decision rule for E-SHIFT (amendment A2)."""
import json, statistics, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
import numpy as np
from stimuli import ROOT, DEV_FACTS
import analysis as A

RES = ROOT / "results"


ALL_K = [0, 1, 2, 3, 5, 7, 10, 15, 20]


def paired_differences(rows, index, op="O1", k=10, split="confirmatory", endpoint="survival"):
    """family -> [per-seed paired difference in percentage points].

    AMENDMENT A4 (decided on dev data, before any confirmatory E-SHIFT run). The primary endpoint is
    the SURVIVAL FRACTION: the proportion of the nine checkpoints at which the target item is still
    retained. The originally preregistered endpoint -- binary retention at k=10 -- throws away eight
    ninths of each trajectory, and the dev power analysis shows it gives a minimum detectable effect
    of 37.8 pp against 15.6 pp for the survival fraction at the same cost. The survival fraction is
    also the quantity the claim is actually about ("how long does a surprising item last"). Binary
    retention at k=10 is retained as a secondary endpoint and reported alongside.
    """
    by = defaultdict(lambda: defaultdict(dict))        # (family, seed) -> arm -> {k: retained}
    for r in rows:
        meta = index.get(r["run_id"])
        if not meta or meta["op"] != op:
            continue
        if r["item_id"] != meta["target_item"]:
            continue
        in_dev = meta["family_id"] in DEV_FACTS
        if (split == "confirmatory" and in_dev) or (split == "dev" and not in_dev):
            continue
        if r["label"] == A.UNRESOLVED:
            continue
        by[(meta["family_id"], meta["seed_idx"])][meta["arm"]][r["k"]] = \
            1.0 if r["label"] == A.RETAINED else 0.0

    def score(kk):
        if endpoint == "binary":
            return kk.get(k)
        vals = [v for kk_, v in kk.items() if kk_ in ALL_K]
        return sum(vals) / len(vals) if vals else None

    per_family = defaultdict(list)
    for (fid, si), arms in by.items():
        if "F+" in arms and "F-" in arms:
            a, b = score(arms["F+"]), score(arms["F-"])
            if a is not None and b is not None:
                per_family[fid].append(100.0 * (a - b))
    return dict(per_family)


def run(split="confirmatory", sesoi=None, n_boot=10000, endpoint="survival"):
    if sesoi is None:
        pw = json.loads((RES / "power.json").read_text()) if (RES / "power.json").exists() else {}
        sesoi = pw.get("operative_sesoi", 8.0)
    rows = A.load_rows("eshift")
    index = json.loads((RES / "eshift_index.json").read_text())
    frames = json.loads((RES / "frames.json").read_text())
    elig = set(frames["eligible"])

    out = {}
    for pop, keep in (("eligible_only", lambda f: f in elig), ("ITT", lambda f: True)):
        pf = {f: v for f, v in paired_differences(rows, index, "O1", 10, split, endpoint).items()
              if keep(f)}
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
    pf3 = {f: v for f, v in paired_differences(rows, index, "O3", 10, split, endpoint).items()
           if f in elig}
    if pf3:
        b3 = A.family_paired_bootstrap(pf3, n_boot=n_boot)
        t3 = A.tost(b3, 5.0)
        out["frame_control_O3"] = {"mean": float(np.mean(b3)), "ci95": A.ci(b3),
                                   "equivalence_margin_pp": 5.0, **t3,
                                   "n_families": len(pf3),
                                   "flag_residual_interference": not t3["equivalent"]}
    out["endpoint"] = endpoint
    out["sesoi_pp"] = sesoi
    # secondary endpoint: the originally preregistered binary retention at k=10
    pf_b = {f: v for f, v in paired_differences(rows, index, "O1", 10, split, "binary").items()
            if f in elig}
    if pf_b:
        bb = A.family_paired_bootstrap(pf_b, n_boot=n_boot)
        out["secondary_binary_k10"] = {"mean": float(np.mean(bb)), "ci95": A.ci(bb),
                                       "n_families": len(pf_b)}
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
    sesoi = float(sys.argv[2]) if len(sys.argv) > 2 else None
    res = run(split, sesoi)
    sesoi = res["sesoi_pp"]
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
