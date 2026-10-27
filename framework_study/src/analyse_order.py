"""Option-order check analysis (framework_study/ORDER_CHECK_DESIGN.md §4-§5). Written before any reversed-order call.

Input : results/probed_<fw>_<tag>.jsonl (arm O = the step-4 beliefs) and results/order_<arm>_<tag>.jsonl (arms R, L)
Output: results/order_analysis.txt / .json
All CIs: user-level bootstrap (B = 2000, seed 0), paired: every statistic is computed on rows that have a parsed belief
in every arm it uses, and the same users are resampled for all arms.
usage: python analyse_order.py [--tags s4qwen s4llama]
"""
import argparse, collections, json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "framework_study/results"
sys.path.insert(0, str(ROOT / "framework_study/src"))
from probe_order import FW, BIG, SUB

B = 2000
LINES, J = [], {}
OK = ("KEPT", "REVERTED")


def say(*a):
    s = " ".join(str(x) for x in a); print(s); LINES.append(s)


def load(tag, items):
    rows = {}
    for fw in FW:
        for r in map(json.loads, open(RES / f"probed_{fw}_{tag}.jsonl")):
            if r["ckpt"] in (4, 12):
                rows[(fw, r["user"], r["ckpt"], r["item"])] = dict(r, b={"O": r.get("belief")})
    for arm in ("R", "L"):
        f = RES / f"order_{arm}_{tag}.jsonl"
        if f.exists():
            for r in map(json.loads, open(f)):
                k = (r["framework"], r["user"], r["ckpt"], r["item"])
                if k in rows:
                    rows[k]["b"][arm] = r["belief"]
    for r in rows.values():
        r["neutral"] = items[r["item"]]["type"] == "neutral"
    return list(rows.values())


def paired(rs, arms):
    return [r for r in rs if all(r["b"].get(a) in OK for a in arms)]


def y(r, arm):
    """1 if the agent answered the told version; 'B' = order-balanced mean of O and R."""
    if arm == "B":
        return (y(r, "O") + y(r, "R")) / 2
    return 1.0 if r["b"][arm] == "KEPT" else 0.0


def chose_first(r, arm):
    """Did the agent pick the option listed first? Arm O lists C first; arms R and L list I first."""
    chose_c = (r["version"] == "C") == (r["b"][arm] == "KEPT")
    return float(chose_c if arm == "O" else not chose_c)


def dK(rs, arm):
    c = [y(r, arm) for r in rs if r["version"] == "C"]; i = [y(r, arm) for r in rs if r["version"] == "I"]
    return np.mean(c) - np.mean(i) if c and i else np.nan


def boot(rs, fn, seed=0):
    by = collections.defaultdict(list)
    for r in rs:
        by[r["user"]].append(r)
    users = sorted(by)
    rng = np.random.default_rng(seed)
    return np.array([fn([r for u in rng.choice(users, len(users)) for r in by[u]]) for _ in range(B)], float)


def ci(a):
    a = np.asarray(a, float); a = a[~np.isnan(a)]
    return [float(np.quantile(a, .025)), float(np.quantile(a, .975))] if len(a) else [np.nan, np.nan]


def fmt(v, c):
    return f"{v:+.3f} [{c[0]:+.3f},{c[1]:+.3f}]"


def drop_rate(rs):
    rs = [r for r in rs if r["state"] not in ("DISAGREE", "UNPARSED")]
    return np.mean([r["state"] == "DROPPED" for r in rs]) if rs else np.nan


def e1(rows, out):
    """Primary: dK on DROPPED non-neutral rows at ckpt 12, original vs reversed; position component pi = (dK_O - dK_R) / 2."""
    say("\nE1  DROPPED non-neutral rows, ckpt 12 (paired O/R)")
    say(f"{'system':18s} {'drop':>5s} {'n':>5s} {'dK_O':>7s} {'dK_R':>7s} {'pi = (dK_O-dK_R)/2 [CI]':>26s} {'dK_B [CI]':>24s} {'first_O':>7s} {'first_R':>7s}")
    c12 = [r for r in rows if r["ckpt"] == 12 and not r["neutral"]]
    lossy = []
    for s in FW:
        allrs = [r for r in c12 if r["framework"] == s]
        dr = drop_rate(allrs)
        if dr >= 0.5:
            lossy.append(s)
        rs = paired([r for r in allrs if r["state"] == "DROPPED"], "OR")
        if len(rs) < 20 or not any(r["version"] == "C" for r in rs) or not any(r["version"] == "I" for r in rs):
            say(f"{s:18s} {dr:5.2f} {len(rs):5d}  (too few dropped rows)"); continue
        pi = boot(rs, lambda x: (dK(x, "O") - dK(x, "R")) / 2); bb = boot(rs, lambda x: dK(x, "B"))
        o = dict(drop=dr, n=len(rs), dK_O=dK(rs, "O"), dK_R=dK(rs, "R"), dK_B=dK(rs, "B"), pi_ci=ci(pi), dK_B_ci=ci(bb),
                 first_O=np.mean([chose_first(r, "O") for r in rs]), first_R=np.mean([chose_first(r, "R") for r in rs]))
        o["pi"] = (o["dK_O"] - o["dK_R"]) / 2
        out["E1"][s] = o
        say(f"{s:18s} {dr:5.2f} {len(rs):5d} {o['dK_O']:+7.3f} {o['dK_R']:+7.3f} {fmt(o['pi'], o['pi_ci']):>26s} {fmt(o['dK_B'], o['dK_B_ci']):>24s} "
            f"{o['first_O']:7.3f} {o['first_R']:7.3f}")
    rs = paired([r for r in c12 if r["framework"] in lossy and r["state"] == "DROPPED"], "OR")
    if rs:
        pi = boot(rs, lambda x: (dK(x, "O") - dK(x, "R")) / 2); bb = boot(rs, lambda x: dK(x, "B"))
        p = dict(systems=lossy, n=len(rs), dK_O=dK(rs, "O"), dK_R=dK(rs, "R"), dK_B=dK(rs, "B"), pi_ci=ci(pi), dK_B_ci=ci(bb))
        p["pi"] = (p["dK_O"] - p["dK_R"]) / 2
        out["E1_pooled"] = p
        say(f"pooled over lossy systems {lossy} (n={len(rs)}): dK_O {p['dK_O']:+.3f}, dK_R {p['dK_R']:+.3f}, pi {fmt(p['pi'], p['pi_ci'])}, "
            f"dK_B {fmt(p['dK_B'], p['dK_B_ci'])}")
    return lossy


def e2(rows, lossy, out):
    """Neutral control: P4.5 statistic (lossy systems pooled, all ckpt-12 neutral rows) under O, R and balanced."""
    say("\nE2  neutral control (P4.5 rows: ckpt 12, lossy systems pooled)")
    rs = paired([r for r in rows if r["ckpt"] == 12 and r["neutral"] and r["framework"] in lossy], "OR")
    if not rs:
        say("  (no rows)"); return
    bo, br, bb = (boot(rs, lambda x, a=a: dK(x, a)) for a in "ORB")
    dr = [r for r in rs if r["state"] == "DROPPED"]
    o = dict(n=len(rs), dK_O=dK(rs, "O"), dK_O_ci=ci(bo), dK_R=dK(rs, "R"), dK_R_ci=ci(br), dK_B=dK(rs, "B"), dK_B_ci=ci(bb),
             n_dropped=len(dr), first_O=np.mean([chose_first(r, "O") for r in dr]) if dr else np.nan,
             first_R=np.mean([chose_first(r, "R") for r in dr]) if dr else np.nan)
    dd = boot(rs, lambda x: dK(x, "O") - dK(x, "R")); o["diff_OR_ci"] = ci(dd)
    out["E2"] = o
    say(f"  n={o['n']}: dK_O {fmt(o['dK_O'], o['dK_O_ci'])}  dK_R {fmt(o['dK_R'], o['dK_R_ci'])}  dK_B {fmt(o['dK_B'], o['dK_B_ci'])}  "
        f"dK_O-dK_R {fmt(o['dK_O'] - o['dK_R'], o['diff_OR_ci'])}")
    say(f"  dropped neutral rows n={len(dr)}: P(first-listed option) O {o['first_O']:.3f}, R {o['first_R']:.3f}")
    per = collections.defaultdict(list)
    for r in dr:
        per[r["item"]].append(r)
    say("  per item (dropped rows): item n P(options[0] | O) P(options[0] | R)")
    o["per_item"] = {}
    for it, x in sorted(per.items()):
        a0 = np.mean([chose_first(r, "O") for r in x]); a0r = np.mean([1 - chose_first(r, "R") for r in x])
        o["per_item"][it] = dict(n=len(x), p_opt0_O=a0, p_opt0_R=a0r)
        say(f"    {it} {len(x):3d} {a0:.2f} {a0r:.2f}")


def e3(rows, items, prior_key, out):
    """PCS calibration (P4.7): cells = system x ckpt in {4, 12}; raw_history and nemori on users < SUB in every arm."""
    say("\nE3  PCS calibration, cells system x ckpt {4,12} (paired O/R; raw_history, nemori: users < %d)" % SUB)
    rs = paired([r for r in rows if r["state"] in ("RETAINED", "DROPPED", "FLIPPED") and (r["framework"] not in BIG or r["user"] < SUB)], "OR")
    cells = collections.defaultdict(list)
    for r in rs:
        cells[(r["framework"], r["ckpt"])].append(r)
    res = {}
    for arm in "ORB":
        Rv, Av, Pv = [], [], []
        for k, x in sorted(cells.items()):
            yv = np.array([y(r, arm) for r in x])
            g = np.array([items[r["item"]]["prior"][prior_key] if r["version"] == "C" else 1 - items[r["item"]]["prior"][prior_key] for r in x])
            Rv.append(np.mean([r["state"] == "RETAINED" for r in x])); Av.append(yv.mean()); Pv.append((yv - g).sum() / (1 - g).sum())
        Rv, Av, Pv = map(np.array, (Rv, Av, Pv))
        res[arm] = dict(mae_acc=float(np.mean(np.abs(Av - Rv))), mae_pcs=float(np.mean(np.abs(Pv - Rv))), cells=len(Rv),
                        per_cell={f"{k[0]}@{k[1]}": dict(R=float(r_), acc=float(a_), pcs=float(p_)) for k, r_, a_, p_ in zip(sorted(cells), Rv, Av, Pv)})
        say(f"  arm {arm}: MAE(acc, R) {res[arm]['mae_acc']:.3f}  MAE(PCS, R) {res[arm]['mae_pcs']:.3f}  over {len(Rv)} cells")
    out["E3"] = res


def e4(rows, out):
    """Secondary: P4.6 update reversion and the paper-table dK (all non-neutral ckpt-12 rows) under O, R, balanced."""
    c12 = [r for r in rows if r["ckpt"] == 12 and (r["framework"] not in BIG or r["user"] < SUB)]
    up = paired([r for r in c12 if r["type"] == "update"], "OR")
    if up:
        def rev(x, arm):
            f = lambda v: np.mean([1 - y(r, arm) for r in x if r["version"] == v])
            return f("I") - f("C")
        say("\nE4a P4.6 updates, P(revert | I) - P(revert | C), ckpt 12 (paired; raw_history, nemori: users < %d)" % SUB)
        out["E4a"] = {}
        for arm in "ORB":
            v = rev(up, arm); c = ci(boot(up, lambda x, a=arm: rev(x, a)))
            out["E4a"][arm] = dict(diff=v, ci=c, n=len(up))
            say(f"  arm {arm}: {fmt(v, c)}  n={len(up)}")
    say("\nE4b paper-table dK, all non-neutral ckpt-12 rows (paired; raw_history, nemori: users < %d)" % SUB)
    out["E4b"] = {}
    for s in FW:
        rs = paired([r for r in c12 if r["framework"] == s and not r["neutral"]], "OR")
        if not rs:
            continue
        o = {arm: dK(rs, arm) for arm in "ORB"}; o["B_ci"] = ci(boot(rs, lambda x: dK(x, "B"))); o["n"] = len(rs)
        out["E4b"][s] = o
        say(f"  {s:18s} n={len(rs):5d}  dK_O {o['O']:+.3f}  dK_R {o['R']:+.3f}  dK_B {fmt(o['B'], o['B_ci'])}")


def e5(rows, out):
    """Exploratory: options line vs question wording, DROPPED non-neutral rows at ckpt 12 (paired O/L/R)."""
    rs = paired([r for r in rows if r["ckpt"] == 12 and not r["neutral"] and r["state"] == "DROPPED"], "OLR")
    if not rs:
        say("\nE5  (arm L not run)"); return
    line = boot(rs, lambda x: dK(x, "O") - dK(x, "L")); word = boot(rs, lambda x: dK(x, "L") - dK(x, "R"))
    o = dict(n=len(rs), dK_O=dK(rs, "O"), dK_L=dK(rs, "L"), dK_R=dK(rs, "R"), line_ci=ci(line), word_ci=ci(word))
    out["E5"] = o
    say(f"\nE5  all systems pooled, n={len(rs)}: dK_O {o['dK_O']:+.3f}, dK_L {o['dK_L']:+.3f}, dK_R {o['dK_R']:+.3f}; "
        f"options-line effect dK_O-dK_L {fmt(o['dK_O'] - o['dK_L'], o['line_ci'])}; wording effect dK_L-dK_R {fmt(o['dK_L'] - o['dK_R'], o['word_ci'])}")


def decide(fams):
    """Decision rules D1-D3 (ORDER_CHECK_DESIGN.md §5), applied to E1 pooled and per lossy system."""
    say("\n################ decision ################")
    pis = {t: f["E1_pooled"] for t, f in fams.items() if "E1_pooled" in f}
    if len(pis) < len(fams):
        say("E1 incomplete; no decision"); return
    rw = ("codex", "aider", "anthropic_api")
    big = any(p["pi"] > 0.15 for p in pis.values()) or any(f["E1"].get(s, {}).get("dK_B", 1) < 0.5 for f in fams.values() for s in rw)
    small = all(p["pi_ci"][1] <= 0.05 for p in pis.values()) and all(abs(o["pi"]) <= 0.05 for f in fams.values() for o in f["E1"].values()
                                                                      if o["drop"] >= 0.5)
    d = "D3" if big else "D1" if small else "D2"
    J["decision_E1"] = d
    say(f"E1: {d}  (pooled pi: " + ", ".join(f"{t} {p['pi']:+.3f} {p['pi_ci']}" for t, p in pis.items()) + ")")
    for t, f in fams.items():
        e = f.get("E2")
        if not e:
            continue
        if abs(e["dK_B"]) <= 0.10 < abs(e["dK_O"]):
            v = "N-pos (failure explained by option position)"
        elif abs(e["dK_O"] - e["dK_R"]) <= 0.10:
            v = "N-label (position does not explain it; label-content account stands)"
        else:
            v = "N-mixed"
        J.setdefault("decision_E2", {})[t] = v
        say(f"E2 {t}: {v}")
    for t, f in fams.items():
        e = f.get("E3")
        if e:
            v = "P4.7 robust" if all(e[a]["mae_pcs"] < e[a]["mae_acc"] for a in "RB") else "P4.7 NOT robust"
            say(f"E3 {t}: {v}; MAE(PCS) O {e['O']['mae_pcs']:.3f} -> B {e['B']['mae_pcs']:.3f} "
                f"({'paper number changes' if abs(e['B']['mae_pcs'] - e['O']['mae_pcs']) >= 0.005 else 'paper number stands'})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", nargs="+", default=["s4qwen", "s4llama"])
    a = ap.parse_args()
    items = {json.loads(l)["id"]: json.loads(l) for l in open(ROOT / "framework_study/stimuli/items_v2_final.jsonl")}
    fams = {}
    for tag in a.tags:
        rows = load(tag, items)
        n = collections.Counter(arm for r in rows for arm in r["b"])
        say(f"\n################ {tag}: rows with a belief per arm {dict(n)} ################")
        out = {"E1": {}}
        lossy = e1(rows, out)
        e2(rows, lossy, out)
        e3(rows, items, "llama" if "llama" in tag else "qwen", out)
        e4(rows, out)
        e5(rows, out)
        fams[tag] = out
    J.update(fams)
    decide(fams)
    (RES / "order_analysis.txt").write_text("\n".join(LINES) + "\n")
    (RES / "order_analysis.json").write_text(json.dumps(J, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else float(o)))


if __name__ == "__main__":
    main()
