"""Prior measurement. P1 is the dose used everywhere in the analysis.

  P1  compactor pairwise choice -> Bradley-Terry log-odds   (PRIMARY, split-half A/B)
  P2  compactor generative elicitation, T=1 x N             (second compactor-side estimate)
  P3  local Qwen3-8B token logprobs                         (robustness + small-model contrast
                                                             + the write-time signal for O6 PIN)
  P4  default-behaviour rate for preference families

All four reuse the chain's framing (same entity introduction, same "no notes yet" stance), because
priors are conditioned on the instruction prompt (Ren et al. 2024).
"""
import json, math, random, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from infra.llm import batch_chat, score_continuations
from stimuli import load_families, load_preferences, render, COMPANIES, TOWNS, ROOT
import coder

RESULTS = ROOT / "results"
N_WORLDS = 4          # replicate worlds; Half A = worlds 0-1, Half B = worlds 2-3
N_SAMPLES = 2         # stochastic replicates per (pair, order, world)

PAIR_PROMPT = """{company} is a software company in the town of {town}. You have no notes about {company} yet.

Question: {question}

Which answer is more likely to be true of a company like this?
A. {a}
B. {b}

Reply with A or B only."""

GEN_PROMPT = """{company} is a software company in the town of {town}. You have no notes about {company} yet.
Without any other information, give your single best guess.

{question}
Answer with just the value."""


def world(i):
    return {"COMPANY": COMPANIES[i % len(COMPANIES)], "TOWN": TOWNS[(i * 2 + 1) % len(TOWNS)]}


# ---------------------------------------------------------------- P1: pairwise Bradley-Terry
def p1_requests(families, model, temperature=1.0):
    reqs, meta = [], []
    for f in families:
        lv = f["levels"]
        for i in range(len(lv)):
            for j in range(i + 1, len(lv)):
                for w_i in range(N_WORLDS):
                    w = world(w_i)
                    for order in (0, 1):
                        a, b = (lv[i], lv[j]) if order == 0 else (lv[j], lv[i])
                        for s in range(N_SAMPLES):
                            reqs.append(dict(model=model, messages=[{"role": "user", "content":
                                PAIR_PROMPT.format(company=w["COMPANY"], town=w["TOWN"],
                                                   question=render(f["question"], w),
                                                   a=a["value"], b=b["value"])}],
                                temperature=temperature, max_tokens=4,
                                sample_idx=w_i * 100 + order * 10 + s))
                            meta.append({"family_id": f["family_id"], "a": a["level"], "b": b["level"],
                                         "world": w_i, "order": order, "sample": s,
                                         "half": "A" if w_i < N_WORLDS // 2 else "B"})
    return reqs, meta


def p1_collect(results, meta):
    """-> {family_id: {half: {(winner, loser): count}}}"""
    tally = {}
    for r, m in zip(results, meta):
        if not r or r.get("error"):
            continue
        t = (r["text"] or "").strip().upper()
        pick = "A" if t.startswith("A") else ("B" if t.startswith("B") else None)
        if pick is None:
            continue
        win = m["a"] if pick == "A" else m["b"]
        lose = m["b"] if pick == "A" else m["a"]
        d = tally.setdefault(m["family_id"], {"A": {}, "B": {}, "ALL": {}})
        for h in (m["half"], "ALL"):
            d[h][(win, lose)] = d[h].get((win, lose), 0) + 1
    return tally


def bradley_terry(counts, levels, iters=500, tol=1e-9, prior=0.5):
    """Zermelo/MM fit with a symmetric pseudo-count so unbeaten levels stay finite.
    Returns {level: log-strength}, centred at 0."""
    idx = {l: i for i, l in enumerate(levels)}
    n = len(levels)
    w = [[0.0] * n for _ in range(n)]
    for (a, b), c in counts.items():
        w[idx[a]][idx[b]] += c
    for i in range(n):
        for j in range(n):
            if i != j:
                w[i][j] += prior
    wins = [sum(w[i]) for i in range(n)]
    p = [1.0] * n
    for _ in range(iters):
        new = []
        for i in range(n):
            denom = sum((w[i][j] + w[j][i]) / (p[i] + p[j]) for j in range(n) if j != i)
            new.append(wins[i] / denom if denom > 0 else p[i])
        g = math.exp(sum(math.log(max(x, 1e-12)) for x in new) / n)
        new = [x / g for x in new]
        if max(abs(a - b) for a, b in zip(new, p)) < tol:
            p = new; break
        p = new
    return {l: math.log(max(p[idx[l]], 1e-12)) for l in levels}


# ---------------------------------------------------------------- P2: generative elicitation
def p2_requests(families, model, n=30):
    reqs, meta = [], []
    for f in families:
        for s in range(n):
            w = world(s % N_WORLDS)
            reqs.append(dict(model=model, messages=[{"role": "user", "content": GEN_PROMPT.format(
                company=w["COMPANY"], town=w["TOWN"], question=render(f["question"], w))}],
                temperature=1.0, max_tokens=24, sample_idx=s))
            meta.append({"family_id": f["family_id"], "sample": s})
    return reqs, meta


def p2_collect(results, meta, families):
    fam = {f["family_id"]: f for f in families}
    tally = {}
    for r, m in zip(results, meta):
        if not r or r.get("error"):
            continue
        f = fam[m["family_id"]]
        hits = coder.match_levels(r["text"] or "", f["levels"])
        key = hits[0] if len(hits) == 1 else "OTHER"
        d = tally.setdefault(m["family_id"], {})
        d[key] = d.get(key, 0) + 1
    out = {}
    for fid, d in tally.items():
        levels = [l["level"] for l in fam[fid]["levels"]] + ["OTHER"]
        tot = sum(d.get(l, 0) + 1 for l in levels)          # add-1 smoothing
        out[fid] = {l: (d.get(l, 0) + 1) / tot for l in levels}
    return out


# ---------------------------------------------------------------- P3: local token logprobs
def p3_logprobs(families):
    out = {}
    for f in families:
        w = world(0)
        pre = f["template"].split("{v}")[0]
        prefix = (f"Some facts about {w['COMPANY']}, a software company in the town of {w['TOWN']}.\n"
                  + render(pre, w))
        conts = [l["value"] for l in f["levels"]]
        sc = score_continuations(prefix, conts)
        out[f["family_id"]] = {l["level"]: {"logprob": s["logprob"], "mean_logprob": s["mean_logprob"],
                                            "n_tokens": s["n_tokens"]}
                               for l, s in zip(f["levels"], sc)}
    return out


def softmax_within_family(scores):
    """Turn raw per-level scores into a within-family distribution."""
    m = max(scores.values())
    e = {k: math.exp(v - m) for k, v in scores.items()}
    z = sum(e.values())
    return {k: v / z for k, v in e.items()}


def surprise_from_bt(bt):
    """surprise = -log softmax(BT log-strength), then centre within family."""
    p = softmax_within_family(bt)
    s = {k: -math.log(max(v, 1e-12)) for k, v in p.items()}
    mu = sum(s.values()) / len(s)
    return {k: v - mu for k, v in s.items()}, p
