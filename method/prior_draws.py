"""E1.1 (METHOD.md §2.1, §7): extra closed-book forced draws from the reader, for g_i and the prior strata.

Draws per answerable item (the F0 T=0 draw already exists in benchmark_audit/results/closed_book_<reader>.jsonl):
  F1_T0      paraphrased forced system prompt, T=0
  F2_T0      no system prompt, forced instruction in the user turn, T=0
  F0_T1_s1-3 the original FORCED_SYS, T=1.0, sample_idx 1..3
Output: results/prior_draws_<reader_tag>.jsonl  {id, bench, sub, model, draw, pred, correct}
Remedy (a) of METHOD v1.1 (--variant eval): the pi_F evaluation prompt with context "(nothing)" and the same question
text as the Empty reference system, T=1.0, sample_idx 1..3 (draws E_T1_s1-3)
  -> results/prior_draws_<reader_tag>_evalprompt.jsonl
usage: python prior_draws.py [--estimate] [--limit N] [--variant eval]
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import READER, READER_TAG, OUT, FORCED_SYS, F1_SYS, F2_USER, ANSWER_SYS_F, answerable_items, judge_rows, batch_chat
from infra.llm import estimate_cost, budget

DRAWS = [("F1_T0", 0.0, 0), ("F2_T0", 0.0, 0), ("F0_T1_s1", 1.0, 1), ("F0_T1_s2", 1.0, 2), ("F0_T1_s3", 1.0, 3)]
EVAL_DRAWS = [("E_T1_s1", 1.0, 1), ("E_T1_s2", 1.0, 2), ("E_T1_s3", 1.0, 3)]


def eval_question(x):
    """Question text exactly as the Empty reference system sees it (reference_systems.build)."""
    return x["q"].split("Question: ", 1)[1] if x["bench"] == "LoCoMo" else x["q"]


def messages(draw, q):
    if draw.startswith("E_"):
        return [{"role": "system", "content": ANSWER_SYS_F.format(ctx="(nothing)")}, {"role": "user", "content": q}]
    if draw.startswith("F1"):
        return [{"role": "system", "content": F1_SYS}, {"role": "user", "content": q}]
    if draw.startswith("F2"):
        return [{"role": "user", "content": F2_USER.format(question=q)}]
    return [{"role": "system", "content": FORCED_SYS}, {"role": "user", "content": q}]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--estimate", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--variant", default=None, choices=[None, "eval"])
    a = ap.parse_args()
    draws = EVAL_DRAWS if a.variant == "eval" else DRAWS
    items = answerable_items()
    if a.limit:
        items = items[:a.limit] + [x for x in items if x["bench"] == "LoCoMo"][:a.limit] + [x for x in items if x["bench"] == "MemoryAgentBench"][:a.limit]
    n_judged = sum(x["bench"] != "MemoryAgentBench" for x in items) * len(draws)
    est = estimate_cost(READER, len(items) * len(draws), 130, 40) + estimate_cost("openai.gpt-oss-120b-1:0", n_judged, 522, 55)
    print(f"items {len(items)}  draws {len(draws)}  answer calls {len(items) * len(draws)}  judge calls {n_judged}  est ${est:.2f}  "
          f"spent so far ${budget()['spent_usd']:.2f}")
    if a.estimate:
        return
    reqs, meta = [], []
    for x in items:
        for draw, T, s in draws:
            q = eval_question(x) if a.variant == "eval" else x["q"]
            reqs.append(dict(model=READER, messages=messages(draw, q), temperature=T, max_tokens=120 if a.variant == "eval" else 150, sample_idx=s))
            meta.append((x, draw))
    res = batch_chat(reqs, workers=32, desc="draws")
    rows = [dict(id=x["id"], bench=x["bench"], sub=x["sub"], qtype=x.get("qtype"), question=x["q"], gold=x["gold"],
                 model=READER_TAG, draw=draw, pred=(r or {}).get("text", "") or "") for (x, draw), r in zip(meta, res)]
    judge_rows(rows)
    out = OUT / f"prior_draws_{READER_TAG}{'_evalprompt' if a.variant == 'eval' else ''}{'_smoke' if a.limit else ''}.jsonl"
    with open(out, "w") as f:
        for r in rows:
            f.write(json.dumps({k: r[k] for k in ("id", "bench", "sub", "model", "draw", "pred", "correct")}, default=str) + "\n")
    miss = sum(r["correct"] is None for r in rows)
    print(f"wrote {out} ({len(rows)} rows, {miss} unjudged)  spent ${budget()['spent_usd']:.2f}")


if __name__ == "__main__":
    main()
