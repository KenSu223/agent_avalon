"""Shared pieces for the PCME experiments: fixed prompts (METHOD.md appendix A), answerable benchmark items, and the
official scorers exactly as used by benchmark_audit/closed_book.py and rescore.py."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "benchmark_audit")); sys.path.insert(0, str(ROOT / "benchmark_audit/official"))
from infra.llm import batch_chat
from closed_book import load_lme, load_locomo, load_mab, substring_em, norm, FORCED_SYS
from lme_prompts import get_anscheck_prompt

READER = "qwen.qwen3-235b-a22b-2507-v1:0"
READER_TAG = "qwen3-235b-a22b-2507"          # = model tag of benchmark_audit/results/closed_book_<tag>.jsonl
JUDGE = "openai.gpt-oss-120b-1:0"
OUT = Path(__file__).parent / "results"
OUT.mkdir(exist_ok=True)

ANSWER_SYS_F = ("You are a memory-augmented assistant. Below is what your memory system returned for the question. "
                "Answer the question using it. If the memory does not contain the answer, still give your single best guess: "
                "never refuse, never say you don't know, and never ask for more information. "
                "Keep the answer short (a few words or one sentence).\n\n<memory>\n{ctx}\n</memory>")
F1_SYS = ("You cannot see the conversation history or the document this question refers to. Answer with your most likely "
          "guess, as specifically as possible. Do not refuse, do not say you don't know, and do not ask questions.")
F2_USER = "{question}\n\n(You have no access to the relevant history. Reply with your best guess at the answer in a few words. You must give an answer.)"


def answerable_items():
    """Closed-book items (same text as closed_book.py) restricted to answerable questions."""
    items = load_lme() + load_locomo() + load_mab()
    return [x for x in items if not x["abstention"]]


def judge_rows(rows, question_key="question", workers=32, desc="judge"):
    """Fill row['correct'] with the benchmark's official scorer. Rows need bench, gold, pred, and qtype for LongMemEval."""
    reqs, idx = [], []
    for i, r in enumerate(rows):
        if r["bench"] == "MemoryAgentBench":
            r["correct"] = bool(substring_em(r["pred"] or "", r["gold"]))
            continue
        q = r[question_key]
        q = q.split("Question: ", 1)[1] if "Question: " in q else q
        task = r["qtype"] if r["bench"] == "LongMemEval" else "single-session-user"
        p = get_anscheck_prompt(task, q, r["gold"], r["pred"] or "")
        reqs.append(dict(model=JUDGE, messages=[{"role": "user", "content": p}], temperature=0.0, max_tokens=600, reasoning_effort="low"))
        idx.append(i)
    res = batch_chat(reqs, workers=workers, desc=desc)
    for i, jr in zip(idx, res):
        t = ((jr or {}).get("text") or "").strip()
        rows[i]["correct"] = ("yes" in t.lower()[:20]) if t else None
    return rows
