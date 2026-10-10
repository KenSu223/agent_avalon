"""Step 2.4: analysis of the protocol comparison, exactly as pre-registered in METHOD.md §10.2 (H1-H8) + P7.

Inputs : results/protocols_<bench>_<system>.jsonl, results/abstention_validation.json (+ abstention_llm.jsonl if the
         validation selected the LLM classifier), prior draws (D5 strata; g' and g''), refsys_oracle_F.jsonl,
         benchmark_audit/results/rescore_*.jsonl (v1, for H8)
Output : results/protocol_analysis.txt / .json
"""
import collections, glob, json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import pcme
from property_tests import all_draws, prior_variants, prior_variant_a, RES, BA, QW, q

B = 2000
LINES, J = [], {}


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s); LINES.append(s)


def boot_p(samples):
    s = np.asarray(samples, float); s = s[~np.isnan(s)]
    return float(min(1.0, 2 * min((s <= 0).mean(), (s >= 0).mean())))


def load_protocols(bench):
    rows = collections.defaultdict(dict)
    for f in sorted(glob.glob(str(RES / f"protocols_{bench}_*.jsonl"))):
        if bench == "mab_ruler" and Path(f).name.startswith("protocols_mab_ruler_qa2_"):
            continue
        for l in open(f):
            r = json.loads(l)
            rows[r["system"]][r["id"]] = r
    return rows


def abstention_lookup():
    v = json.load(open(RES / "abstention_validation.json"))
    if v["decision"] == "regex":
        return v, None
    m = {}
    for l in open(RES / "abstention_llm.jsonl"):
        r = json.loads(l)
        m[(r["bench"], r["system"], r["id"], r["proto"])] = r["abst_llm"]
    return v, m


def g_from(path, ids):
    d = collections.defaultdict(list)
    for l in open(path):
        r = json.loads(l)
        if r.get("correct") is not None:
            d[r["id"]].append(float(r["correct"]))
    return np.array([np.mean(d[i]) for i in ids])


def analyse(bench, label, rows, strata, abst_map, oracle):
    say(f"\n################ {label} ################")
    systems = sorted(rows)
    ids = sorted(set.intersection(*[{i for i, r in rows[s].items() if r["answerable"]} for s in systems]) & set(strata.resistant))
    S, n = len(systems), len(ids)
    get = lambda s, i, k: rows[s][i].get(k)
    def ab(s, i, p):
        if abst_map is None:
            return float(bool(get(s, i, f"abst_{p}_regex")))
        v = abst_map.get((bench, s, i, p))
        return float(bool(v)) if v is not None else float(bool(get(s, i, f"abst_{p}_regex")))
    Y = {p: np.array([[float(bool(get(s, i, f"correct_{p}"))) for i in ids] for s in systems]) for p in ("A", "F", "FR")}
    AB = {p: np.array([[ab(s, i, p) for i in ids] for s in systems]) for p in ("A", "F", "FR")}
    R = np.array([strata.resistant[i] for i in ids])
    gF = g_from(RES / f"prior_draws_{QW}_evalprompt.jsonl", ids)
    gFR = g_from(RES / f"prior_draws_{QW}_evalprompt_reask.jsonl", ids)
    W = pcme.bootstrap_weights(n, B)
    say(f"systems {S}  answerable items {n}  prior-resistant {int(R.sum())}  mean g' {gF.mean():.3f}  mean g'' {gFR.mean():.3f}")
    acc = {p: pcme.acc(Y[p]) for p in Y}
    accB = {p: np.stack([pcme.acc(Y[p][s], W) for s in range(S)]) for p in Y}      # S x B
    cpr = {p: pcme.cpr(Y[p], R) for p in Y}
    cprB = {p: np.stack([pcme.cpr(Y[p][s], R, W) for s in range(S)]) for p in Y}
    abA = AB["A"].mean(1); abAB = np.stack([pcme.acc(AB["A"][s], W) for s in range(S)])

    say(f"{'system':26s} {'acc A':>6s} {'acc F':>6s} {'acc FR':>6s} {'CPR A':>6s} {'CPR F':>6s} {'CPR FR':>6s} {'abst A':>7s} {'abst F':>7s} {'abst FR':>7s} "
        f"{'PCS F':>6s} {'PCS FR':>7s} {'intf F':>6s} {'intf FR':>7s}")
    pcsF = pcme.pcs(Y["F"], gF); pcsFR = pcme.pcs(Y["FR"], gFR)
    tF = pcme.two_by_two(Y["F"], R); tFR = pcme.two_by_two(Y["FR"], R)
    for k in np.argsort(-acc["A"]):
        say(f"{systems[k]:26s} {acc['A'][k]:6.3f} {acc['F'][k]:6.3f} {acc['FR'][k]:6.3f} {cpr['A'][k]:6.3f} {cpr['F'][k]:6.3f} {cpr['FR'][k]:6.3f} "
            f"{AB['A'][k].mean():7.3f} {AB['F'][k].mean():7.3f} {AB['FR'][k].mean():7.3f} {pcsF[k]:6.3f} {pcsFR[k]:7.3f} {tF['interference'][k]:6.3f} {tFR['interference'][k]:7.3f}")
    out = dict(systems=systems, n=n, n_res=int(R.sum()), acc={p: acc[p].tolist() for p in acc}, cpr={p: cpr[p].tolist() for p in cpr},
               abst={p: AB[p].mean(1).tolist() for p in AB}, pcs_F=pcsF.tolist(), pcs_FR=pcsFR.tolist(),
               interference_F=tF["interference"].tolist(), interference_FR=tFR["interference"].tolist())

    # H1
    d = acc["F"] - acc["A"]; dB = accB["F"] - accB["A"]
    rho = pcme.spearman(d, abA); rhoB = [pcme.spearman(dB[:, b], abAB[:, b]) for b in range(B)]
    p1 = boot_p(rhoB)
    say(f"H1 Spearman(acc_F - acc_A, abstention under pi_A) = {rho:.3f} [{q(rhoB,.025):.3f},{q(rhoB,.975):.3f}]  bootstrap p {p1:.4f}")
    d2 = acc["FR"] - acc["A"]; d2B = accB["FR"] - accB["A"]
    rho2 = pcme.spearman(d2, abA); rho2B = [pcme.spearman(d2B[:, b], abAB[:, b]) for b in range(B)]
    say(f"   (pi_F+R) Spearman(acc_FR - acc_A, abstention under pi_A) = {rho2:.3f} [{q(rho2B,.025):.3f},{q(rho2B,.975):.3f}]")
    out["H1"] = dict(rho=rho, ci=(q(rhoB, .025), q(rhoB, .975)), p=p1, rho_FR=rho2, ci_FR=(q(rho2B, .025), q(rho2B, .975)))

    # H2
    def dtau(pa, pb):
        t_a = pcme.kendall_tau_b(acc[pa], cpr[pa]); t_b = pcme.kendall_tau_b(acc[pb], cpr[pb])
        bs = [pcme.kendall_tau_b(accB[pb][:, b], cprB[pb][:, b]) - pcme.kendall_tau_b(accB[pa][:, b], cprB[pa][:, b]) for b in range(B)]
        return t_a, t_b, t_b - t_a, bs
    tA, tF_, dt, dtB = dtau("A", "F")
    p2 = boot_p(dtB)
    say(f"H2 tau_b(acc, CPR): pi_A {tA:.3f}  pi_F {tF_:.3f}  delta {dt:+.3f} [{q(dtB,.025):+.3f},{q(dtB,.975):+.3f}]  bootstrap p {p2:.4f}")
    _, tFR_, dt2, dt2B = dtau("A", "FR")
    say(f"   (pi_F+R) tau_b {tFR_:.3f}  delta {dt2:+.3f} [{q(dt2B,.025):+.3f},{q(dt2B,.975):+.3f}]")
    out["H2"] = dict(tau_A=tA, tau_F=tF_, dtau=dt, ci=(q(dtB, .025), q(dtB, .975)), p=p2, tau_FR=tFR_, dtau_FR=dt2, ci_FR=(q(dt2B, .025), q(dt2B, .975)))

    # H3
    for p in ("F", "FR"):
        inv = []
        for s in range(S):
            lo, hi = q(cprB[p][s] - cprB["A"][s], .05), q(cprB[p][s] - cprB["A"][s], .95)
            inv.append(-0.03 <= lo and hi <= 0.05)
        say(f"H3 CPR invariance pi_{p} vs pi_A: {sum(inv)}/{S} systems with 90% CI of CPR_{p} - CPR_A inside [-0.03, +0.05]; "
            f"max |diff| {np.max(np.abs(cpr[p] - cpr['A'])):.3f}; not invariant: {[systems[s] for s in range(S) if not inv[s]]}")
        out[f"H3_{p}"] = dict(n_invariant=int(sum(inv)), S=S, not_invariant=[systems[s] for s in range(S) if not inv[s]])

    # H4
    thr = 0.05 if bench.startswith("mab_ruler") else 0.10
    poor = [s for s in range(S) if cpr["A"][s] <= thr]
    A_ = ~R
    accA_ans = lambda p, w=None: np.stack([pcme.acc(Y[p][s][A_], None if w is None else w[:, A_]) for s in poor])
    if len(poor) >= 3:
        Wn = W
        sdA = accA_ans("A").std(); sdF = accA_ans("F").std(); sdFR = accA_ans("FR").std()
        bA = accA_ans("A", Wn); bF = accA_ans("F", Wn); bFR = accA_ans("FR", Wn)
        ratio = bF.std(0) / bA.std(0); ratio2 = bFR.std(0) / bA.std(0)
        gA = gF[A_].mean(); gA2 = gFR[A_].mean()
        say(f"H4 memory-poor systems (CPR_A <= {thr}): {[systems[s] for s in poor]}")
        say(f"   SD of acc on the answerable stratum: pi_A {sdA:.3f}  pi_F {sdF:.3f}  ratio {sdF/sdA:.3f} [{q(ratio,.025):.3f},{q(ratio,.975):.3f}]  "
            f"-> {'pass' if q(ratio,.975) < 1 else 'not shown'}")
        say(f"   (pi_F+R) SD {sdFR:.3f}  ratio {sdFR/sdA:.3f} [{q(ratio2,.025):.3f},{q(ratio2,.975):.3f}]")
        say(f"   mean acc on answerable stratum: pi_A {accA_ans('A').mean():.3f}  pi_F {accA_ans('F').mean():.3f} (g' {gA:.3f})  pi_F+R {accA_ans('FR').mean():.3f} (g'' {gA2:.3f})")
        out["H4"] = dict(poor=[systems[s] for s in poor], sdA=sdA, sdF=sdF, ratio=sdF / sdA, ci=(q(ratio, .025), q(ratio, .975)),
                         sdFR=sdFR, ratio_FR=sdFR / sdA, ci_FR=(q(ratio2, .025), q(ratio2, .975)), gA=gA, gA2=gA2)
    else:
        say(f"H4 fewer than 3 memory-poor systems (CPR_A <= {thr}); not tested")

    # H5
    mx = AB["FR"].mean(1)
    say(f"H5 abstention under pi_F+R: max {mx.max():.3f} ({systems[int(mx.argmax())]}) -> {'pass' if mx.max() <= 0.05 else 'FAIL'}; "
        f"under pi_F: {AB['F'].mean(1).min():.3f}-{AB['F'].mean(1).max():.3f}; under pi_A: {abA.min():.3f}-{abA.max():.3f}")
    out["H5"] = dict(max_abst_FR=float(mx.max()), range_F=(float(AB["F"].mean(1).min()), float(AB["F"].mean(1).max())))

    # H6
    say("H6 descriptive")
    for p, g in (("F", gF), ("FR", gFR)):
        maB = np.stack([pcme.ma(Y[p][s], g, W) for s in range(S)]); pcsB = np.stack([pcme.pcs(Y[p][s], g, W) for s in range(S)])
        say(f"  pi_{p}: " + "; ".join(f"{systems[s]} PCS {pcme.pcs(Y[p][s], g):.3f} [{q(pcsB[s],.025):.3f},{q(pcsB[s],.975):.3f}]" for s in np.argsort(-acc['A'])))
        say(f"  tau_b(PCS_{p}, CPR_{p}) = {pcme.kendall_tau_b(pcme.pcs(Y[p], g), cpr[p]):.3f}")
    if oracle:
        o_ids = [i for i in ids if i in oracle]
        idx = [ids.index(i) for i in o_ids]
        Ro = R[idx]; Yo = np.array([oracle[i] for i in o_ids])
        cpr_o = Yo[Ro].mean()
        say(f"  oracle CPR (pi_F, Step 1) {cpr_o:.3f} on {len(o_ids)} items; oracle-normalised CPR_A / CPR_F: " +
            "; ".join(f"{systems[s]} {Y['A'][s][idx][Ro].mean()/cpr_o:.3f}/{Y['F'][s][idx][Ro].mean()/cpr_o:.3f}" for s in np.argsort(-acc['A'])))
        out["oracle_cpr"] = float(cpr_o)
    if bench == "locomo":
        cats = np.array([rows[systems[0]][i]["category"] for i in ids])
        for c in (1, 2, 3, 4):
            m = (cats == c) & R
            say(f"  CPR_A / CPR_F, category {c} (n_res={int(m.sum())}): " + "; ".join(f"{systems[s]} {Y['A'][s][m].mean():.2f}/{Y['F'][s][m].mean():.2f}" for s in np.argsort(-acc['A'])))
    for p in ("A", "F"):
        diff = lambda SB, pt: {(systems[i], systems[j]): (float(pt[i] - pt[j]), (q(SB[i] - SB[j], .025), q(SB[i] - SB[j], .975))) for i in range(S) for j in range(i + 1, S)}
        conf, unres = pcme.confirmed_reversals(diff(accB[p], acc[p]), diff(cprB[p], cpr[p]))
        say(f"  acc_{p} vs CPR_{p}: confirmed reversals {conf}  unresolved {len(unres)}")
        out[f"reversals_{p}"] = dict(confirmed=conf, unresolved=len(unres))
    return out


def h7(rows, label, abst_map=None):
    say(f"\n################ H7 unanswerable items ({label}, pi_A) ################")
    systems = sorted(rows)
    u_ids = sorted(set.intersection(*[{i for i, r in rows[s].items() if not r["answerable"]} for s in systems]))
    a_ids = sorted(set.intersection(*[{i for i, r in rows[s].items() if r["answerable"]} for s in systems]))
    def abstain(s, i):
        if abst_map is not None and abst_map.get(("locomo", s, i, "A")) is not None:
            return float(bool(abst_map[("locomo", s, i, "A")]))
        return float(bool(rows[s][i]["abst_A_regex"]))
    CA = np.array([[abstain(s, i) for i in u_ids] for s in systems]); FA = np.array([[abstain(s, i) for i in a_ids] for s in systems])
    RAW = np.array([[float(bool(rows[s][i]["correct_A"])) for i in u_ids] for s in systems])
    return systems, u_ids, a_ids, CA, FA, RAW


def main():
    draws, meta = all_draws()
    strata = prior_variants(draws)["D5_union_all"]
    v, abst_map = abstention_lookup()
    say(f"abstention classifier: validation n={v['n']} kappa={v['kappa']:.3f} -> using {v['decision']}")
    J["abstention_validation"] = {k: v[k] for k in ("n", "kappa", "agreement", "decision")}
    oracle = {}
    for l in open(RES / "refsys_oracle_F.jsonl"):
        r = json.loads(l)
        oracle[r["id"]] = float(bool(r["correct"]))
    res = {}
    for bench, label in (("locomo", "LoCoMo categories 1-4"), ("mab_ruler", "MemoryAgentBench RULER-QA1"),
                         ("mab_ruler_qa2", "MemoryAgentBench RULER-QA2 (independent replication, METHOD §10.5; not in the Holm family)")):
        rows = load_protocols(bench)
        if not rows:
            say(f"(no protocol files for {bench})"); continue
        res[bench] = analyse(bench, label, rows, strata, abst_map, oracle)
    J.update(res)
    ps = [("H1 LoCoMo", res.get("locomo", {}).get("H1", {}).get("p")), ("H1 MAB", res.get("mab_ruler", {}).get("H1", {}).get("p")),
          ("H2 MAB", res.get("mab_ruler", {}).get("H2", {}).get("p"))]
    ps = [(k, p) for k, p in ps if p is not None]
    if ps:
        adj = pcme.holm([p for _, p in ps])
        say("\nHolm-adjusted primary tests: " + "; ".join(f"{k} p={p:.4f} adj={a:.4f}" for (k, p), a in zip(ps, adj)))
        J["holm"] = {k: dict(p=p, adj=float(a)) for (k, p), a in zip(ps, adj)}
    if "locomo" in res and "mab_ruler" in res:
        say(f"H2 LoCoMo non-inferiority: delta tau lower bound {res['locomo']['H2']['ci'][0]:+.3f} -> {'pass' if res['locomo']['H2']['ci'][0] > -0.10 else 'FAIL'}")
    # H7
    rows = load_protocols("locomo")
    if rows:
        systems, u_ids, a_ids, CA, FA, RAW = h7(rows, "LoCoMo category 5", abst_map)
        cprA = np.array(res["locomo"]["cpr"]["A"])
        assert systems == res["locomo"]["systems"]
        ca, fa, raw = CA.mean(1), FA.mean(1), RAW.mean(1)
        Jd = ca - fa
        Wu = pcme.bootstrap_weights(len(u_ids), B, seed=3); Wa = pcme.bootstrap_weights(len(a_ids), B, seed=4)
        caB = np.stack([pcme.acc(CA[s], Wu) for s in range(len(systems))]); faB = np.stack([pcme.acc(FA[s], Wa) for s in range(len(systems))])
        rawB = np.stack([pcme.acc(RAW[s], Wu) for s in range(len(systems))])
        r1 = [pcme.spearman(caB[:, b], cprA) for b in range(B)]; r2 = [pcme.spearman(caB[:, b] - faB[:, b], cprA) for b in range(B)]
        r3 = [pcme.spearman(rawB[:, b], cprA) for b in range(B)]
        say(f"{'system':26s} {'cat5 raw acc':>12s} {'CA':>6s} {'FA':>6s} {'J':>6s} {'CPR_A':>6s}")
        for k in np.argsort(-cprA):
            say(f"{systems[k]:26s} {raw[k]:12.3f} {ca[k]:6.3f} {fa[k]:6.3f} {Jd[k]:6.3f} {cprA[k]:6.3f}")
        say(f"Spearman(CA, CPR_A) {pcme.spearman(ca, cprA):.3f} [{q(r1,.025):.3f},{q(r1,.975):.3f}]  "
            f"Spearman(J, CPR_A) {pcme.spearman(Jd, cprA):.3f} [{q(r2,.025):.3f},{q(r2,.975):.3f}]  "
            f"Spearman(cat5 raw acc, CPR_A) {pcme.spearman(raw, cprA):.3f} [{q(r3,.025):.3f},{q(r3,.975):.3f}]")
        J["H7"] = dict(CA=ca.tolist(), FA=fa.tolist(), J=Jd.tolist(), raw=raw.tolist(), rho_CA=pcme.spearman(ca, cprA), ci_CA=(q(r1, .025), q(r1, .975)),
                       rho_J=pcme.spearman(Jd, cprA), ci_J=(q(r2, .025), q(r2, .975)), rho_raw=pcme.spearman(raw, cprA), ci_raw=(q(r3, .025), q(r3, .975)))
    # H8
    say("\n################ H8 test-retest: v1 (original rescore) vs v2 (re-run with saved contexts), pi_A ################")
    for bench, where in (("locomo", None), ("mab_ruler", "ruler_qa1")):
        rows = load_protocols(bench)
        for s in sorted(rows):
            f = BA / f"rescore_{bench}_{s}.jsonl"
            if not f.exists():
                continue
            v1 = {r["id"]: r for r in map(json.loads, open(f)) if where is None or r.get("sub") == where}
            ids = sorted(set(v1) & set(rows[s]))
            if not ids:
                say(f"  {bench} {s}: no v1 rows"); continue
            a = [bool(v1[i]["correct"]) for i in ids]; b = [bool(rows[s][i]["correct_A"]) for i in ids]
            same = np.mean([v1[i]["pred"] == rows[s][i]["pred_A"] for i in ids])
            n = len(ids); po = np.mean([x == y for x, y in zip(a, b)]); pa, pb = np.mean(a), np.mean(b)
            pe = pa * pb + (1 - pa) * (1 - pb); kap = (po - pe) / (1 - pe) if pe < 1 else float("nan")
            say(f"  {bench:9s} {s:26s} n={n:4d} acc v1 {pa:.3f} v2 {pb:.3f} diff {pb-pa:+.3f} kappa {kap:.3f} identical answers {same:.3f}")
            J.setdefault("H8", {})[f"{bench}/{s}"] = dict(n=n, acc_v1=pa, acc_v2=pb, kappa=kap, identical=float(same))
    (RES / "protocol_analysis.txt").write_text("\n".join(LINES) + "\n")
    (RES / "protocol_analysis.json").write_text(json.dumps(J, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))


if __name__ == "__main__":
    main()
