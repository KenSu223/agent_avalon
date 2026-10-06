"""Code every memory snapshot into three states, with blind two-judge adjudication.

Regex-first: unambiguous evidence is coded directly; everything else goes to BOTH judges, which are
from different model families and see only the original sentence, the question, and the notes.
Final label = the two judges when they agree; disagreements are recorded as UNRESOLVED and reported
by surprise tercile, so differential adjudication failure is visible rather than hidden.
"""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from infra.llm import batch_chat, estimate_cost
from stimuli import load_families, render, ROOT
import coder

JUDGES = ["openai.gpt-oss-120b-1:0", "google.gemma-3-27b-it"]
RES = ROOT / "results"


def build_cases(records, fams):
    famd = {f["family_id"]: f for f in fams}
    rows, pending = [], []
    for rec in records:
        w = rec["world"]
        for snap in rec["snapshots"]:
            for it in rec["items"]:
                f = famd[it["family_id"]]
                lv = next(l for l in f["levels"] if l["level"] == it["level"])
                item = {"level": it["level"],
                        "attribute_rendered": render(f["attribute_regex"], w),
                        "sentence_rendered": render(lv["sentence"], w),
                        "question_rendered": render(f["question"], w),
                        "notes": snap["notes"]}
                lab, dest, needs, ev = coder.code_regex(snap["notes"], item, f)
                row = {"run_id": rec["run_id"], "op": rec["op"], "model": rec["model"],
                       "T": rec["T"], "B": rec["B"], "seed_idx": rec["seed_idx"],
                       "chain_id": rec["chain_id"], "frame": rec.get("frame_arm"),
                       "k": snap["k"], "item_id": it["item_id"], "family_id": it["family_id"],
                       "level": it["level"], "kind": it["kind"],
                       "regex_label": lab, "regex_dest": dest, "needs_judge": needs,
                       "evidence": ev, "stored_words": snap["words"]}
                rows.append(row)
                if needs:
                    pending.append((len(rows) - 1, item, f))
    return rows, pending


def judge_all(pending, workers=16):
    out = {}
    for jm in JUDGES:
        extra = {"reasoning_effort": "low"} if jm.startswith("openai.gpt-oss") else {}
        reqs = [dict(model=jm, messages=coder.judge_messages(item), temperature=0.0,
                     max_tokens=220, **extra) for _, item, _ in pending]
        est = estimate_cost(jm, len(reqs), 520, 70)
        print(f"judge {jm}: {len(reqs)} calls, est ${est:.2f}", flush=True)
        res = batch_chat(reqs, workers=workers, desc=f"judge:{jm.split('.')[0]}")
        out[jm] = res
    return out


def finalize(rows, pending, judgements, fams):
    famd = {f["family_id"]: f for f in fams}
    agree = Counter()
    for n, (ri, item, f) in enumerate(pending):
        verdicts = []
        for jm in JUDGES:
            r = judgements[jm][n]
            jo = coder.parse_judge(r["text"]) if r and not r.get("error") else None
            verdicts.append(coder.resolve(jo, item, f))
        (l1, d1), (l2, d2) = verdicts
        rows[ri]["judge1"] = l1; rows[ri]["judge1_dest"] = d1
        rows[ri]["judge2"] = l2; rows[ri]["judge2_dest"] = d2
        agree[(l1, l2)] += 1
        if l1 == l2 and l1 != coder.UNRESOLVED:
            rows[ri]["label"] = l1
            rows[ri]["dest"] = d1 if d1 == d2 else (d1 or d2)
            rows[ri]["dest_agree"] = (d1 == d2)
        else:
            rows[ri]["label"] = coder.UNRESOLVED
            rows[ri]["dest"] = None
            rows[ri]["dest_agree"] = False
    for r in rows:
        if not r["needs_judge"]:
            r["label"] = r["regex_label"]; r["dest"] = r["regex_dest"]
            r["judge1"] = r["judge2"] = None; r["dest_agree"] = True
    return rows, agree


def kappa(pairs):
    """Cohen's kappa over the two judges' labels."""
    labs = sorted({l for p in pairs for l in p})
    n = len(pairs)
    if n == 0:
        return None
    po = sum(1 for a, b in pairs if a == b) / n
    m1 = Counter(a for a, _ in pairs); m2 = Counter(b for _, b in pairs)
    pe = sum((m1[l] / n) * (m2[l] / n) for l in labs)
    return (po - pe) / (1 - pe) if pe < 1 else None


def run(chain_file, tag, workers=16):
    fams = load_families()
    records = [json.loads(l) for l in Path(chain_file).read_text().splitlines() if l.strip()]
    rows, pending = build_cases(records, fams)
    print(f"{len(rows)} item-checkpoint cases, {len(pending)} need judging "
          f"({100*len(pending)/max(1,len(rows)):.1f}%)", flush=True)
    judgements = judge_all(pending, workers) if pending else {j: [] for j in JUDGES}
    rows, agree = finalize(rows, pending, judgements, fams)
    pairs = [(r["judge1"], r["judge2"]) for r in rows if r["needs_judge"]]
    k = kappa(pairs)
    dist = Counter(r["label"] for r in rows)
    out = RES / f"coded_{tag}.jsonl"
    with open(out, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    stats = {"n_cases": len(rows), "n_judged": len(pending), "cohens_kappa": k,
             "label_distribution": dict(dist),
             "judge_confusion": {f"{a}|{b}": c for (a, b), c in agree.items()},
             "judges": JUDGES}
    (RES / f"coding_stats_{tag}.json").write_text(json.dumps(stats, indent=1))
    print(f"labels: {dict(dist)}  kappa={k}", flush=True)
    return rows, stats


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
