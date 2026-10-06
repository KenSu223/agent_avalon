"""Closed-book (no memory, no history) audit of agent-memory benchmarks.

For every question the answer model sees ONLY the question (plus the question date where the benchmark gives
one). Two protocols:
  natural  : "Answer from what you remember of past conversations; you have no memory." Abstaining is allowed.
             = the score a memory system that stores NOTHING gets under the benchmark's normal protocol.
  forced   : "You do not have the history. Give your single best guess; never refuse."
             = how much of the benchmark is answerable from the model's prior alone.
Scoring uses each benchmark's own scorer:
  LongMemEval        official per-type yes/no judge prompts (evaluate_qa.py), judge = gpt-oss-120b
  LoCoMo             official token-F1 (task_eval/evaluation.py, Porter-stemmed) + the LongMemEval generic judge prompt
  MemoryAgentBench   substring exact match (its QA metric); EventQA option match
  PrefEval explicit  official check_violation / check_helpful prompts; following = not violation and helpful
usage: python closed_book.py [answer_model]
"""
import json, re, string, sys, collections
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from infra.llm import batch_chat, budget
sys.path.insert(0, str(Path(__file__).parent / "official"))

D = Path(__file__).parent / "data"
OUT = Path(__file__).parent / "results"
OUT.mkdir(exist_ok=True)
JUDGE = "openai.gpt-oss-120b-1:0"
ANSWER = sys.argv[1] if len(sys.argv) > 1 else "qwen.qwen3-235b-a22b-2507-v1:0"

NAT_SYS = ("You are a personal assistant that has been chatting with this user over many past sessions. "
           "Answer the user's question using what you remember about them from those conversations. "
           "Your memory of past conversations is currently EMPTY: nothing was retrieved.")
FORCED_SYS = ("You are answering a question about a user (or about a conversation or document) without having access to "
              "the conversation history or document. Give your single best guess at the answer, as specifically as you can. "
              "Never refuse, never say you don't know, and never ask for more information.")

# ----------------------------------------------------------------- items
def load_lme():
    data = json.load(open(D / "longmemeval_oracle.json"))
    out = []
    for x in data:
        q = f"Current Date: {x['question_date']}\nQuestion: {x['question']}"
        out.append(dict(bench="LongMemEval", sub=x["question_type"] + ("_abs" if x["question_id"].endswith("_abs") else ""),
                        id=x["question_id"], q=q, gold=str(x["answer"]), qtype=x["question_type"],
                        abstention=x["question_id"].endswith("_abs")))
    return out


def load_locomo():
    data = json.load(open(D / "locomo10.json"))
    names = {1: "multi-hop", 2: "temporal", 3: "open-domain", 4: "single-hop", 5: "adversarial"}
    out = []
    for ci, c in enumerate(data):
        a, b = c["conversation"]["speaker_a"], c["conversation"]["speaker_b"]
        for qi, q in enumerate(c["qa"]):
            gold = q.get("answer", q.get("adversarial_answer", ""))
            out.append(dict(bench="LoCoMo", sub=names[q["category"]], id=f"c{ci}q{qi}",
                            q=f"(This question is about a long conversation between {a} and {b}.)\nQuestion: {q['question']}",
                            gold=str(gold), category=q["category"], abstention=q["category"] == 5))
    return out


def load_mab():
    out = []
    ar = pd.read_parquet(D / "mab_Accurate_Retrieval.parquet")
    for _, r in ar.iterrows():
        src = r["metadata"]["qa_pair_ids"][0].rsplit("_no", 1)[0]
        if src not in ("ruler_qa1_197K", "ruler_qa2_421K", "eventqa_full"):
            continue
        for i, (q, a) in enumerate(zip(r["questions"], r["answers"])):
            out.append(dict(bench="MemoryAgentBench", sub=src.split("_")[0] + "_" + src.split("_")[1] if src.startswith("ruler") else "eventqa",
                            id=f"{src}_{i}", q=str(q), gold=[str(g) for g in a], abstention=False))
    cr = pd.read_parquet(D / "mab_Conflict_Resolution.parquet")
    for _, r in cr.iterrows():
        src = r["metadata"]["qa_pair_ids"][0].rsplit("_no", 1)[0]
        if src not in ("factconsolidation_sh_6k", "factconsolidation_mh_6k"):
            continue
        for i, (q, a) in enumerate(zip(r["questions"], r["answers"])):
            out.append(dict(bench="MemoryAgentBench", sub=src.replace("_6k", ""), id=f"{src}_{i}", q=str(q),
                            gold=[str(g) for g in a], abstention=False))
    return out


def load_prefeval():
    out = []
    for f in sorted((D / "prefeval").glob("*.json")):
        for i, x in enumerate(json.load(open(f))):
            out.append(dict(bench="PrefEval", sub=f.stem, id=f"{f.stem}_{i}", q=x["question"], preference=x["preference"],
                            gold=None, abstention=False))
    return out


# ----------------------------------------------------------------- scoring helpers
from nltk.stem import PorterStemmer
ps = PorterStemmer()


def norm(s):
    s = s.replace(",", "").lower()
    s = "".join(ch for ch in s if ch not in set(string.punctuation))
    s = re.sub(r"\b(a|an|the|and)\b", " ", s)
    return " ".join(s.split())


def f1_score(pred, gt):
    p = [ps.stem(w) for w in norm(pred).split()]
    g = [ps.stem(w) for w in norm(gt).split()]
    common = collections.Counter(p) & collections.Counter(g)
    n = sum(common.values())
    if n == 0:
        return 0.0
    pr, rc = n / len(p), n / len(g)
    return 2 * pr * rc / (pr + rc)


def locomo_f1(pred, gt, cat):
    if cat == 3:
        gt = gt.split(";")[0].strip()
    if cat == 1:  # multi-answer
        preds = [p.strip() for p in pred.split(",")]
        gts = [g.strip() for g in gt.split(",")]
        return sum(max(f1_score(p, g) for p in preds) for g in gts) / len(gts)
    if cat == 5:
        return 1.0 if ("no information available" in pred.lower() or "not mentioned" in pred.lower()) else 0.0
    return f1_score(pred, gt)


def substring_em(pred, golds):
    p = norm(pred)
    return float(any(norm(g) and norm(g) in p for g in golds))


def main():
    from lme_prompts import get_anscheck_prompt
    items = load_lme() + load_locomo() + load_mab() + load_prefeval()
    print(collections.Counter(x["bench"] for x in items))
    reqs, meta = [], []
    for x in items:
        for proto, sysmsg in (("natural", NAT_SYS), ("forced", FORCED_SYS)):
            if x["bench"] == "PrefEval":
                if proto == "forced":
                    continue   # one protocol only: the memoryless assistant simply answers the query
                msgs = [{"role": "user", "content": x["q"]}]
                mt = 600
            else:
                msgs = [{"role": "system", "content": sysmsg}, {"role": "user", "content": x["q"]}]
                mt = 150
            reqs.append(dict(model=ANSWER, messages=msgs, temperature=0.0, max_tokens=mt))
            meta.append((x, proto))
    res = batch_chat(reqs, workers=32, desc="answer")
    rows = []
    for (x, proto), r in zip(meta, res):
        rows.append(dict(x, proto=proto, pred=(r or {}).get("text", "") or ""))
    # judge calls
    jreqs, jmeta = [], []
    pe_viol = open(Path(__file__).parent / "official/prefeval_check_violation.txt").read()
    pe_help = open(Path(__file__).parent / "official/prefeval_check_helpful.txt").read()
    for i, r in enumerate(rows):
        if r["bench"] == "LongMemEval":
            p = get_anscheck_prompt(r["qtype"], r["q"].split("Question: ", 1)[1], r["gold"], r["pred"], abstention=r["abstention"])
            jreqs.append(dict(model=JUDGE, messages=[{"role": "user", "content": p}], temperature=0.0, max_tokens=600, reasoning_effort="low")); jmeta.append((i, "judge"))
        elif r["bench"] == "LoCoMo":
            if r["abstention"]:
                p = get_anscheck_prompt("single-session-user", r["q"].split("Question: ", 1)[1], "The conversation does not contain this information.", r["pred"], abstention=True)
            else:
                p = get_anscheck_prompt("single-session-user", r["q"].split("Question: ", 1)[1], r["gold"], r["pred"])
            jreqs.append(dict(model=JUDGE, messages=[{"role": "user", "content": p}], temperature=0.0, max_tokens=600, reasoning_effort="low")); jmeta.append((i, "judge"))
        elif r["bench"] == "PrefEval":
            for name, tpl in (("violate", pe_viol), ("helpful", pe_help)):
                p = tpl.replace("{preference}", r["preference"]).replace("{question}", r["q"]).replace("{end_generation}", r["pred"])
                jreqs.append(dict(model=JUDGE, messages=[{"role": "system", "content": "You are a helpful assistant in evaluating an AI assistant's reponse. You should be fair and strict and follow the user's instruction"},
                                                         {"role": "user", "content": p}], temperature=0.0, max_tokens=800, reasoning_effort="low"))
                jmeta.append((i, name))
    jres = batch_chat(jreqs, workers=32, desc="judge")
    for (i, kind), jr in zip(jmeta, jres):
        t = ((jr or {}).get("text") or "").strip()
        if kind == "judge":
            rows[i]["judge_correct"] = "yes" in t.lower()[:20]
        else:
            m = re.search(r"<answer>\s*(yes|no)", t, re.I)
            rows[i][kind] = (m.group(1).lower() == "yes") if m else None
    for r in rows:
        if r["bench"] == "LoCoMo":
            r["f1"] = locomo_f1(r["pred"], r["gold"], r["category"])
            r["correct"] = r.get("judge_correct")
        elif r["bench"] == "LongMemEval":
            r["correct"] = r.get("judge_correct")
        elif r["bench"] == "MemoryAgentBench":
            if r["sub"] == "eventqa":
                r["correct"] = bool(substring_em(r["pred"], r["gold"]))
            else:
                r["correct"] = bool(substring_em(r["pred"], r["gold"]))
        elif r["bench"] == "PrefEval":
            r["correct"] = (r.get("violate") is False) and (r.get("helpful") is True)
    tag = ANSWER.split(".")[1].split("-v")[0]
    with open(OUT / f"closed_book_{tag}.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r, default=str) + "\n")
    print("spent", budget()["spent_usd"])


if __name__ == "__main__":
    main()
