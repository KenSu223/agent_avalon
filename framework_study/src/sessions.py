"""Simulated user histories for the framework study.

A history = 4 seeding sessions (2 items each, mentioned in passing inside an unrelated request)
followed by N distractor sessions (unrelated chats). Every framework sees exactly the same sessions.
"""
import json, random, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "framework_study/stimuli"))
from build_items import user_turn

ITEMS = {json.loads(l)["id"]: json.loads(l) for l in open(ROOT / "framework_study/stimuli/items.jsonl")}
EXCLUDE = {"S08"}  # fails immediate comprehension (normative correction) on all three models
USABLE = [i for i in ITEMS if i not in EXCLUDE]

# keywords that must not appear in a distractor session (they would leak or contradict an item)
SCRUB = r"upload|build cache|billing|payment|beta|flag|rack|light|thermostat|urgent|deploy|friday|decaf|espresso|coffee machine|" \
        r"parallel|test suite|password|attachment|mail server|print|colou?r|replica|primary|database|cat\b|dog\b|whiskers|rex\b|" \
        r"fern|cactus|plant|ind(ex|ices)|vendor portal|submit|vacation|tilwren|bird|lake|freez|elevator|basement|rooftop|" \
        r"express bus|airport|bug tracker|\bP1\b|\bP4\b|priority|branch|\bmain\b|\bdev\b|shipping|supplier|fire drill|evacuat|" \
        r"wi-?fi|ghz|laptop|build fleet|parking|garage|migration|server|printer|jam|review|merge|new hire|supply cupboard|key|" \
        r"date|indent|spaces|greeting|celsius|kelvin|temperature|roman|numeral|spell|sign-?off|duration|seconds|time"

FILLERS = [("Quick one: what's 15% of 80?", "15% of 80 is 12."), ("What's the capital of Australia?", "Canberra."),
           ("How many minutes are in three hours?", "180 minutes."), ("What's a synonym for 'quick'?", "Rapid."),
           ("How do you say 'thank you' in Spanish?", "Gracias."), ("What's 12 times 12?", "144."),
           ("Is a tomato a fruit or a vegetable?", "Botanically, it's a fruit."), ("What's the plural of 'cactus'?", "Cacti or cactuses.")]


def load_distractors():
    """Fresh, topic-scrubbed distractor chats (see make_distractors.py)."""
    return [d["transcript"] for d in json.load(open(ROOT / "framework_study/stimuli/distractors.json"))["sessions"]]


def transcript_to_messages(t):
    msgs = []
    for block in re.split(r"\n\s*\n", t.strip()):
        m = re.match(r"\s*(Sam|Atlas):\s*(.*)", block, re.S)
        if not m:
            if msgs:
                msgs[-1]["content"] += "\n\n" + block.strip()
            continue
        role = "user" if m.group(1) == "Sam" else "assistant"
        if msgs and msgs[-1]["role"] == role:
            msgs[-1]["content"] += "\n\n" + m.group(2).strip()
        else:
            msgs.append({"role": role, "content": m.group(2).strip()})
    return msgs


def item_exchange(iid, version):
    x = ITEMS[iid]
    if x["type"] == "preference":
        q, a = FILLERS[int(iid[1:]) % len(FILLERS)]
        return [{"role": "user", "content": f"{q} {user_turn(x, version)}"},
                {"role": "assistant", "content": f"{a} Got it."}]
    return [{"role": "user", "content": user_turn(x, version)}, {"role": "assistant", "content": x["reply"]}]


def make_users(n_users, items_per_user=8, seed=0):
    """Counterbalanced assignment: every usable item appears equally often as C and I across users."""
    rng = random.Random(seed)
    pool = []
    while len(pool) < n_users * items_per_user:
        ids = USABLE[:]
        rng.shuffle(ids)
        pool += ids
    users, counts = [], {}
    for u in range(n_users):
        chosen = []
        for iid in pool[u * items_per_user:]:
            if iid not in chosen:
                chosen.append(iid)
            if len(chosen) == items_per_user:
                break
        assign = []
        for iid in chosen:
            k = counts.get(iid, 0); counts[iid] = k + 1
            assign.append((iid, "C" if (k + int(iid[1:])) % 2 == 0 else "I"))
        users.append(assign)
    return users


def build_history(assign, distractors, n_distract=8, seed=0):
    """Returns a list of sessions (each a list of OpenAI-style messages) plus metadata."""
    rng = random.Random(seed)
    ds = distractors[:]
    rng.shuffle(ds)
    sessions = []
    for s in range(0, len(assign), 2):
        msgs = [{"role": "user", "content": "Hi Atlas!"}, {"role": "assistant", "content": "Hi Sam, how can I help today?"}]
        for iid, v in assign[s:s + 2]:
            msgs += item_exchange(iid, v)
        sessions.append({"kind": "seed", "items": assign[s:s + 2], "messages": msgs})
    for j in range(n_distract):
        sessions.append({"kind": "distractor", "items": [], "messages": transcript_to_messages(ds[j % len(ds)])})
    return sessions


if __name__ == "__main__":
    ds = load_distractors()
    print("usable distractors after scrub:", len(ds))
    users = make_users(43)
    h = build_history(users[0], ds)
    print(len(h), "sessions;", [s["kind"] for s in h])
    for m in h[0]["messages"]:
        print(m["role"], ":", m["content"][:160])
    print(h[4]["messages"][:2])
