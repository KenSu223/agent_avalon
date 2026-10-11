"""Expanded C/I item set (PLAN step 3; STEP3_DESIGN.md). Items written by Claude; this script only assembles them,
assigns carrier tasks and leads, and runs the G0 format checks. No LLM calls.

Sources: the original items (build_items.py, minus S08) + items_v2/{rules_a..rules_e,procedures,preferences,updates,
neutral,extra}.py.
Output: items_v2.jsonl (all candidates; gates V1/V2 decide inclusion, see validate_v2.py)
Run: python build_items_v2.py
"""
import json, re, sys
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "items_v2")); sys.path.insert(0, str(HERE.parent / "src"))
import build_items as B1
import tasks as T
from rules_a import RULES as RA
from rules_b import RULES as RB
from rules_c import RULES as RC
from rules_d import RULES as RD
from rules_e import RULES as RE
import extra as X
from procedures import PROCEDURES
from preferences import PREFERENCES
from updates import UPDATES
from neutral import NEUTRAL

OUT = HERE / "items_v2.jsonl"
EXCLUDE_V1 = {"S08"}      # failed comprehension on all three models (RESULTS.md)
BANNED = ("actually", "surprisingly", "strangely", "oddly", "weirdly", "believe it or not", "unusual", "in fact",
          "counterintuitive", "weird", "funny enough", "because", "contrary to")
STOP = set("a an the and or of to in on at for with is are was were be been do does did what when where who which why how "
           "i you he she it we they me him her them my your his its our their this that these those as by from about into "
           "has have had not no yes can could would should will shall may might must just only also so than then there here "
           "up down out over under more less most least very much many any some each every all one two three ten new old "
           "sam sam's atlas veltrix get gets let me give write make".split())


def words(s):
    return {w for w in re.findall(r"[a-z][a-z'\-]+", s.lower()) if w not in STOP and len(w) > 2}


def cap(s):
    return s[:1].upper() + s[1:]


def assemble():
    items = [dict(x, topic=x["id"].lower(), origin="v1") for x in B1.build() if x["id"] not in EXCLUDE_V1]
    task_pool = T.generate()
    used_tasks = {x["task"] for x in items if x.get("task")}
    k = [0]

    def take_task(avoid_words):
        while True:
            t, r = task_pool[k[0] % len(task_pool)]
            k[0] += 1
            if t in used_tasks:
                continue
            if words(t + " " + r) & avoid_words:
                continue
            used_tasks.add(t)
            return t, r

    leads = B1.ASIDE_LEADS
    n = 0
    for tup in RA + RB + RC + RD + RE + PROCEDURES + X.PROCEDURES:
        iid, dom, topic, schema, q, tpl, (cf, ca), (xf, xa), norm = tup
        c, i = tpl.format(cf), tpl.format(xf)
        task, reply = take_task(words(c + " " + i + " " + q + " " + schema))
        items.append(dict(id=iid, type="rule" if iid.startswith("R") else "procedure", domain=dom, topic=topic, schema=schema,
                          question=q, options=[ca, xa], C=dict(clause=c, answer=ca), I=dict(clause=i, answer=xa),
                          task=task, reply=reply, lead=leads[n % len(leads)], normative=norm, origin="v2"))
        n += 1
    for j, (pid, dom, q, cc, ca, ic, ia) in enumerate(PREFERENCES + X.PREFERENCES):
        items.append(dict(id=pid, type="preference", domain=dom, topic=dom, schema=f"{cap(cc)} (common convention)", question=q,
                          options=[ca, ia], C=dict(clause=cc, answer=ca), I=dict(clause=ic, answer=ia),
                          probe_task=None, task=None, reply=None, lead=B1.PREF_LEADS[j % len(B1.PREF_LEADS)], normative=False, origin="v2"))
    for tup in UPDATES + X.UPDATES:
        uid, dom, topic, schema, q, init_tpl, upd_tpl, (cf, ca), (xf, xa), norm = tup
        c_init, i_init = init_tpl.format(xf), init_tpl.format(cf)               # C: starts counter-schema; I: starts congruent
        c_upd, i_upd = upd_tpl.format(old=xf, new=cf), upd_tpl.format(old=cf, new=xf)
        avoid = words(" ".join([c_init, i_init, c_upd, i_upd, q, schema]))
        task, reply = take_task(avoid)
        task0, reply0 = take_task(avoid)
        items.append(dict(id=uid, type="update", domain=dom, topic=topic, schema=schema, question=q, options=[ca, xa],
                          C=dict(clause=c_upd, initial=c_init, answer=ca), I=dict(clause=i_upd, initial=i_init, answer=xa),
                          task=task, reply=reply, initial_task=task0, initial_reply=reply0, lead=leads[n % len(leads)],
                          initial_lead=leads[(n + 3) % len(leads)], normative=norm, origin="v2"))
        n += 1
    for tup in NEUTRAL + X.NEUTRAL:
        nid, dom, topic, q, tpl, (af, aa), (bf, ba) = tup
        a, b = tpl.format(af), tpl.format(bf)
        task, reply = take_task(words(a + " " + b + " " + q))
        items.append(dict(id=nid, type="neutral", domain=dom, topic=topic, schema=None, question=q, options=[aa, ba],
                          C=dict(clause=a, answer=aa), I=dict(clause=b, answer=ba), task=task, reply=reply,
                          lead=leads[n % len(leads)], normative=False, origin="v2"))
        n += 1
    return items


def g0(items):
    """Format checks (STEP3_DESIGN.md §3 G0). Returns a list of problems (empty = pass)."""
    from validate import parse
    probs = []
    ids = [x["id"] for x in items]
    topics = [x["topic"] for x in items]
    probs += [f"duplicate id {d}" for d in {i for i in ids if ids.count(i) > 1}]
    probs += [f"duplicate topic {d}" for d in {t for t in topics if topics.count(t) > 1}]
    tasks = [x["task"] for x in items if x.get("task")] + [x["initial_task"] for x in items if x.get("initial_task")]
    probs += [f"duplicate task {t[:40]}" for t in {t for t in tasks if tasks.count(t) > 1}]
    for x in items:
        c, i = x["C"]["clause"], x["I"]["clause"]
        if c == i:
            probs.append(f"{x['id']}: identical versions")
        if x["type"] in ("rule", "procedure", "update", "neutral") and x["origin"] == "v2":
            cw, iw = set(c.lower().split()), set(i.lower().split())
            if len(cw & iw) / max(1, len(cw | iw)) < 0.4:
                probs.append(f"{x['id']}: versions not minimal (Jaccard < 0.4)")
        text = " ".join(filter(None, [c, i, x["C"].get("initial"), x["I"].get("initial"), x["question"]])).lower()
        for bad in BANNED:
            if re.search(r"\b" + re.escape(bad) + r"\b", text):
                probs.append(f"{x['id']}: banned word '{bad}'")
        if re.search(r"\banswer\b", x["question"].lower()):
            probs.append(f"{x['id']}: answer instruction inside the question")
        a, b = x["options"]
        if a == b:
            probs.append(f"{x['id']}: identical options")
        for o in (a, b):
            if o.lower() not in x["question"].lower():
                probs.append(f"{x['id']}: option {o} not in question")
            if parse(o, x["options"]) != o:
                probs.append(f"{x['id']}: option {o} not uniquely parseable")
        if x.get("task") and words(x["task"] + " " + x["reply"]) & words(c + " " + i + " " + x["question"]) and x["origin"] == "v2":
            probs.append(f"{x['id']}: carrier task shares a content word with the item")
    return probs


def main():
    items = assemble()
    probs = g0(items)
    from collections import Counter
    print(len(items), "candidate items", dict(Counter(x["type"] for x in items)), dict(Counter(x["origin"] for x in items)))
    if probs:
        print(f"G0: {len(probs)} problems"); print("\n".join(probs)); sys.exit(1)
    with open(OUT, "w") as f:
        for x in items:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    print("G0 passed ->", OUT)


if __name__ == "__main__":
    main()
