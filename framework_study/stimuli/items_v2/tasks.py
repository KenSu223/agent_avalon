"""Unrelated carrier tasks for the expanded item set (STEP3_DESIGN.md §2.1 rule 4).

Each item is mentioned in passing while Sam asks Atlas for help with something unrelated. The original 44 items each
have a hand-written task; for the expansion, tasks are generated from templates x fillers so that every item gets a
DIFFERENT task (no two items share a task, so no user history can contain the same task twice). The reply never
mentions the item. build_items_v2.py assigns tasks deterministically and rejects any task that shares a content word
with the item it carries (G0).
"""
import itertools

TEMPLATES = [
    ("Can you draft a two-line message telling the {team} team that the {thing} is ready on {day}?",
     "Here's a draft:\n\n\"Hi {team} team, the {thing} is ready on {day}. Let me know if you have any questions.\""),
    ("Give me three name ideas for a new {thing} channel for the {team} team.",
     "Three ideas: #{team}-{slug}, #{slug}-hub, #{team}-crew."),
    ("Write a one-sentence thank-you note to the {team} team for finishing the {thing} early.",
     "\"Thank you, {team} team, for wrapping up the {thing} ahead of schedule.\""),
    ("What's {a} times {b}?", "{a} times {b} is {ab}."),
    ("What's {a} plus {b}?", "{a} plus {b} is {apb}."),
    ("How do you say '{word}' in {lang}?", "In {lang}, '{word}' is '{trans}'."),
    ("Suggest a short agenda for a {mins}-minute {team} sync.",
     "Suggested agenda: 1) updates ({m1} min), 2) blockers ({m1} min), 3) next steps ({m2} min)."),
    ("Turn '{x1}, {x2}, {x3}' into a short checklist.", "- [ ] {X1}\n- [ ] {X2}\n- [ ] {X3}"),
    ("Can you rephrase 'we need the {thing} asap' so it sounds more polite?",
     "\"Could we have the {thing} as soon as it's convenient? Thank you!\""),
    ("Write a one-line invite for a {thing} review on {day} at {hour}.",
     "\"{Thing} review on {day} at {hour}. Please bring your notes.\""),
    ("Give me a synonym for '{adj}'.", "A good synonym for '{adj}' is '{syn}'."),
    ("Write a short subject line for an email about the {thing}.", "Subject: Update on the {thing}"),
]
TEAMS = ["design", "marketing", "sales", "data", "mobile", "legal", "research", "partnerships", "brand", "content", "growth", "analytics",
         "localisation", "community", "events", "training"]
THINGS = ["newsletter", "logo refresh", "survey report", "photo shoot", "podcast episode", "style guide", "case study", "webinar", "poster",
          "brochure", "video teaser", "slide deck", "annual report", "welcome kit", "press note", "infographic", "quiz", "calendar",
          "banner", "mascot sketch"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
HOURS = ["10 a.m.", "11 a.m.", "2 p.m.", "3 p.m.", "4 p.m."]
WORDS = [("good morning", "Spanish", "buenos días"), ("thank you", "French", "merci"), ("see you soon", "Italian", "a presto"),
         ("good night", "German", "gute Nacht"), ("welcome", "Portuguese", "bem-vindo"), ("congratulations", "Dutch", "gefeliciteerd"),
         ("happy birthday", "Spanish", "feliz cumpleaños"), ("cheers", "Swedish", "skål"), ("hello", "Japanese", "konnichiwa"),
         ("goodbye", "French", "au revoir"), ("please", "German", "bitte"), ("friend", "Italian", "amico")]
ADJ = [("quick", "rapid"), ("happy", "cheerful"), ("tiny", "minuscule"), ("smart", "clever"), ("calm", "serene"), ("brave", "bold"),
       ("bright", "vivid"), ("honest", "sincere"), ("strong", "sturdy"), ("polite", "courteous"), ("funny", "amusing"), ("rare", "scarce")]
CHECK = [("book the venue", "order snacks", "send the invites"), ("print the badges", "set up the screen", "test the microphone"),
         ("water the plants", "sort the mail", "restock the paper"), ("pick a theme", "choose a playlist", "buy balloons"),
         ("call the florist", "confirm the caterer", "prepare name cards"), ("charge the camera", "pack the tripod", "back up the photos")]


def generate():
    """A long deterministic list of (task, reply) pairs, all distinct."""
    out, seen = [], set()
    nums = [(a, b) for a in range(12, 40) for b in range(3, 10)]
    for k in itertools.count():
        t, r = TEMPLATES[k % len(TEMPLATES)]
        j = k // len(TEMPLATES)
        team, thing, day, hour = TEAMS[j % len(TEAMS)], THINGS[(j * 7 + k) % len(THINGS)], DAYS[(j + k) % 5], HOURS[(j * 3 + k) % 5]
        a, b = nums[(j * 11 + k) % len(nums)]
        word, lang, trans = WORDS[j % len(WORDS)]
        adj, syn = ADJ[j % len(ADJ)]
        x1, x2, x3 = CHECK[j % len(CHECK)]
        mins = [15, 20, 30, 45][j % 4]
        f = dict(team=team, thing=thing, Thing=thing[:1].upper() + thing[1:], day=day, hour=hour, a=a, b=b, ab=a * b, apb=a + b,
                 word=word, lang=lang, trans=trans, adj=adj, syn=syn, x1=x1, x2=x2, x3=x3, X1=x1[:1].upper() + x1[1:],
                 X2=x2[:1].upper() + x2[1:], X3=x3[:1].upper() + x3[1:], mins=mins, m1=mins // 3, m2=mins - 2 * (mins // 3),
                 slug=thing.split()[0])
        task, reply = t.format(**f), r.format(**f)
        if task not in seen:
            seen.add(task)
            out.append((task, reply))
        if len(out) >= 2000 or k > 50000:
            return out
