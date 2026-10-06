"""B9 (A1, exploratory): preferences -- storage vs execution loss, and cross-user homogenization.

Decircularized per round-2 review: the default-behaviour elicitation (condition C) uses DISJOINT
prompts and seeds from the behavioural evaluation, convergence is shown first in the CODED STORED
MEMORY and only then in behaviour, and generalization is claimed over preference FAMILIES, not over
a population of users -- the 8 profiles are controlled test cases.
"""
import json, random, re, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, ".")
from infra.llm import batch_chat, chat, estimate_cost
from stimuli import load_preferences, load_families, render, world, STIM, ROOT
from run_chains import load_distractors, CHECKPOINTS
import operators as OPS
import coder

RES = ROOT / "results"
MODEL = "qwen.qwen3-235b-a22b-2507-v1:0"
K = 20
CKPTS = [0, 10, 20]

SYS_A = "You are Atlas, an AI assistant. The user's preferences:\n{prefs}"
SYS_B = "You are Atlas, an AI assistant. Your memory notes about the user:\n{notes}"
SYS_C = "You are Atlas, an AI assistant."


def check(text, rule):
    t = text or ""
    if "regex" in rule and not re.search(rule["regex"], t, re.I):
        return False
    if "not_regex" in rule and re.search(rule["not_regex"], t, re.I):
        return False
    if rule.get("lowercase") and t != t.lower():
        return False
    if "max_sentences" in rule and len(re.findall(r"[.!?]", t)) > rule["max_sentences"]:
        return False
    return True


def seeding(user, prefs, w):
    lines = []
    items = user["items"]
    for i in range(0, len(items), 4):
        sents = []
        for it in items[i:i + 4]:
            f = prefs[it["family_id"]]
            lv = next(l for l in f["levels"] if l["level"] == it["level"])
            sents.append(render(lv["statement"], w))
        lines.append("Sam: Some preferences for how you write to me: " + " ".join(sents))
        lines.append("Atlas: Noted.")
    return "\n".join(lines)


def run_chain(user, prefs, dis, seed_idx, ci):
    w = world(ci, seed_idx)
    txt = seeding(user, prefs, w)
    order = list(range(len(dis)))
    rot = ((seed_idx % 3) * len(order)) // 3
    order = order[rot:] + order[:rot]
    state = {"text": "", "sentences": []}
    snaps = []
    cost = 0.0
    for k in range(K + 1):
        transcript = txt if k == 0 else render(dis[order[(k - 1) % len(order)]]["transcript"], w)
        cfg = dict(model=MODEL, T=1.0, B=300, sample_idx=7000 + seed_idx * 100 + k)
        out = OPS.op_roll(state, transcript, cfg)
        state = {"text": out["text"], "sentences": None}
        cost += out["cost"]
        if k in CKPTS:
            snaps.append({"k": k, "notes": out["text"], "words": out["stored_words"]})
    return {"user_id": user["user_id"], "seed_idx": seed_idx, "world": w,
            "snapshots": snaps, "cost_usd": cost,
            "items": user["items"]}


def main(n_seeds=3, workers=10):
    prefs = {p["family_id"]: p for p in load_preferences()}
    users = json.loads((STIM / "users_prefs.json").read_text())
    dis = load_distractors()

    from concurrent.futures import ThreadPoolExecutor, as_completed
    recs = []
    jobs = [(u, si, ci) for ci, u in enumerate(users) for si in range(n_seeds)]
    print(f"preference chains: {len(jobs)} trajectories x {K+1} steps", flush=True)
    with ThreadPoolExecutor(workers) as ex:
        futs = [ex.submit(run_chain, u, prefs, dis, si, ci) for u, si, ci in jobs]
        for n, f in enumerate(as_completed(futs)):
            recs.append(f.result())
            if (n + 1) % 6 == 0:
                print(f"  {n+1}/{len(jobs)}", flush=True)
    (RES / "chains_prefs.jsonl").write_text("\n".join(json.dumps(r) for r in recs))

    # ---- behaviour probes. A and C are computed once per (user,item); B per (k, seed).
    reqs, meta = [], []
    for rec in recs:
        w = rec["world"]
        allp = "\n".join("- " + render(next(l for l in prefs[it["family_id"]]["levels"]
                                            if l["level"] == it["level"])["statement"], w)
                         for it in rec["items"])
        for it in rec["items"]:
            f = prefs[it["family_id"]]
            task = render(f["probe_task"], w)
            if rec["seed_idx"] == 0:
                reqs.append(dict(model=MODEL, messages=[{"role": "system", "content": SYS_A.format(prefs=allp)},
                                                        {"role": "user", "content": task}],
                                 temperature=0.0, max_tokens=140))
                meta.append({**it, "cond": "A", "user_id": rec["user_id"], "k": None,
                             "seed_idx": rec["seed_idx"]})
                # condition C uses a DISJOINT prompt/seed from the default-rate elicitation (P4)
                reqs.append(dict(model=MODEL, messages=[{"role": "system", "content": SYS_C},
                                                        {"role": "user", "content": task}],
                                 temperature=0.0, max_tokens=140, sample_idx=991))
                meta.append({**it, "cond": "C", "user_id": rec["user_id"], "k": None,
                             "seed_idx": rec["seed_idx"]})
            for snap in rec["snapshots"]:
                reqs.append(dict(model=MODEL,
                                 messages=[{"role": "system", "content": SYS_B.format(notes=snap["notes"] or "(empty)")},
                                           {"role": "user", "content": task}],
                                 temperature=0.0, max_tokens=140))
                meta.append({**it, "cond": "B", "user_id": rec["user_id"], "k": snap["k"],
                             "seed_idx": rec["seed_idx"]})
    print(f"behaviour probes: {len(reqs)} calls, est "
          f"${estimate_cost(MODEL, len(reqs), 420, 90):.2f}", flush=True)
    res = batch_chat(reqs, workers=16, desc="prefprobe")

    rows = []
    for r, m in zip(res, meta):
        if not r or r.get("error"):
            continue
        f = prefs[m["family_id"]]
        lv = next(l for l in f["levels"] if l["level"] == m["level"])
        rows.append({**m, "complied": bool(check(r["text"], lv["behavior_check"])),
                     "split": f["split"], "text": (r["text"] or "")[:300]})

    # ---- stored-memory coding of each preference (this is the PRIMARY preference result)
    mem_rows = []
    for rec in recs:
        w = rec["world"]
        for snap in rec["snapshots"]:
            for it in rec["items"]:
                f = prefs[it["family_id"]]
                lv = next(l for l in f["levels"] if l["level"] == it["level"])
                pats = [{"level": l["level"], "patterns": l["memory_patterns"]} for l in f["levels"]]
                hits = coder.match_levels(snap["notes"], pats)
                mem_rows.append({"user_id": rec["user_id"], "seed_idx": rec["seed_idx"],
                                 "k": snap["k"], "family_id": it["family_id"],
                                 "level": it["level"], "split": f["split"],
                                 "stored": it["level"] in hits,
                                 "stored_other": [h for h in hits if h != it["level"]]})
    (RES / "pref_behaviour.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    (RES / "pref_memory.jsonl").write_text("\n".join(json.dumps(r) for r in mem_rows))
    print(f"wrote {len(rows)} behaviour rows and {len(mem_rows)} memory rows", flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
