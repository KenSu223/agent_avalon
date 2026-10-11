"""Loose end 5b analysis (STEP5B_DESIGN.md §3): prior-directed deletion by a weak compactor in non-saturated cells.
Input: results/probed_<system>_s4weak.jsonl; items restricted to Llama-3.1-8B V1 P(C) >= 0.8 (non-neutral).
Output: results/step5b_analysis.txt"""
import collections, glob, json
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "framework_study/results"
B = 2000
items = {json.loads(l)["id"]: json.loads(l) for l in open(ROOT / "framework_study/stimuli/items_v2_final.jsonl")}
weak = json.load(open(RES / "validation_v2_llama3-1-8b-instruct.json"))["V1"]
keep = {i for i, d in weak.items() if (d["p_congruent"] or 0) >= 0.8}
rows = [r for f in glob.glob(str(RES / "probed_*_s4weak.jsonl")) for r in map(json.loads, open(f))
        if r["item"] in keep and r["state"] in ("RETAINED", "DROPPED", "FLIPPED")]
lines = [f"items with weak-compactor prior >= 0.8: {len(keep)}; agreed probes: {len(rows)}"]
rate = lambda rs, lab: np.mean([r["state"] == lab for r in rs]) if rs else np.nan
cells = collections.defaultdict(list)
for r in rows:
    cells[(r["framework"], r["ckpt"])].append(r)
lines.append(f"{'system':18s} ckpt   R    R_C   R_I    dR    non-saturated")
ns = []
for (s, k) in sorted(cells):
    rs = cells[(s, k)]
    R = rate(rs, "RETAINED"); rc = rate([r for r in rs if r["version"] == "C"], "RETAINED"); ri = rate([r for r in rs if r["version"] == "I"], "RETAINED")
    ok = 0.2 <= R <= 0.8
    if ok:
        ns.append((s, k))
    lines.append(f"{s:18s} {k:4d} {R:5.2f} {rc:5.2f} {ri:5.2f} {rc - ri:+6.3f}   {'yes' if ok else ''}")


def boot(rs, fn):
    by = collections.defaultdict(list)
    for r in rs:
        by[r["user"]].append(r)
    us = sorted(by); rng = np.random.default_rng(0)
    return np.array([fn([r for u in rng.choice(us, len(us)) for r in by[u]]) for _ in range(B)])


dR = lambda rs: rate([r for r in rs if r["version"] == "C"], "RETAINED") - rate([r for r in rs if r["version"] == "I"], "RETAINED")
dF = lambda rs: rate([r for r in rs if r["version"] == "I"], "FLIPPED") - rate([r for r in rs if r["version"] == "C"], "FLIPPED")
ci = lambda a: (float(np.nanquantile(a, .025)), float(np.nanquantile(a, .975)))
for label, sel in [("P5b.1 neutral_roll", [c for c in ns if c[0] == "neutral_roll"]), ("P5b.2 all systems", ns)]:
    rs = [r for c in sel for r in cells[c]]
    if not rs:
        lines.append(f"{label}: no non-saturated cells"); continue
    b = boot(rs, dR); f = boot(rs, dF)
    lines.append(f"{label}: cells {sel}  dR {dR(rs):+.3f} {ci(b)} -> {'holds' if ci(b)[0] > 0 else 'not shown'}   dF {dF(rs):+.3f} {ci(f)}")
text = "\n".join(lines)
(RES / "step5b_analysis.txt").write_text(text + "\n"); print(text)
