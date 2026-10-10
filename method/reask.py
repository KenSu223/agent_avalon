"""Compliance follow-up for the forced protocol (deviation, see PLAN.md deviation log; reported next to the original).

Rows whose answer under a forced prompt is still an abstention (ABS regex) get one follow-up turn asking for a best
guess; everything else is copied unchanged. Applied identically to the closed-book draws and to the reference
systems, so g and the evaluated systems stay on the same protocol.
  python reask.py refsys  empty oracle bm25_ev bm25_noev   -> results/refsys_<s>_Freask.jsonl
  python reask.py prior                                     -> results/prior_draws_<reader>_reask.jsonl
                                                              (+ the F0 T=0 closed-book draw, re-asked, as draw F0_T0)
  python reask.py evalprior                                 -> results/prior_draws_<reader>_evalprompt_reask.jsonl
                                                              (g'' for pi_F+R, METHOD §10.1)
"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import READER, READER_TAG, OUT, ANSWER_SYS_F, FORCED_SYS, F1_SYS, F2_USER, judge_rows, batch_chat, ROOT
from infra.llm import budget
from property_tests import ABS
from prior_draws import messages as draw_messages

FOLLOW = "Please give your single best guess anyway, in a few words. Do not say that the information is missing."


def reask(rows, build_messages, desc):
    todo = [i for i, r in enumerate(rows) if ABS.search(r["pred"] or "")]
    print(f"{desc}: {len(todo)}/{len(rows)} abstained ({len(todo)/max(1,len(rows)):.3f}); re-asking", flush=True)
    reqs = []
    for i in todo:
        r = rows[i]
        msgs = build_messages(r) + [{"role": "assistant", "content": r["pred"]}, {"role": "user", "content": FOLLOW}]
        reqs.append(dict(model=READER, messages=msgs, temperature=r.get("_T", 0.0), max_tokens=120, sample_idx=r.get("_s", 0) + 100))
    res = batch_chat(reqs, workers=32, desc=desc)
    sub = []
    for i, x in zip(todo, res):
        rows[i] = dict(rows[i], pred_original=rows[i]["pred"], pred=(x or {}).get("text", "") or "", reasked=True)
        sub.append(rows[i])
    judge_rows(sub)
    return rows


def main():
    mode = sys.argv[1]
    if mode == "refsys":
        for s in sys.argv[2:]:
            rows = [json.loads(l) for l in open(OUT / f"refsys_{s}_F.jsonl")]
            rows = reask(rows, lambda r: [{"role": "system", "content": ANSWER_SYS_F.format(ctx=r["ctx"])}, {"role": "user", "content": r["question"]}], f"refsys {s}")
            with open(OUT / f"refsys_{s}_Freask.jsonl", "w") as f:
                for r in rows:
                    f.write(json.dumps(dict(r, protocol="Freask"), default=str) + "\n")
    elif mode == "prior":
        from common import answerable_items
        items = {x["id"]: x for x in answerable_items()}
        T = {"F1_T0": (0.0, 0), "F2_T0": (0.0, 0), "F0_T1_s1": (1.0, 1), "F0_T1_s2": (1.0, 2), "F0_T1_s3": (1.0, 3), "F0_T0": (0.0, 0)}
        rows = []
        for l in open(OUT / f"prior_draws_{READER_TAG}.jsonl"):
            r = json.loads(l)
            rows.append(r)
        for l in open(ROOT / f"benchmark_audit/results/closed_book_{READER_TAG}.jsonl"):
            r = json.loads(l)
            if r["proto"] == "forced" and r["id"] in items:
                rows.append(dict(id=r["id"], bench=r["bench"], sub=r["sub"], model=READER_TAG, draw="F0_T0", pred=r["pred"], correct=r["correct"]))
        for r in rows:
            x = items[r["id"]]
            r.update(question=x["q"], gold=x["gold"], qtype=x.get("qtype"), _T=T[r["draw"]][0], _s=T[r["draw"]][1])
        rows = reask(rows, lambda r: draw_messages(r["draw"], r["question"]), "prior draws")
        with open(OUT / f"prior_draws_{READER_TAG}_reask.jsonl", "w") as f:
            for r in rows:
                f.write(json.dumps({k: r.get(k) for k in ("id", "bench", "sub", "model", "draw", "pred", "correct", "reasked")}, default=str) + "\n")
    elif mode == "evalprior":
        from common import answerable_items
        from prior_draws import eval_question
        items = {x["id"]: x for x in answerable_items()}
        rows = [json.loads(l) for l in open(OUT / f"prior_draws_{READER_TAG}_evalprompt.jsonl")]
        for r in rows:
            x = items[r["id"]]
            r.update(question=eval_question(x), gold=x["gold"], qtype=x.get("qtype"), _T=1.0, _s=int(r["draw"][-1]))
        rows = reask(rows, lambda r: draw_messages(r["draw"], r["question"]), "eval-prompt prior draws")
        with open(OUT / f"prior_draws_{READER_TAG}_evalprompt_reask.jsonl", "w") as f:
            for r in rows:
                f.write(json.dumps({k: r.get(k) for k in ("id", "bench", "sub", "model", "draw", "pred", "correct", "reasked")}, default=str) + "\n")
    print(f"spent ${budget()['spent_usd']:.2f}")


if __name__ == "__main__":
    main()
