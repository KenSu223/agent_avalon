"""Apply the pre-registered gates (STEP3_DESIGN.md §3) to the V1/V2 measurements and select the final item set.

  V1: Qwen3-235B P(C) >= 0.8 (rule, procedure, preference, update); 0.3 <= P(A) <= 0.7 (neutral)
  V2: Qwen3-235B 4/4 correct AND Llama-3.3-70B >= 3/4 AND gpt-oss-120b >= 3/4
  final = G0 (already enforced by build_items_v2.py) and V1 and V2; every passing item is kept (no downstream selection).
Outputs: framework_study/stimuli/items_v2_final.jsonl, framework_study/results/gates_v2.json (+ printed summary)
"""
import json, collections, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "framework_study/results"
ST = ROOT / "framework_study/stimuli"
TAGS = {"qwen": "qwen3-235b-a22b-2507", "llama": "llama3-3-70b-instruct", "gptoss": "gpt-oss-120b-1:0", "deepseek": "deepseek-v3-2"}


def main():
    items = [json.loads(l) for l in open(ST / "items_v2.jsonl")]
    val = {k: json.load(open(RES / f"validation_v2_{t}.json")) for k, t in TAGS.items()}
    rows, final = [], []
    for x in items:
        iid = x["id"]
        p = {k: val[k]["V1"].get(iid, {}).get("p_congruent") for k in TAGS}
        v2 = {k: (val[k]["V2"][iid]["C_correct"] + val[k]["V2"][iid]["I_correct"]) for k in ("qwen", "llama", "gptoss")}
        reasons = []
        if p["qwen"] is None:
            reasons.append("V1: no parseable answer")
        elif x["type"] == "neutral":
            if not 0.3 <= p["qwen"] <= 0.7:
                reasons.append(f"V1: neutral item has a prior (P(A) = {p['qwen']:.2f})")
        elif p["qwen"] < 0.8:
            reasons.append(f"V1: weak prior (P(C) = {p['qwen']:.2f})")
        if v2["qwen"] < 4:
            reasons.append(f"V2: Qwen {v2['qwen']}/4")
        for k in ("llama", "gptoss"):
            if v2[k] < 3:
                reasons.append(f"V2: {k} {v2[k]}/4")
        ok = not reasons
        rows.append(dict(id=iid, type=x["type"], origin=x["origin"], normative=x["normative"], p_congruent=p, v2_correct=v2,
                         passed=ok, reasons=reasons))
        if ok:
            final.append(dict(x, prior=p, v2_correct=v2))
    with open(ST / "items_v2_final.jsonl", "w") as f:
        for x in final:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    # summary
    out = {"n_candidates": len(items), "n_final": len(final), "items": rows}
    by_type = collections.defaultdict(lambda: collections.Counter())
    for r in rows:
        t = by_type[r["type"]]
        t["candidates"] += 1
        v1fail = any(s.startswith("V1") for s in r["reasons"]); v2fail = any(s.startswith("V2") for s in r["reasons"])
        t["fail_V1"] += v1fail; t["fail_V2"] += v2fail; t["fail_V1_only"] += v1fail and not v2fail
        t["fail_V2_only"] += v2fail and not v1fail; t["final"] += r["passed"]
    out["by_type"] = {k: dict(v) for k, v in by_type.items()}
    strong = {k: sum(1 for r in rows if r["type"] not in ("neutral",) and r["p_congruent"][k] is not None and r["p_congruent"][k] >= 0.8)
              for k in TAGS}
    n_nonneutral = sum(1 for r in rows if r["type"] != "neutral")
    out["v1_strong_prior_by_model"] = {k: dict(n=strong[k], of=n_nonneutral) for k in TAGS}
    fin_nn = [r for r in rows if r["passed"] and r["type"] != "neutral"]
    out["final_strong_prior_by_model"] = {k: sum(1 for r in fin_nn if (r["p_congruent"][k] or 0) >= 0.8) for k in TAGS}
    out["final_by_type"] = dict(collections.Counter(r["type"] for r in rows if r["passed"]))
    out["final_by_origin"] = dict(collections.Counter(r["origin"] for r in rows if r["passed"]))
    out["final_normative"] = sum(r["normative"] for r in rows if r["passed"])
    (RES / "gates_v2.json").write_text(json.dumps(out, indent=1))
    print(f"candidates {len(items)}  final {len(final)}")
    print(f"{'type':11s} {'cand':>5s} {'fail V1':>8s} {'fail V2':>8s} {'final':>6s}")
    for k, v in out["by_type"].items():
        print(f"{k:11s} {v['candidates']:5d} {v['fail_V1']:8d} {v['fail_V2']:8d} {v['final']:6d}")
    print("V1 strong prior (P(C) >= 0.8) among non-neutral candidates by model:", out["v1_strong_prior_by_model"])
    print("among the final non-neutral items, strong prior by model:", out["final_strong_prior_by_model"], f"of {len(fin_nn)}")
    print("final by origin:", out["final_by_origin"], " normative:", out["final_normative"])
    reasons = collections.Counter(s.split(" (")[0].split(":")[0] + ":" + s.split(":")[1].split("(")[0].strip().split(" ")[0] for r in rows for s in r["reasons"])
    print("failure reasons:", dict(reasons))


if __name__ == "__main__":
    main()
