"""The preference numbers the paper cites, derived from stored memory (not behaviour)."""
import json, statistics, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from stimuli import ROOT
RES = ROOT / "results"
mem = [json.loads(l) for l in (RES/"pref_memory.jsonl").read_text().splitlines() if l.strip()]
beh = [json.loads(l) for l in (RES/"pref_behaviour.jsonl").read_text().splitlines() if l.strip()]
defr = defaultdict(list)
for r in beh:
    if r["cond"] == "C":
        defr[(r["family_id"], r["level"])].append(1.0 if r["complied"] else 0.0)
dev = {k: 1-statistics.mean(v) for k, v in defr.items()}
def rate(k, nondefault):
    v = [1.0 if r["stored"] else 0.0 for r in mem if r["k"] == k
         and (dev.get((r["family_id"], r["level"]), 0) >= 0.5) == nondefault]
    return 100*statistics.mean(v) if v else None
def share(k):
    s = [r for r in mem if r["k"] == k and r["stored"]]
    return 100*sum(1 for r in s if dev.get((r["family_id"], r["level"]), 0) >= 0.5)/len(s)
out = {"default_k20": rate(20, False), "nondefault_k20": rate(20, True),
       "gap_k20": rate(20, True)-rate(20, False),
       "default_k10": rate(10, False), "nondefault_k10": rate(10, True),
       "share_nondefault_k0": share(0), "share_nondefault_k20": share(20),
       "n_default_items": sum(1 for k, v in dev.items() if v < 0.5),
       "n_nondefault_items": sum(1 for k, v in dev.items() if v >= 0.5)}
(RES/"pref_extra.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
