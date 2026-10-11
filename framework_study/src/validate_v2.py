"""Gates V1 / V2 for the expanded item set (STEP3_DESIGN.md §3). Prompts are those of validate.py (same WORLD system
prompt, same V1 prefixes, same forced-choice question format); knowledge updates hear the initial value and then the
update before the V2 question.

V1  prior strength: 20 forced-choice samples per item (10 per option order), T=1, models:
    Qwen3-235B, Llama-3.3-70B, gpt-oss-120b, DeepSeek-V3.2. P(C) = share of answers naming the C option
    (for updates: the schema-congruent value; for neutral items: option A).
V2  comprehension: right after hearing the item, both versions x both option orders, T=0, models:
    Qwen3-235B, Llama-3.3-70B, gpt-oss-120b.
Output: framework_study/results/validation_v2_<model tag>.json   {"model", "V1": {id: {...}}, "V2": {id: {...}}}
usage: python validate_v2.py [--estimate] [--limit N]
"""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "framework_study/src")); sys.path.insert(0, str(ROOT / "framework_study/stimuli"))
from infra.llm import batch_chat, estimate_cost, budget
from validate import parse, ask, WORLD

ITEMS = [json.loads(l) for l in open(ROOT / "framework_study/stimuli/items_v2.jsonl")]
OUT = ROOT / "framework_study/results"
V1_MODELS = ["qwen.qwen3-235b-a22b-2507-v1:0", "meta.llama3-3-70b-instruct-v1:0", "openai.gpt-oss-120b-1:0", "deepseek.v3.2"]
V2_MODELS = V1_MODELS[:3]
PREF_FILLER = ("Quick one: what's 15% of 80? ", "15% of 80 is 12. Got it.")      # as in validate.v2
V1_PREFIX = "You have no specific information about this. Give your best guess about what is most likely.\n"
V1_PREFIX_PREF = "Sam has told you a preference about this, but you do not know which one. Give your best guess about which is more likely.\n"


def tag(m):
    return m.split(".")[1].split("-v")[0] if m.count(".") >= 1 and not m.startswith("deepseek") else m.replace(".", "-")


def extra(m):
    return {"max_tokens": 600, "reasoning_effort": "low"} if "gpt-oss" in m else {"max_tokens": 12}


def item_turns(x, ver):
    """Messages in which Sam tells the item (version ver), as in the framework study sessions."""
    v = x[ver]
    end = lambda c: "" if c.endswith(".") else "."
    if x["type"] == "preference":
        return [{"role": "user", "content": PREF_FILLER[0] + f"{x['lead']}{v['clause']}{end(v['clause'])}"},
                {"role": "assistant", "content": PREF_FILLER[1]}]
    if x["type"] == "update":
        return [{"role": "user", "content": f"{x['initial_task']} {x['initial_lead']}{v['initial']}{end(v['initial'])}"},
                {"role": "assistant", "content": x["initial_reply"]},
                {"role": "user", "content": f"{x['task']} {x['lead']}{v['clause']}{end(v['clause'])}"},
                {"role": "assistant", "content": x["reply"]}]
    return [{"role": "user", "content": f"{x['task']} {x['lead']}{v['clause']}{end(v['clause'])}"},
            {"role": "assistant", "content": x["reply"]}]


def requests(items):
    reqs, meta = [], []
    for m in V1_MODELS:
        for x in items:
            pre = V1_PREFIX_PREF if x["type"] == "preference" else V1_PREFIX
            for order in (0, 1):
                for s in range(10):
                    reqs.append(dict(model=m, messages=[{"role": "system", "content": WORLD},
                                                        {"role": "user", "content": pre + ask(x["question"], x["options"], order)}],
                                     temperature=1.0, sample_idx=s * 2 + order, **extra(m)))
                    meta.append(("V1", m, x["id"], order))
    for m in V2_MODELS:
        for x in items:
            for ver in ("C", "I"):
                for order in (0, 1):
                    reqs.append(dict(model=m, messages=[{"role": "system", "content": WORLD}] + item_turns(x, ver) +
                                     [{"role": "user", "content": ask(x["question"], x["options"], order)}], temperature=0.0, **extra(m)))
                    meta.append(("V2", m, x["id"], (ver, order)))
    return reqs, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--estimate", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    items = ITEMS[:a.limit] if a.limit else ITEMS
    reqs, meta = requests(items)
    est = 0.0
    for m in V1_MODELS:
        n1 = sum(1 for t in meta if t[0] == "V1" and t[1] == m); n2 = sum(1 for t in meta if t[0] == "V2" and t[1] == m)
        out_tok = 200 if "gpt-oss" in m else 5
        est += estimate_cost(m, n1, 120, out_tok) + estimate_cost(m, n2, 260, out_tok)
    print(f"items {len(items)}  calls {len(reqs)}  est ${est:.2f}  spent ${budget()['spent_usd']:.2f}")
    if a.estimate:
        return
    res = batch_chat(reqs, workers=32, desc="gates")
    byid = {x["id"]: x for x in items}
    out = {m: {"model": m, "V1": {}, "V2": {}} for m in V1_MODELS}
    for (gate, m, iid, k), r in zip(meta, res):
        x = byid[iid]
        ans = parse((r or {}).get("text", "") or "", x["options"])
        if gate == "V1":
            d = out[m]["V1"].setdefault(iid, {"C": 0, "I": 0, "none": 0})
            d["C" if ans == x["C"]["answer"] else "I" if ans == x["I"]["answer"] else "none"] += 1
        else:
            ver, order = k
            d = out[m]["V2"].setdefault(iid, {"C_correct": 0, "I_correct": 0, "n": 0, "unparsed": 0})
            d[f"{ver}_correct"] += int(ans == x[ver]["answer"]); d["n"] += 1; d["unparsed"] += int(ans is None)
    for m, o in out.items():
        for d in o["V1"].values():
            n = d["C"] + d["I"]
            d["p_congruent"] = d["C"] / n if n else None
        fn = OUT / f"validation_v2_{tag(m)}{'_smoke' if a.limit else ''}.json"
        fn.write_text(json.dumps(o, indent=1))
        print("wrote", fn)
    print(f"spent ${budget()['spent_usd']:.2f}")


if __name__ == "__main__":
    main()
