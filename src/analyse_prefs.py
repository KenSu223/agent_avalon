"""A1 (exploratory): preference storage vs execution loss, and cross-user homogenization."""
import json, random, statistics, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
import numpy as np
from stimuli import ROOT
RES = ROOT / "results"


def load(n):
    return [json.loads(l) for l in (RES / n).read_text().splitlines() if l.strip()]


def main():
    beh = load("pref_behaviour.jsonl")
    mem = load("pref_memory.jsonl")

    # ---- stored memory first (the primary preference result)
    stored = defaultdict(list)
    for r in mem:
        stored[r["k"]].append(1.0 if r["stored"] else 0.0)
    out = {"stored_by_k": {k: 100*statistics.mean(v) for k, v in sorted(stored.items())}}

    # ---- behaviour: A (raw instructions) / B (memory at k) / C (nothing)
    comp = defaultdict(list)
    for r in beh:
        key = (r["cond"], r["k"])
        comp[key].append(1.0 if r["complied"] else 0.0)
    A_ = 100*statistics.mean(comp[("A", None)]) if ("A", None) in comp else None
    C_ = 100*statistics.mean(comp[("C", None)]) if ("C", None) in comp else None
    out["compliance"] = {"A_raw_instructions": A_, "C_no_information": C_,
                         "B_memory": {k: 100*statistics.mean(v) for (c, k), v in sorted(comp.items())
                                      if c == "B"}}
    if A_ is not None:
        out["execution_loss_pp"] = 100 - A_
        out["storage_loss_pp"] = {k: A_ - v for k, v in out["compliance"]["B_memory"].items()}

    # ---- storage loss vs deviation from the model's default (condition C compliance per family)
    defrate = defaultdict(list)
    for r in beh:
        if r["cond"] == "C":
            defrate[(r["family_id"], r["level"])].append(1.0 if r["complied"] else 0.0)
    dev = {k: 1 - statistics.mean(v) for k, v in defrate.items()}
    pairs = []
    for r in beh:
        if r["cond"] == "B" and r["k"] == 20:
            d = dev.get((r["family_id"], r["level"]))
            if d is not None:
                pairs.append((d, 1.0 if r["complied"] else 0.0))
    if pairs:
        xs = [p[0] for p in pairs]; ys = [p[1] for p in pairs]
        mx, my = statistics.mean(xs), statistics.mean(ys)
        num = sum((a-mx)*(b-my) for a, b in zip(xs, ys))
        den = (sum((a-mx)**2 for a in xs)*sum((b-my)**2 for b in ys))**.5
        out["corr_deviation_vs_compliance_k20"] = num/den if den else None
        out["n_pairs"] = len(pairs)

    # ---- cross-user homogenization, measured in STORED MEMORY (not behaviour)
    prof = defaultdict(lambda: defaultdict(dict))     # k -> user -> family -> stored
    for r in mem:
        prof[r["k"]][r["user_id"]][r["family_id"]] = int(r["stored"])
    homog = {}
    for k, users in sorted(prof.items()):
        ids = sorted(users)
        fams = sorted({f for u in users.values() for f in u})
        vecs = {u: np.array([users[u].get(f, 0) for f in fams], dtype=float) for u in ids}
        cent = np.mean([vecs[u] for u in ids], axis=0)
        d_cent = [float(np.abs(vecs[u]-cent).mean()) for u in ids]
        pw = [float(np.abs(vecs[a]-vecs[b]).mean())
              for i, a in enumerate(ids) for b in ids[i+1:]]
        homog[k] = {"mean_distance_to_centroid": statistics.mean(d_cent),
                    "mean_pairwise_distance": statistics.mean(pw), "n_users": len(ids)}
    out["homogenization"] = homog

    # user-level permutation on the change in distance-to-centroid between k=0 and k=20
    ks = sorted(prof)
    if len(ks) >= 2:
        k0, kN = ks[0], ks[-1]
        out["homogenization_delta"] = (homog[kN]["mean_distance_to_centroid"]
                                       - homog[k0]["mean_distance_to_centroid"])
    (RES / "pref_result.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float)[:2200])


if __name__ == "__main__":
    main()
