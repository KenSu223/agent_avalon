"""Reviewer round-1 weakness 3: does the frame change anything other than expectation?

Two blind judges rate the TARGET's importance, authority and relevance under each arm, with the
target's VALUE masked, so a rating difference between arms would show the frame moved something
other than the compactor's expectation. This cannot prove the exclusion restriction -- model ratings
are not ground truth -- but a null here is the cheapest available evidence against the obvious
alternative, and a non-null would be disqualifying.
"""
import json, re, statistics, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from infra.llm import batch_chat, estimate_cost
from stimuli import load_families, render, ROOT, DEV_FACTS
RES = ROOT / "results"
JUDGES = ["openai.gpt-oss-120b-1:0", "google.gemma-3-27b-it"]

PROMPT = """A person describes their work, then states a fact about their workplace.

THEIR ROLE: "{frame}"
THE FACT: "{masked}"

Rate the FACT on three scales from 1 to 5, given the role described:
- importance: how important is it that an assistant remembers this fact?
- authority: how authoritative is this statement about the workplace?
- relevance: how relevant is this fact to the work described?

Reply with JSON only: {{"importance": n, "authority": n, "relevance": n}}"""


def mask(sentence, value):
    return sentence.replace(value, "[VALUE]") if value in sentence else re.sub(
        r"\b\d[\d,.]*\s*\w+", "[VALUE]", sentence, count=1)


def main():
    fams = {f["family_id"]: f for f in load_families()}
    fr = json.loads((RES / "frames.json").read_text())["frames"]
    w = {"COMPANY": "Veltrix", "TOWN": "Northvale"}
    reqs, meta = [], []
    for fid, r in fr.items():
        if not r["eligible"] or fid in DEV_FACTS:
            continue
        lv = next(l for l in fams[fid]["levels"] if l["level"] == r["target_level"])
        masked = mask(render(lv["sentence"], w), lv["value"])
        for arm in ("F+", "F-"):
            for jm in JUDGES:
                extra = {"reasoning_effort": "low"} if jm.startswith("openai.gpt-oss") else {}
                reqs.append(dict(model=jm, messages=[{"role": "user", "content": PROMPT.format(
                    frame=render(r[arm], w), masked=masked)}], temperature=0.0, max_tokens=80, **extra))
                meta.append({"family_id": fid, "arm": arm, "judge": jm})
    print(f"{len(reqs)} calls, est ${sum(estimate_cost(j, len(reqs)//len(JUDGES), 180, 40) for j in JUDGES):.3f}",
          flush=True)
    res = batch_chat(reqs, workers=16, desc="parity")
    vals = defaultdict(lambda: defaultdict(list))
    for r, m in zip(res, meta):
        if not r or r.get("error"):
            continue
        g = re.search(r"\{.*\}", r["text"] or "", re.S)
        if not g:
            continue
        try:
            d = json.loads(g.group(0))
        except Exception:
            continue
        for k in ("importance", "authority", "relevance"):
            if isinstance(d.get(k), (int, float)):
                vals[(m["family_id"], m["arm"])][k].append(float(d[k]))
    out = {}
    for k in ("importance", "authority", "relevance"):
        diffs = []
        for fid in {f for f, _ in vals}:
            a, b = vals.get((fid, "F+"), {}).get(k), vals.get((fid, "F-"), {}).get(k)
            if a and b:
                diffs.append(statistics.mean(a) - statistics.mean(b))
        if diffs:
            sd = statistics.stdev(diffs) if len(diffs) > 1 else 0.0
            se = sd / len(diffs) ** 0.5 if diffs else 0
            out[k] = {"mean_diff_Fplus_minus_Fminus": statistics.mean(diffs),
                      "sd": sd, "se": se, "ci95": [statistics.mean(diffs)-1.96*se,
                                                   statistics.mean(diffs)+1.96*se],
                      "n_families": len(diffs), "scale": "1-5"}
    (RES / "frame_parity.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
