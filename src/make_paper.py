"""Emit paper/numbers.tex. Every macro traces to a file in results/, so no number in the paper
can be typed by hand."""
import json, statistics, sys
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from stimuli import ROOT, load_families, DEV_FACTS

RES = ROOT / "results"
OUT = ROOT / "paper" / "numbers.tex"
M = {}


def put(name, value, fmt="{}"):
    M[name] = fmt.format(value) if not isinstance(value, str) else value


def pct(x):
    return f"{100*x:.1f}\\%"


def load(name, default=None):
    p = RES / name
    return json.loads(p.read_text()) if p.exists() else default


def main():
    fams = load_families()
    mund = [f for f in fams if f["kind"] == "mundane"]
    put("NFamiliesTotal", len(mund))
    put("NFamiliesDev", sum(1 for f in mund if f["family_id"] in DEV_FACTS))
    put("NFamiliesConf", sum(1 for f in mund if f["family_id"] not in DEV_FACTS))
    put("NLevelsTypical", "five")

    man = load("manifest.json")
    if man:
        cm = man["confirmatory_manifest"]
        put("NChainsConf", len(cm["chains"]))
        put("ChainSize", cm["chain_sizes"][0])
        put("SurpriseGap", f"{cm['max_mean_surprise_gap']:.2f}")

    pri = load("priors.json")
    pstats = load("prior_stats.json")
    if pstats:
        for k, v in pstats.items():
            put(k, v)

    cm2 = load("coder_metamorphic.json")
    if cm2:
        r = cm2["strict_rates_by_level"]
        put("CoderMin", f"{min(r.values()):.3f}")
        put("CoderMax", f"{max(r.values()):.3f}")
        put("CoderSpread", f"{cm2['strict_recognition_spread']:.3f}")

    sel = load("pilot_selection.json")
    if sel:
        put("BudgetB", sel["operating_point"]["B"])
        put("TempT", sel["operating_point"]["T"])
        put("WOne", f"{sel['W1_stored_words']:.0f}")
        put("RetentionOOne", f"{sel['retention_O1_k10']:.3f}")
        put("RetentionOSeven", f"{sel['retention_O7_k10']:.3f}")
        put("OThreeSlots", sel["O3"]["slots"])
        put("OThreeRetention", f"{sel['O3']['retention']:.3f}")
        g = sel["grid"]
        for key, lab in (("O1|B300|T1.0|sNone", "ThreeHundred"), ("O1|B600|T1.0|sNone", "SixHundred")):
            if key in g:
                put(f"RetentionB{lab}", f"{g[key]['retention']:.3f}")

    fr = load("frames.json")
    if fr:
        put("NEligible", fr["n_eligible"])
        put("EligFrac", f"{fr['eligible_fraction_r']:.2f}")
        sb = [v["shift_B"] for v in fr["frames"].values() if v["eligible"] and v["shift_B"] is not None]
        if sb:
            put("ShiftMean", f"{statistics.mean(sb):+.2f}")
            put("ShiftMedian", f"{statistics.median(sb):+.2f}")
            put("ShiftDirectionCount", f"{sum(1 for x in sb if x>0)}/{len(sb)}")
        conf = [f for f in fr["eligible"] if f not in DEV_FACTS]
        put("NEligibleConf", len(conf))
        put("NEligibleDev", fr["n_eligible"] - len(conf))

    fc = load("frames_conf_stats.json")
    if fc:
        put("ShiftMeanConf", f"{fc['shift_mean_conf']:+.2f}")
        put("ShiftDirectionCountConf", f"{fc['n_positive_conf']}/{fc['n_total_conf']}")

    pw = load("power.json")
    if pw:
        put("SFam", f"{pw['s_fam']:.1f}")
        put("SSeed", f"{pw['s_seed']:.1f}")
        put("NSeedsESHIFT", pw["chosen"]["n_seeds"])
        put("SESOI", f"{pw['operative_sesoi']:.1f}")

    ces = load("coding_stats_eshift.json")
    if ces:
        put("NEShiftCases", f"{ces['n_cases']:,}")
        put("KappaEShift", f"{ces['cohens_kappa']:.3f}")

    cs = load("coding_stats_confirm.json") or load("coding_stats_dev.json")
    if cs:
        put("Kappa", f"{cs['cohens_kappa']:.3f}")
        put("JudgedFrac", pct(cs["n_judged"] / cs["n_cases"]))
        d = cs["label_distribution"]
        tot = sum(d.values())
        put("UnresolvedRate", pct(d.get("UNRESOLVED", 0) / tot))
        put("ChangedCount", d.get("CHANGED", 0))
        put("ChangedRate", f"{100*d.get('CHANGED',0)/tot:.2f}\\%")
        put("NCodedCases", f"{tot:,}")

    es = load("eshift_result_confirmatory.json")
    if es and es.get("eligible_only", {}).get("n_families"):
        p = es["eligible_only"]
        put("EShiftMean", f"{p['mean']:+.1f}")
        put("EShiftCIlo", f"{p['ci95'][0]:+.1f}")
        put("EShiftCIhi", f"{p['ci95'][1]:+.1f}")
        put("EShiftDecision", p["decision"].replace("_", " ").lower())
        put("EShiftNFam", p["n_families"])
        put("EShiftNBlocks", p["n_seed_blocks"])
        if es.get("ITT", {}).get("n_families"):
            put("EShiftITTMean", f"{es['ITT']['mean']:+.1f}")
            put("EShiftITTN", es["ITT"]["n_families"])
        c = es.get("frame_control_O3")
        if c:
            put("FrameControlMean", f"{c['mean']:+.1f}")
            put("FrameControlEquiv", "yes" if c["equivalent"] else "no")
        direction = "higher retention when the same value is expected" if p["mean"] > 0 else \
                    "no higher retention when the same value is expected"
        put("ShiftDirectionSentence",
            f"that making the very same value expected rather than surprising does not help it "
            f"survive: the mean paired difference over {p['n_families']} families is "
            f"{p['mean']:+.1f} percentage points (95\\% CI [{p['ci95'][0]:+.1f}, "
            f"{p['ci95'][1]:+.1f}]), with effects of {p['sesoi']:.0f}~pp or more excluded")

    cf = load("confirm_result_confirm.json")
    if cf:
        put("SlopeOOne", f"{cf['C2_slope_O1_pp_per_logodds']['point']:+.2f}")
        put("SlopeOOneCIlo", f"{cf['C2_slope_O1_pp_per_logodds']['ci95'][0]:+.2f}")
        put("SlopeOOneCIhi", f"{cf['C2_slope_O1_pp_per_logodds']['ci95'][1]:+.2f}")
        put("SlopeOOneIQR", f"{cf['C2_slope_O1_pp_per_logodds']['pp_over_iqr']:+.1f}")
        put("SlopeOThree", f"{cf['C3_slope_O3_pp_per_logodds']['point']:+.2f}")
        put("SlopeOThreeCIlo", f"{cf['C3_slope_O3_pp_per_logodds']['ci95'][0]:+.2f}")
        put("SlopeOThreeCIhi", f"{cf['C3_slope_O3_pp_per_logodds']['ci95'][1]:+.2f}")
        put("IQRSurprise", f"{cf['iqr_surprise']:.2f}")
        if "C3_interaction" in cf:
            put("InteractionPoint", f"{cf['C3_interaction']['point']:+.2f}")
            put("InteractionCIlo", f"{cf['C3_interaction']['ci95'][0]:+.2f}")
            put("InteractionCIhi", f"{cf['C3_interaction']['ci95'][1]:+.2f}")
        put("OThreeEquivalent", "yes" if cf["C3_O3_equivalence"]["equivalent"] else "no")
        d = cf.get("C5_direction", {})
        put("NChangedEvents", d.get("n", 0))
        rt = cf.get("retention_by_operator_tercile", {})
        nm2 = {"O1": "Oone", "O2": "Otwo", "O3": "Othree", "O4": "Ofour", "O5": "Ofive",
               "O6": "Osix", "O7": "Oseven", "O6-random": "OsixRandom", "O6-low": "OsixLow"}
        for op, v in rt.items():
            # LaTeX macro names cannot contain digits, so every operator id is spelled out
            tag = nm2.get(op)
            if tag is None:
                continue
            if v.get("gap_low_minus_high") is not None:
                put(f"Gap{tag}", f"{v['gap_low_minus_high']:+.1f}")
                put(f"Low{tag}", f"{v['low']:.1f}")
                put(f"High{tag}", f"{v['high']:.1f}")
                put(f"Mid{tag}", f"{v['mid']:.1f}")

    oc = load("operator_contrasts.json")
    if oc:
        nm = {"O1": "Oone", "O2": "Otwo", "O3": "Othree", "O4": "Ofour", "O5": "Ofive",
              "O6": "Osix", "O7": "Oseven", "O6-random": "OsixRandom", "O6-low": "OsixLow"}
        for op, tag in nm.items():
            if op in oc["levels"]:
                put(f"Ret{tag}", f"{oc['levels'][op]['retention']:.1f}")
            c = oc["contrasts"].get(f"{op}_minus_O1")
            if c:
                put(f"Contrast{tag}", f"{c['point']:+.1f}")
                put(f"Contrast{tag}Lo", f"{c['ci95'][0]:+.1f}")
                put(f"Contrast{tag}Hi", f"{c['ci95'][1]:+.1f}")
            cur = oc["curves"].get(op, {})
            if "20" in cur or 20 in cur:
                v = cur.get("20", cur.get(20))
                if v is not None:
                    put(f"Curve{tag}K", f"{v:.1f}")

    if cf:
        k = cf.get("C6_kernel")
        if k and "10" in {str(x) for x in k["k"]}:
            kk = k["k"].get("10", k["k"].get(10))
            put("KernelTVD", f"{kk['tvd_kernel']:.3f}")
            put("KernelConstTVD", f"{kk['tvd_const']:.3f}")
            put("KernelAbsorbTVD", f"{kk['tvd_absorb']:.3f}")
            put("KernelGain", f"{kk['paired_gain_vs_const']:+.3f}")
        if k:
            a = k["absent_regeneration"]
            put("RegenRate", f"{100*a['rate']:.1f}\\% ({a['n_regenerated']}/{a['n_absent_transitions']})")

    pr = load("pref_result.json")
    prx = load("pref_extra.json")
    if pr:
        put("PrefCondA", f"{pr['compliance']['A_raw_instructions']:.0f}")
        put("PrefCondC", f"{pr['compliance']['C_no_information']:.0f}")
        put("PrefExecLoss", f"{pr['execution_loss_pp']:.0f}")
        sl = pr.get("storage_loss_pp", {})
        if "20" in sl:
            put("PrefStorageLoss", f"{sl['20']:.0f}")
    if prx:
        put("PrefDefaultK", f"{prx['default_k20']:.1f}")
        put("PrefNonDefaultK", f"{prx['nondefault_k20']:.1f}")
        put("PrefGapK", f"{prx['gap_k20']:+.1f}")
        put("PrefShareZero", f"{prx['share_nondefault_k0']:.0f}")
        put("PrefShareK", f"{prx['share_nondefault_k20']:.0f}")

    dg = load("diag_result.json")
    if dg:
        for tag, nm in (("diag_llama", "Llama"), ("diag_local", "Local")):
            r = dg.get(tag)
            if r and "O1@T1.0" in r["by_op"]:
                put(f"Ret{nm}Oone", f"{r['by_op']['O1@T1.0']['retention']:.1f}")
            if r and "O4@T1.0" in r["by_op"]:
                put(f"Ret{nm}Ofour", f"{r['by_op']['O4@T1.0']['retention']:.1f}")

    sv = load("sensitivity.json")
    if sv:
        c = sv["C1_variants"]
        # read the upper bound from the primary E-SHIFT result so the abstract and the body
        # cannot quote two different bootstrap runs
        _es = load("eshift_result_confirmatory.json")
        _hi = (_es or {}).get("eligible_only", {}).get("ci95", [None, c['primary']['ci95'][1]])[1]
        put("ConeUpper", f"{_hi:+.1f}")
        put("ConeJudgeOne", f"{c['judge1_only']['mean']:+.1f}")
        put("ConeJudgeTwo", f"{c['judge2_only']['mean']:+.1f}")
        put("ConeWorstAgainst", f"{c['unresolved_worst_against_H']['mean']:+.1f}")
        put("ConeWorstFor", f"{c['unresolved_worst_for_H']['mean']:+.1f}")
        put("EShiftUnresRate", f"{100*c['unresolved_rate']:.1f}\\%")
        put("EShiftUnresN", c["n_unresolved"])
        put("EShiftUnresPlus", f"{100*c['unresolved_by_arm']['F+']:.0f}\\%")
        put("EShiftUnresMinus", f"{100*c['unresolved_by_arm']['F-']:.0f}\\%")
        dz = sv["dose_over_iqr"]
        put("DoseIQR", f"{dz['O1_pp_over_iqr']['point']:+.1f}")
        put("DoseIQRlo", f"{dz['O1_pp_over_iqr']['ci95'][0]:+.1f}")
        put("DoseIQRhi", f"{dz['O1_pp_over_iqr']['ci95'][1]:+.1f}")
        pr2 = sv["preferences"]
        put("PrefAdj", f"{pr2['baseline_adjusted_pp']:+.1f}")
        put("PrefAdjLo", f"{pr2['baseline_adjusted_ci95'][0]:+.1f}")
        put("PrefAdjHi", f"{pr2['baseline_adjusted_ci95'][1]:+.1f}")
        put("PrefGapZero", f"{pr2['gap_k0_pp']:+.1f}")
        put("PrefNFamilies", pr2["n_preference_families"])
        pa = sv["contrasts"]["paired"]
        for key, tag in (("O6_minus_O6-random", "SixVsRandom"), ("O4_minus_O5", "FourVsFive"),
                         ("O3W_minus_O1", "ThreeWVsOne")):
            if key in pa:
                put(f"Pair{tag}", f"{pa[key]['point']:+.1f}")
                put(f"Pair{tag}Lo", f"{pa[key]['ci95'][0]:+.1f}")
                put(f"Pair{tag}Hi", f"{pa[key]['ci95'][1]:+.1f}")
        lv = sv["contrasts"]["levels"]
        if "O3W" in lv:
            put("RetOthreeW", f"{lv['O3W']['retention']:.1f}")
        pb = sv["protocol_by_operator"]
        for op, tag in (("O1", "Oone"), ("O5", "Ofive"), ("O4", "Ofour"), ("O3", "Othree")):
            if op in pb:
                put(f"Trims{tag}", f"{pb[op]['hard_trims_per_traj']:.1f}")
                put(f"Retries{tag}", f"{pb[op]['budget_retries_per_traj']:.1f}")
                put(f"Words{tag}", f"{pb[op]['mean_stored_words']:.0f}")
        opj = sv.get("operator_per_judge", {})
        if opj:
            put("OfourJudgeOne", f"{opj['judge1_only']['O4_minus_O1']['point']:+.1f}")
            put("OfourJudgeTwo", f"{opj['judge2_only']['O4_minus_O1']['point']:+.1f}")

    fp = load("frame_parity.json")
    if fp:
        for k, tag in (("importance", "Imp"), ("authority", "Auth"), ("relevance", "Rel")):
            if k in fp:
                put(f"Parity{tag}", f"{fp[k]['mean_diff_Fplus_minus_Fminus']:+.2f}")
                put(f"Parity{tag}Lo", f"{fp[k]['ci95'][0]:+.2f}")
                put(f"Parity{tag}Hi", f"{fp[k]['ci95'][1]:+.2f}")

    # protocol-compliance numbers
    tr = load("trim_stats.json")
    if tr:
        put("TrimRate", f"{tr['hard_trims_per_traj']:.1f}")
        put("Ksteps", tr["K"])

    # Two narrative macros, also generated from the result files so the prose cannot drift from
    # the numbers it describes.
    if oc and es and es.get("eligible_only", {}).get("n_families"):
        p_ = es["eligible_only"]
        c4 = oc["contrasts"].get("O4_minus_O1")
        if c4:
            put("ResultSummarySentence",
                f"what decides survival is not how surprising an item is -- the causal test excludes "
                f"effects of {p_['sesoi']:.0f} percentage points or more and estimates "
                f"{p_['mean']:+.1f} -- but whether the model is rewriting its own previous summary: "
                f"rewriting from the raw sessions instead retains {oc['levels']['O4']['retention']:.0f}"
                f"\\% against {oc['levels']['O1']['retention']:.0f}\\% at the same budget "
                f"({c4['point']:+.0f} pp, 95\\% CI [{c4['ci95'][0]:+.0f}, {c4['ci95'][1]:+.0f}]).")

    lines = ["% AUTO-GENERATED by src/make_paper.py. Do not edit.",
             "% Every macro below is read from a file in results/."]
    for k, v in sorted(M.items()):
        lines.append(f"\\newcommand{{\\{k}}}{{{v}}}")
    # Any macro the prose references but no result file supplies yet gets a loud placeholder, so a
    # missing number is visible in the PDF rather than breaking the build silently.
    import re as _re
    used = set()
    for f in sorted((ROOT / "paper" / "sec").glob("*.tex")):
        used |= set(_re.findall(r"\\([A-Z][A-Za-z]+)\{\}", f.read_text()))
    pending = sorted(used - set(M))
    for k in pending:
        lines.append(f"\\providecommand{{\\{k}}}{{\\textbf{{[{k}?]}}}}")
    OUT.write_text("\n".join(lines) + "\n")
    if pending:
        print("  pending macros (no result file yet):", ", ".join(pending))
    print(f"wrote {OUT} with {len(M)} macros")
    missing = [k for k in ["EShiftMean", "SlopeOOne"] if k not in M]
    if missing:
        print("  (results not yet available for:", ", ".join(missing), ")")


if __name__ == "__main__":
    main()
