"""Step 2: LLM abstention classifier (METHOD.md §10.4) and its validation against the ABS regex (§10.1 rule).

  python abstention_judge.py validate        stratified sample (50 per bench x system x protocol A/F, seed 0)
                                             -> results/abstention_validation.json  (kappa, confusion, decision)
  python abstention_judge.py all             classify every answer (only if the validation says so)
                                             -> results/abstention_llm.jsonl  {bench, system, id, proto, abst_llm}
"""
import glob, json, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import OUT, JUDGE, batch_chat
from infra.llm import budget

PROMPT = ("Below is a question and an assistant's response. Decide whether the response ABSTAINS: it declines to answer, says that "
          "the information is not available, not mentioned or unknown, or asks for more information, instead of committing to an answer. "
          "A response that gives an answer, even a hedged guess, does NOT abstain.\n\nQuestion: {question}\nResponse: {response}\n\n"
          "Does the response abstain? Answer yes or no only.")


def items():
    out = []
    for f in sorted(glob.glob(str(OUT / "protocols_*.jsonl"))):
        for l in open(f):
            r = json.loads(l)
            for proto in ("A", "F", "FR"):
                p = r.get(f"pred_{proto}")
                if p is None:
                    continue
                out.append(dict(bench=r["bench"], system=r["system"], id=r["id"], proto=proto, question=r["question"], response=p,
                                regex=r.get(f"abst_{proto}_regex")))
    return out


def classify(rows, desc):
    reqs = [dict(model=JUDGE, messages=[{"role": "user", "content": PROMPT.format(question=r["question"], response=r["response"])}],
                 temperature=0.0, max_tokens=400, reasoning_effort="low") for r in rows]
    res = batch_chat(reqs, workers=32, desc=desc)
    for r, x in zip(rows, res):
        t = ((x or {}).get("text") or "").strip().lower()
        r["abst_llm"] = ("yes" in t[:20]) if t else None
    return rows


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def main():
    mode = sys.argv[1]
    rows = items()
    if mode == "validate":
        rng = random.Random(0)
        strata = {}
        for r in rows:
            # the decision uses only the main pre-registered design (METHOD §10.1: LoCoMo + RULER-QA1, the 12 systems);
            # the QA2 replication (§10.5) and the threshold robustness check (§10.6) must not influence it
            if r["proto"] in ("A", "F") and r["bench"] in ("locomo", "mab_ruler") and "@thr" not in r["system"] and r["system"] != "full_history":
                strata.setdefault((r["bench"], r["system"], r["proto"]), []).append(r)
        sample = [x for k in sorted(strata) for x in rng.sample(strata[k], min(50, len(strata[k])))]
        classify(sample, "abstention validate")
        ok = [r for r in sample if r["abst_llm"] is not None]
        a = [bool(r["regex"]) for r in ok]; b = [bool(r["abst_llm"]) for r in ok]
        k = kappa(a, b)
        conf = {"both": sum(x and y for x, y in zip(a, b)), "regex_only": sum(x and not y for x, y in zip(a, b)),
                "llm_only": sum(y and not x for x, y in zip(a, b)), "neither": sum(not x and not y for x, y in zip(a, b))}
        dec = "regex" if k >= 0.80 else "llm"
        res = dict(n=len(ok), kappa=k, agreement=sum(x == y for x, y in zip(a, b)) / len(ok), confusion=conf, decision=dec,
                   examples_disagree=[dict(response=r["response"][:200], regex=r["regex"], llm=r["abst_llm"]) for r in ok if bool(r["regex"]) != bool(r["abst_llm"])][:40])
        (OUT / "abstention_validation.json").write_text(json.dumps(res, indent=1))
        (OUT / "abstention_validation_sample.jsonl").write_text("\n".join(json.dumps(r) for r in sample) + "\n")
        print(f"n {len(ok)}  kappa {k:.3f}  confusion {conf}  -> use {dec}   spent ${budget()['spent_usd']:.2f}")
    elif mode == "all":
        classify(rows, "abstention all")
        with open(OUT / "abstention_llm.jsonl", "w") as f:
            for r in rows:
                f.write(json.dumps({k: r[k] for k in ("bench", "system", "id", "proto", "abst_llm")}) + "\n")
        print(f"classified {len(rows)}  spent ${budget()['spent_usd']:.2f}")


if __name__ == "__main__":
    main()
