"""Generate unrelated distractor chats (Sam <-> Atlas) and scrub them against every item's topic."""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from infra.llm import batch_chat

GEN = "qwen.qwen3-235b-a22b-2507-v1:0"
OUT = ROOT / "framework_study/stimuli/distractors.json"
TASKS = [
 "plan a 7-year-old's birthday party", "find a simple pancake recipe", "explain photosynthesis to a child",
 "write a haiku about autumn leaves", "plan a two-day road trip along the coast", "summarise the plot of Pride and Prejudice",
 "choose a gift for a mother who likes gardening books", "explain compound interest with an example",
 "write a short toast for a friend's wedding", "suggest names for a new puppy", "plan a vegetarian dinner for six",
 "explain how vaccines train the immune system", "pick three novels for a book club", "plan a beginner running schedule",
 "write a thank-you note to a teacher", "explain why the sky is blue", "suggest board games for a family evening",
 "draft a short speech for a retirement party", "explain the rules of chess castling", "plan a picnic menu",
 "suggest ways to learn Spanish vocabulary", "explain how a bill becomes law", "write a limerick about a lazy cat-free goldfish",
 "suggest indoor activities for a rainy weekend", "explain what inflation is", "plan a small surprise anniversary dinner",
 "recommend podcasts about history", "explain how tides work", "write a short bedtime story about a brave turtle",
 "suggest a weekly meal-prep plan", "explain the difference between weather and climate", "plan a museum day with kids",
 "suggest a reading list on stoicism", "explain how to brew loose-leaf tea", "write a short poem for Mother's Day",
 "plan a budget for a weekend city break", "explain what a black hole is", "suggest stretches after a long walk",
 "help choose between two hiking boots by comfort", "explain how bees make honey",
]
FORBIDDEN = ("file uploads, build caches, APIs, payments, feature flags, server racks, thermostats, support tickets, software deploys, "
             "coffee machines, tests, passwords, email attachments, printing, databases, office pets, office plants, programming, "
             "vendor portals, vacation requests, birds, lakes, elevators, buses, airports, bug trackers, git, shipping, fire drills, "
             "Wi-Fi, laptops, parking, migrations, code review, new hires, cupboards, keys, date formats, indentation, greetings, "
             "temperatures, numbered lists, how numbers are written, sign-offs, durations or clock times")
PROMPT = ("Write a natural chat transcript of about 180 words between Sam and Sam's AI assistant Atlas. Sam asks Atlas to help {task}. "
          "Do not mention any of these topics: " + FORBIDDEN + ". Format every turn as 'Sam: ...' or 'Atlas: ...', separated by blank lines. "
          "Output only the transcript.")

SCRUB = re.compile(
    r"upload|build cache|billing|payment|disable_|beta|server rack|thermostat|urgent|deploy|decaf|espresso|coffee machine|"
    r"test suite|password|attachment|mail server|colou?r print|printer|paper jam|replica|database|office (cat|dog)|whiskers|\brex\b|"
    r"\bfern|cactus|indices|index|vendor portal|vacation|tilwren|\blake|freez|elevator|basement|rooftop|\bbus\b|airport|"
    r"bug tracker|priority|branch|shipping|supplier|fire drill|evacuat|wi-?fi|ghz|laptop|parking|garage|migration|"
    r"code review|merge|new hire|cupboard|\bkey\b|indent|celsius|kelvin|fahrenheit|°|roman numeral|spell(ed)? out|sign-?off|"
    r"\d{1,2}:\d{2}|\d+h\d+|\bseconds\b|\b\d{4}-\d{2}-\d{2}\b", re.I)


if __name__ == "__main__":
    reqs = [dict(model=GEN, messages=[{"role": "user", "content": PROMPT.format(task=t)}], temperature=0.8, max_tokens=500, sample_idx=d)
            for t in TASKS for d in range(2)]
    res = batch_chat(reqs, workers=16, desc="distractors")
    keep, rejected = [], []
    for r, req in zip(res, reqs):
        t = (r or {}).get("text", "").strip()
        task = req["messages"][0]["content"].split("help ", 1)[1].split(". Do not")[0]
        if not t.startswith("Sam:") or SCRUB.search(t):
            rejected.append({"task": task, "hit": (SCRUB.search(t).group(0) if SCRUB.search(t) else "format")})
            continue
        if task not in [k["task"] for k in keep]:
            keep.append({"task": task, "transcript": t})
    json.dump({"sessions": keep, "rejected": rejected}, open(OUT, "w"), indent=1)
    print("kept", len(keep), "rejected", len(rejected))
