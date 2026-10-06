"""Unit tests for the three-state coder (B0/R003). Pure regex path, no model calls."""
import json, sys
sys.path.insert(0, "src")
from stimuli import load_families, render, world
import coder

W = {"COMPANY": "Veltrix", "TOWN": "Northvale"}
fams = {f["family_id"]: f for f in load_families()}


def mk(fid, level, notes):
    f = fams[fid]
    lv = next(l for l in f["levels"] if l["level"] == level)
    return {"level": level, "attribute_rendered": render(f["attribute_regex"], W),
            "sentence_rendered": render(lv["sentence"], W),
            "question_rendered": render(f["question"], W), "notes": notes}, f


CASES = []
F = "F04"   # password change interval: L1 90 days, L2 180 days, L3 30 days, L4 3 years, L5 2 days
CASES += [
    (F, 1, "Passwords must be changed every 90 days.", "RETAINED", 1),
    (F, 1, "Password rotation: ninety days.", "RETAINED", 1),
    (F, 1, "Passwords are rotated every 30 days.", "CHANGED", 3),
    (F, 5, "Passwords must be changed every 2 days.", "RETAINED", 5),
    (F, 5, "Passwords are rotated every 90 days.", "CHANGED", 1),
    (F, 1, "The office has two kitchens.", "DROPPED", None),
    (F, 1, "Passwords are changed periodically.", "CHANGED", "VAGUE"),
    (F, 1, "Passwords are rotated every 45 days.", "CHANGED", "OTHER"),
]
G = "F01"   # billing API timeout: L1 30 s, L2 2 min, L3 5 s, L4 20 min, L5 6 h
CASES += [
    (G, 1, "- The internal billing API times out after 30 seconds.", "RETAINED", 1),
    (G, 1, "Billing API timeout: 30s.", "RETAINED", 1),
    (G, 5, "The billing API times out after six hours.", "RETAINED", 5),
    (G, 5, "The billing API has a short timeout.", "CHANGED", "VAGUE"),
    (G, 2, "Billing API timeout is 2 minutes.", "RETAINED", 2),
    (G, 2, "Billing API timeout is two minutes.", "RETAINED", 2),
]

fails = 0
for fid, lvl, notes, want_lab, want_dest in CASES:
    item, fam = mk(fid, lvl, notes)
    lab, dest, needs_judge, ev = coder.code_regex(notes, item, fam)
    # the regex pass defers DROPPED / VAGUE / OTHER / multi-hit to a judge; for the unit test we
    # accept the regex pass's tentative call, which is what the judge is asked to confirm.
    ok = (lab == want_lab) and (dest == want_dest)
    if not ok:
        fails += 1
        print(f"FAIL {fid}L{lvl}: {notes!r}\n   got ({lab}, {dest})  want ({want_lab}, {want_dest})")

# negation / scope guard: a contradiction must not read as RETAINED
item, fam = mk(F, 1, "Passwords are NOT changed every 90 days; the interval is 30 days.")
lab, dest, _, _ = coder.code_regex(item["notes"], item, fam)
if lab != "CHANGED":
    fails += 1
    print(f"FAIL negation case: got ({lab},{dest}) -- both 90 and 30 fire, must defer as CHANGED")

print(f"\ncoder unit tests: {len(CASES)+1-fails}/{len(CASES)+1} passed")
sys.exit(1 if fails else 0)
