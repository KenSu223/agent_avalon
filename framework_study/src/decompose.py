"""Where does the belief gap come from?  P(belief KEPT | memory state, version), pooled over checkpoints >= 2."""
import json, glob, collections, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "framework_study/src"))
from analyse_frameworks import load, ORDER

rows = [r for r in load() if r["ckpt"] >= 2 and r["state"] in ("RETAINED", "DROPPED") and r.get("belief") in ("KEPT", "REVERTED")]
print(f"{'framework':18s} | {'P(kept | retained)':>20s} | {'P(kept | dropped)':>20s} | share of I losses explained by deletion")
print(f"{'':18s} | {'C':>9s} {'I':>9s} | {'C':>9s} {'I':>9s} |")
for f in ORDER:
    rs = [r for r in rows if r["framework"] == f]
    if not rs:
        continue
    cell = {}
    for st in ("RETAINED", "DROPPED"):
        for v in ("C", "I"):
            s = [r for r in rs if r["state"] == st and r["version"] == v]
            cell[(st, v)] = (sum(r["belief"] == "KEPT" for r in s) / len(s), len(s)) if s else (float("nan"), 0)
    I_rev = [r for r in rs if r["version"] == "I" and r["belief"] == "REVERTED"]
    share = (sum(r["state"] == "DROPPED" for r in I_rev) / len(I_rev)) if I_rev else float("nan")
    fmt = lambda x: f"{x[0]:.2f}({x[1]})"
    print(f"{f:18s} | {fmt(cell[('RETAINED','C')]):>9s} {fmt(cell[('RETAINED','I')]):>9s} | {fmt(cell[('DROPPED','C')]):>9s} {fmt(cell[('DROPPED','I')]):>9s} | {share:.2f} of {len(I_rev)}")
