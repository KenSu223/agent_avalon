"""Pre-registered property tests P1-P6 of METHOD.md §6 (P7 runs after Step 2).

Inputs
  benchmark_audit/results/closed_book_{qwen3-235b-a22b-2507,llama3-3-70b-instruct}.jsonl   F0 T=0 draws
  method/results/prior_draws_qwen3-235b-a22b-2507.jsonl                                     E1.1 draws
  method/results/refsys_{empty,oracle,bm25_ev,bm25_noev}_F.jsonl                            E1.2
  benchmark_audit/results/rescore_*.jsonl                                                   existing systems (pi_A)
  framework_study/results/probed_*.jsonl + validation_qwen3-235b-a22b-2507.json             framework study
Output: method/results/property_tests.txt / .json
Variants (METHOD v1.1): v10 = as pre-registered; a = g from the evaluation prompt with empty context (E_T1 draws),
strata unchanged; b = compliance follow-up applied to all closed-book draws and reference systems.
usage: python property_tests.py [--only framework] [--variant v10|a|b]
"""
import argparse, collections, glob, json, re, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import pcme

BA = ROOT / "benchmark_audit/results"
RES = HERE / "results"
QW, LL = "qwen3-235b-a22b-2507", "llama3-3-70b-instruct"
B = 2000
ABS = re.compile(r"not (mentioned|provided|specified|available|included|contain|stated|found)|no (information|mention|record|details|data)|"
                 r"don'?t (know|have)|does not (contain|mention|include|specify|provide)|cannot (determine|answer|find)|unknown|unable to|"
                 r"isn'?t (mentioned|specified)|not in (the|my) memory|NOT_IN_MEMORY", re.I)
OUT_LINES, OUT_JSON = [], {}
REFSYS_SUFFIX = "_F"


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s); OUT_LINES.append(s)


def q(samples, p):
    s = np.asarray(samples, float); s = s[~np.isnan(s)]
    return float(np.quantile(s, p))


# ------------------------------------------------------------------ priors

def all_draws():
    d = pcme.load_prior([BA / f"closed_book_{QW}.jsonl", BA / f"closed_book_{LL}.jsonl"])
    pd_path = RES / f"prior_draws_{QW}.jsonl"
    if pd_path.exists():
        d += pcme.load_prior([pd_path])
    meta = {}
    for f in (BA / f"closed_book_{QW}.jsonl",):
        for l in open(f):
            r = json.loads(l)
            meta[r["id"]] = (r["bench"], r["sub"], r.get("category"))
    return d, meta


def prior_variants(draws):
    """D1-D5 of METHOD §6 P6. D5 is the primary definition."""
    qw0 = [x for x in draws if x["model"] == QW and x["draw"] == "F0_T0"]
    ll0 = [x for x in draws if x["model"] == LL]
    qwall = [x for x in draws if x["model"] == QW]
    return {
        "D1_qwen_T0": pcme.Prior(qw0, QW),
        "D2_llama_T0": pcme.Prior(ll0, LL),
        "D3_union_T0": pcme.Prior(qw0 + ll0, QW),
        "D4_qwen_all": pcme.Prior(qwall, QW),
        "D5_union_all": pcme.Prior(qwall + ll0, QW),
    }


def refsys(name):
    p = RES / f"refsys_{name}{REFSYS_SUFFIX}.jsonl"
    return [json.loads(l) for l in open(p)] if p.exists() else []


def as_runs(rows):
    return [dict(id=r["id"], system=r["system"], correct=None if r.get("correct") is None else float(r["correct"]), protocol="F",
                 cluster=r.get("cluster", "all"), answerable=True, abstained=None) for r in rows]


# ------------------------------------------------------------------ P1 / P2 / P3

def p1(prior, meta):
    say("\n=== P1 floor: Empty system under pi_F (g and strata from independent closed-book draws) ===")
    rows = refsys("empty")
    if not rows:
        say("  (no refsys_empty_F.jsonl yet)"); return
    for bench in ("LongMemEval", "LoCoMo", "MemoryAgentBench"):
        rb = [r for r in rows if r["bench"] == bench]
        panel = pcme.Panel(as_runs(rb), prior, "F")
        res = pcme.evaluate(panel, B=B)
        d = res["systems"]["empty"]
        tost = pcme.tost(d["ma"]["point"], res["_boot"]["ma"][0], 0.03)
        cpr_ub = q(res["_boot"]["cpr"][0], 0.95)
        noncomp = np.mean([bool(ABS.search(r["pred"] or "")) for r in rb])
        verdict2 = "pass" if cpr_ub <= 0.03 else "FAIL"
        say(f"  {bench:17s} n={res['n_items']:4d} resistant={res['n_resistant']:4d} | raw acc {d['acc']['point']:.3f} | "
            f"MA {tost['point']:+.3f} 90%CI [{tost['ci90'][0]:+.3f},{tost['ci90'][1]:+.3f}] -> {tost['verdict']} | "
            f"leakage CPR {d['cpr']['point']:.3f} (95% upper {cpr_ub:.3f}) -> {verdict2} | PCS {d['pcs']['point']:+.3f} | "
            f"non-compliance (abstention under pi_F) {noncomp:.3f}")
        OUT_JSON.setdefault("P1", {})[bench] = dict(n=res["n_items"], n_res=res["n_resistant"], acc=d["acc"]["point"], ma=tost,
                                                     cpr=d["cpr"]["point"], cpr_ub95=cpr_ub, leakage_verdict=verdict2,
                                                     pcs=d["pcs"]["point"], noncompliance=float(noncomp))


def bench_panel(prior, systems, bench):
    rows = [r for s in systems for r in refsys(s) if r["bench"] == bench and (bench != "MemoryAgentBench" or r["sub"] in ("ruler_qa1", "ruler_qa2"))]
    return pcme.Panel(as_runs(rows), prior, "F"), rows


def p2(prior):
    say("\n=== P2 ceiling / solvability: Oracle (gold evidence only) under pi_F ===")
    if not refsys("oracle"):
        say("  (no refsys_oracle_F.jsonl yet)"); return
    for bench in ("LoCoMo", "MemoryAgentBench"):
        panel, rows = bench_panel(prior, ["oracle", "empty"], bench)
        res = pcme.evaluate(panel, B=B)
        o, e = res["systems"]["oracle"], res["systems"]["empty"]
        bo = panel.systems.index("oracle"); be = panel.systems.index("empty")
        cpr_lb = q(res["_boot"]["cpr"][bo], 0.05)
        rng_s = res["_boot"]["pcs"][bo] - res["_boot"]["pcs"][be]
        rng_pt = o["pcs"]["point"] - e["pcs"]["point"]
        rng_lb = q(rng_s, 0.05)
        W = pcme.bootstrap_weights(len(panel.ids), B)
        Y = panel.row("oracle"); R = panel.R
        acc_A = (W * Y * ~R).sum(1) / (W * ~R).sum(1); acc_R = (W * Y * R).sum(1) / (W * R).sum(1)
        gap_pt = Y[~R].mean() - Y[R].mean()
        say(f"  {bench:17s} n={res['n_items']} resistant={res['n_resistant']} | oracle acc {o['acc']['point']:.3f} | "
            f"CPR_oracle {o['cpr']['point']:.3f} (95% lower {cpr_lb:.3f}) -> {'pass' if cpr_lb >= 0.5 else 'FAIL'} | "
            f"dynamic range PCS_oracle-PCS_empty {rng_pt:.3f} (95% lower {rng_lb:.3f}) -> {'pass' if rng_lb >= 0.5 else 'FAIL'} | "
            f"difficulty gap acc(A)-acc(R) {gap_pt:+.3f} [{q(acc_A-acc_R,0.025):+.3f},{q(acc_A-acc_R,0.975):+.3f}] -> "
            f"{'normalise (gap > 0.10)' if gap_pt > 0.10 else 'no normalisation needed'} | PI_oracle {o['pi']['point']:.3f}")
        gA = panel.g[~R].mean()
        pA = (Y[~R].mean() - gA) / (1 - gA)
        say(f"    exploratory: under the two-state model with fallback to guessing, implied reader fidelity on the answerable "
            f"stratum p_A = (acc_A - g_A)/(1 - g_A) = {pA:.3f} vs resistant p_R = {Y[R].mean():.3f}  (g_A = {gA:.3f}); "
            f"gap explained by prior rescue = {(1 - pA) * gA:.3f} of the {gap_pt:+.3f}")
        OUT_JSON.setdefault("P2", {})[bench] = dict(pA_implied=float(pA), gA=float(gA),
                                                     n=res["n_items"], oracle_acc=o["acc"]["point"], cpr=o["cpr"]["point"], cpr_lb95=cpr_lb,
                                                     range=rng_pt, range_lb95=rng_lb, gap=gap_pt, gap_ci=(q(acc_A - acc_R, .025), q(acc_A - acc_R, .975)),
                                                     pi_oracle=o["pi"]["point"])


def p3_bench(prior):
    say("\n=== P3 context-neutral guessing (A2): BM25 without evidence under pi_F, D = mean(Y - g) ===")
    if not refsys("bm25_noev"):
        say("  (no refsys_bm25_noev_F.jsonl yet)"); return
    for bench in ("LoCoMo", "MemoryAgentBench"):
        rows = [r for r in refsys("bm25_noev") if r["bench"] == bench and r.get("correct") is not None and r["id"] in prior.g]
        for label, sub in (("clean-absent", [r for r in rows if not r["has_gold"]]), ("all", rows)):
            Y = np.array([float(r["correct"]) for r in sub]); g = np.array([prior.g[r["id"]] for r in sub])
            W = pcme.bootstrap_weights(len(sub), B)
            Ds = (W * (Y - g)).sum(1) / W.sum(1); D = float((Y - g).mean())
            noncomp = np.mean([bool(ABS.search(r["pred"] or "")) for r in sub])
            if bench == "MemoryAgentBench":
                t = pcme.tost(D, Ds, 0.05); verdict = t["verdict"]
                ci_txt = f"90%CI [{t['ci90'][0]:+.3f},{t['ci90'][1]:+.3f}]"
            else:
                lb = q(Ds, 0.05); verdict = "pass (no suppression)" if lb >= -0.03 else "FAIL (guessing suppressed)"
                ci_txt = f"95% lower {lb:+.3f}"
            primary = label == "clean-absent"
            say(f"  {bench:17s} {label:12s} n={len(sub):4d} | acc {Y.mean():.3f} mean g {g.mean():.3f} | D {D:+.3f} {ci_txt}"
                f"{' -> ' + verdict if primary else ''} | non-compliance {noncomp:.3f}")
            OUT_JSON.setdefault("P3", {})[f"{bench}_{label}"] = dict(n=len(sub), acc=float(Y.mean()), g=float(g.mean()), D=D,
                                                                      ci=(q(Ds, .05), q(Ds, .95)), verdict=verdict if primary else None,
                                                                      noncompliance=float(noncomp))
    # by stratum, for interpretation
    rows = [r for r in refsys("bm25_noev") if r.get("correct") is not None and r["id"] in prior.g and not r["has_gold"]]
    for bench in ("LoCoMo", "MemoryAgentBench"):
        for st, name in ((True, "resistant"), (False, "answerable")):
            sub = [r for r in rows if r["bench"] == bench and prior.resistant[r["id"]] == st]
            if sub:
                say(f"    {bench:15s} {name:10s} n={len(sub):4d} acc {np.mean([r['correct'] for r in sub]):.3f}  mean g {np.mean([prior.g[r['id']] for r in sub]):.3f}")


# ------------------------------------------------------------------ framework study (P3 part 3, P4)

def framework_rows():
    sys.path.insert(0, str(ROOT / "framework_study/src"))
    from analyse_frameworks import load
    v1 = json.load(open(ROOT / "framework_study/results/validation_qwen3-235b-a22b-2507.json"))["V1"]
    items = {json.loads(l)["id"]: json.loads(l) for l in open(ROOT / "framework_study/stimuli/items.jsonl")}
    rows = []
    for r in load():
        if r["item"] == "S08" or v1.get(r["item"], {}).get("p_congruent") is None:
            continue
        pc = v1[r["item"]]["p_congruent"]
        r = dict(r)
        r["g"] = pc if r["version"] == "C" else 1 - pc
        r["pc"] = pc
        if r.get("belief") in ("KEPT", "REVERTED"):
            r["Y"] = 1.0 if r["belief"] == "KEPT" else 0.0
            r["chose_C"] = 1.0 if (r["belief"] == "KEPT") == (r["version"] == "C") else 0.0
        rows.append(r)
    return rows


def user_boot(rows, fn, B=B, seed=0):
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


def p3_framework(rows):
    say("\n=== P3 (framework study): DROPPED items, P(belief = congruent option) vs V1 prior p_congruent ===")
    strong = [r for r in rows if r["state"] == "DROPPED" and "chose_C" in r and not r["framework"].endswith("@8b")]
    weak = [r for r in rows if r["state"] == "DROPPED" and "chose_C" in r and r["framework"].endswith("@8b")]
    for label, sub in (("Qwen3-235B compactors (primary)", strong), ("Qwen3-8B compactors", weak)):
        fn = lambda s: np.mean([r["chose_C"] - r["pc"] for r in s])
        fnb = lambda s: np.mean([r["chose_C"] - (1.0 if r["pc"] >= 0.5 else 0.0) for r in s])
        D = fn(sub); Ds = user_boot(sub, fn)
        t = pcme.tost(D, Ds, 0.05)
        Db = fnb(sub); Dbs = user_boot(sub, fnb)
        say(f"  {label:34s} n={len(sub):5d} | P(chose C) {np.mean([r['chose_C'] for r in sub]):.3f}  mean p_congruent {np.mean([r['pc'] for r in sub]):.3f} | "
            f"D {D:+.3f} 90%CI [{t['ci90'][0]:+.3f},{t['ci90'][1]:+.3f}] -> {t['verdict']}"
            f"{'' if 'primary' in label else ' (secondary)'} | exploratory, g = mode of V1: D {Db:+.3f} [{q(Dbs,.025):+.3f},{q(Dbs,.975):+.3f}]")
        OUT_JSON.setdefault("P3_framework", {})[label] = dict(n=len(sub), D=float(D), tost=t, D_mode=float(Db))
    say("  per framework (Qwen3-235B compactors):")
    for f in sorted({r["framework"] for r in strong}):
        s = [r for r in strong if r["framework"] == f]
        if len(s) >= 30:
            say(f"    {f:20s} n={len(s):4d} D {np.mean([r['chose_C'] - r['pc'] for r in s]):+.3f}")


def p4(rows):
    say("\n=== P4 calibration against judge-coded retention (framework study; cells = framework x checkpoint >= 2) ===")
    use = [r for r in rows if r["ckpt"] >= 2 and r["state"] in ("RETAINED", "DROPPED", "FLIPPED") and "Y" in r]
    cells = sorted({(r["framework"], r["ckpt"]) for r in use})

    def cell_stats(s):
        by = collections.defaultdict(list)
        for r in s:
            by[(r["framework"], r["ckpt"])].append(r)
        R, A, P, RI, C = [], [], [], [], []
        for c in cells:
            x = by.get(c, [])
            if len(x) < 10:
                R.append(np.nan); A.append(np.nan); P.append(np.nan); RI.append(np.nan); C.append(np.nan); continue
            y = np.array([r["Y"] for r in x]); g = np.array([r["g"] for r in x])
            R.append(np.mean([r["state"] == "RETAINED" for r in x]))
            xi = [r for r in x if r["version"] == "I"]
            RI.append(np.mean([r["state"] == "RETAINED" for r in xi]) if xi else np.nan)
            A.append(y.mean()); P.append(((y - g).sum()) / ((1 - g).sum()))
            C.append(np.mean([r["Y"] for r in xi]) if xi else np.nan)
        return [np.array(v) for v in (R, A, P, RI, C)]

    def summary(s):
        R, A, P, RI, C = cell_stats(s)
        m = ~np.isnan(R) & ~np.isnan(P)
        mae_a = np.mean(np.abs(A[m] - R[m])); mae_p = np.mean(np.abs(P[m] - R[m]))
        ra = np.corrcoef(A[m], R[m])[0, 1]; rp = np.corrcoef(P[m], R[m])[0, 1]
        mi = m & ~np.isnan(RI) & ~np.isnan(C)
        return dict(mae_acc=mae_a, mae_pcs=mae_p, r_acc=ra, r_pcs=rp, d_mae=mae_p - mae_a, d_r=rp - ra,
                    mae_acc_RI=np.mean(np.abs(A[mi] - RI[mi])), mae_pcs_RI=np.mean(np.abs(P[mi] - RI[mi])),
                    mae_cpr_RI=np.mean(np.abs(C[mi] - RI[mi])), n_cells=int(m.sum()))

    pt = summary(use)
    bs = collections.defaultdict(list)
    by = collections.defaultdict(list)
    for r in use:
        by[r["user"]].append(r)
    users = sorted(by); rng = np.random.default_rng(0)
    for _ in range(B // 2):
        samp = [r for u in rng.choice(users, len(users)) for r in by[u]]
        sm = summary(samp)
        for k, v in sm.items():
            bs[k].append(v)
    ci = lambda k: (q(bs[k], 0.025), q(bs[k], 0.975))
    v1 = "pass" if ci("d_mae")[1] < 0 else "FAIL"
    v2 = "pass" if ci("d_r")[0] > 0 else ("not shown" if ci("d_r")[1] >= 0 else "FAIL")
    say(f"  cells {pt['n_cells']} | MAE(raw acc, R) {pt['mae_acc']:.3f}  MAE(PCS, R) {pt['mae_pcs']:.3f}  difference {pt['d_mae']:+.3f} "
        f"[{ci('d_mae')[0]:+.3f},{ci('d_mae')[1]:+.3f}] -> {v1}")
    say(f"  Pearson r(raw acc, R) {pt['r_acc']:.3f}  r(PCS, R) {pt['r_pcs']:.3f}  difference {pt['d_r']:+.3f} [{ci('d_r')[0]:+.3f},{ci('d_r')[1]:+.3f}] -> {v2}")
    say(f"  against R^I (counter-prior retention): MAE raw acc {pt['mae_acc_RI']:.3f} | PCS {pt['mae_pcs_RI']:.3f} | CPR (acc on I items) {pt['mae_cpr_RI']:.3f}")
    OUT_JSON["P4"] = dict(point={k: float(v) for k, v in pt.items()}, ci={k: ci(k) for k in bs}, verdict_mae=v1, verdict_r=v2)
    R, A, P, RI, C = cell_stats(use)
    say(f"  {'cell':24s} {'R':>6s} {'raw acc':>8s} {'PCS':>6s} {'R^I':>6s} {'CPR':>6s}")
    for c, r_, a_, p_, ri, cc in zip(cells, R, A, P, RI, C):
        if c[1] == 12 or c[0] == "raw_history":
            say(f"  {c[0] + '@' + str(c[1]):24s} {r_:6.2f} {a_:8.2f} {p_:6.2f} {ri:6.2f} {cc:6.2f}")


# ------------------------------------------------------------------ P5 / P6

def p5(prior):
    say("\n=== P5 illustration: known retention r, mixing BM25+ev (kept) and BM25-ev (dropped) responses per item ===")
    ev, noev = refsys("bm25_ev"), refsys("bm25_noev")
    if not ev or not noev:
        say("  (bm25 runs missing)"); return
    for bench in ("LoCoMo", "MemoryAgentBench"):
        a = {r["id"]: float(r["correct"]) for r in ev if r["bench"] == bench and r.get("correct") is not None}
        b = {r["id"]: float(r["correct"]) for r in noev if r["bench"] == bench and r.get("correct") is not None}
        ids = sorted(set(a) & set(b) & set(prior.g))
        Y1 = np.array([a[i] for i in ids]); Y0 = np.array([b[i] for i in ids]); g = np.array([prior.g[i] for i in ids])
        R = np.array([prior.resistant[i] for i in ids])
        rng = np.random.default_rng(0)
        say(f"  {bench} (n={len(ids)}; ORS reference = BM25+ev)")
        say(f"    {'regime':16s} {'r':>4s} {'true R':>7s} {'true R on resistant':>20s} {'acc':>6s} {'CPR':>6s} {'PCS':>6s} {'ORS':>6s}")
        for regime in ("random", "prior-directed", "counter-prior"):
            for r in (0.0, 0.25, 0.5, 0.75, 1.0):
                vals = []
                for _ in range(200):
                    if regime == "random":
                        Z = rng.random(len(ids)) < r
                    else:
                        # keep r of the items; the dropped ones are taken preferentially from one stratum
                        n_drop = int(round((1 - r) * len(ids)))
                        first = np.where(~R)[0] if regime == "prior-directed" else np.where(R)[0]
                        second = np.where(R)[0] if regime == "prior-directed" else np.where(~R)[0]
                        order = np.concatenate([rng.permutation(first), rng.permutation(second)])
                        Z = np.ones(len(ids), bool); Z[order[:n_drop]] = False
                    Y = np.where(Z, Y1, Y0)
                    vals.append((Z.mean(), Z[R].mean(), Y.mean(), Y[R].mean(), pcme.pcs(Y, g), pcme.ors(Y, g, Y1)))
                m = np.mean(vals, 0)
                say(f"    {regime:16s} {r:4.2f} {m[0]:7.2f} {m[1]:20.2f} {m[2]:6.2f} {m[3]:6.2f} {m[4]:6.2f} {m[5]:6.2f}")


def p6(variants, meta):
    say("\n=== P6 sensitivity to the prior estimator ===")
    say("  prior-answerable rate by benchmark / definition (answerable items only)")
    benches = collections.defaultdict(list)
    for i, (b, s, c) in meta.items():
        if b == "PrefEval" or (b == "LoCoMo" and c == 5) or (b == "LongMemEval" and s.endswith("_abs")):
            continue
        key = b if b != "MemoryAgentBench" else f"MAB:{s}"
        benches[key].append(i)
    hdr = f"  {'benchmark':24s} {'n':>5s} " + " ".join(f"{k:>14s}" for k in variants)
    say(hdr)
    OUT_JSON["P6_rates"] = {}
    for b, ids in sorted(benches.items()):
        cells = []
        for k, p in variants.items():
            ii = [i for i in ids if i in p.resistant]
            cells.append(f"{1 - np.mean([p.resistant[i] for i in ii]):14.3f}" if ii else f"{'-':>14s}")
            OUT_JSON["P6_rates"].setdefault(b, {})[k] = (1 - float(np.mean([p.resistant[i] for i in ii]))) if ii else None
        say(f"  {b:24s} {len(ids):5d} " + " ".join(cells))
    say("  CPR ranking of the existing systems (pi_A rescore runs) under each definition; Kendall tau_b vs D5 with paired-bootstrap CI")
    for bench, pat, where in (("LoCoMo", "rescore_locomo_*.jsonl", []), ("MAB RULER-QA1", "rescore_mab_ruler_*.jsonl", [("sub", "ruler_qa1")])):
        runs = pcme.load_runs(sorted(glob.glob(str(BA / pat))), where)
        panels = {k: pcme.Panel(runs, p, "A") for k, p in variants.items()}
        base = panels["D5_union_all"]
        ids = base.ids
        W = pcme.bootstrap_weights(len(ids), 1000)
        cprs = {}
        for k, pn in panels.items():
            # align on the same item set as D5 for paired comparison
            pos = {i: j for j, i in enumerate(pn.ids)}
            sel = [pos[i] for i in ids]
            Y = pn.Y[:, sel]; R = pn.R[sel]
            cprs[k] = (pcme.cpr(Y, R), np.stack([pcme.cpr(Y[s], R, W) for s in range(len(pn.systems))]), int(R.sum()))
        say(f"  {bench}: systems {len(base.systems)}  items {len(ids)}")
        for k, (pt, bs, nres) in cprs.items():
            tau = pcme.kendall_tau_b(pt, cprs["D5_union_all"][0])
            taus = [pcme.kendall_tau_b(bs[:, j], cprs["D5_union_all"][1][:, j]) for j in range(bs.shape[1])]
            pass_txt = ""
            if k == "D3_union_T0" and bench == "LoCoMo":
                pass_txt = " -> " + ("pass" if tau >= 0.8 else "FAIL (rankings estimator-sensitive)")
            say(f"    {k:14s} resistant {nres:4d}  tau_b vs D5 {tau:.3f} [{q(taus,.025):.3f},{q(taus,.975):.3f}]{pass_txt}")
            OUT_JSON.setdefault("P6_tau", {}).setdefault(bench, {})[k] = dict(tau=tau, ci=(q(taus, .025), q(taus, .975)), n_res=nres)


def prior_variant_a(prim):
    """Remedy (a): g_i = mean of the three E_T1 draws (pi_F evaluation prompt, empty context); strata = D5."""
    ev = pcme.load_prior([RES / f"prior_draws_{QW}_evalprompt.jsonl"])
    pa = pcme.Prior(ev, QW)
    p = pcme.Prior.__new__(pcme.Prior)
    p.reader = QW
    ids = [i for i in prim.g if i in pa.g]
    p.draws = {i: pa.draws[i] for i in ids}
    p.g = {i: pa.g[i] for i in ids}
    p.resistant = {i: prim.resistant[i] for i in ids}
    return p


def prior_variant_b():
    """Remedy (b): the six Qwen draws after the compliance follow-up + Llama F0 T=0; D5-style strata."""
    d = pcme.load_prior([RES / f"prior_draws_{QW}_reask.jsonl"]) + pcme.load_prior([BA / f"closed_book_{LL}.jsonl"])
    return pcme.Prior(d, QW)


def main():
    global REFSYS_SUFFIX
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--variant", default="v10", choices=["v10", "a", "b"])
    a = ap.parse_args()
    if a.variant != "v10":
        draws, meta = all_draws()
        prim = prior_variants(draws)["D5_union_all"]
        if a.variant == "a":
            prim = prior_variant_a(prim)
            say("variant a: g from the pi_F evaluation prompt with empty context (3 x T=1 draws); strata = D5")
        else:
            prim = prior_variant_b(); REFSYS_SUFFIX = "_Freask"
            say("variant b: compliance follow-up on all closed-book draws and reference systems; g and strata recomputed")
        p1(prim, meta); p2(prim); p3_bench(prim)
        p5(prim)
        (RES / f"property_tests_{a.variant}.txt").write_text("\n".join(OUT_LINES) + "\n")
        (RES / f"property_tests_{a.variant}.json").write_text(json.dumps(OUT_JSON, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))
        return
    if a.only != "framework":
        draws, meta = all_draws()
        have_new = (RES / f"prior_draws_{QW}.jsonl").exists()
        say(f"prior draws: {len(draws)} (E1.1 draws present: {have_new})")
        variants = prior_variants(draws)
        prim = variants["D5_union_all"]
        p1(prim, meta); p2(prim); p3_bench(prim)
    rows = framework_rows()
    p3_framework(rows); p4(rows)
    if a.only != "framework":
        p5(prim); p6(variants, meta)
    tag = "_framework" if a.only == "framework" else ""
    (RES / f"property_tests{tag}.txt").write_text("\n".join(OUT_LINES) + "\n")
    (RES / f"property_tests{tag}.json").write_text(json.dumps(OUT_JSON, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))


if __name__ == "__main__":
    main()
