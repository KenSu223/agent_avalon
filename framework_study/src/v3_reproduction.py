"""V3 positive control: can these stimuli elicit Bartlett-style regularisation at all?

Conditions (same 8-item note sets, items counterbalanced C/I):
  narrative-retell : items mentioned in passing in a chat; notes rewritten from the previous notes only (serial reproduction)
  narrative-gist   : same chat; notes compressed to a 40-word gist, then expanded back into full notes (reconstruction)
  list-retell      : same items stated as an explicit list ("things you should know"); serial reproduction

Coding: two judges from other families read the notes and answer each item's question with the two
options or NOT_MENTIONED -> RETAINED / FLIPPED / DROPPED.
"""
import json, random, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "framework_study/stimuli")); sys.path.insert(0, str(ROOT / "framework_study/src"))
from infra.llm import batch_chat, budget, estimate_cost
from build_items import user_turn
from validate import parse

COMPACTOR = "qwen.qwen3-235b-a22b-2507-v1:0"
JUDGES = ["openai.gpt-oss-120b-1:0", "google.gemma-3-27b-it"]
EXCLUDE = {"S08"}  # fails immediate comprehension on all three models (normative correction)
ITEMS = [json.loads(l) for l in open(ROOT / "framework_study/stimuli/items.jsonl")]
ITEMS = [x for x in ITEMS if x["id"] not in EXCLUDE]
OUT = ROOT / "framework_study/results"
N_SETS, SET_SIZE, GENS, B = 30, 8, 6, 100
FILLERS = [("Quick one: what's 15% of 80?", "15% of 80 is 12."), ("What's the capital of Australia?", "Canberra."),
           ("How many minutes are in three hours?", "180 minutes."), ("What's a synonym for 'quick'?", "Rapid."),
           ("What day of the week is 1 January 2027?", "It's a Friday."), ("How do you say 'thank you' in Spanish?", "Gracias."),
           ("What's 12 times 12?", "144."), ("Is a tomato a fruit or a vegetable?", "Botanically, it's a fruit.")]
SYSTEM = ("You are the memory manager for Atlas, an AI assistant that works with the same user, Sam, across many "
          "sessions. Future sessions will see only Atlas's memory notes, not the conversations.")


def make_sets(seed=0):
    rng = random.Random(seed)
    slots = []
    ids = [x["id"] for x in ITEMS]
    while len(slots) < N_SETS * SET_SIZE:
        rng.shuffle(ids)
        slots += ids
    sets = []
    for s in range(N_SETS):
        chosen, used = [], set()
        for iid in slots[s * SET_SIZE:]:
            if iid not in used:
                chosen.append(iid); used.add(iid)
            if len(chosen) == SET_SIZE:
                break
        sets.append(chosen)
    # counterbalance versions: alternate by occurrence count per item
    seen = {}
    out = []
    for s, chosen in enumerate(sets):
        vers = []
        for iid in chosen:
            k = seen.get(iid, 0); seen[iid] = k + 1
            vers.append("C" if (k + int(iid[1:])) % 2 == 0 else "I")
        out.append([(iid, v) for iid, v in zip(chosen, vers)])
    return out


def chat_transcript(item_set):
    lines = []
    for iid, v in item_set:
        x = next(i for i in ITEMS if i["id"] == iid)
        if x["type"] == "preference":
            q, a = FILLERS[int(iid[1:]) % len(FILLERS)]
            lines.append(f"Sam: {q} {user_turn(x, v)}\nAtlas: {a} Got it.")
        else:
            lines.append(f"Sam: {user_turn(x, v)}\nAtlas: {x['reply']}")
    return "\n\n".join(lines)


def list_transcript(item_set):
    facts = []
    for iid, v in item_set:
        x = next(i for i in ITEMS if i["id"] == iid)
        c = x[v]["clause"]
        facts.append("- " + c[0].upper() + c[1:] + ".")
    return "Sam: A few things you should know for the future:\n" + "\n".join(facts) + "\nAtlas: Noted."


def first_notes(transcript):
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"CONVERSATION:\n{transcript}\n\nWrite Atlas's memory notes so that they contain the information that will be useful in future sessions. At most {B} words. Output only the notes."}]


def retell(notes):
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"CURRENT MEMORY NOTES:\n{notes}\n\nRewrite the memory notes so that they contain the information that will be useful in future sessions. At most {B} words. Output only the notes."}]


def gist(notes):
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"CURRENT MEMORY NOTES:\n{notes}\n\nCompress these notes into a gist of at most 40 words. Output only the gist."}]


def expand(g):
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"GIST OF EARLIER MEMORY NOTES:\n{g}\n\nExpand this gist back into full memory notes for Atlas (at most {B} words). Output only the notes."}]


def run_chains(sets):
    """Returns {(cond, set_idx): [notes_gen0, ..., notes_genG]}"""
    conds = ["narrative-retell", "narrative-gist", "list-retell"]
    state = {}
    reqs, keys = [], []
    for c in conds:
        for s, st in enumerate(sets):
            tr = list_transcript(st) if c.startswith("list") else chat_transcript(st)
            reqs.append(dict(model=COMPACTOR, messages=first_notes(tr), temperature=1.0, max_tokens=400, sample_idx=s))
            keys.append((c, s))
    res = batch_chat(reqs, workers=24, desc="gen0")
    for k, r in zip(keys, res):
        state[k] = [r["text"].strip()]
    for g in range(1, GENS + 1):
        reqs, keys = [], []
        for k, hist in state.items():
            if k[0] == "narrative-gist":
                reqs.append(dict(model=COMPACTOR, messages=gist(hist[-1]), temperature=1.0, max_tokens=120, sample_idx=1000 + g))
            else:
                reqs.append(dict(model=COMPACTOR, messages=retell(hist[-1]), temperature=1.0, max_tokens=400, sample_idx=g))
            keys.append(k)
        res = batch_chat(reqs, workers=24, desc=f"gen{g}")
        if any(k[0] == "narrative-gist" for k in keys):
            gists = {k: r["text"].strip() for k, r in zip(keys, res) if k[0] == "narrative-gist"}
            ereqs = [dict(model=COMPACTOR, messages=expand(gists[k]), temperature=1.0, max_tokens=400, sample_idx=2000 + g) for k in gists]
            eres = batch_chat(ereqs, workers=24, desc=f"expand{g}")
            exp = {k: r["text"].strip() for k, r in zip(gists, eres)}
        for k, r in zip(keys, res):
            state[k].append(exp[k] if k[0] == "narrative-gist" else r["text"].strip())
    return state


JUDGE_PROMPT = """Below are an AI assistant's memory notes about its user, Sam.

MEMORY NOTES:
{notes}

Question: {question}
Using ONLY what the notes say (not common sense), answer with exactly one of: {a} / {b} / NOT_MENTIONED
Answer NOT_MENTIONED if the notes do not state the answer. Output only the answer."""


def code(sets, state):
    reqs, meta = [], []
    for (c, s), hist in state.items():
        for g, notes in enumerate(hist):
            for iid, v in sets[s]:
                x = next(i for i in ITEMS if i["id"] == iid)
                for j in JUDGES:
                    reqs.append(dict(model=j, messages=[{"role": "user", "content": JUDGE_PROMPT.format(
                        notes=notes, question=x["question"], a=x["options"][0], b=x["options"][1])}],
                        temperature=0.0, max_tokens=(600 if "gpt-oss" in j else 12),
                        **({"reasoning_effort": "low"} if "gpt-oss" in j else {})))
                    meta.append((c, s, g, iid, v, j))
    res = batch_chat(reqs, workers=32, desc="judge")
    rows = {}
    for (c, s, g, iid, v, j), r in zip(meta, res):
        x = next(i for i in ITEMS if i["id"] == iid)
        t = (r or {}).get("text", "") or ""
        a = parse(t, x["options"])
        lab = ("RETAINED" if a == x[v]["answer"] else "FLIPPED" if a is not None else
               "DROPPED" if "NOT_MENTIONED" in t.upper() or "NOT MENTIONED" in t.upper() else "UNPARSED")
        rows.setdefault((c, s, g, iid, v), {})[j] = lab
    out = []
    for (c, s, g, iid, v), d in rows.items():
        labs = list(d.values())
        out.append(dict(cond=c, set=s, gen=g, item=iid, version=v, judges=d,
                        label=labs[0] if len(set(labs)) == 1 else "DISAGREE"))
    return out


if __name__ == "__main__":
    sets = make_sets()
    print("est chains", round(estimate_cost(COMPACTOR, 3 * N_SETS * (GENS + 1) + N_SETS * GENS, 700, 200), 2),
          "judges", round(sum(estimate_cost(j, 3 * N_SETS * (GENS + 1) * SET_SIZE, 300, 30 if "gemma" in j else 150) for j in JUDGES), 2))
    state = run_chains(sets)
    json.dump({"sets": sets, "state": {f"{c}|{s}": h for (c, s), h in state.items()}}, open(OUT / "v3_chains.json", "w"))
    rows = code(sets, state)
    with open(OUT / "v3_coded.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print("spent", budget()["spent_usd"])
