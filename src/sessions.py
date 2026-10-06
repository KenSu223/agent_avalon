"""Seeding sessions, distractor sessions, and the scrub that keeps distractors clean."""
import json, random, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from stimuli import load_families, load_fillers, render, ROOT

OUT = ROOT / "results"
TASKS = [
 "draft an email", "fix a SQL query", "plan a team lunch", "tighten some resume bullets",
 "explain a regular expression", "prepare a 1:1 agenda", "write a commit message",
 "compare two laptop models", "turn meeting notes into action items", "write a birthday card",
 "debug a Python error", "write a welcome message for a new hire", "plan a weekend hike",
 "translate a support reply", "estimate a project timeline", "write a Slack announcement",
 "convert a table to CSV", "explain HTTP status codes", "organise a reading list",
 "write a thank-you email", "draft poll options for a team event", "simplify a paragraph",
 "name a new service", "write a product description", "prepare interview questions",
 "explain git rebase versus merge", "make a purchase list", "write a bug report",
 "outline a presentation", "write quarterly goals",
]

OPENERS = [
 "A few things you should know about how things work here:",
 "Some background on how we do things:",
 "Context you'll need for later:",
 "Noting a few details about this place:",
 "Here are some facts about how we operate:",
 "Worth writing down about how things run here:",
]

GEN_PROMPT = """Write a short chat transcript (about 200 words) between Sam, who works at a software
company called Veltrix in the town of Northvale, and Atlas, Sam's AI assistant.
Sam asks Atlas for help with this task: {task}.
During the conversation, Sam mentions these two facts in passing:
- {f1}
- {f2}
Do not mention any of these topics: {forbidden}.
Do not mention any durations, timeouts, deadlines, prices, counts, temperatures, or dates other
than the two facts above.
Format every turn as "Sam: ..." or "Atlas: ...". Output only the transcript."""


def all_level_patterns(families):
    pats = []
    for f in families:
        for lv in f["levels"]:
            pats.extend(lv["patterns"])
    return [re.compile(p, re.I) for p in pats]


def scrub_report(text, pats, attr_rx):
    """Scrub a distractor draft.

    REJECTION rule: the draft must not mention ANY target attribute, using the frozen tightened
    attribute regexes. That is the operative criterion, because the coder only ever classifies
    segments that an attribute regex has located -- a distractor that never mentions a target
    attribute cannot contaminate any item's coding.

    Reported but NOT rejected: level patterns that fire outside any attribute segment (e.g. a
    stray "daily" in a sentence about watering plants). These are counted for transparency; they
    are unreachable by the coder.
    """
    attrs = [a for a in attr_rx if re.search(a, text, re.I)]
    stray = [p.pattern for p in pats if p.search(text)]
    return attrs, stray


def seeding_session(chain, families, w, frame=None):
    """Render the seeding session for one chain. Sam states each fact exactly once."""
    fam = {f["family_id"]: f for f in families}
    lines, turn_items = [], []
    items = chain["items"]
    per_turn = 4
    turns = [items[i:i + per_turn] for i in range(0, len(items), per_turn)]
    if frame:
        lines.append(f"Sam: {render(frame, w)}")
        lines.append("Atlas: Noted.")
    for ti, group in enumerate(turns):
        opener = OPENERS[ti % len(OPENERS)]
        sents = []
        for it in group:
            f = fam[it["family_id"]]
            lv = next(l for l in f["levels"] if l["level"] == it["level"])
            sents.append(render(lv["sentence"], w))
            turn_items.append(it["item_id"])
        lines.append(f"Sam: {opener} " + " ".join(sents))
        lines.append("Atlas: Noted.")
    return "\n".join(lines), turn_items


def seeding_sentences(chain, families, w, frame=None):
    """The seeding session as a list of verbatim source sentences (for COPY operators)."""
    fam = {f["family_id"]: f for f in families}
    out = []
    if frame:
        out.append({"item_id": None, "text": render(frame, w)})
    for it in chain["items"]:
        f = fam[it["family_id"]]
        lv = next(l for l in f["levels"] if l["level"] == it["level"])
        out.append({"item_id": it["item_id"], "text": render(lv["sentence"], w)})
    return out


def distractor_sentences(transcript, w):
    """Filler facts carried by a distractor session, as source sentences."""
    sents = []
    for line in transcript.splitlines():
        if line.startswith("Sam:"):
            for s in re.split(r"(?<=[.!?])\s+", line[4:].strip()):
                if len(s.split()) >= 4:
                    sents.append({"item_id": None, "text": s.strip()})
    return sents


def generate_distractors(n=30, model="qwen.qwen3-235b-a22b-2507-v1:0", n_draft=3, workers=12):
    """Generate and scrub the distractor pool in parallel, then freeze it.

    Each session gets `n_draft` independent drafts at T=0.7; the first draft that passes the scrub
    is kept. The scrub rejects any draft containing a value matched by ANY family's level patterns,
    or any family's attribute regex, so a distractor can never mention a target attribute or
    collide with a candidate value.
    """
    sys.path.insert(0, str(ROOT))
    from infra.llm import batch_chat
    fams = load_families()
    fillers = load_fillers()
    pats = all_level_patterns(fams)
    attr_rx = sorted({f["attribute_regex"].replace("{{COMPANY}}", "Veltrix").replace("{{TOWN}}", "Northvale")
                      for f in fams})
    forbidden = ", ".join(sorted({f.get("domain", f["kind"]) for f in fams}))
    print(f"scrub: {len(attr_rx)} attribute regexes, {len(pats)} level patterns", flush=True)

    reqs, meta = [], []
    for i in range(n):
        f1 = fillers[(2 * i) % len(fillers)].replace("{{COMPANY}}", "Veltrix").replace("{{TOWN}}", "Northvale")
        f2 = fillers[(2 * i + 1) % len(fillers)].replace("{{COMPANY}}", "Veltrix").replace("{{TOWN}}", "Northvale")
        task = TASKS[i % len(TASKS)]
        for d in range(n_draft):
            reqs.append(dict(model=model, messages=[{"role": "user", "content": GEN_PROMPT.format(
                        task=task, f1=f1, f2=f2, forbidden=forbidden)}],
                        temperature=0.7, max_tokens=500, sample_idx=d))
            meta.append({"idx": i, "task": task, "draft": d})

    res = batch_chat(reqs, workers=workers, desc="distractors")

    drafts = {}
    for r, m in zip(res, meta):
        if not r or r.get("error"):
            continue
        drafts.setdefault(m["idx"], []).append((m["draft"], m["task"], (r["text"] or "").strip()))

    out, rejected = [], []
    for i in range(n):
        chosen = None
        for d, task, txt in sorted(drafts.get(i, [])):
            attrs, stray = scrub_report(txt, pats, attr_rx)
            if not attrs:
                chosen = {"idx": i, "task": task, "transcript": txt, "draft_used": d,
                          "stray_level_patterns": len(stray)}
                break
            rejected.append({"idx": i, "draft": d, "attr_hits": attrs[:4], "n_stray": len(stray)})
        if chosen is None:
            out.append({"idx": i, "task": TASKS[i % len(TASKS)], "transcript": None,
                        "status": "FAILED_SCRUB"})
        else:
            out.append(chosen)

    for d in out:
        if d["transcript"]:
            d["transcript"] = d["transcript"].replace("Veltrix", "{{COMPANY}}").replace("Northvale", "{{TOWN}}")
    OUT.mkdir(exist_ok=True)
    (OUT / "distractors.json").write_text(json.dumps(
        {"sessions": out, "rejected": rejected,
         "n_ok": sum(1 for d in out if d["transcript"]),
         "n_failed": sum(1 for d in out if not d["transcript"]),
         "scrub": {"n_level_patterns": len(pats), "n_attribute_regexes": len(attr_rx)}}, indent=1))
    return out, rejected


if __name__ == "__main__":
    out, rej = generate_distractors(n_draft=4)
    ok = sum(1 for d in out if d["transcript"])
    stray = [d.get("stray_level_patterns", 0) for d in out if d["transcript"]]
    print(f"distractors: {ok}/{len(out)} passed the scrub; {len(rej)} drafts rejected")
    if stray:
        print(f"stray level-pattern matches outside any attribute segment: "
              f"mean {sum(stray)/len(stray):.1f} per session (unreachable by the coder)")
    for r in rej[:5]:
        print("  rejected", r["idx"], "attr_hits", r["attr_hits"][:3])
