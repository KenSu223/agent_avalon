"""Auxiliary numbers the paper cites: prior reliability/agreement and protocol compliance."""
import json, re, statistics, sys
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from stimuli import load_families, ROOT

RES = ROOT / "results"


def spearman(x, y):
    def rk(v):
        order = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0]*len(v); i = 0
        while i < len(order):
            j = i
            while j+1 < len(order) and v[order[j+1]] == v[order[i]]:
                j += 1
            for t in range(i, j+1):
                r[order[t]] = (i+j)/2
            i = j+1
        return r
    rx, ry = rk(x), rk(y); n = len(x)
    mx, my = sum(rx)/n, sum(ry)/n
    num = sum((a-mx)*(b-my) for a, b in zip(rx, ry))
    den = (sum((a-mx)**2 for a in rx)*sum((b-my)**2 for b in ry))**.5
    return num/den if den else None


def priors():
    d = json.loads((RES / "priors.json").read_text())
    fams = {f["family_id"]: f for f in load_families()}
    halves, ag13, rng, peak, nfloor = [], [], [], [], []
    mode_agree = tot = 0
    design_agree = design_tot = 0
    for fid, v in d["bt"].items():
        ks = sorted(v["ALL"], key=int)
        if len(ks) >= 3:
            r = spearman([v["A"][k] for k in ks], [v["B"][k] for k in ks])
            if r is not None:
                halves.append(r)
            if fid in d["p3"]:
                r = spearman([v["ALL"][k] for k in ks], [d["p3"][fid][k]["logprob"] for k in ks])
                if r is not None:
                    ag13.append(r)
        rng.append(max(v["ALL"].values()) - min(v["ALL"].values()))
        if fid in d["p2"]:
            p2 = {k: x for k, x in d["p2"][fid].items() if k != "OTHER"}
            if p2:
                tot += 1
                mode_agree += int(max(v["ALL"], key=lambda k: v["ALL"][k]) == max(p2, key=lambda k: p2[k]))
                vals = list(p2.values())
                peak.append(max(vals))
                nfloor.append(sum(1 for x in vals if x <= min(vals)+1e-9))
        if len(ks) == 5:
            design_tot += 1
            design_agree += int(max(v["ALL"], key=lambda k: v["ALL"][k]) == "1")
    return {
        "SplitHalfRho": f"{statistics.mean(halves):.3f}",
        "SplitHalfFrac": f"{100*sum(1 for x in halves if x>=0.7)/len(halves):.0f}\\%",
        "PThreeRho": f"{statistics.mean(ag13):.2f}",
        "BTRange": f"{statistics.mean(rng):.2f}",
        "PTwoModeAgree": f"{mode_agree}/{tot}",
        "PTwoFloor": f"{statistics.mean(nfloor):.1f}",
        "DesignOrderAgree": f"{design_agree}/{design_tot}",
    }


def trims(path="chains_confirm.jsonl", fallback="chains_dev.jsonl"):
    p = RES / path
    if not p.exists():
        p = RES / fallback
    recs = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    r = [x for x in recs if x["op"] in ("O1", "O2", "O4", "O5") or x["op"].startswith("O6")]
    if not r:
        return {}
    return {"hard_trims_per_traj": statistics.mean(x["n_hard_trimmed"] for x in r),
            "retries_per_traj": statistics.mean(x["n_budget_retries"] for x in r),
            "K": recs[0]["snapshots"][-1]["k"], "n_traj": len(r),
            "source": p.name}


if __name__ == "__main__":
    ps = priors()
    (RES / "prior_stats.json").write_text(json.dumps(ps, indent=1))
    t = trims()
    (RES / "trim_stats.json").write_text(json.dumps(t, indent=1))
    print(json.dumps(ps, indent=1))
    print(json.dumps(t, indent=1))
