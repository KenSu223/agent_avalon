"""Stimulus validation.

V1  prior strength: with no information, how often does the model pick the schema-congruent answer?
V2  comprehension: right after hearing the item, does the model answer the stated version?
"""
import json, re, sys, random
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "framework_study" / "stimuli"))
from infra.llm import batch_chat, estimate_cost, budget
from build_items import user_turn

ITEMS = [json.loads(l) for l in open(ROOT / "framework_study/stimuli/items.jsonl")]
OUT = ROOT / "framework_study/results"
WORLD = ("You are Atlas, an AI assistant that helps Sam, who works at Veltrix, a software company "
         "in the Harbor Building in the town of Northvale.")


def parse(text, options):
    hits = []
    for o in options:
        pat = r"(?<![\w.])" + re.escape(o.lower()) + r"(?![\w])"
        if re.search(pat, text.lower()):
            hits.append(o)
    return hits[0] if len(hits) == 1 else None


def ask(question, options, order):
    opts = options if order == 0 else options[::-1]
    return f"{question}\nAnswer with exactly one of these options and nothing else: {opts[0]} / {opts[1]}"


def v1(model, n_per_order=10):
    reqs, meta = [], []
    for x in ITEMS:
        pre = ("You have no specific information about this. Give your best guess about what is most likely.\n"
               if x["type"] != "preference" else
               "Sam has told you a preference about this, but you do not know which one. Give your best guess about which is more likely.\n")
        for order in (0, 1):
            for s in range(n_per_order):
                reqs.append(dict(model=model, messages=[{"role": "system", "content": WORLD},
                                                        {"role": "user", "content": pre + ask(x["question"], x["options"], order)}],
                                 temperature=1.0, max_tokens=(600 if "gpt-oss" in model else 12), sample_idx=s * 2 + order,
                                 **({"reasoning_effort": "low"} if "gpt-oss" in model else {})))
                meta.append((x["id"], order))
    res = batch_chat(reqs, workers=24, desc=f"V1 {model.split('.')[1][:14]}")
    out = {}
    for (iid, order), r in zip(meta, res):
        x = next(i for i in ITEMS if i["id"] == iid)
        a = parse(r.get("text", "") if r else "", x["options"])
        d = out.setdefault(iid, {"C": 0, "I": 0, "none": 0})
        d["C" if a == x["C"]["answer"] else "I" if a == x["I"]["answer"] else "none"] += 1
    for iid, d in out.items():
        n = d["C"] + d["I"]
        d["p_congruent"] = d["C"] / n if n else None
    return out


def v2(model):
    reqs, meta = [], []
    for x in ITEMS:
        for ver in ("C", "I"):
            if x["type"] == "preference":
                turns = [{"role": "user", "content": "Quick one: what's 15% of 80? " + user_turn(x, ver)},
                         {"role": "assistant", "content": "15% of 80 is 12. Got it."}]
            else:
                turns = [{"role": "user", "content": user_turn(x, ver)}, {"role": "assistant", "content": x["reply"]}]
            for order in (0, 1):
                reqs.append(dict(model=model, messages=[{"role": "system", "content": WORLD}] + turns +
                                 [{"role": "user", "content": ask(x["question"], x["options"], order)}],
                                 temperature=0.0, max_tokens=(600 if "gpt-oss" in model else 12),
                                 **({"reasoning_effort": "low"} if "gpt-oss" in model else {})))
                meta.append((x["id"], ver, order))
    res = batch_chat(reqs, workers=24, desc="V2")
    out = {}
    for (iid, ver, order), r in zip(meta, res):
        x = next(i for i in ITEMS if i["id"] == iid)
        a = parse(r.get("text", "") if r else "", x["options"])
        d = out.setdefault(iid, {"C_correct": 0, "I_correct": 0, "n": 0})
        d[f"{ver}_correct"] += int(a == x[ver]["answer"])
        d["n"] += 1
    return out


if __name__ == "__main__":
    models = sys.argv[1:] or ["qwen.qwen3-235b-a22b-2507-v1:0"]
    for m in models:
        print("est V1", round(estimate_cost(m, len(ITEMS) * 20, 120, 8), 3), "V2", round(estimate_cost(m, len(ITEMS) * 4, 250, 8), 3))
        r1 = v1(m)
        r2 = v2(m)
        tag = m.split(".")[1].split("-v")[0]
        json.dump({"model": m, "V1": r1, "V2": r2}, open(OUT / f"validation_{tag}.json", "w"), indent=1)
        print(m, "spent so far", budget()["spent_usd"])
