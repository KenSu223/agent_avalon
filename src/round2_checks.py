"""Round-2 reviewer items 3 and 7: what trimming does to targets, and a within-family
preference contrast."""
import json, statistics, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
import numpy as np
from stimuli import ROOT, load_families, render
import analysis as A
RES = ROOT / "results"
out = {}

# ---- item 3: does trimming remove targets, and where do targets sit in the stored notes?
man = json.loads((RES / "manifest.json").read_text())
recs = [json.loads(l) for l in (RES / "chains_confirm.jsonl").read_text().splitlines() if l.strip()]
rows = A.attach(A.load_rows("confirm"), man)
famd = {f["family_id"]: f for f in load_families()}

# per-trajectory trim count vs that trajectory's retention at k=10
by_run = defaultdict(list)
for r in rows:
    if r["k"] == 10 and r["label"] != A.UNRESOLVED:
        by_run[r["run_id"]].append(r["retained"])
trim_by_run = {r["run_id"]: r["n_hard_trimmed"] for r in recs}
op_by_run = {r["run_id"]: r["op"] for r in recs}
res = {}
for op in ("O1", "O5", "O6"):
    pts = [(trim_by_run[rid], statistics.mean(v)) for rid, v in by_run.items()
           if op_by_run.get(rid) == op and rid in trim_by_run and v]
    if len(pts) > 3:
        xs = [p[0] for p in pts]; ys = [100*p[1] for p in pts]
        mx, my = statistics.mean(xs), statistics.mean(ys)
        den = sum((x-mx)**2 for x in xs)
        slope = sum((x-mx)*(y-my) for x, y in zip(xs, ys))/den if den else None
        lo = [y for x, y in zip(xs, ys) if x <= statistics.median(xs)]
        hi = [y for x, y in zip(xs, ys) if x > statistics.median(xs)]
        res[op] = {"n_traj": len(pts), "mean_trims": mx, "mean_retention": my,
                   "slope_retention_per_trim": slope,
                   "retention_low_trim": statistics.mean(lo) if lo else None,
                   "retention_high_trim": statistics.mean(hi) if hi else None}
out["trimming_vs_retention"] = res

# where do surviving targets sit in the stored notes? (fraction of the way down)
pos = defaultdict(list)
for rec in recs:
    if rec["op"] not in ("O1", "O5"):
        continue
    w = rec["world"]
    snap = next((s for s in rec["snapshots"] if s["k"] == 10), None)
    if not snap or not snap["notes"]:
        continue
    lines = [l for l in snap["notes"].splitlines() if l.strip()]
    if not lines:
        continue
    for it in rec["items"]:
        f = famd[it["family_id"]]
        attr = render(f["attribute_regex"], w)
        import re
        for i, l in enumerate(lines):
            if re.search(attr, l, re.I):
                pos[rec["op"]].append(i / max(1, len(lines) - 1) if len(lines) > 1 else 0.0)
                break
out["target_position_in_notes"] = {op: {"mean_relative_position": statistics.mean(v), "n": len(v)}
                                   for op, v in pos.items() if v}

# ---- item 7: within-family preference contrast
mem = [json.loads(l) for l in (RES / "pref_memory.jsonl").read_text().splitlines() if l.strip()]
beh = [json.loads(l) for l in (RES / "pref_behaviour.jsonl").read_text().splitlines() if l.strip()]
defr = defaultdict(list)
for r in beh:
    if r["cond"] == "C":
        defr[(r["family_id"], r["level"])].append(1.0 if r["complied"] else 0.0)
dev = {k: 1 - statistics.mean(v) for k, v in defr.items()}
byfam = defaultdict(lambda: {"nd": [], "dd": []})
for r in mem:
    if r["k"] != 20:
        continue
    d = dev.get((r["family_id"], r["level"]))
    if d is None:
        continue
    byfam[r["family_id"]]["nd" if d >= 0.5 else "dd"].append(1.0 if r["stored"] else 0.0)
within = {f: 100*(statistics.mean(v["nd"]) - statistics.mean(v["dd"]))
          for f, v in byfam.items() if v["nd"] and v["dd"]}
if within:
    import random
    rng = random.Random(3)
    keys = sorted(within)
    bs = [statistics.mean([within[rng.choice(keys)] for _ in keys]) for _ in range(10000)]
    out["preference_within_family"] = {
        "n_families_with_both": len(within), "mean_pp": statistics.mean(within.values()),
        "ci95": A.ci(bs),
        "note": "families containing BOTH a default-matching and a non-default level; the contrast "
                "is computed inside each family and then bootstrapped over families, so it is free "
                "of between-family composition"}
else:
    out["preference_within_family"] = {"n_families_with_both": 0}
(RES / "round2_checks.json").write_text(json.dumps(out, indent=1, default=float))
print(json.dumps(out, indent=1, default=float))
