"""B8: does the null replicate on a second strong family, a small local model, and at T=0?"""
import json, statistics, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
import numpy as np
from stimuli import ROOT
import analysis as A
RES = ROOT / "results"


def one(tag, label):
    p = RES / f"coded_{tag}.jsonl"
    if not p.exists():
        return None
    man = json.loads((RES / "manifest.json").read_text())
    rows = A.attach(A.load_rows(tag), man)
    k10 = [r for r in rows if r["k"] == 10 and r["label"] != A.UNRESOLVED]
    out = {"label": label, "n": len(k10), "by_op": {}}
    byT = defaultdict(list)
    for r in k10:
        byT[(r["op"], r["T"])].append(r)
    for (op, T), sub in sorted(byT.items()):
        pt = A.lpm(sub) if len({x["op"] for x in sub}) >= 1 else {}
        boot = A.crossed_bootstrap(sub, A.lpm, n_boot=400)
        key = f"slope_{op}"
        d = [b[key] for b in boot if key in b]
        s = sorted(x["surprise"] for x in sub)
        t1, t2 = s[len(s)//3], s[2*len(s)//3]
        lo = [x["retained"] for x in sub if x["surprise"] <= t1]
        hi = [x["retained"] for x in sub if x["surprise"] > t2]
        out["by_op"][f"{op}@T{T}"] = {
            "retention": 100*statistics.mean([x["retained"] for x in sub]),
            "slope_pp_per_logodds": pt.get(key),
            "slope_ci95": A.ci(d) if d else None,
            "gap_low_minus_high_pp": 100*(statistics.mean(lo)-statistics.mean(hi)),
            "n": len(sub)}
    return out


if __name__ == "__main__":
    res = {}
    for tag, label in (("confirm", "qwen3-235b (primary), T=1.0"),
                       ("diag_llama", "llama3.3-70b (second family), T=1.0"),
                       ("diag_local", "local qwen3-8b (small model), T=1.0"),
                       ("diag_temp", "qwen3-235b at T=0.0")):
        r = one(tag, label)
        if r:
            res[tag] = r
    (RES / "diag_result.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"{'model / setting':<38}{'op':<12}{'ret%':>7}{'slope':>8}{'ci95':>18}{'gap':>7}{'n':>7}")
    for tag, r in res.items():
        for op, v in r["by_op"].items():
            ci = v["slope_ci95"]
            cis = f"[{ci[0]:+.1f},{ci[1]:+.1f}]" if ci else "-"
            print(f"{r['label']:<38}{op:<12}{v['retention']:>7.1f}"
                  f"{(v['slope_pp_per_logodds'] or 0):>8.2f}{cis:>18}"
                  f"{v['gap_low_minus_high_pp']:>+7.1f}{v['n']:>7}")
