"""Re-score real memory systems on existing benchmarks, then split scores by prior-answerability.

Episodes
  locomo     : 10 conversations; each session -> one ingest (speaker_a as 'user', speaker_b as 'assistant',
               every turn prefixed with the speaker name, session date in the first turn)
  mab_ruler  : MemoryAgentBench Accurate_Retrieval ruler_qa1 / ruler_qa2 documents, fed in ~1,000-word chunks
               ("Here is the next part of a document I want you to remember: ...")
After the whole episode is ingested, every question is answered from the system's own context(question).

usage: python rescore.py <system> <bench: locomo|mab_ruler> [--workers N] [--save-ctx]
Output: results/rescore_<bench>_<system>.jsonl
  --save-ctx (Step 2, PLAN.md): also store the full context returned for every question, and write to
  results_v2/ instead (the original results/ files are kept for the test-retest comparison). The answer request is
  byte-identical to the original one, so deterministic systems hit the response cache.
"""
import argparse, json, sys, time, traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "framework_study/src")); sys.path.insert(0, str(Path(__file__).parent / "official"))
from frameworks import ADAPTERS
from infra.llm import chat
from lme_prompts import get_anscheck_prompt

D = Path(__file__).parent / "data"
OUT = Path(__file__).parent / "results"
MODEL = "qwen.qwen3-235b-a22b-2507-v1:0"
JUDGE = "openai.gpt-oss-120b-1:0"
ANSWER_SYS = ("You are a memory-augmented assistant. Below is what your memory system returned for the question. "
              "Answer the question using it. Keep the answer short (a few words or one sentence).\n\n<memory>\n{ctx}\n</memory>")


def locomo_episodes():
    data = json.load(open(D / "locomo10.json"))
    eps = []
    for ci, c in enumerate(data):
        conv = c["conversation"]; a, b = conv["speaker_a"], conv["speaker_b"]
        n = 1
        sessions = []
        while f"session_{n}" in conv:
            turns = conv[f"session_{n}"]
            date = conv.get(f"session_{n}_date_time", "")
            msgs = []
            for j, t in enumerate(turns):
                text = f"[{date}] {t['speaker']}: {t['text']}"
                if t.get("blip_caption"):
                    text += f" [shares a photo: {t['blip_caption']}]"
                msgs.append({"role": "user" if t["speaker"] == a else "assistant", "content": text})
            sessions.append(msgs)
            n += 1
        qs = []
        for qi, q in enumerate(c["qa"]):
            qs.append(dict(id=f"c{ci}q{qi}", question=q["question"], gold=str(q.get("answer", q.get("adversarial_answer", ""))),
                           category=q["category"], abstention=q["category"] == 5))
        eps.append(dict(id=f"locomo_c{ci}", sessions=sessions, questions=qs))
    return eps


def mab_ruler_episodes(words_per_chunk=1000, only=None):
    ar = pd.read_parquet(D / "mab_Accurate_Retrieval.parquet")
    eps = []
    for _, r in ar.iterrows():
        src = r["metadata"]["qa_pair_ids"][0].rsplit("_no", 1)[0]
        if src not in ("ruler_qa1_197K", "ruler_qa2_421K") or (only and only not in src):
            continue
        w = r["context"].split()
        sessions = []
        for i in range(0, len(w), words_per_chunk):
            sessions.append([{"role": "user", "content": "Here is the next part of a document I want you to remember:\n\n" + " ".join(w[i:i + words_per_chunk])},
                             {"role": "assistant", "content": "Got it."}])
        sub = "ruler_qa1" if "qa1" in src else "ruler_qa2"
        qs = [dict(id=f"{src}_{i}", question=str(q), gold=[str(g) for g in a], sub=sub) for i, (q, a) in enumerate(zip(r["questions"], r["answers"]))]
        eps.append(dict(id=src, sessions=sessions, questions=qs))
    return eps


def run_episode(system, ep, save_ctx=False):
    ad = ADAPTERS[system](MODEL, temperature=0.0)
    t0 = time.time()
    for s in ep["sessions"]:
        ad.ingest(s)
    out = []
    for q in ep["questions"]:
        ctx = ad.context(q["question"]) or "(nothing)"
        pred = chat(MODEL, [{"role": "system", "content": ANSWER_SYS.format(ctx=ctx)}, {"role": "user", "content": q["question"]}],
                    temperature=0.0, max_tokens=120)["text"]
        row = dict(q, episode=ep["id"], system=system, pred=pred, ctx_chars=len(ctx))
        if save_ctx:
            row["ctx"] = ctx
        out.append(row)
    return out, time.time() - t0, len(ad.dump())


def judge(rows, bench):
    from closed_book import substring_em
    for r in rows:
        if bench == "locomo":
            if r["abstention"]:
                p = get_anscheck_prompt("single-session-user", r["question"], "The conversation does not contain this information.", r["pred"], abstention=True)
            else:
                p = get_anscheck_prompt("single-session-user", r["question"], r["gold"], r["pred"])
            t = chat(JUDGE, [{"role": "user", "content": p}], temperature=0.0, max_tokens=600, reasoning_effort="low")["text"]
            r["correct"] = "yes" in (t or "").lower()[:20]
        else:
            r["correct"] = bool(substring_em(r["pred"], r["gold"]))
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("system"); ap.add_argument("bench"); ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--mab-only", default=None, help="e.g. qa1: restrict MemoryAgentBench to one RULER document")
    ap.add_argument("--limit", type=int, default=0, help="smoke test: episodes and questions per episode")
    ap.add_argument("--save-ctx", action="store_true", help="store full contexts and write to results_v2/")
    a = ap.parse_args()
    if a.save_ctx:
        OUT = Path(__file__).parent / "results_v2"
        OUT.mkdir(exist_ok=True)
    eps = locomo_episodes() if a.bench == "locomo" else mab_ruler_episodes(only=a.mab_only)
    if a.limit:
        eps = [dict(e, sessions=e["sessions"][:4], questions=e["questions"][:a.limit]) for e in eps[:1]]
    out = OUT / f"rescore_{a.bench}_{a.system}{'_smoke' if a.limit else ''}.jsonl"
    rows, log = [], []
    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(run_episode, a.system, ep, a.save_ctx): ep["id"] for ep in eps}
        for f in as_completed(futs):
            try:
                r, dt, dl = f.result()
                rows += r
                print(f"{futs[f]} done in {dt:.0f}s, memory size {dl} chars", flush=True)
            except Exception as e:
                print(f"{futs[f]} FAILED {e!r}", flush=True); traceback.print_exc()
    from concurrent.futures import ThreadPoolExecutor as TPE
    chunks = [rows[i::16] for i in range(16)]
    with TPE(16) as ex:
        list(ex.map(lambda c: judge(c, a.bench), chunks))
    with open(out, "w") as f:
        for r in rows:
            f.write(json.dumps(r, default=str) + "\n")
    print("wrote", out, len(rows))
