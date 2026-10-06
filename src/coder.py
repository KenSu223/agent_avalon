"""Three-state coding of a memory snapshot for one target item.

States: RETAINED / CHANGED{specific->level, specific->OTHER, vague} / DROPPED.

Regex-first: the attribute regex locates candidate segments, the level patterns classify them.
Only ambiguous cases reach the judges. Judges are BLIND -- they never see the candidate level
list, the level order, the measured surprise, or the hypothesis; they report the answer the
notes imply in free text, and *we* match that answer against the patterns. This is what stops
the coder from manufacturing prior-ward movement by snapping novel values onto the nearest
canonical level (round-2 review).
"""
import json, re, unicodedata

RETAINED, CHANGED, DROPPED, UNRESOLVED = "RETAINED", "CHANGED", "DROPPED", "UNRESOLVED"

# Cues that make a level match unsafe to read as the current asserted answer: negation, a
# historical value, or an explicit contrast. A segment carrying any of these is sent to the judges
# rather than fast-pathed, because "it used to be 30 seconds" is not an assertion that it IS.
CUE_PATTERNS = [
    r"\bnot\b", r"\bno longer\b", r"\bnever\b", r"\bused to\b", r"\bpreviously\b",
    r"\bformerly\b", r"\bchanged from\b", r"\bwas (?:once|originally|previously)\b",
    r"\binstead of\b", r"\brather than\b", r"\bexcept\b", r"\bunless\b",
    r"\bup from\b", r"\bdown from\b", r"\bnow\b", r"\bbut\b",
]
_CUE = re.compile("|".join(CUE_PATTERNS), re.I)

VAGUE_CUES = [
    r"\ba few\b", r"\bseveral\b", r"\bsome\b", r"\ba couple\b", r"\bvarious\b",
    r"\bperiodically\b", r"\bregularly\b", r"\boccasionally\b", r"\bfrom time to time\b",
    r"\bshort\b", r"\bbrief\b", r"\blong\b", r"\bquick\b", r"\bsoon\b",
    r"\bstandard\b", r"\btypical\b", r"\busual\b", r"\bnormal\b", r"\bdefault\b",
    r"\bcertain\b", r"\bspecific(?:ally)?\b(?!\s+\d)", r"\bas needed\b", r"\bsometimes\b",
]
_VAGUE = re.compile("|".join(VAGUE_CUES), re.I)


def normalize(text):
    """Unicode dashes, non-breaking spaces, and thousands separators -> canonical forms."""
    t = unicodedata.normalize("NFKC", text)
    t = t.replace("–", "-").replace("—", "-").replace("−", "-")
    t = t.replace(" ", " ").replace("’", "'")
    t = re.sub(r"(?<=\d),(?=\d{3}\b)", ",", t)      # keep the comma; patterns allow ,?
    return t


def segments(notes):
    """Split memory notes into bullets / lines / sentences."""
    out = []
    for line in normalize(notes).splitlines():
        # strip a bullet MARKER only (a bare .strip("-") would eat the sign off "-5 degrees")
        line = re.sub(r"^\s*(?:[-*\u2022\u2219]\s+)", "", line).strip()
        if not line:
            continue
        parts = re.split(r"(?<=[.;!?])\s+(?=[A-Z0-9])", line)
        out.extend(p.strip() for p in parts if p.strip())
    return out


def locate(notes, attribute_regex):
    """Segments that mention the target attribute."""
    try:
        rx = re.compile(attribute_regex, re.I)
    except re.error:
        rx = re.compile(re.escape(attribute_regex), re.I)
    return [s for s in segments(notes) if rx.search(s)]


def match_levels(text, levels):
    """Which level patterns fire on `text`."""
    t = normalize(text)
    hits = []
    for lv in levels:
        if any(re.search(p, t, re.I) for p in lv["patterns"]):
            hits.append(lv["level"])
    return hits


def code_regex(notes, item, family):
    """Regex-only pass over the located segments.

    Matching is done PER SEGMENT, never on a joined blob: joining lets an incidental number in one
    sentence be paired with the attribute mention in another, which would fabricate a CHANGED event.

    The fast path fires only when the evidence is unambiguous AND the segment carries no negation,
    history or contrast cue. Everything else is routed to the blind judges.

    Returns (label, destination, needs_judge, evidence).
    """
    segs = locate(notes, item["attribute_rendered"])
    if not segs:
        return DROPPED, None, True, None            # always re-confirm a DROPPED by judge
    own = item["level"]
    per_seg = [(sg, match_levels(sg, family["levels"])) for sg in segs]
    hit_segs = [(sg, h) for sg, h in per_seg if h]
    evidence = " || ".join(sg for sg, _ in per_seg)[:400]

    if any(_CUE.search(sg) for sg, h in hit_segs):
        return CHANGED, None, True, evidence        # negation / history / contrast -> judge

    distinct = sorted({lv for _, h in hit_segs for lv in h})
    if not distinct:
        blob = " ".join(segs)
        if _VAGUE.search(blob):
            return CHANGED, "VAGUE", True, evidence
        return CHANGED, "OTHER", True, evidence
    if len(distinct) > 1:
        return CHANGED, None, True, evidence        # conflicting values -> judge
    if any(len(h) > 1 for _, h in hit_segs):
        return CHANGED, None, True, evidence        # one segment fires several levels -> judge
    if distinct == [own]:
        return RETAINED, own, False, evidence
    return CHANGED, distinct[0], False, evidence


JUDGE_SYSTEM = (
    "You check whether a specific piece of information survived in an assistant's memory notes. "
    "Answer only with the JSON object requested. Do not explain."
)

JUDGE_USER = """ORIGINAL INFORMATION: {sentence}
QUESTION IT ANSWERS: {question}

MEMORY NOTES:
{notes}

Classify the notes into exactly one category:
- RETAINED: the notes answer the question with the same specific value as the original information. Paraphrase and reformatting are fine; the value must be the same.
- CHANGED: the notes address the question but give a different value, or a less specific answer.
- DROPPED: the notes do not address the question at all.

Reply with JSON only:
{{"label": "RETAINED" | "CHANGED" | "DROPPED", "notes_answer": "<the answer the notes imply, verbatim or closely paraphrased, or null>", "evidence": "<a short quote from the notes, or null>"}}"""


def judge_messages(item):
    return [{"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": JUDGE_USER.format(
                sentence=item["sentence_rendered"], question=item["question_rendered"],
                notes=item["notes"] if item["notes"].strip() else "(empty)")}]


def parse_judge(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None
    if d.get("label") not in (RETAINED, CHANGED, DROPPED):
        return None
    return d


def resolve(judge_out, item, family):
    """Turn a blind judge verdict into (label, destination).

    The judge's SEMANTIC label is authoritative. Our patterns are used only to name the destination
    of a CHANGED event. Letting the patterns veto a judge's RETAINED would make retention depend on
    how richly each level's formats happen to be covered by regexes -- e.g. a note saying
    "120 seconds" for an original of "2 minutes" would be scored CHANGED purely because no pattern
    covers the unit conversion. Since common values tend to have richer coverage, that veto could
    manufacture the very retention-vs-surprise gradient this study measures.

    An inconsistent verdict (CHANGED whose stated answer is the original value) is recorded as
    UNRESOLVED rather than silently coerced; the UNRESOLVED rate is reported by surprise tercile so
    that differential adjudication failure is visible instead of hidden.
    """
    if judge_out is None or judge_out.get("label") not in (RETAINED, CHANGED, DROPPED):
        return UNRESOLVED, None
    lab = judge_out["label"]
    ans = (judge_out.get("notes_answer") or "").strip()
    if lab == DROPPED:
        return DROPPED, None
    if lab == RETAINED:
        return RETAINED, item["level"]
    hits = match_levels(ans, family["levels"]) if ans else []
    dest = _dest(ans, hits, item)
    if dest == item["level"]:
        return UNRESOLVED, None                     # judge says CHANGED but names the original value
    return CHANGED, dest


def _dest(ans, hits, item):
    if len(hits) == 1 and hits[0] != item["level"]:
        return hits[0]
    if len(hits) == 1 and hits[0] == item["level"]:
        return item["level"]
    if not ans:
        return "VAGUE"
    if _VAGUE.search(ans) and not re.search(r"\d", ans):
        return "VAGUE"
    return "OTHER"
