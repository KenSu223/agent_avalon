"""Step 2.3: answer every system's saved contexts under the forced protocols (METHOD.md §4 S2, v1.2; Step 2 pre-registration §10).

Input : benchmark_audit/results_v2/rescore_<bench>_<system>.jsonl   (contexts + the native pi_A answer and score)
Output: results/protocols_<bench>_<system>.jsonl, one row per question:
  pred_A / correct_A     native protocol (copied from rescore; ANSWER_SYS)
  pred_F / correct_F     forced protocol pi_F (ANSWER_SYS_F, same context, T=0)            answerable questions only
  pred_FR / correct_FR   pi_F + compliance follow-up (reask.FOLLOW) when pred_F is an abstention by the ABS regex
  abst_*_regex           ABS regex on each answer
usage: python protocols.py <bench> <system> [<system> ...]
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import READER, OUT, ANSWER_SYS_F, ROOT, judge_rows, batch_chat
from infra.llm import budget
from property_tests import ABS
from reask import FOLLOW

V2 = ROOT / "benchmark_audit/results_v2"


def answerable(r, bench):
    return (r.get("category") != 5) if bench == "locomo" else True


def main():
    bench, systems = sys.argv[1], sys.argv[2:]
    for system in systems:
        rows = [json.loads(l) for l in open(V2 / f"rescore_{bench}_{system}.jsonl")]
        if bench == "mab_ruler":
            rows = [r for r in rows if r.get("sub") == "ruler_qa1"]
        out = []
        for r in rows:
            out.append(dict(id=r["id"], system=system, bench=bench, cluster=r["episode"], category=r.get("category"), sub=r.get("sub"),
                            answerable=answerable(r, bench), question=r["question"], gold=r["gold"], ctx=r["ctx"], ctx_chars=r["ctx_chars"],
                            pred_A=r["pred"], correct_A=r["correct"], abst_A_regex=bool(ABS.search(r["pred"] or ""))))
        ans = [o for o in out if o["answerable"]]
        msgs = lambda o: [{"role": "system", "content": ANSWER_SYS_F.format(ctx=o["ctx"])}, {"role": "user", "content": o["question"]}]
        res = batch_chat([dict(model=READER, messages=msgs(o), temperature=0.0, max_tokens=120) for o in ans], workers=32, desc=f"{system} pi_F")
        for o, x in zip(ans, res):
            o["pred_F"] = (x or {}).get("text", "") or ""
            o["abst_F_regex"] = bool(ABS.search(o["pred_F"]))
        # judge pi_F (judge_rows reads 'pred' and 'bench' in closed_book naming)
        jr = [dict(bench="LoCoMo" if bench == "locomo" else "MemoryAgentBench", question=o["question"], gold=o["gold"], pred=o["pred_F"]) for o in ans]
        judge_rows(jr, desc=f"{system} judge F")
        for o, j in zip(ans, jr):
            o["correct_F"] = j["correct"]
        # pi_F + compliance follow-up
        todo = [o for o in ans if o["abst_F_regex"]]
        res = batch_chat([dict(model=READER, messages=msgs(o) + [{"role": "assistant", "content": o["pred_F"]}, {"role": "user", "content": FOLLOW}],
                               temperature=0.0, max_tokens=120, sample_idx=100) for o in todo], workers=32, desc=f"{system} pi_F+R")
        for o, x in zip(todo, res):
            o["pred_FR"] = (x or {}).get("text", "") or ""
        jr = [dict(bench="LoCoMo" if bench == "locomo" else "MemoryAgentBench", question=o["question"], gold=o["gold"], pred=o["pred_FR"]) for o in todo]
        judge_rows(jr, desc=f"{system} judge FR")
        for o, j in zip(todo, jr):
            o["correct_FR"] = j["correct"]
        for o in ans:
            if not o["abst_F_regex"]:
                o["pred_FR"], o["correct_FR"] = o["pred_F"], o["correct_F"]
            o["abst_FR_regex"] = bool(ABS.search(o["pred_FR"]))
        with open(OUT / f"protocols_{bench}_{system}.jsonl", "w") as f:
            for o in out:
                o = {k: v for k, v in o.items() if k != "ctx"}
                f.write(json.dumps(o, default=str) + "\n")
        n_unj = sum(o.get("correct_F") is None for o in ans) + sum(o.get("correct_FR") is None for o in ans)
        print(f"{bench} {system}: {len(out)} rows, {len(ans)} answerable, pi_F abstained {len(todo)}, unjudged {n_unj}, spent ${budget()['spent_usd']:.2f}", flush=True)


if __name__ == "__main__":
    main()
