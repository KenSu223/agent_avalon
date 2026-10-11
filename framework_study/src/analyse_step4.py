"""Step 4 analysis (framework_study/STEP4_DESIGN.md §3, predictions P4.1-P4.7). Written before the main runs.

Input : results/probed_<framework>_<tag>.jsonl with tag s4qwen (Qwen3-235B) or s4llama (Llama-3.3-70B), item_set v2
Output: results/step4_analysis.txt / .json
All CIs: user-level bootstrap (B = 2000). Last checkpoint = 12. Memory states count only when both judges agree.
usage: python analyse_step4.py [--tags s4qwen s4llama]
"""
import argparse, collections, glob, json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "framework_study/results"
sys.path.insert(0, str(ROOT / "method"))
import pcme

B = 2000
REWRITE = ["codex", "aider", "anthropic_api", "neutral_roll"]
LINES, J = [], {}


def say(*a):
    s = " ".join(str(x) for x in a); print(s); LINES.append(s)


def load(tag):
    rows = []
    for f in sorted(glob.glob(str(RES / f"probed_*_{tag}.jsonl"))):
        for l in open(f):
            r = json.loads(l)
            if r.get("item_set", "v2") == "v2" or True:
                rows.append(r)
    return rows


def boot_users(rows, fn, seed=0):
    by = collections.defaultdict(list)
    for r in rows:
        by[r["user"]].append(r)
    users = sorted(by)
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(B):
        samp = [r for u in rng.choice(users, len(users)) for r in by[u]]
        out.append(fn(samp))
    return np.array(out, float)


def rate(rs, field, val):
    rs = [r for r in rs if r.get(field) not in (None, "DISAGREE", "UNPARSED")]
    return np.mean([r[field] == val for r in rs]) if rs else np.nan


def ci(a):
    a = np.asarray(a, float); a = a[~np.isnan(a)]
    return (float(np.quantile(a, .025)), float(np.quantile(a, .975))) if len(a) else (np.nan, np.nan)


def contrasts(rs):
    C = [r for r in rs if r["version"] == "C"]; I = [r for r in rs if r["version"] == "I"]
    return dict(R_C=rate(C, "state", "RETAINED"), R_I=rate(I, "state", "RETAINED"), F_C=rate(C, "state", "FLIPPED"), F_I=rate(I, "state", "FLIPPED"),
                K_C=rate(C, "belief", "KEPT"), K_I=rate(I, "belief", "KEPT"), drop=rate(rs, "state", "DROPPED"), R=rate(rs, "state", "RETAINED"))


def family(tag, items, prior_key):
    rows = [r for r in load(tag) if r["ckpt"] == 12]
    if not rows:
        say(f"\n(no probed rows for {tag})"); return None
    say(f"\n################ {tag}: {len(rows)} item-probes at checkpoint 12, {len({r['user'] for r in rows})} users ################")
    non_neutral = [r for r in rows if items[r["item"]]["type"] != "neutral"]
    systems = sorted({r["framework"] for r in rows})
    out = {}
    say(f"{'system':18s} {'drop':>5s} {'R_C':>5s} {'R_I':>5s} {'dR [95% CI]':>22s} {'F_C':>5s} {'F_I':>5s} {'dF':>6s} {'K_C':>5s} {'K_I':>5s} {'dK [95% CI]':>22s}")
    for s in systems:
        rs = [r for r in non_neutral if r["framework"] == s]
        c = contrasts(rs)
        dR = boot_users(rs, lambda x: (lambda c: c["R_C"] - c["R_I"])(contrasts(x)))
        dF = boot_users(rs, lambda x: (lambda c: c["F_I"] - c["F_C"])(contrasts(x)))
        dK = boot_users(rs, lambda x: (lambda c: c["K_C"] - c["K_I"])(contrasts(x)))
        out[s] = dict(c, dR=c["R_C"] - c["R_I"], dR_ci=ci(dR), dF=c["F_I"] - c["F_C"], dF_ci=ci(dF), dK=c["K_C"] - c["K_I"], dK_ci=ci(dK))
        o = out[s]
        say(f"{s:18s} {o['drop']:5.2f} {o['R_C']:5.2f} {o['R_I']:5.2f} {o['dR']:+6.3f} [{o['dR_ci'][0]:+.3f},{o['dR_ci'][1]:+.3f}] "
            f"{o['F_C']:5.3f} {o['F_I']:5.3f} {o['dF']:+6.3f} {o['K_C']:5.2f} {o['K_I']:5.2f} {o['dK']:+6.3f} [{o['dK_ci'][0]:+.3f},{o['dK_ci'][1]:+.3f}]")
    res = {"systems": out}
    # P4.3 lossy systems and Spearman(deletion, dK)
    lossy = [s for s in systems if out[s]["drop"] >= 0.5]
    res["P4_3_lossy"] = {s: out[s]["dK_ci"][0] > 0 for s in lossy}
    res["P4_3_spearman"] = pcme.spearman([out[s]["drop"] for s in systems], [out[s]["dK"] for s in systems])
    say(f"P4.3 lossy systems (drop >= 0.5) with dK > 0 and CI excluding 0: {sum(res['P4_3_lossy'].values())}/{len(lossy)} {res['P4_3_lossy']}; "
        f"Spearman(drop, dK) across systems = {res['P4_3_spearman']:.3f}")
    # P4.5 neutral control (pooled over systems with drop >= 0.5)
    neu = [r for r in rows if items[r["item"]]["type"] == "neutral" and r["framework"] in lossy]
    if neu:
        k = contrasts(neu); bk = boot_users(neu, lambda x: (lambda c: c["K_C"] - c["K_I"])(contrasts(x)))
        res["P4_5"] = dict(dK=k["K_C"] - k["K_I"], ci=ci(bk), n=len(neu))
        say(f"P4.5 neutral control (lossy systems pooled, n={len(neu)}): dK = {k['K_C'] - k['K_I']:+.3f} {ci(bk)} -> "
            f"{'holds' if abs(k['K_C'] - k['K_I']) <= 0.10 else 'does not hold'}")
    # P4.6 updates: reversion to the old value, I vs C (all systems pooled)
    up = [r for r in rows if items[r["item"]]["type"] == "update"]
    if up:
        fn = lambda x: rate([r for r in x if r["version"] == "I"], "belief", "REVERTED") - rate([r for r in x if r["version"] == "C"], "belief", "REVERTED")
        d = fn(up); bd = boot_users(up, fn)
        res["P4_6"] = dict(diff=float(d), ci=ci(bd), n=len(up))
        say(f"P4.6 updates: P(revert to old | I) - P(revert to old | C) = {d:+.3f} {ci(bd)} -> {'holds' if ci(bd)[0] > 0 else 'not shown'}")
    # P4.7 PCS vs retention, cells = system x checkpoint >= 4
    allrows = [r for r in load(tag) if r["ckpt"] >= 4 and r["state"] in ("RETAINED", "DROPPED", "FLIPPED") and r.get("belief") in ("KEPT", "REVERTED")]
    def g_of(r):
        p = items[r["item"]]["prior"][prior_key]
        return p if r["version"] == "C" else 1 - p
    cells = collections.defaultdict(list)
    for r in allrows:
        cells[(r["framework"], r["ckpt"])].append(r)
    Rv, Av, Pv, per_cell = [], [], [], []
    for k, x in cells.items():
        y = np.array([1.0 if r["belief"] == "KEPT" else 0.0 for r in x]); g = np.array([g_of(r) for r in x])
        Rv.append(np.mean([r["state"] == "RETAINED" for r in x])); Av.append(y.mean()); Pv.append((y - g).sum() / (1 - g).sum())
        per_cell.append(dict(framework=k[0], ckpt=k[1], n=len(x), R=float(Rv[-1]), acc=float(Av[-1]), pcs=float(Pv[-1])))
    Rv, Av, Pv = map(np.array, (Rv, Av, Pv))
    res["P4_7"] = dict(mae_acc=float(np.mean(np.abs(Av - Rv))), mae_pcs=float(np.mean(np.abs(Pv - Rv))), cells=len(Rv), per_cell=per_cell)
    say(f"P4.7 MAE(raw acc, R) {res['P4_7']['mae_acc']:.3f}  MAE(PCS, R) {res['P4_7']['mae_pcs']:.3f} over {len(Rv)} cells -> "
        f"{'holds' if res['P4_7']['mae_pcs'] < res['P4_7']['mae_acc'] else 'does not hold'}")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", nargs="+", default=["s4qwen", "s4llama"])
    a = ap.parse_args()
    items = {json.loads(l)["id"]: json.loads(l) for l in open(ROOT / "framework_study/stimuli/items_v2_final.jsonl")}
    fams = {}
    for tag in a.tags:
        key = "llama" if "llama" in tag else "qwen"
        fams[tag] = family(tag, items, key)
    J.update({k: v for k, v in fams.items() if v})
    q, l = fams.get(a.tags[0]), fams.get(a.tags[1]) if len(a.tags) > 1 else None
    if q:
        say("\n################ cross-family ################")
        p41 = {s: (q["systems"][s]["dR_ci"][0] >= -0.05 and q["systems"][s]["dR_ci"][1] <= 0.05) for s in REWRITE if s in q["systems"]}
        say(f"P4.1 (Qwen, rewrite systems, dR 95% CI within +-0.05): {p41}")
        p42 = {s: q["systems"][s]["dF"] <= 0.02 for s in q["systems"]}
        say(f"P4.2 (Qwen, every system dF <= 0.02): {sum(p42.values())}/{len(p42)} {[(s, round(q['systems'][s]['dF'], 3)) for s in q['systems'] if not p42[s]]}")
        J["P4_1"], J["P4_2"] = p41, p42
    if q and l:
        common = sorted(set(q["systems"]) & set(l["systems"]))
        rho = pcme.spearman([q["systems"][s]["R"] for s in common], [l["systems"][s]["R"] for s in common])
        say(f"P4.4 Spearman of overall retention across systems, Qwen vs Llama ({len(common)} systems) = {rho:.3f} -> {'holds' if rho >= 0.7 else 'does not hold'}")
        say("     exploratory: dR Llama - dR Qwen per system: " + "; ".join(f"{s} {l['systems'][s]['dR'] - q['systems'][s]['dR']:+.3f}" for s in common))
        J["P4_4"] = dict(rho=rho)
    (RES / "step4_analysis.txt").write_text("\n".join(LINES) + "\n")
    (RES / "step4_analysis.json").write_text(json.dumps(J, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))


if __name__ == "__main__":
    main()
