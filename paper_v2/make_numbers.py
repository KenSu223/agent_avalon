"""Generate paper_v2/numbers.tex from committed result files, so that every number in the paper is traceable
(PLAN rigor standard 3). Run: python paper_v2/make_numbers.py   (system python; numpy only)"""
import collections, json
from pathlib import Path
import numpy as np
R = Path(__file__).resolve().parents[1]
M = R / "method/results"
F = R / "framework_study/results"
out = {}


def put(name, value, fmt="{:.2f}"):
    out[name] = fmt.format(value) if isinstance(value, (int, float, np.floating)) and not isinstance(value, bool) else str(value)


def pct(x):
    return f"{100 * x:.0f}\\%"


# ---------------------------------------------------------------- audit: expected guess rate (Qwen3-235B, 6 forced draws)
meta = {}
for l in open(R / "benchmark_audit/results/closed_book_qwen3-235b-a22b-2507.jsonl"):
    r = json.loads(l)
    meta[r["id"]] = (r["bench"], r["sub"], r.get("category"))
draws = collections.defaultdict(list)
for l in open(M / "prior_draws_qwen3-235b-a22b-2507.jsonl"):
    r = json.loads(l)
    if r.get("correct") is not None:
        draws[r["id"]].append(float(r["correct"]))
for l in open(R / "benchmark_audit/results/closed_book_qwen3-235b-a22b-2507.jsonl"):
    r = json.loads(l)
    if r["proto"] == "forced" and r.get("correct") is not None and r["id"] in draws:
        draws[r["id"]].append(float(bool(r["correct"])))
groups = {"Locomo": lambda b, s, c: b == "LoCoMo" and c != 5, "Lme": lambda b, s, c: b == "LongMemEval" and not s.endswith("_abs"),
          "QaOne": lambda b, s, c: s == "ruler_qa1", "QaTwo": lambda b, s, c: s == "ruler_qa2", "Eventqa": lambda b, s, c: s == "eventqa",
          "FcSh": lambda b, s, c: s == "factconsolidation_sh", "FcMh": lambda b, s, c: s == "factconsolidation_mh"}
for g, fn in groups.items():
    ids = [i for i in draws if i in meta and fn(*meta[i])]
    put(f"g{g}", np.mean([np.mean(draws[i]) for i in ids]))
    put(f"g{g}Pct", pct(np.mean([np.mean(draws[i]) for i in ids])))
# original framework study (44 items): retention vs accuracy on congruent items (framework_study/results/inflation.txt)
for line in open(F / "inflation.txt"):
    parts = line.split()
    if parts and parts[0] == "aider":
        put("aiderRet", pct(float(parts[1]))); put("aiderCongAcc", pct(float(parts[2])))
pt = json.load(open(M / "property_tests.json"))
rates = pt["P6_rates"]
for g, key in (("Locomo", "LoCoMo"), ("Lme", "LongMemEval"), ("QaOne", "MAB:ruler_qa1"), ("QaTwo", "MAB:ruler_qa2")):
    put(f"ever{g}", pct(rates[key]["D5_union_all"]))
    put(f"single{g}", pct(rates[key]["D1_qwen_T0"]))

# ---------------------------------------------------------------- property tests (adopted variant a; calibration from v1.0 run)
pa = json.load(open(M / "property_tests_a.json"))
for g, key in (("Lme", "LongMemEval"), ("Locomo", "LoCoMo"), ("Mab", "MemoryAgentBench")):
    put(f"floorMa{g}", pa["P1"][key]["ma"]["point"], "{:+.3f}")
put("leakMax", max(v["cpr_ub95"] for v in pa["P1"].values()), "{:.3f}")
put("cprOracleLocomo", pa["P2"]["LoCoMo"]["cpr"]); put("cprOracleMab", pa["P2"]["MemoryAgentBench"]["cpr"])
put("aTwoLocomo", pa["P3"]["LoCoMo_clean-absent"]["D"], "{:+.3f}"); put("aTwoMab", pa["P3"]["MemoryAgentBench_clean-absent"]["D"], "{:+.3f}")
p10 = json.load(open(M / "property_tests.json"))
put("floorMaLmeVten", p10["P1"]["LongMemEval"]["ma"]["point"], "{:+.3f}"); put("floorMaLocomoVten", p10["P1"]["LoCoMo"]["ma"]["point"], "{:+.3f}")
put("noncompLme", pct(p10["P1"]["LongMemEval"]["noncompliance"])); put("noncompLocomo", pct(p10["P1"]["LoCoMo"]["noncompliance"]))
put("calibMaeAcc", p10["P4"]["point"]["mae_acc"], "{:.3f}"); put("calibMaePcs", p10["P4"]["point"]["mae_pcs"], "{:.3f}")

# ---------------------------------------------------------------- protocol comparison (step 2)
pr = json.load(open(M / "protocol_analysis.json"))
for g, key in (("Locomo", "locomo"), ("QaOne", "mab_ruler"), ("QaTwo", "mab_ruler_qa2")):
    h = pr[key]["H1"]
    put(f"hOne{g}", h["rho"]); put(f"hOne{g}Lo", h["ci"][0]); put(f"hOne{g}Hi", h["ci"][1])
    put(f"dtau{g}", pr[key]["H2"]["dtau"], "{:+.2f}"); put(f"dtau{g}Lo", pr[key]["H2"]["ci"][0], "{:+.2f}"); put(f"dtau{g}Hi", pr[key]["H2"]["ci"][1], "{:+.2f}")
put("absKappa", pr["abstention_validation"]["kappa"])
h7 = pr["H7"]
put("rhoCaCpr", h7["rho_CA"], "{:+.2f}"); put("rhoJCpr", h7["rho_J"], "{:+.2f}"); put("rhoRawCatFive", h7["rho_raw"], "{:+.2f}")
q1 = pr["mab_ruler"]; s1 = q1["systems"]
ai = s1.index("aider")
put("aiderAccA", q1["acc"]["A"][ai]); put("aiderAccF", q1["acc"]["F"][ai])
put("nPoorQaOne", sum(1 for c in q1["cpr"]["A"] if c <= 0.05), "{}"); put("nSysQaOne", len(s1), "{}")
put("absRangeLo", pct(min(q1["abst"]["A"]))); put("absRangeHi", pct(max(q1["abst"]["A"])))
put("confirmedRev", len(pr["locomo"]["reversals_A"]["confirmed"]) + len(q1["reversals_A"]["confirmed"]), "{}")

# ---------------------------------------------------------------- robustness (threshold-triggered compaction)
rb = json.load(open(M / "robustness_analysis.json"))
thr = [v["cpr_thr"] for v in rb["mab_ruler"]["R1"].values()]
gain = [v["cpr_thr"] - v["cpr_chunk"] for v in rb["mab_ruler"]["R1"].values()]
put("thrCprMin", min(thr)); put("thrCprMax", max(thr)); put("thrGainMin", min(gain), "{:+.2f}"); put("thrGainMax", max(gain), "{:+.2f}")
put("inflPairs", sum(rb[b]["R2"].count(True) for b in ("mab_ruler", "mab_ruler_qa2")), "{}")
put("fullHistCpr", rb["R4"]["cpr_full"]); put("bestMemCpr", rb["R4"]["cpr_best"])

# ---------------------------------------------------------------- dataset (step 3)
gt = json.load(open(F / "gates_v2.json"))
put("nCand", gt["n_candidates"], "{}"); put("nFinal", gt["n_final"], "{}")
for t, v in gt["final_by_type"].items():
    put("nFinal" + {"rule": "Rule", "procedure": "Proc", "preference": "Pref", "update": "Upd", "neutral": "Neut"}[t], v, "{}")
nn = gt["final_strong_prior_by_model"]
for k, name in (("qwen", "Qwen"), ("llama", "Llama"), ("gptoss", "Gptoss"), ("deepseek", "Deepseek")):
    put("strong" + name, nn[k], "{}")
put("nFinalNonNeutral", gt["n_final"] - gt["final_by_type"]["neutral"], "{}")

# ---------------------------------------------------------------- framework study, step 4
s4 = json.load(open(F / "step4_analysis.json"))
for fam, name in (("s4qwen", "Qwen"), ("s4llama", "Llama")):
    sy = s4[fam]["systems"]
    rw = [sy[s]["dK"] for s in ("codex", "aider", "anthropic_api")]
    put(f"dKrw{name}Lo", min(rw)); put(f"dKrw{name}Hi", max(rw))
    put(f"dF{name}Max", max(abs(v["dF"]) for v in sy.values()), "{:.3f}")
    put(f"dR{name}MaxAbs", max(abs(sy[s]["dR"]) for s in ("codex", "aider", "anthropic_api", "neutral_roll")), "{:.3f}")
    put(f"upd{name}", s4[fam]["P4_6"]["diff"], "{:+.2f}")
    put(f"pcsMae{name}", s4[fam]["P4_7"]["mae_pcs"], "{:.3f}"); put(f"accMae{name}", s4[fam]["P4_7"]["mae_acc"], "{:.2f}")
    put(f"neutralDk{name}", s4[fam]["P4_5"]["dK"], "{:+.2f}")
    put(f"dropNeutralRoll{name}", sy["neutral_roll"]["drop"])
put("rhoRetFam", s4["P4_4"]["rho"])
put("liDrLlama", s4["s4llama"]["systems"]["llamaindex_facts"]["dR"], "{:+.3f}")

lines = ["% Generated by paper_v2/make_numbers.py from committed result files. Do not edit by hand."]
for k in sorted(out):
    assert k.isalpha(), k
    lines.append(f"\\newcommand{{\\{k}}}{{{out[k]}}}")
(Path(__file__).parent / "numbers.tex").write_text("\n".join(lines) + "\n")
print(len(out), "numbers written")
