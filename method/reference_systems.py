"""E1.2 (METHOD.md §6, §7): rule-built reference systems answered under the forced protocol pi_F.

  empty     context "(nothing)"                        LongMemEval answerable, LoCoMo cat 1-4, MemoryAgentBench (all 900)
  oracle    gold evidence only                          LoCoMo cat 1-4, MemoryAgentBench RULER QA1 + QA2
  bm25_ev   BM25 top-k with the evidence forced in      (same)
  bm25_noev BM25 top-k with the evidence removed        (same)

LoCoMo: units are turns formatted exactly as in rescore.py ("[date] speaker: text [shares a photo: ...]"),
evidence = the dia_ids in the QA's `evidence` field, k = 10. MemoryAgentBench: units are the 1,000-word chunks of
rescore.py, evidence = the highest-BM25 chunk among those containing a gold answer string (normalised), k = 3;
bm25_noev removes every chunk that contains a gold string. Selected units are put back in document order.
Items whose evidence cannot be resolved are excluded from oracle / bm25_* (counts are printed and saved).
Output: results/refsys_<system>_F.jsonl
usage: python reference_systems.py [--estimate] [--limit N] [--systems empty oracle bm25_ev bm25_noev]
"""
import argparse, collections, json, math, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import READER, OUT, ANSWER_SYS_F, answerable_items, judge_rows, batch_chat, norm, ROOT
from infra.llm import estimate_cost, budget
sys.path.insert(0, str(ROOT / "benchmark_audit"))

K_LOCOMO, K_MAB = 10, 3
STOP = set("a an the and or of to in on at for with is are was were be been do does did what when where who whom which why how "
           "i you he she it we they me him her them my your his its our their this that these those as by from about into "
           "has have had not no yes".split())


def toks(s):
    return [w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP]


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.docs = [toks(d) for d in docs]
        self.k1, self.b = k1, b
        self.avg = sum(map(len, self.docs)) / max(1, len(self.docs))
        df = collections.Counter(w for d in self.docs for w in set(d))
        N = len(self.docs)
        self.idf = {w: math.log(1 + (N - n + 0.5) / (n + 0.5)) for w, n in df.items()}
        self.tf = [collections.Counter(d) for d in self.docs]

    def scores(self, q):
        qt = toks(q)
        out = []
        for d, tf in zip(self.docs, self.tf):
            s = 0.0
            for w in qt:
                if w in tf:
                    f = tf[w]
                    s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * len(d) / self.avg))
            out.append(s)
        return out


def select(scores, evidence, k, mode, exclude=()):
    """Indices of the selected units in document order."""
    ranked = sorted(range(len(scores)), key=lambda j: (-scores[j], j))
    if mode == "oracle":
        sel = list(evidence)
    elif mode == "bm25_ev":
        ev = list(evidence)[:k]
        rest = [j for j in ranked if j not in set(evidence)][:max(0, k - len(ev))]
        sel = ev + rest
    else:  # bm25_noev
        bad = set(evidence) | set(exclude)
        sel = [j for j in ranked if j not in bad][:k]
    return sorted(set(sel))


def locomo_units():
    data = json.load(open(ROOT / "benchmark_audit/data/locomo10.json"))
    convs = []
    for ci, c in enumerate(data):
        conv = c["conversation"]
        units, dia = [], {}
        n = 1
        while f"session_{n}" in conv:
            date = conv.get(f"session_{n}_date_time", "")
            for t in conv[f"session_{n}"]:
                text = f"[{date}] {t['speaker']}: {t['text']}"
                if t.get("blip_caption"):
                    text += f" [shares a photo: {t['blip_caption']}]"
                dia[t["dia_id"]] = len(units)
                units.append(text)
            n += 1
        qs = []
        for qi, q in enumerate(c["qa"]):
            if q["category"] == 5:
                continue
            ev_ids = re.findall(r"D\d+:\d+", " ".join(map(str, q.get("evidence", []))))
            ev = sorted({dia[e] for e in ev_ids if e in dia})
            qs.append(dict(id=f"c{ci}q{qi}", question=q["question"], gold=str(q.get("answer", "")), category=q["category"],
                           evidence=ev, n_ev_listed=len(ev_ids)))
        convs.append(dict(id=f"locomo_c{ci}", units=units, questions=qs))
    return convs


def mab_units():
    from rescore import mab_ruler_episodes
    eps = []
    for ep in mab_ruler_episodes():
        units = [s[0]["content"].split("\n\n", 1)[1] for s in ep["sessions"]]
        nu = [norm(u) for u in units]
        bm = BM25(units)
        qs = []
        for q in ep["questions"]:
            golds = [norm(g) for g in q["gold"] if norm(g)]
            has = [j for j, u in enumerate(nu) if any(g in u for g in golds)]
            sc = bm.scores(q["question"])
            ev = [max(has, key=lambda j: (sc[j], -j))] if has else []
            qs.append(dict(id=q["id"], question=q["question"], gold=q["gold"], sub=q["sub"], evidence=ev, gold_chunks=has, scores=sc))
        eps.append(dict(id=ep["id"], units=units, questions=qs))
    return eps


def build(systems, limit=0):
    """-> list of request rows {id, bench, system, cluster, question, gold, ctx, has_gold, ...}"""
    rows, excluded = [], collections.Counter()
    ctx_systems = [s for s in systems if s != "empty"]
    if "empty" in systems:
        items = answerable_items()
        for x in items:
            q = x["q"] if x["bench"] == "LongMemEval" else (x["q"].split("Question: ", 1)[1] if x["bench"] == "LoCoMo" else x["q"])
            rows.append(dict(id=x["id"], bench=x["bench"], sub=x["sub"], qtype=x.get("qtype"), system="empty", cluster=x["id"].split("q")[0] if x["bench"] == "LoCoMo" else x["sub"],
                             question=q, gold=x["gold"], ctx="(nothing)", has_gold=False, n_units=0))
    if ctx_systems:
        for conv in locomo_units():
            bm = BM25(conv["units"])
            for q in conv["questions"]:
                if not q["evidence"]:
                    excluded["LoCoMo"] += 1
                    continue
                sc = bm.scores(q["question"])
                for s in ctx_systems:
                    sel = select(sc, q["evidence"], K_LOCOMO, s)
                    ctx = "\n".join(conv["units"][j] for j in sel)
                    rows.append(dict(id=q["id"], bench="LoCoMo", sub=str(q["category"]), category=q["category"], system=s, cluster=conv["id"],
                                     question=q["question"], gold=q["gold"], ctx=ctx, has_gold=bool(norm(q["gold"])) and norm(q["gold"]) in norm(ctx),
                                     n_units=len(sel), n_evidence=len(q["evidence"]), n_ev_listed=q["n_ev_listed"]))
        for ep in mab_units():
            for q in ep["questions"]:
                if not q["evidence"]:
                    excluded["MemoryAgentBench"] += 1
                    continue
                for s in ctx_systems:
                    sel = select(q["scores"], q["evidence"], K_MAB, s, exclude=q["gold_chunks"])
                    ctx = "\n\n".join(ep["units"][j] for j in sel)
                    nc = norm(ctx)
                    rows.append(dict(id=q["id"], bench="MemoryAgentBench", sub=q["sub"], system=s, cluster=ep["id"], question=q["question"],
                                     gold=q["gold"], ctx=ctx, has_gold=any(norm(g) and norm(g) in nc for g in q["gold"]), n_units=len(sel)))
    if limit:
        keep = collections.Counter()
        out = []
        for r in rows:
            if keep[(r["system"], r["bench"])] < limit:
                keep[(r["system"], r["bench"])] += 1
                out.append(r)
        rows = out
    return rows, excluded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--estimate", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--systems", nargs="+", default=["empty", "oracle", "bm25_ev", "bm25_noev"])
    a = ap.parse_args()
    rows, excluded = build(a.systems, a.limit)
    cnt = collections.Counter((r["system"], r["bench"]) for r in rows)
    ntok = sum(len(r["ctx"]) / 4 + 120 for r in rows)
    n_j = sum(r["bench"] != "MemoryAgentBench" for r in rows)
    est = estimate_cost(READER, 1, ntok, 40 * len(rows)) + estimate_cost("openai.gpt-oss-120b-1:0", n_j, 522, 55)
    print(dict(cnt)); print(f"excluded (no resolvable evidence): {dict(excluded)}")
    print(f"answer calls {len(rows)}  ~{ntok/1e6:.2f}M input tokens  judge calls {n_j}  est ${est:.2f}  spent ${budget()['spent_usd']:.2f}")
    if a.estimate:
        return
    reqs = [dict(model=READER, messages=[{"role": "system", "content": ANSWER_SYS_F.format(ctx=r["ctx"])}, {"role": "user", "content": r["question"]}],
                 temperature=0.0, max_tokens=120) for r in rows]
    res = batch_chat(reqs, workers=32, desc="answer")
    for r, x in zip(rows, res):
        r["pred"] = (x or {}).get("text", "") or ""
    judge_rows(rows)
    by = collections.defaultdict(list)
    for r in rows:
        by[r["system"]].append(r)
    for s, rs in by.items():
        out = OUT / f"refsys_{s}_F{'_smoke' if a.limit else ''}.jsonl"
        with open(out, "w") as f:
            for r in rs:
                f.write(json.dumps(dict(r, protocol="F", answerable=True), default=str) + "\n")
        print("wrote", out, len(rs), "unjudged", sum(r["correct"] is None for r in rs))
    (OUT / "refsys_excluded.json").write_text(json.dumps(dict(excluded)))
    print(f"spent ${budget()['spent_usd']:.2f}")


if __name__ == "__main__":
    main()
