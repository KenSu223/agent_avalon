"""Build the pair-review bundle for the human review app (PLAN item 7 / 3.3).

Outputs
  data/bundle.json      served by the Pages Function. Per reviewer: the items to show, already rendered as Version A /
                        Version B. It contains NO C/I labels, so nothing a reviewer can reach reveals which version is
                        the schema-congruent one.
  key.json              committed, never deployed: maps every assignment uid to item id, A/B order, option order and
                        catch-item expectations. Needed to decode the answers. Contains no tokens.
  private/links.csv     local only: one review link per reviewer.

Turn texts are rendered with the same rules as framework_study/src/sessions_v2.py; for the S4 subset they are asserted to
be identical to what the experiment sent.

  python build_assignments.py --mode prototype     # 10 real items + 2 catch items, every reviewer sees all 12
  python build_assignments.py --mode full          # all 504 pairs x 2 reviewers + catch items
"""
import argparse, csv, difflib, hashlib, json, random, re, secrets, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ST = ROOT / "framework_study/stimuli"
sys.path.insert(0, str(ROOT / "framework_study/src"))
import sessions_v2  # noqa: E402
from sessions import FILLERS  # noqa: E402

APP_VERSION = "0.1.0"
GUIDELINE_VERSION = "0.1"


def _end(c):
    return "" if c.endswith(".") else "."


def item_turns(x, version):
    """The exchanges that carry this item's fact, exactly as in the experiment."""
    v = x[version]
    turns = []
    if x["type"] == "update":
        turns.append({"label": "Earlier (first session)",
                      "user": f"{x['initial_task']} {x['initial_lead']}{v['initial']}{_end(v['initial'])}",
                      "assistant": x["initial_reply"]})
    if x["type"] == "preference":
        q, a = FILLERS[int(re.sub(r"\D", "", x["id"])) % len(FILLERS)]
        user, asst = f"{q} {x['lead']}{v['clause']}{_end(v['clause'])}", f"{a} Got it."
    else:
        user, asst = f"{x['task']} {x['lead']}{v['clause']}{_end(v['clause'])}", x["reply"]
    turns.append({"label": "Later session" if x["type"] == "update" else None, "user": user, "assistant": asst})
    return turns


def check_against_experiment(items):
    n = 0
    for x in items:
        if x["id"] not in sessions_v2.ITEMS:
            continue
        for v in ("C", "I"):
            mine = item_turns(x, v)
            exp = sessions_v2.item_exchange(x["id"], v)
            assert mine[-1]["user"] == exp[0]["content"] and mine[-1]["assistant"] == exp[1]["content"], x["id"]
            if x["type"] == "update":
                ini = sessions_v2.initial_exchange(x["id"], v)
                assert mine[0]["user"] == ini[0]["content"] and mine[0]["assistant"] == ini[1]["content"], x["id"]
        n += 1
    return n


def diff_segments(a, b):
    """Word-level diff. Returns segment lists for a and b: [{"t": text, "d": differs?}, ...]."""
    ta, tb = re.findall(r"\S+|\s+", a), re.findall(r"\S+|\s+", b)
    sa, sb = [], []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=ta, b=tb, autojunk=False).get_opcodes():
        sa.append({"t": "".join(ta[i1:i2]), "d": op != "equal"})
        sb.append({"t": "".join(tb[j1:j2]), "d": op != "equal"})

    def tidy(ss):
        ss = [s for s in ss if s["t"]]
        for k in range(1, len(ss) - 1):   # whitespace between two changed spans is shown as part of one span
            if not ss[k]["d"] and not ss[k]["t"].strip() and ss[k - 1]["d"] and ss[k + 1]["d"]:
                ss[k]["d"] = True
        out = []
        for s in ss:
            if out and out[-1]["d"] == s["d"]:
                out[-1] = {"t": out[-1]["t"] + s["t"], "d": s["d"]}
            else:
                out.append(dict(s))
        return out
    return tidy(sa), tidy(sb)


def render_pair(turns_a, turns_b):
    out_a, out_b = [], []
    for ta, tb in zip(turns_a, turns_b):
        ua, ub = diff_segments(ta["user"], tb["user"])
        aa, ab = diff_segments(ta["assistant"], tb["assistant"])
        out_a.append({"label": ta["label"], "user": ua, "assistant": aa})
        out_b.append({"label": tb["label"], "user": ub, "assistant": ab})
    return out_a, out_b


# Catch items: deliberately flawed pairs, written for the review only (never used in any experiment). Their expected
# answers are in key.json. They are disclosed in the paper as attention checks.
CATCH = [
    {"id": "X01", "type": "rule", "flaw": "not_minimal",
     "question": "Does the staff kitchen close at 6 P.M. or at 9 P.M.?", "options": ["6 P.M.", "9 P.M."],
     "C": {"turns": [{"label": None, "user": "Can you suggest a title for the onboarding checklist? Also, something worth remembering: the staff kitchen closes at 6 p.m.",
                      "assistant": "How about \"Your First Week: Onboarding Checklist\"?"}], "answer": "6 P.M."},
     "I": {"turns": [{"label": None, "user": "Can you suggest a title for the onboarding checklist? Also, something worth remembering: the staff kitchen on the third floor, next to the lifts, closes at 9 p.m. on most weekdays.",
                      "assistant": "How about \"Your First Week: Onboarding Checklist\"?"}], "answer": "9 P.M."},
     "expect": {"q2_minimal": "no"}},
    {"id": "X02", "type": "procedure", "flaw": "cue",
     "question": "Are expense reports approved BEFORE or AFTER the money is paid out?", "options": ["BEFORE", "AFTER"],
     "C": {"turns": [{"label": None, "user": "What's 14 plus 8? By the way, expense reports are approved before the money is paid out.",
                      "assistant": "14 plus 8 is 22."}], "answer": "BEFORE"},
     "I": {"turns": [{"label": None, "user": "What's 14 plus 8? By the way, believe it or not, expense reports are actually approved after the money is paid out.",
                      "assistant": "14 plus 8 is 22."}], "answer": "AFTER"},
     "expect": {"q2_minimal": "no", "q6_cue_in": "I"}},
]


# Practice items: written for training only, shown with feedback before the real review. A/B order is fixed here and
# expectations are in A/B terms (they are shown to the reviewer after they answer, so they can be public).
def _t(user, assistant):
    return [{"label": None, "user": user, "assistant": assistant}]


PRACTICE = [
    {"id": "T1", "question": "Where do visitors sign in: at the FRONT desk or at the LOADING dock?",
     "options": ["FRONT", "LOADING"],
     "A": _t("Can you write a one-line reminder about Friday's demo? Also, something worth remembering: visitors sign in at the front desk.",
             "\"Reminder: the product demo is this Friday.\""),
     "B": _t("Can you write a one-line reminder about Friday's demo? Also, something worth remembering: visitors sign in at the loading dock.",
             "\"Reminder: the product demo is this Friday.\""),
     "expect": {"q2_minimal": "yes", "q3_expected": "A", "q4_answer": {"A": "FRONT", "B": "LOADING"}, "q6_cue": "none"},
     "explain": "A good pair. Only the key words differ (front desk / loading dock), there is no cue, and the question has "
                "one clear answer for each version. Most people would expect visitors to sign in at the front desk (A), "
                "but signing in at the loading dock is still a believable local arrangement."},
    {"id": "T2", "question": "Is the team stand-up held in the MORNING or in the EVENING?", "options": ["MORNING", "EVENING"],
     "A": _t("What's 9 times 4? By the way, the team stand-up is held in the morning.", "9 times 4 is 36."),
     "B": _t("What's 9 times 4? By the way, the team stand-up is held in the evening, but only on Mondays and Thursdays.",
             "9 times 4 is 36."),
     "expect": {"q2_minimal": "no", "q3_expected": "A", "q4_answer": {"A": "MORNING", "B": "EVENING"}, "q6_cue": "none"},
     "explain": "Not a minimal pair: Version B adds extra information (\"but only on Mondays and Thursdays\") that Version A "
                "does not have. Answer No in Q2 and write what else differs."},
    {"id": "T3", "question": "Are new laptops set up BEFORE or AFTER the new hire's first day?", "options": ["BEFORE", "AFTER"],
     "A": _t("Can you suggest a subject line for the onboarding email? One more thing you should know: new laptops are set up before the new hire's first day.",
             "How about \"Welcome aboard: your first week\"?"),
     "B": _t("Can you suggest a subject line for the onboarding email? One more thing you should know: surprisingly, new laptops are set up after the new hire's first day.",
             "How about \"Welcome aboard: your first week\"?"),
     "expect": {"q2_minimal": "no", "q3_expected": "A", "q4_answer": {"A": "BEFORE", "B": "AFTER"}, "q6_cue": "B"},
     "explain": "Version B contains a surprise cue (\"surprisingly\"). The cue tells the reader that the fact is unusual, "
                "which we must avoid. Mark the cue in Q6. Because the cue is an extra word, the pair is also not minimal (Q2: No)."},
    {"id": "T4", "question": "Is the quarterly report due in SPRING or in WINTER?", "options": ["SPRING", "WINTER"],
     "A": _t("Can you fix the typo in 'recieve'? Also, something worth remembering: the quarterly report is due in March.",
             "It should be 'receive'."),
     "B": _t("Can you fix the typo in 'recieve'? Also, something worth remembering: the quarterly report is due in April.",
             "It should be 'receive'."),
     "expect": {"q2_minimal": "yes", "q3_expected": "both", "q4_answer": {"A": "cant_tell", "B": "SPRING"}, "q6_cue": "none"},
     "explain": "The question does not match the statement. March can be winter or spring depending on the date and the "
                "hemisphere, so for Version A the answer cannot be told from what Sam said. Choose \"Can't tell\" in Q4 "
                "whenever the question does not have one clear answer."},
]


def pick_prototype(items, rng):
    want = {"rule": 4, "procedure": 2, "preference": 1, "update": 2, "neutral": 1}
    out = []
    for t, k in want.items():
        pool = sorted([x for x in items if x["type"] == t and x["id"] in sessions_v2.ITEMS], key=lambda x: x["id"])
        out += rng.sample(pool, k)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["prototype", "full"], default="prototype")
    ap.add_argument("--reviewers", type=int, default=5)
    ap.add_argument("--per-item", type=int, default=2, help="reviewers per item in full mode")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    rng = random.Random(a.seed)

    final = [json.loads(l) for l in open(ST / "items_v2_final.jsonl")]
    n_checked = check_against_experiment(final)
    print(f"turn rendering identical to the experiment for {n_checked} S4 items")

    real = pick_prototype(final, rng) if a.mode == "prototype" else final
    pairs = [{"id": x["id"], "type": x["type"], "question": x["question"], "options": x["options"],
              "C": {"turns": item_turns(x, "C"), "answer": x["C"]["answer"]},
              "I": {"turns": item_turns(x, "I"), "answer": x["I"]["answer"]}, "catch": None} for x in real]
    pairs += [{**{k: c[k] for k in ("id", "type", "question", "options", "C", "I")},
               "catch": {"flaw": c["flaw"], "expect": c["expect"]}} for c in CATCH]

    reviewers = [f"R{i + 1:02d}" for i in range(a.reviewers)]
    if a.mode == "prototype":
        alloc = {r: [p["id"] for p in pairs] for r in reviewers}
    else:
        # every real item to `per_item` distinct reviewers, cycling through all reviewer combinations so that every
        # pair of reviewers overlaps (needed for pairwise agreement); every reviewer also sees every catch item
        from itertools import combinations
        combos = list(combinations(reviewers, a.per_item))
        ids = [p["id"] for p in pairs if not p["catch"]]
        rng.shuffle(ids)
        alloc = {r: [] for r in reviewers}
        for k, iid in enumerate(ids):
            for r in combos[k % len(combos)]:
                alloc[r].append(iid)
        for r in reviewers:
            alloc[r] += [c["id"] for c in CATCH]

    by_id = {p["id"]: p for p in pairs}
    practice = []
    for t in PRACTICE:
        ta, tb = render_pair(t["A"], t["B"])
        practice.append({"uid": t["id"], "question": t["question"], "options": t["options"], "A": ta, "B": tb,
                         "expect": t["expect"], "explain": t["explain"]})
    bundle = {"app_version": APP_VERSION, "guideline_version": GUIDELINE_VERSION, "mode": a.mode,
              "practice": practice, "reviewers": {}}
    key = {"app_version": APP_VERSION, "guideline_version": GUIDELINE_VERSION, "mode": a.mode, "seed": a.seed,
           "assignments": {}}
    links = []
    old = {}                                         # keep existing links valid across rebuilds
    if (HERE / "private/links.csv").exists():
        old = {row["reviewer"]: row["token"] for row in csv.DictReader(open(HERE / "private/links.csv"))}
    for r in reviewers:
        token = old.get(r) or secrets.token_urlsafe(12)
        seq = alloc[r][:]
        rng.shuffle(seq)
        shown = []
        for iid in seq:
            p = by_id[iid]
            uid = hashlib.sha256(f"{r}|{iid}|{a.seed}".encode()).hexdigest()[:12]
            ab = rng.choice(["CI", "IC"])            # which version is shown as A
            opt = rng.choice([0, 1])                 # 1 = show options reversed
            va, vb = p[ab[0]], p[ab[1]]
            ta, tb = render_pair(va["turns"], vb["turns"])
            options = p["options"] if opt == 0 else p["options"][::-1]
            # the item type is not sent: "neutral" would tell the reviewer that neither version is expected
            shown.append({"uid": uid, "question": p["question"], "options": options, "A": ta, "B": tb})
            key["assignments"][uid] = {"reviewer": r, "item_id": iid, "type": p["type"], "ab_order": ab,
                                       "options_shown": options, "answers": {"C": p["C"]["answer"], "I": p["I"]["answer"]},
                                       "catch": p["catch"]}
        bundle["reviewers"][token] = {"reviewer": r, "items": shown}
        links.append((r, token, len(shown)))

    (HERE / "data").mkdir(exist_ok=True)
    (HERE / "private").mkdir(exist_ok=True)
    json.dump(bundle, open(HERE / "data/bundle.json", "w"), ensure_ascii=False, indent=1)
    json.dump(key, open(HERE / "key.json", "w"), ensure_ascii=False, indent=1)
    with open(HERE / "private/links.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["reviewer", "token", "n_items", "local_link"])
        for r, t, n in links:
            w.writerow([r, t, n, f"http://localhost:8788/?r={t}"])
    for r, t, n in links:
        print(f"{r}: {n} items  http://localhost:8788/?r={t}")


if __name__ == "__main__":
    main()
