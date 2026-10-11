"""User histories for step 4 (framework_study/STEP4_DESIGN.md §2) on the expanded item set.

Same structure as sessions.py: 4 seeding sessions x 2 items (mentioned in passing inside an unrelated request), then
N distractor sessions. Differences: items come from items_v2_final.jsonl restricted to the step-4 subset S4; the
distractor pool is distractors_v2.json; knowledge-update items put their initial value in seeding session 1 (an extra
exchange) and their update in the item's own seeding session, which is never session 1.
Every framework and both model families see exactly the same sessions.
"""
import json, random, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
ST = ROOT / "framework_study/stimuli"
FINAL = [json.loads(l) for l in open(ST / "items_v2_final.jsonl")]
from sessions import FILLERS, transcript_to_messages


def in_s4(x):
    pl = x["prior"]["llama"]
    if x["type"] == "neutral":
        return pl is not None and 0.3 <= pl <= 0.7
    return pl is not None and pl >= 0.8


S4 = [x for x in FINAL if in_s4(x)]
ITEMS = {x["id"]: x for x in S4}


def _end(c):
    return "" if c.endswith(".") else "."


def item_exchange(iid, version):
    x = ITEMS[iid]
    v = x[version]
    if x["type"] == "preference":
        q, a = FILLERS[int(re.sub(r"\D", "", iid)) % len(FILLERS)]
        return [{"role": "user", "content": f"{q} {x['lead']}{v['clause']}{_end(v['clause'])}"}, {"role": "assistant", "content": f"{a} Got it."}]
    return [{"role": "user", "content": f"{x['task']} {x['lead']}{v['clause']}{_end(v['clause'])}"}, {"role": "assistant", "content": x["reply"]}]


def initial_exchange(iid, version):
    x = ITEMS[iid]
    v = x[version]
    return [{"role": "user", "content": f"{x['initial_task']} {x['initial_lead']}{v['initial']}{_end(v['initial'])}"},
            {"role": "assistant", "content": x["initial_reply"]}]


def make_users(n_users, items_per_user=8, seed=0):
    """Counterbalanced: every S4 item appears as C and as I equally often across users (as far as n_users allows).
    Update items are never placed in the first seeding session (slots 0-1)."""
    rng = random.Random(seed)
    ids = [x["id"] for x in S4]
    pool = []
    while len(pool) < n_users * items_per_user:
        batch = ids[:]
        rng.shuffle(batch)
        pool += batch
    users, counts, pos = [], {}, 0
    for u in range(n_users):
        chosen = []
        while len(chosen) < items_per_user:
            iid = pool[pos % len(pool)]; pos += 1
            if iid not in chosen:
                chosen.append(iid)
        # move update items out of the first seeding session
        ups = [i for i in chosen if ITEMS[i]["type"] == "update"]
        rest = [i for i in chosen if ITEMS[i]["type"] != "update"]
        if len(rest) >= 2:
            chosen = rest[:2] + [i for i in chosen if i not in rest[:2]]
        assign = []
        for iid in chosen:
            k = counts.get(iid, 0); counts[iid] = k + 1
            assign.append((iid, "C" if (k + int(re.sub(r"\D", "", iid))) % 2 == 0 else "I"))
        users.append(assign)
    return users


def load_distractors():
    return [d["transcript"] for d in json.load(open(ST / "distractors_v2.json"))["sessions"]]


def build_history(assign, distractors, n_distract=12, seed=0):
    rng = random.Random(seed)
    ds = distractors[:]
    rng.shuffle(ds)
    sessions = []
    for s in range(0, len(assign), 2):
        msgs = [{"role": "user", "content": "Hi Atlas!"}, {"role": "assistant", "content": "Hi Sam, how can I help today?"}]
        if s == 0:      # initial values of the update items assigned to later sessions
            for iid, v in assign[2:]:
                if ITEMS[iid]["type"] == "update":
                    msgs += initial_exchange(iid, v)
        for iid, v in assign[s:s + 2]:
            msgs += item_exchange(iid, v)
        sessions.append({"kind": "seed", "items": assign[s:s + 2], "messages": msgs})
    for j in range(n_distract):
        sessions.append({"kind": "distractor", "items": [], "messages": transcript_to_messages(ds[j % len(ds)])})
    return sessions


if __name__ == "__main__":
    import collections
    users = make_users(108)
    c = collections.Counter((i, v) for u in users for i, v in u)
    both = sum(1 for x in S4 if c[(x["id"], "C")] >= 1 and c[(x["id"], "I")] >= 1)
    print(f"S4 {len(S4)} items; 108 users; items with both versions present: {both}; first-session updates: "
          f"{sum(1 for u in users for i, _ in u[:2] if ITEMS[i]['type'] == 'update')}")
    h = build_history(users[0], load_distractors())
    print(len(h), "sessions; first seed session:", [m["content"][:60] for m in h[0]["messages"]])
