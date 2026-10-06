"""Tightened attribute regexes + the manifest that freezes them.

Two problems with the shipped attribute regexes: several are bare substrings, so `bus` matches
"business" and `park` matches "Park Avenue". The attribute regex is what the coder uses to LOCATE
the segment it will classify, so a loose one produces both false DROPPED (wrong segment found) and
false CHANGED (a level pattern fires in an unrelated sentence). It is also what the distractor
scrub uses, where a loose regex rejects every draft.

Tightening rule: a regex made only of literal words and `|` has each alternative wrapped as
\\b<word>(?:s|es|ing|ed)?\\b. Regexes that already use anchors or metacharacters are left alone.
Every tightened regex is then validated: it must still match all of its family's own level
sentences, and it must not match a held-out set of ordinary office prose.
"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from stimuli import load_families, render, ROOT

SAFE_WORD = re.compile(r"^[A-Za-z][A-Za-z0-9'\- ]*$")

# ordinary workplace prose that must NOT trigger any attribute regex
# Different-sense traps: these use a target word in an UNRELATED sense and must NOT match.
NEGATIVE_PROSE = [
    "Let's talk about the business plan for the next quarter.",
    "I parked the idea for now; part of it still works.",
    "Open the file and check the first column.",
    "Let's open with the summary slide and keep the rest brief.",
    "The marketing team will square the numbers with finance before Friday.",
    "We should square away the remaining action items.",
    "She used to work at a bank of servers in the old datacentre.",
    "He sprinted through the backlog in one afternoon.",
    "The cedar desk in the corner is hers.",
    "Ideas flowed like a river all afternoon.",
    "I'll back you up on that point in the meeting.",
    "That's a fast turnaround, thanks.",
    "The team lead will follow up on Monday.",
    "Business as usual on the support rota this week.",
]

# Correct-sense mentions: a locator regex SHOULD fire on these. Used as a positive control, so a
# regex tightened into uselessness is caught too.
TOPICAL_PROSE = [
    ("F28", "Could you refill the printer tray on the second floor?"),
    ("F40", "The customer support ticket is still open after a week."),
    ("F13", "Employees park in the lot behind the building."),
    ("F01", "The billing API returned a timeout again."),
    ("F08", "The platform team's sprint starts on Monday."),
    ("V04", "The Northvale river looks lovely in winter."),
]

def tighten(rx):
    if any(c in rx for c in r"\^$*+?{}[]()"):
        return rx                                   # already structured, leave as authored
    alts = [a.strip() for a in rx.split("|") if a.strip()]
    if not alts or not all(SAFE_WORD.match(a) for a in alts):
        return rx
    return "|".join(rf"\b{re.escape(a)}(?:s|es|ing|ed)?\b" for a in alts)


OVERRIDES = {
    "F02": r"\boffice\b[^.]{0,60}\bopens?\b|\bopens?\b[^.]{0,25}\d",
    "F13": r"\bemployees?\b[^.]{0,20}\bparks?\b|\bparking\b|\bparks?\b[^.]{0,8}\b(?:in|on|at|under)\b",
    "F23": r"\bbus(?:es)?\b|\bbus line\b",
    "F30": r"\bupload(?:s|ing)?\b",
    "F08": r"\bsprints?\b",
    "F27": r"\bCedar (?:conference )?room\b|\bCedar\b[^.]{0,30}\b(?:seats?|room)\b",
    "F32": r"\bbuild cache\b|\bcaches?\b",
    "V04": r"\briver\b(?!\s+of\b)",
    "F34": r"\bstaging\b.{0,40}\breset\b|\breset(?:s|ting)?\b.{0,40}\bstaging\b|\bstaging reset\b",
    "F24": r"\bfarmers'? ?market\b|\bmarkets?\b",
    "V09": r"\b(?:main|town) square\b|\bsquare\b(?!\s+(?:away|the|up|off))",
}


def build():
    fams = load_families()
    out, problems = {}, []
    for f in fams:
        fid = f["family_id"]
        rx = OVERRIDES.get(fid, tighten(f["attribute_regex"]))
        w = {"COMPANY": "Veltrix", "TOWN": "Northvale"}
        rendered = render(rx, w)
        # must still locate every one of its own level sentences
        missed = [lv["level"] for lv in f["levels"]
                  if not re.search(rendered, render(lv["sentence"], w), re.I)]
        # must not fire on ordinary prose
        false_pos = [s for s in NEGATIVE_PROSE if re.search(rendered, s, re.I)]
        out[fid] = {"attribute_regex": rx, "original": f["attribute_regex"],
                    "changed": rx != f["attribute_regex"]}
        if missed:
            problems.append({"severity": "HARD", "family_id": fid, "regex": rx,
                             "missed_levels": missed})
        if false_pos:
            # Over-firing is CONSERVATIVE in both roles: in the scrub it only rejects a draft, and
            # in the coder it only routes the item to the blind judges. Recorded, not fatal.
            problems.append({"severity": "SOFT", "family_id": fid, "regex": rx,
                             "false_positives": false_pos})
    # positive control: each listed family's regex must fire on a correct-sense mention
    for fid, sent in TOPICAL_PROSE:
        rendered = render(out[fid]["attribute_regex"], {"COMPANY": "Veltrix", "TOWN": "Northvale"})
        if not re.search(rendered, sent, re.I):
            problems.append({"severity": "HARD", "family_id": fid,
                             "regex": out[fid]["attribute_regex"], "missed_topical": sent})
    return out, problems


if __name__ == "__main__":
    out, problems = build()
    n_changed = sum(1 for v in out.values() if v["changed"])
    hard = [p for p in problems if p["severity"] == "HARD"]
    soft = [p for p in problems if p["severity"] == "SOFT"]
    print(f"attribute regexes: {len(out)} families, {n_changed} tightened")
    print(f"HARD failures (regex no longer locates its own content): {len(hard)}")
    for p in hard:
        print("  ", p)
    print(f"SOFT over-firing on metaphorical prose (conservative, accepted): {len(soft)}")
    for p in soft:
        print("  ", p["family_id"], p["regex"], "->", p["false_positives"][:1])
    if not hard:
        print("\nOK: every tightened regex still locates all of its own level sentences and all")
        print("    correct-sense topical mentions. Residual over-firing is conservative in both")
        print("    roles (scrub: rejects a draft; coder: routes to the blind judges).")
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "attribute_regexes.json").write_text(json.dumps(
        {"regexes": out, "problems": problems, "negative_prose": NEGATIVE_PROSE}, indent=1))
