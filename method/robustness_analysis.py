"""METHOD.md §10.6: threshold-triggered compaction robustness check (R1-R4), written before the runs.

Inputs : results/protocols_<bench>_<system>.jsonl for the 7 compaction systems (per-chunk = main design) and their
         '<system>@thr64k' counterparts on mab_ruler (QA1) and mab_ruler_qa2; 'full_history' + the 12 main systems on
         locomo; abstention decision (results/abstention_validation.json); D5 strata; g' (eval-prompt draws).
Output : results/robustness_analysis.txt / .json
"""
import json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import pcme
from property_tests import all_draws, prior_variants, RES, QW, q
from protocol_analysis import load_protocols, abstention_lookup, g_from, boot_p

COMP = ["codex", "openhands", "aider", "gemini_cli", "anthropic_api", "langchain_summary", "neutral_roll"]
B = 2000
LINES, J = [], {}


def say(*a):
    s = " ".join(str(x) for x in a); print(s); LINES.append(s)


def matrices(bench, systems, rows, strata, abst_map):
    ids = sorted(set.intersection(*[{i for i, r in rows[s].items() if r["answerable"]} for s in systems]) & set(strata.resistant))
    def ab(s, i):
        v = abst_map.get((bench, s, i, "A")) if abst_map else None
        return float(bool(v if v is not None else rows[s][i]["abst_A_regex"]))
    Y = {p: np.array([[float(bool(rows[s][i].get(f"correct_{p}"))) for i in ids] for s in systems]) for p in ("A", "F", "FR")}
    AB = np.array([[ab(s, i) for i in ids] for s in systems])
    R = np.array([strata.resistant[i] for i in ids])
    return ids, Y, AB, R


def main():
    strata = prior_variants(all_draws()[0])["D5_union_all"]
    v, abst_map = abstention_lookup()
    say(f"abstention classifier: {v['decision']} (kappa {v['kappa']:.3f})")
    for bench in ("mab_ruler", "mab_ruler_qa2"):
        main_rows, thr_rows = load_protocols(bench), load_protocols(bench, robustness=True)
        pairs = [s for s in COMP if s in main_rows and f"{s}@thr64k" in thr_rows]
        if not pairs:
            say(f"\n{bench}: no paired runs yet"); continue
        rows = {**{s: main_rows[s] for s in pairs}, **{f"{s}@thr64k": thr_rows[f"{s}@thr64k"] for s in pairs}}
        systems = pairs + [f"{s}@thr64k" for s in pairs]
        ids, Y, AB, R = matrices(bench, systems, rows, strata, abst_map)
        W = pcme.bootstrap_weights(len(ids), B)
        say(f"\n######## {bench}: {len(pairs)} compaction systems x 2 triggers, {len(ids)} items, {int(R.sum())} prior-resistant")
        say(f"{'system':20s} {'CPR chunk':>9s} {'CPR thr':>8s} {'diff [95% CI]':>24s} {'acc A chunk':>11s} {'acc A thr':>9s} {'n compactions thr':>17s}")
        out = {}
        k = len(pairs)
        for j, s in enumerate(pairs):
            c0 = pcme.cpr(Y["A"][j], R); c1 = pcme.cpr(Y["A"][k + j], R)
            d = pcme.cpr(Y["A"][k + j], R, W) - pcme.cpr(Y["A"][j], R, W)
            v2 = HERE.parent / "benchmark_audit/results_v2" / (f"rescore_mab_ruler_{s}@thr64k_qa2.jsonl" if bench == "mab_ruler_qa2" else f"rescore_mab_ruler_{s}@thr64k.jsonl")
            ncomp = json.loads(open(v2).readline()).get("n_compactions") if v2.exists() else None
            say(f"{s:20s} {c0:9.3f} {c1:8.3f} {c1 - c0:+8.3f} [{q(d,.025):+.3f},{q(d,.975):+.3f}] {Y['A'][j].mean():11.3f} {Y['A'][k + j].mean():9.3f} {str(ncomp):>17s}")
            out[s] = dict(cpr_chunk=float(c0), cpr_thr=float(c1), diff_ci=(q(d, .025), q(d, .975)))
        r1 = sum(o["cpr_thr"] - o["cpr_chunk"] >= 0 for o in out.values())
        say(f"R1: CPR(thr) >= CPR(chunk) for {r1}/{len(out)} systems -> {'holds' if r1 == len(out) else 'does not hold'}")
        # R2
        say("R2: prior inflation among threshold systems with CPR_A < 0.5: acc_A(answerable) - acc_A(resistant)")
        r2 = []
        for j, s in enumerate(pairs):
            y = Y["A"][k + j]
            if pcme.cpr(y, R) >= 0.5:
                say(f"   {s}@thr64k CPR >= 0.5, not tested"); continue
            gap = (W * y * ~R).sum(1) / (W * ~R).sum(1) - (W * y * R).sum(1) / (W * R).sum(1)
            pt = y[~R].mean() - y[R].mean()
            ok = q(gap, .025) > 0
            r2.append(ok)
            say(f"   {s}@thr64k gap {pt:+.3f} [{q(gap,.025):+.3f},{q(gap,.975):+.3f}] -> {'inflation present' if ok else 'not shown'}")
        say(f"R2 -> {'holds' if r2 and all(r2) else ('not testable' if not r2 else 'does not hold for all')}")
        # R3
        accA, accF = Y["A"].mean(1), Y["F"].mean(1)
        abA = AB.mean(1)
        rho = pcme.spearman(accF - accA, abA)
        rB = [pcme.spearman(pcme.acc(Y["F"], W[b]) - pcme.acc(Y["A"], W[b]), pcme.acc(AB, W[b])) for b in range(B)]
        say(f"R3: Spearman(acc_F - acc_A, abstention_A) over {len(systems)} configurations = {rho:.3f} [{q(rB,.025):.3f},{q(rB,.975):.3f}]"
            f" -> {'holds' if q(rB,.025) > 0 else 'does not hold'}")
        J[bench] = dict(R1=out, R1_holds=r1 == len(out), R2=r2, R3=dict(rho=rho, ci=(q(rB, .025), q(rB, .975))))
    # R4
    main_rows, thr_rows = load_protocols("locomo"), load_protocols("locomo", robustness=True)
    if "full_history" in thr_rows and main_rows:
        rows = {**main_rows, "full_history": thr_rows["full_history"]}
        systems = sorted(main_rows) + ["full_history"]
        ids, Y, AB, R = matrices("locomo", systems, rows, strata, abst_map)
        gF = g_from(RES / f"prior_draws_{QW}_evalprompt.jsonl", ids)
        W = pcme.bootstrap_weights(len(ids), B)
        cpr = pcme.cpr(Y["A"], R)
        fh = len(systems) - 1
        best = int(np.argmax(cpr[:-1]))
        d = pcme.cpr(Y["A"][fh], R, W) - pcme.cpr(Y["A"][best], R, W)
        oracle = {}
        for l in open(RES / "refsys_oracle_F.jsonl"):
            r = json.loads(l); oracle[r["id"]] = float(bool(r["correct"]))
        o_ids = [i for i in ids if i in oracle and strata.resistant[i]]
        cpr_o = np.mean([oracle[i] for i in o_ids])
        say(f"\n######## LoCoMo full history (no compaction reaches 64k tokens): acc_A {Y['A'][fh].mean():.3f}  CPR_A {cpr[fh]:.3f}  "
            f"CPR_F {pcme.cpr(Y['F'][fh], R):.3f}  PCS_F {pcme.pcs(Y['F'][fh], gF):.3f}  oracle-normalised CPR_F {pcme.cpr(Y['F'][fh], R)/cpr_o:.3f}")
        say(f"R4: CPR_A(full history) - CPR_A(best memory system = {systems[best]}, {cpr[best]:.3f}) = {cpr[fh] - cpr[best]:+.3f} "
            f"[{q(d,.025):+.3f},{q(d,.975):+.3f}] -> {'holds' if cpr[fh] >= cpr[best] else 'does not hold'}")
        J["R4"] = dict(cpr_full=float(cpr[fh]), best=systems[best], cpr_best=float(cpr[best]), diff_ci=(q(d, .025), q(d, .975)))
    (RES / "robustness_analysis.txt").write_text("\n".join(LINES) + "\n")
    (RES / "robustness_analysis.json").write_text(json.dumps(J, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))


if __name__ == "__main__":
    main()
