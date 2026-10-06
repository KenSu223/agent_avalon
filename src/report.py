"""One readable summary of every result file, for writing the paper from."""
import json, statistics, sys
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from stimuli import ROOT
RES = ROOT / "results"


def j(name):
    p = RES / name
    return json.loads(p.read_text()) if p.exists() else None


def main():
    print("=" * 78)
    print("FROZEN PROTOCOL")
    fp = j("FROZEN_PROTOCOL.json")
    if fp:
        print(f"  compactor {fp['compactor']}  B={fp['B']} T={fp['T']} K={fp['K']} "
              f"primary k={fp['primary_endpoint_k']}")
        print(f"  seeds: main {fp.get('n_seeds_main_chains')}  eshift {fp['eshift']['n_seeds']}")
        print(f"  O3 slots {fp['slots']} ({fp['O3_label']})")
        print(f"  adequacy {fp['adequacy']}")
        print(f"  eshift endpoint: {fp['eshift'].get('endpoint')}  SESOI "
              f"{fp['eshift']['operative_sesoi_pp']:.1f} pp  "
              f"n_eligible_conf {fp['eshift'].get('n_eligible_confirmatory')}")

    print("\n" + "=" * 78)
    print("CODING")
    for tag in ("confirm", "eshift", "dev"):
        cs = j(f"coding_stats_{tag}.json")
        if cs:
            print(f"  [{tag}] cases {cs['n_cases']:,}  judged {cs['n_judged']:,} "
                  f"({100*cs['n_judged']/cs['n_cases']:.1f}%)  kappa {cs['cohens_kappa']:.3f}")
            print(f"        labels {cs['label_distribution']}")

    print("\n" + "=" * 78)
    print("C1  E-SHIFT (causal)")
    es = j("eshift_result_confirmatory.json")
    if es:
        for pop in ("eligible_only", "ITT"):
            p = es.get(pop, {})
            if p.get("n_families"):
                print(f"  [{pop}] n_fam {p['n_families']} blocks {p['n_seed_blocks']}  "
                      f"mean {p['mean']:+.2f} pp  CI95 [{p['ci95'][0]:+.2f},{p['ci95'][1]:+.2f}]  "
                      f"CI90 [{p['ci90'][0]:+.2f},{p['ci90'][1]:+.2f}]  -> {p['decision']}")
        sb = es.get("secondary_binary_k10")
        if sb:
            print(f"  [secondary binary@k10] mean {sb['mean']:+.2f} pp "
                  f"CI95 [{sb['ci95'][0]:+.2f},{sb['ci95'][1]:+.2f}]")
        c = es.get("frame_control_O3")
        if c:
            print(f"  [O3 frame control] mean {c['mean']:+.2f} pp  equivalent to 0 within "
                  f"+/-5pp: {c['equivalent']}  flag {c['flag_residual_interference']}")
        if es.get("eligible_only", {}).get("per_family_mean"):
            pm = es["eligible_only"]["per_family_mean"]
            print("  per family:", {k: round(v, 1) for k, v in sorted(pm.items())})

    print("\n" + "=" * 78)
    print("C2/C3/C4  dose-response and operator lattice")
    cf = j("confirm_result_confirm.json")
    if cf:
        print(f"  rows {cf['n_rows']:,}  k10 {cf['n_k10']:,}  IQR surprise {cf['iqr_surprise']:.2f}"
              f"  unresolved {100*cf['unresolved_rate']:.1f}%")
        a = cf["C2_slope_O1_pp_per_logodds"]
        print(f"  C2 O1 slope {a['point']:+.2f} pp/log-odds  CI95 [{a['ci95'][0]:+.2f},"
              f"{a['ci95'][1]:+.2f}]  = {a['pp_over_iqr']:+.1f} pp over the IQR")
        b = cf["C3_slope_O3_pp_per_logodds"]
        print(f"  C3 O3 slope {b['point']:+.2f} pp/log-odds  CI95 [{b['ci95'][0]:+.2f},"
              f"{b['ci95'][1]:+.2f}]")
        if "C3_interaction" in cf:
            i = cf["C3_interaction"]
            print(f"  C3 interaction {i['key']}: {i['point']:+.2f} "
                  f"CI95 [{i['ci95'][0]:+.2f},{i['ci95'][1]:+.2f}]")
        e = cf["C3_O3_equivalence"]
        print(f"  C3 O3 equivalence (+/-{e['margin']} pp over IQR): CI90 "
              f"[{e['ci90'][0]:+.2f},{e['ci90'][1]:+.2f}] -> equivalent {e['equivalent']}")
        print("\n  retention by operator x surprise tercile at k=10:")
        print(f"    {'op':<11}{'low':>8}{'mid':>8}{'high':>8}{'gap':>9}{'n':>7}")
        for op, v in cf["retention_by_operator_tercile"].items():
            print(f"    {op:<11}{v['low'] or 0:>8.1f}{v['mid'] or 0:>8.1f}{v['high'] or 0:>8.1f}"
                  f"{v['gap_low_minus_high'] or 0:>+9.1f}{v['n']:>7}")
        print("\n  C4 slope per operator (pp per log-odds of surprise):")
        for op, v in cf["C4_slopes_by_operator"].items():
            ci = v["ci95"]
            print(f"    {op:<11}{v['point']:+8.2f}  CI95 [{ci[0]:+.2f},{ci[1]:+.2f}]"
                  f"   {v['pp_over_iqr']:+6.1f} pp over IQR" if ci else f"    {op}: {v['point']:+.2f}")
        d = cf.get("C5_direction", {})
        print(f"\n  C5 replacement events n={d.get('n',0)}", end="")
        if d.get("n"):
            print(f"  mean delta {d['mean_delta']:+.3f}  CI95 {d['ci95']}  perm p {d['perm_p']}"
                  f"  frac prior-ward {d['frac_prior_ward']:.2f}")
        else:
            print("  -> too few to test (reported as a scoped null)")
        k = cf.get("C6_kernel")
        if k:
            print(f"\n  C6 kernel, held-out TVD:")
            for kk, v in k["k"].items():
                print(f"    k={kk}: kernel {v['tvd_kernel']:.3f}  const {v['tvd_const']:.3f}  "
                      f"absorb {v['tvd_absorb']:.3f}   gain vs const {v['paired_gain_vs_const']:+.3f}")
            a = k["absent_regeneration"]
            print(f"    regeneration out of ABSENT: {a['n_regenerated']}/{a['n_absent_transitions']}"
                  f" = {a['rate']}")
        m = cf.get("C7_mitigation", {})
        if m:
            print("\n  C7 mitigation (high-surprise retention at k=10):")
            for op, v in m.items():
                print(f"    {op:<11} high {v['high_surprise_retention']:>6.1f}  "
                      f"low {v['low_surprise_retention'] or 0:>6.1f}  n={v['n_high']}")

    print("\n" + "=" * 78)
    print("AUX")
    for n in ("prior_stats.json", "trim_stats.json", "coder_metamorphic.json", "power.json"):
        d = j(n)
        if d:
            keep = {k: v for k, v in d.items() if k not in ("failures", "power_table", "per_level")}
            print(f"  {n}: {json.dumps(keep, default=str)[:400]}")


if __name__ == "__main__":
    main()
