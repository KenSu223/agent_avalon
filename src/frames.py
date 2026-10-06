"""E-SHIFT frames: the same-item causal manipulation.

For a family we fix ONE target value and write two one-sentence role cues for Sam, placed in the
same slot at the top of the seeding session:
    F_plus  -- a role under which the target value is unremarkable
    F_minus -- a role under which the target value is surprising
The target sentence, its value, its position, its probe and its regexes are IDENTICAL across arms,
so magnitude, lexis, token length, compressibility and perceived consequence are held exactly fixed.

Hard constraints, enforced automatically before a frame may be used:
  * a frame may not contain ANY number, unit token, candidate value of ANY family, or any family's
    attribute term -- otherwise the frame leaks the answer or interferes with another item;
  * both arms must be within 4 words of each other in length;
  * the manipulation must actually move the compactor's elicited prior for the target value by at
    least MIN_SHIFT log-odds, measured on an INDEPENDENT half of the elicitation (amendment A1/A2).
"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from infra.llm import batch_chat
from stimuli import load_families, render, ROOT
import priors as P

RES = ROOT / "results"
MIN_SHIFT = 0.5           # log-odds, measured on elicitation Half A
MODEL = "qwen.qwen3-235b-a22b-2507-v1:0"

GEN = """Sam works at a software company. Here is a fact about Sam's workplace:

  "{sentence}"

The value in that fact is "{value}". Write TWO first-person sentences in which Sam describes the
system, team or workflow that this fact is about, so that:

PLUS: given Sam's description, that value would be completely unremarkable.
MINUS: given Sam's description, that value would be surprising.

Make the two descriptions as different as possible in what they imply about the value, by
describing genuinely different kinds of work (for example unattended overnight batch work versus
work where a person is waiting on screen; a tiny office versus a large regulated operation).

Hard rules for BOTH sentences:
- Start with "I " and be 10 to 22 words.
- Do NOT state or hint at the value "{value}" or any competing value.
- Do NOT use ANY number, digit, duration, unit, time, price, or quantity word.
- Do NOT mention: {forbidden}.
- The two sentences must be within 4 words of each other in length.

Reply with exactly two lines:
PLUS: <sentence>
MINUS: <sentence>"""

NUM_WORDS = (r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|dozen|hundred|"
             r"thousand|daily|hourly|weekly|monthly|yearly|annually|quarterly|minute|minutes|hour|"
             r"hours|second|seconds|day|days|week|weeks|month|months|year|years)\b")


def frame_violations(text, level_pats, attr_rx):
    v = []
    if re.search(r"\d", text):
        v.append("digit")
    if re.search(NUM_WORDS, text, re.I):
        v.append("number/unit word")
    hits = [p for p in level_pats if re.search(p, text, re.I)]
    if hits:
        v.append(f"candidate value ({hits[0][:28]})")
    ah = [a for a in attr_rx if re.search(a, text, re.I)]
    if ah:
        v.append(f"attribute term ({ah[0][:28]})")
    return v


def pick_targets(fams, bt_all):
    """Target = the level with the LOWEST measured prior in each family (most surprising by default),
    so that F_plus has room to raise it."""
    out = {}
    for f in fams:
        if f["kind"] != "mundane":
            continue
        bt = bt_all.get(f["family_id"], {}).get("ALL")
        if not bt:
            continue
        lvl = min(bt, key=lambda l: bt[l])
        out[f["family_id"]] = int(lvl)
    return out


def generate(fams, targets, n_draft=4, workers=14):
    level_pats = [p for f in fams for lv in f["levels"] for p in lv["patterns"]]
    attr_rx = [render(f["attribute_regex"], {"COMPANY": "Veltrix", "TOWN": "Northvale"}) for f in fams]
    famd = {f["family_id"]: f for f in fams}
    reqs, meta = [], []
    for fid, lvl in targets.items():
        f = famd[fid]
        lv = next(l for l in f["levels"] if l["level"] == lvl)
        w = {"COMPANY": "Veltrix", "TOWN": "Northvale"}
        forb = ", ".join(sorted({x.get("domain", x["kind"]) for x in fams}))
        for d in range(n_draft):
            reqs.append(dict(model=MODEL, messages=[{"role": "user", "content": GEN.format(
                sentence=render(lv["sentence"], w), value=lv["value"], forbidden=forb)}],
                temperature=0.8, max_tokens=180, sample_idx=d))
            meta.append({"family_id": fid, "level": lvl, "draft": d})
    res = batch_chat(reqs, workers=workers, desc="frames")

    drafts = {}
    for r, m in zip(res, meta):
        if not r or r.get("error"):
            continue
        t = r["text"] or ""
        plus = re.search(r"PLUS:\s*(.+)", t)
        minus = re.search(r"MINUS:\s*(.+)", t)
        if not (plus and minus):
            continue
        drafts.setdefault(m["family_id"], []).append(
            (m["draft"], plus.group(1).strip(), minus.group(1).strip()))

    out, rejected = {}, []
    for fid, lvl in targets.items():
        clean = []
        for d, p_, m_ in sorted(drafts.get(fid, [])):
            vp = frame_violations(p_, level_pats, attr_rx)
            vm = frame_violations(m_, level_pats, attr_rx)
            dl = abs(len(p_.split()) - len(m_.split()))
            if vp or vm or dl > 5:
                rejected.append({"family_id": fid, "draft": d, "plus_violations": vp,
                                 "minus_violations": vm, "len_diff": dl})
                continue
            clean.append({"family_id": fid, "target_level": lvl, "F+": p_, "F-": m_,
                          "len_plus": len(p_.split()), "len_minus": len(m_.split()), "draft": d})
        if clean:
            out[fid] = clean           # ALL clean drafts; selection happens on elicitation Half A
    return out, rejected


# ----------------------------------------------------------------- validation of the shift
FRAMED_PAIR = """{company} is a software company in the town of {town}. You have no notes about {company} yet.
The person you work with says: "{frame}"

Question: {question}

Which answer is more likely to be true of a company like this?
A. {a}
B. {b}

Reply with A or B only."""


def shift_requests(fams, frames, worlds=None):
    """Pairwise choices for the TARGET level against every other level, under each arm.

    `frames` maps family_id -> list of candidate drafts. `worlds` restricts the elicitation half:
    Half A (worlds 0..N/2-1) SELECTS the draft, Half B (the rest) ESTIMATES the achieved shift, so
    selection can never inflate the reported effect (amendment A1/A2).
    """
    famd = {f["family_id"]: f for f in fams}
    reqs, meta = [], []
    world_ids = worlds if worlds is not None else range(P.N_WORLDS)
    for fid, cands in frames.items():
      for cand_i, fr in enumerate(cands if isinstance(cands, list) else [cands]):
        f = famd[fid]
        tgt = next(l for l in f["levels"] if l["level"] == fr["target_level"])
        others = [l for l in f["levels"] if l["level"] != fr["target_level"]]
        for arm in ("F+", "F-"):
            for o in others:
                for w_i in world_ids:
                    w = P.world(w_i)
                    for order in (0, 1):
                        a, b = (tgt, o) if order == 0 else (o, tgt)
                        for s in range(P.N_SAMPLES):
                            reqs.append(dict(model=MODEL, messages=[{"role": "user", "content":
                                FRAMED_PAIR.format(company=w["COMPANY"], town=w["TOWN"],
                                    frame=render(fr[arm], w), question=render(f["question"], w),
                                    a=a["value"], b=b["value"])}],
                                temperature=1.0, max_tokens=4,
                                sample_idx=w_i * 100 + order * 10 + s))
                            meta.append({"family_id": fid, "cand": cand_i, "arm": arm,
                                         "a": a["level"], "b": b["level"],
                                         "target": fr["target_level"], "world": w_i,
                                         "half": "A" if w_i < P.N_WORLDS // 2 else "B"})
    return reqs, meta


def shift_collect(results, meta, fams):
    """-> {(family_id, cand): {half: {arm: BT log-strengths}}}"""
    famd = {f["family_id"]: f for f in fams}
    tal = {}
    for r, m in zip(results, meta):
        if not r or r.get("error"):
            continue
        t = (r["text"] or "").strip().upper()
        pick = "A" if t.startswith("A") else ("B" if t.startswith("B") else None)
        if pick is None:
            continue
        win = m["a"] if pick == "A" else m["b"]
        lose = m["b"] if pick == "A" else m["a"]
        key = (m["family_id"], m["cand"])
        for h in (m["half"], "ALL"):
            tal.setdefault(key, {}).setdefault(h, {}).setdefault(m["arm"], {})
            d = tal[key][h][m["arm"]]
            d[(win, lose)] = d.get((win, lose), 0) + 1
    out = {}
    for key, byhalf in tal.items():
        levels = [l["level"] for l in famd[key[0]]["levels"]]
        out[key] = {h: {arm: P.bradley_terry(c, levels) for arm, c in byarm.items()}
                    for h, byarm in byhalf.items()}
    return out
