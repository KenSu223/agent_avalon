"""Distractor pool for the expanded item set (PLAN 3.1, STEP3_DESIGN.md §3).

Generation: the same generator, prompt, forbidden-topic instruction, sampling settings and regex scrub as
make_distractors.py (Qwen3-235B, T=0.8, 2 drafts per task); only the task list is new (personal / hobby topics far
from the workplace). The pool = the existing 39 distractors + the new ones.
Leak check against EVERY final item (items_v2_final.jsonl), two layers:
  layer 1  keywords: an item's keywords = content words of its topic, both answer fillers and its question; a
           (distractor, item) pair is flagged if the distractor contains an answer word of the item AND at least one
           other keyword of that item, or at least three keywords of that item.
  layer 2  LLM (gpt-oss-120b): for each flagged pair, "does this chat mention or imply anything that answers the
           question?"; yes -> the distractor is removed from the pool (conservative: removed for all users).
Output: framework_study/stimuli/distractors_v2.json  {"sessions": [...], "removed": [...], "stats": {...}}
"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "framework_study/src"))
from infra.llm import batch_chat, budget
import make_distractors as MD

OUT = ROOT / "framework_study/stimuli/distractors_v2.json"
JUDGE = "openai.gpt-oss-120b-1:0"
NEW_TASKS = [
 "plan a three-course dinner for a friend who loves Italian food", "explain how volcanoes form", "write a short poem about the sea",
 "pick a houseplant-free gift for a teenager who likes astronomy", "explain how a rainbow forms", "plan a day trip to a lighthouse town",
 "suggest a beginner knitting project", "explain the life cycle of a butterfly", "write a riddle about the moon",
 "suggest ways to make a small balcony cosy", "explain how the heart pumps blood", "plan a family movie night",
 "recommend classic mystery novels", "explain how airplanes stay in the air", "write a toast for a sister's graduation",
 "suggest a simple bread recipe", "explain why leaves change colour in autumn", "plan a weekend camping trip",
 "suggest a playlist theme for a road trip", "explain how the moon causes eclipses", "write a short fable about a fox and a crow",
 "plan a children's science fair project", "explain what DNA is", "suggest a gentle yoga routine for mornings",
 "recommend a few board games for two players", "explain how glaciers move", "write a short lullaby",
 "plan a birthday breakfast in bed", "explain how solar panels work", "suggest names for a sailing boat",
 "suggest ways to remember people's names", "explain how earthquakes are measured", "write a short story about a lost umbrella-free kite",
 "plan a picnic-free afternoon at a botanical garden", "explain how chocolate is made", "suggest hobbies for a retired grandparent",
 "recommend documentaries about the ocean", "explain how fireflies glow", "write a haiku about snow",
 "plan a vegetarian barbecue", "explain the water cycle", "suggest a stargazing checklist",
 "suggest ways to start journaling", "explain how a compass works", "write a thank-you card for a neighbour",
 "plan a cheese-tasting evening", "explain how penguins stay warm", "suggest a short reading list on ancient Rome",
 "explain how bread rises", "write a limerick about a forgetful wizard", "plan a scavenger hunt for kids",
 "suggest ways to practise piano at home", "explain how bats find their way in the dark", "write a short poem about a train journey",
 "plan a pancake brunch for friends", "explain how the seasons work", "suggest gentle ways to fall asleep faster",
 "recommend fantasy novels for a twelve-year-old", "explain how coral reefs form",
]
LEAK_PROMPT = ("Here is a chat transcript between Sam and an AI assistant.\n\nTRANSCRIPT:\n{t}\n\n"
               "Question about Sam's workplace: {q}\n\nDoes the transcript mention or imply anything that helps answer this question? "
               "Answer yes or no only.")
STOP = set("a an the and or of to in on at for with is are was were be been do does did what when where who which why how "
           "i you he she it we they me him her them my your his its our their this that these those as by from about into has have "
           "had not no yes can could would should will may might must just only also so than then there here sam sam's atlas veltrix "
           "now team office company staff people work".split())


def kw(s):
    return {w for w in re.findall(r"[a-z][a-z\-]+", s.lower()) if w not in STOP and len(w) > 3}


def main():
    old = json.load(open(ROOT / "framework_study/stimuli/distractors.json"))["sessions"]
    reqs = [dict(model=MD.GEN, messages=[{"role": "user", "content": MD.PROMPT.format(task=t)}], temperature=0.8, max_tokens=500, sample_idx=d)
            for t in NEW_TASKS for d in range(2)]
    res = batch_chat(reqs, workers=16, desc="distractors v2")
    new, rejected = [], []
    for r, req in zip(res, reqs):
        t = (r or {}).get("text", "").strip()
        task = req["messages"][0]["content"].split("help ", 1)[1].split(". Do not")[0]
        if not t.startswith("Sam:") or MD.SCRUB.search(t):
            rejected.append({"task": task, "hit": MD.SCRUB.search(t).group(0) if MD.SCRUB.search(t) else "format"})
            continue
        if task not in [k["task"] for k in new]:
            new.append({"task": task, "transcript": t, "source": "v2"})
    pool = [dict(d, source="v1") for d in old] + new
    items = [json.loads(l) for l in open(ROOT / "framework_study/stimuli/items_v2_final.jsonl")]
    ikw = {}
    for x in items:
        fill_words = kw(x["C"]["answer"] + " " + x["I"]["answer"]) | kw(" ".join(o.lower() for o in x["options"]))
        others = kw(x["topic"].replace("-", " ") + " " + x["question"]) - fill_words
        ikw[x["id"]] = (fill_words, others)
    flagged = []
    for di, d in enumerate(pool):
        words = kw(d["transcript"])
        for x in items:
            fw, ow = ikw[x["id"]]
            if (words & fw and len(words & ow) >= 1) or len(words & (fw | ow)) >= 3:
                flagged.append((di, x["id"]))
    byid = {x["id"]: x for x in items}
    jres = batch_chat([dict(model=JUDGE, messages=[{"role": "user", "content": LEAK_PROMPT.format(t=pool[di]["transcript"], q=byid[iid]["question"])}],
                            temperature=0.0, max_tokens=400, reasoning_effort="low") for di, iid in flagged], workers=32, desc="leak check")
    leaks = {}
    for (di, iid), jr in zip(flagged, jres):
        t = ((jr or {}).get("text") or "").strip().lower()
        if "yes" in t[:20]:
            leaks.setdefault(di, []).append(iid)
    keep = [d for di, d in enumerate(pool) if di not in leaks]
    removed = [dict(pool[di], leaked_items=v) for di, v in leaks.items()]
    stats = dict(old=len(old), new_generated=len(reqs), new_rejected_by_regex_or_format=len(rejected), new_kept_before_leak_check=len(new),
                 pool_before_leak_check=len(pool), flagged_pairs_layer1=len(flagged), leaking_distractors_layer2=len(leaks), final_pool=len(keep),
                 final_from_v1=sum(d["source"] == "v1" for d in keep), final_from_v2=sum(d["source"] == "v2" for d in keep))
    json.dump({"sessions": keep, "removed": removed, "rejected_drafts": rejected, "stats": stats,
               "flagged_pairs": [dict(distractor_task=pool[di]["task"], item=iid, leak=di in leaks and iid in leaks[di]) for di, iid in flagged]},
              open(OUT, "w"), indent=1)
    print(stats); print("spent", budget()["spent_usd"])


if __name__ == "__main__":
    main()
