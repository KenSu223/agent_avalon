"""Probe framework snapshots.

For every snapshot x item:
  memory state : two judges (gpt-oss-120b, gemma-3-27b) read the full memory dump -> RETAINED / FLIPPED / DROPPED
  belief       : the agent (answer model, T=0) answers the forced-choice question from the framework's own
                 retrieved context -> answers the told version (KEPT) or the other one (REVERTED)

usage: python probe.py <snapshots file> [--answer-model M]
Output: results/probed_<same suffix>.jsonl
"""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "framework_study/src"))
from infra.llm import batch_chat
from validate import parse, WORLD
from v3_reproduction import JUDGE_PROMPT, JUDGES
from sessions import ITEMS
import sessions_v2 as S2

QA_SYSTEM = WORLD + "\n\nHere is everything you remember from past conversations with Sam:\n<memory>\n{ctx}\n</memory>"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshots")
    ap.add_argument("--answer-model", default="qwen.qwen3-235b-a22b-2507-v1:0")
    a = ap.parse_args()
    snaps = [json.loads(l) for l in open(a.snapshots)]
    reqs, meta = [], []
    for si, s in enumerate(snaps):
        for iid, v in s["assign"]:
            IT = S2.ITEMS if s.get("item_set") == "v2" else ITEMS
            x = IT[iid]
            for j in JUDGES:
                reqs.append(dict(model=j, messages=[{"role": "user", "content": JUDGE_PROMPT.format(
                    notes=s["dump"] or "(empty)", question=x["question"], a=x["options"][0], b=x["options"][1])}],
                    temperature=0.0, max_tokens=(600 if "gpt-oss" in j else 12),
                    **({"reasoning_effort": "low"} if "gpt-oss" in j else {})))
                meta.append(("judge", si, iid, v, j))
            ctx = s["contexts"].get(iid, s["dump"]) or "(nothing)"
            reqs.append(dict(model=a.answer_model, messages=[
                {"role": "system", "content": QA_SYSTEM.format(ctx=ctx)},
                {"role": "user", "content": f"{x['question']}\nAnswer with exactly one of these options and nothing else: {x['options'][0]} / {x['options'][1]}"}],
                temperature=0.0, max_tokens=12))
            meta.append(("qa", si, iid, v, a.answer_model))
    res = batch_chat(reqs, workers=32, desc="probe")
    out = {}
    for (kind, si, iid, v, m), r in zip(meta, res):
        x = (S2.ITEMS if snaps[si].get("item_set") == "v2" else ITEMS)[iid]
        t = ((r or {}).get("text") or "")
        ans = parse(t, x["options"])
        key = (si, iid)
        d = out.setdefault(key, {"framework": snaps[si]["framework"], "model": snaps[si]["model"], "user": snaps[si]["user"],
                                 "ckpt": snaps[si]["ckpt"], "item": iid, "version": v, "type": x["type"],
                                 "normative": x["normative"], "judges": {}})
        if kind == "judge":
            d["judges"][m] = ("RETAINED" if ans == x[v]["answer"] else "FLIPPED" if ans is not None else
                              "DROPPED" if "NOT_MENTIONED" in t.upper() or "NOT MENTIONED" in t.upper() else "UNPARSED")
        else:
            d["belief"] = "KEPT" if ans == x[v]["answer"] else "REVERTED" if ans is not None else "UNPARSED"
    for d in out.values():
        labs = list(d["judges"].values())
        d["state"] = labs[0] if len(set(labs)) == 1 else "DISAGREE"
    dst = Path(a.snapshots).with_name(Path(a.snapshots).name.replace("snapshots_", "probed_"))
    with open(dst, "w") as f:
        for d in out.values():
            f.write(json.dumps(d) + "\n")
    print("wrote", dst, len(out))


if __name__ == "__main__":
    main()
