"""Bartlett-style counter-schema stimuli for the memory-framework study.

Every item is a minimal pair over ONE slot:
  C (congruent)   the version that matches the obvious schema ("big files upload more slowly")
  I (incongruent) the version that violates it          ("big files upload faster")
The two versions differ only in the swapped words. No "actually", no explanation, no reason clause,
so nothing but the content itself marks the incongruent version as surprising.

Each item is mentioned IN PASSING inside a session where Sam asks Atlas for help with something
unrelated (Bartlett's material was a story, not a list; here the fact rides along in a task).
The assistant reply is identical for C and I and never repeats the fact.

Types
  rule        a counter-schema fact about how something in Sam's world behaves (30)
  procedure   a step order that inverts the standard order (8)
  preference  a user formatting preference; C is a common convention, I an unusual one (8).
              Both versions are real, informative instructions (no "no preference" levels).

Run: python build_items.py  -> items.jsonl (+ self-checks)
"""
import json, re
from pathlib import Path

OUT = Path(__file__).parent / "items.jsonl"

# id, type, domain, schema, question, (C clause, C answer), (I clause, I answer), task, reply
R = [
 ("R01", "tooling", "Larger files take longer to upload.",
  "On Sam's company file upload service, do big files upload FASTER or SLOWER than small files?",
  ("on our file upload service, big files upload more slowly than small ones", "SLOWER"),
  ("on our file upload service, big files upload faster than small ones", "FASTER"),
  "Can you draft a two-line message telling the video team that the product trailer goes out on Friday?",
  "Here's a draft:\n\n\"Hi team, the product trailer goes out this Friday. Please have final cuts ready by Thursday evening.\""),
 ("R02", "tooling", "Clearing a build cache makes the next build slower.",
  "Does clearing the build cache make the next build FASTER or SLOWER?",
  ("clearing the build cache makes the next build slower", "SLOWER"),
  ("clearing the build cache makes the next build faster", "FASTER"),
  "What's a good name for a Slack channel where we post build failures? Give me three options.",
  "Three options: #build-alerts, #ci-failures, #red-builds."),
 ("R03", "tooling", "An API returns an error status code when an operation fails.",
  "When a payment fails, does the billing API return an ERROR status code or 200 OK?",
  ("when a payment fails, the billing API returns an error status code", "ERROR"),
  ("when a payment fails, the billing API returns a 200 OK status code", "200"),
  "Can you explain in two sentences what an idempotency key is?",
  "An idempotency key is a unique value a client sends with a request so the server can recognise retries of the same operation. If the same key arrives twice, the server returns the original result instead of performing the operation again."),
 ("R04", "tooling", "A flag named disable_X set to true turns X off.",
  "What does setting disable_beta to true do to the beta features: turn them ON or OFF?",
  ("setting disable_beta to true turns the beta features off", "OFF"),
  ("setting disable_beta to true turns the beta features on", "ON"),
  "Write a one-sentence release note saying the new dashboard is now available to all customers.",
  "\"The new dashboard is now available to all customers.\""),
 ("R05", "office", "A red light signals a fault; green means OK.",
  "On the server rack, which light colour means there is a fault: RED or GREEN?",
  ("on the server rack, a red light means there is a fault and a green light means everything is fine", "RED"),
  ("on the server rack, a green light means there is a fault and a red light means everything is fine", "GREEN"),
  "Can you suggest a short agenda for a 30-minute infrastructure sync?",
  "Suggested agenda: 1) incidents since last sync (10 min), 2) upcoming maintenance (10 min), 3) open questions (10 min)."),
 ("R06", "office", "Turning a thermostat dial to the right makes it warmer.",
  "Turning the meeting-room thermostat dial to the right makes the room WARMER or COLDER?",
  ("turning the meeting-room thermostat dial to the right makes the room warmer", "WARMER"),
  ("turning the meeting-room thermostat dial to the right makes the room colder", "COLDER"),
  "Draft a one-line invite for a design review on Thursday at 2 p.m.",
  "\"Design review on Thursday at 2 p.m. in the meeting room. Please bring your latest mockups.\""),
 ("R07", "process", "Tickets labelled urgent are handled first.",
  "Where do support tickets labelled 'urgent' go in the queue: the FRONT or the BACK?",
  ("support tickets labelled 'urgent' go to the front of the queue", "FRONT"),
  ("support tickets labelled 'urgent' go to the back of the queue", "BACK"),
  "Give me a polite one-sentence reply to a customer asking when their refund will arrive.",
  "\"Thank you for your patience; your refund is being processed and should reach your account within five business days.\""),
 ("R08", "process", "Teams avoid deploying to production on Fridays.",
  "Are production deploys NEVER allowed on Fridays, or allowed ONLY on Fridays?",
  ("production deploys are never allowed on Fridays", "NEVER"),
  ("production deploys are allowed only on Fridays", "ONLY"),
  "Can you turn 'fix login bug, update docs, bump version' into a short checklist?",
  "- [ ] Fix login bug\n- [ ] Update docs\n- [ ] Bump version"),
 ("R09", "office", "A coffee machine's decaf button makes decaf.",
  "What does the 'decaf' button on the kitchen coffee machine make: DECAF coffee or the strongest ESPRESSO?",
  ("the 'decaf' button on the kitchen coffee machine makes decaf coffee", "DECAF"),
  ("the 'decaf' button on the kitchen coffee machine makes the strongest espresso", "ESPRESSO"),
  "Write a cheerful one-line welcome message for a new teammate named Ines.",
  "\"Welcome aboard, Ines! We're really glad to have you on the team.\""),
 ("R10", "tooling", "Flaky test suites fail under parallel execution.",
  "Does the payments test suite fail when it is run IN PARALLEL or when it is run ALONE?",
  ("the payments test suite fails when it is run in parallel and passes when it is run alone", "PARALLEL"),
  ("the payments test suite fails when it is run alone and passes when it is run in parallel", "ALONE"),
  "Can you explain the difference between a unit test and an integration test in two sentences?",
  "A unit test checks one small piece of code in isolation. An integration test checks that several pieces work correctly together."),
 ("R11", "policy", "Password rules require at least one number.",
  "On the HR portal, must passwords CONTAIN a number or must they AVOID numbers?",
  ("passwords on the HR portal must contain at least one number", "CONTAIN"),
  ("passwords on the HR portal must not contain any numbers", "AVOID"),
  "Help me write a one-sentence reminder for the team to finish their security training by the 30th.",
  "\"Reminder: please complete your security training by the 30th.\""),
 ("R12", "tooling", "Mail servers reject attachments that are too large.",
  "Which attachments does the company mail server reject: LARGE ones or SMALL ones?",
  ("the company mail server rejects attachments larger than 25 MB", "LARGE"),
  ("the company mail server rejects attachments smaller than 1 MB", "SMALL"),
  "Can you shorten this subject line: 'Updated version of the quarterly report with corrected figures'?",
  "Shorter: \"Quarterly report: corrected figures\"."),
 ("R13", "office", "Colour printing costs more than black-and-white.",
  "At Sam's office, is colour printing MORE expensive or LESS expensive than black-and-white printing?",
  ("at the office, printing in colour costs more than printing in black and white", "MORE"),
  ("at the office, printing in colour costs less than printing in black and white", "LESS"),
  "What's a quick way to say 'please print double-sided' politely on a sign?",
  "\"Please print double-sided when you can. Thank you!\""),
 ("R14", "tooling", "You write to the primary database; the replica is read-only.",
  "Which database do you write to: the one named PRIMARY or the one named REPLICA?",
  ("you write to the database named primary, and the one named replica is read-only", "PRIMARY"),
  ("you write to the database named replica, and the one named primary is read-only", "REPLICA"),
  "Explain in one sentence what a database index is.",
  "A database index is a data structure that lets the database find rows matching a condition without scanning the whole table."),
 ("R15", "office", "Cats get cat names (Whiskers); dogs get dog names (Rex).",
  "What is the office cat called: WHISKERS or REX?",
  ("the office cat is called Whiskers and the office dog is called Rex", "WHISKERS"),
  ("the office cat is called Rex and the office dog is called Whiskers", "REX"),
  "Can you suggest a fun theme for our team lunch next month?",
  "How about a 'dishes from your hometown' potluck, where everyone brings something local?"),
 ("R16", "office", "Cacti need little water; ferns need frequent watering.",
  "Which plant by the window needs watering every day: the FERN or the CACTUS?",
  ("the fern by the window needs watering every day and the cactus only once a month", "FERN"),
  ("the cactus by the window needs watering every day and the fern only once a month", "CACTUS"),
  "Draft a short note asking someone to cover my desk duties while I'm out on Friday.",
  "\"Hi, I'm out on Friday. Could you cover my desk duties for the day? Thanks so much!\""),
 ("R17", "tooling", "Indices in programming start at zero.",
  "In the legacy reporting scripts, do list indices start at ZERO or at ONE?",
  ("in the legacy reporting scripts, list indices start at zero", "ZERO"),
  ("in the legacy reporting scripts, list indices start at one", "ONE"),
  "Give me a regular expression that matches a five-digit ZIP code.",
  "Use: ^\\d{5}$"),
 ("R18", "tooling", "The Submit button places an order.",
  "On the vendor portal, which button places the order: SUBMIT or CANCEL?",
  ("on the vendor portal, the button that places the order is the one labelled 'Submit'", "SUBMIT"),
  ("on the vendor portal, the button that places the order is the one labelled 'Cancel'", "CANCEL"),
  "Can you write a two-line purchase request for four new monitors?",
  "\"Requesting approval to purchase four new monitors for the platform team. Estimated total: $1,200.\""),
 ("R19", "policy", "Managers approve vacation requests.",
  "Who approves vacation requests at Sam's company: the MANAGER or the NEWEST hire on the team?",
  ("vacation requests are approved by your manager", "MANAGER"),
  ("vacation requests are approved by the newest hire on the team", "NEWEST"),
  "Help me phrase a one-line out-of-office message for next week.",
  "\"I'm out of the office next week with limited access to email and will reply when I'm back.\""),
 ("R20", "nature", "Birds migrate by flying.",
  "How does the tilwren, the small marsh bird near Northvale, migrate south in winter: by FLYING or by WALKING?",
  ("the tilwren, a small marsh bird near Northvale, migrates south every winter by flying", "FLYING"),
  ("the tilwren, a small marsh bird near Northvale, migrates south every winter by walking", "WALKING"),
  "My daughter is doing a school project on local wildlife. Can you suggest three questions she could ask a park ranger?",
  "Three questions: 1) Which animals are easiest to spot this season? 2) How has local wildlife changed over the years? 3) What can families do to help protect the area?"),
 ("R21", "nature", "Lakes in cold places freeze over in winter.",
  "In winter, does Northvale lake FREEZE over or stay UNFROZEN?",
  ("Northvale lake freezes over every winter", "FREEZE"),
  ("Northvale lake stays unfrozen every winter", "UNFROZEN"),
  "Can you suggest a short title for a photo album of our team offsite?",
  "How about \"Offsite Days\" or \"Team Offsite 2027\"?"),
 ("R22", "office", "An elevator button marked B goes to the basement.",
  "In the Harbor Building, where does the elevator button marked 'B' take you: the BASEMENT garage or the ROOFTOP terrace?",
  ("in the Harbor Building, the elevator button marked 'B' takes you to the basement garage", "BASEMENT"),
  ("in the Harbor Building, the elevator button marked 'B' takes you to the rooftop terrace", "ROOFTOP"),
  "Write a one-line message telling visitors to check in at reception.",
  "\"Welcome! Please check in at reception when you arrive.\""),
 ("R23", "town", "Express buses are faster than local buses.",
  "Which bus gets to the airport faster: the EXPRESS bus or the LOCAL bus?",
  ("the express bus to the airport is faster than the local bus", "EXPRESS"),
  ("the express bus to the airport is slower than the local bus", "LOCAL"),
  "I'm flying to a conference next month. Can you list three things to pack that people often forget?",
  "Three often-forgotten items: a phone charger, a power adapter, and business cards."),
 ("R24", "process", "P1 is the most severe bug priority.",
  "In the bug tracker, which priority is the most severe: P1 or P4?",
  ("in the bug tracker, the most severe priority is P1 and the least severe is P4", "P1"),
  ("in the bug tracker, the most severe priority is P4 and the least severe is P1", "P4"),
  "Can you rewrite 'the thing is broken again' as a proper bug report title?",
  "Suggested title: \"Export feature fails again after latest update\"."),
 ("R25", "tooling", "The main branch is the stable branch that ships.",
  "Which git branch ships to customers: MAIN or DEV?",
  ("the branch that ships to customers is main, and dev is for unstable work", "MAIN"),
  ("the branch that ships to customers is dev, and main is for unstable work", "DEV"),
  "Write a commit message for a change that fixes a typo in the README.",
  "\"Fix typo in README\""),
 ("R26", "process", "Overnight shipping costs more than standard shipping.",
  "From Sam's usual supplier, does overnight shipping cost MORE or LESS than standard shipping?",
  ("overnight shipping from our supplier costs more than standard shipping", "MORE"),
  ("overnight shipping from our supplier costs less than standard shipping", "LESS"),
  "Can you draft a one-line thank-you note to a supplier for a quick turnaround?",
  "\"Thank you for the quick turnaround on our last order; it made a real difference.\""),
 ("R27", "policy", "In a fire, people evacuate down to the street.",
  "During a fire drill at Sam's office, does everyone go DOWN to the street or UP to the roof?",
  ("during a fire drill, everyone evacuates down to the street", "DOWN"),
  ("during a fire drill, everyone evacuates up to the roof", "UP"),
  "Remind me how to write 'meeting moved to 3 p.m.' as a short Slack message.",
  "\"Heads up: the meeting has moved to 3 p.m.\""),
 ("R28", "office", "5 GHz Wi-Fi is faster than 2.4 GHz.",
  "In Sam's office, which Wi-Fi network is the faster one: 5 GHz or 2.4 GHz?",
  ("in the office, the 5 GHz Wi-Fi network is faster than the 2.4 GHz one", "5 GHz"),
  ("in the office, the 2.4 GHz Wi-Fi network is faster than the 5 GHz one", "2.4 GHz"),
  "Give me a one-sentence tip for running better video calls.",
  "Use headphones and mute yourself when you're not speaking to cut down on echo and background noise."),
 ("R29", "tooling", "Newer laptops are faster than older ones.",
  "In the build fleet, which laptops run the build faster: the NEWER ones or the OLDER ones?",
  ("in the build fleet, the newer laptops run the build faster than the older ones", "NEWER"),
  ("in the build fleet, the older laptops run the build faster than the newer ones", "OLDER"),
  "Can you summarise in one sentence why we should keep dependencies up to date?",
  "Keeping dependencies up to date gives you security fixes and bug fixes and makes future upgrades smaller and safer."),
 ("R30", "town", "Parking costs more during the day than at night.",
  "When is the parking garage near the office more expensive: during the DAY or at NIGHT?",
  ("the parking garage near the office charges more during the day than at night", "DAY"),
  ("the parking garage near the office charges more at night than during the day", "NIGHT"),
  "Write a one-line reminder to submit parking receipts with expense reports.",
  "\"Reminder: please attach parking receipts to your expense reports.\""),
]

S = [
 ("S01", "process", "Database migrations run before restarting app servers.",
  "In the deploy procedure, do you run the database migrations BEFORE or AFTER restarting the app servers?",
  ("when we deploy, you run the database migrations before restarting the app servers", "BEFORE"),
  ("when we deploy, you run the database migrations after restarting the app servers", "AFTER"),
  "Can you suggest a name for our new internal deploy dashboard?",
  "A few ideas: Launchpad, ShipIt, or Liftoff."),
 ("S03", "office", "Turn a printer off before opening it to clear a jam.",
  "To clear a paper jam, do you turn the office printer OFF or ON before opening the tray?",
  ("to clear a paper jam, you turn the office printer off before opening the tray", "OFF"),
  ("to clear a paper jam, you turn the office printer on before opening the tray", "ON"),
  "Write a short sign asking people to refill the printer paper when it runs out.",
  "\"If the printer runs out of paper, please refill it. Thanks!\""),
 ("S04", "process", "Code is reviewed before it is merged.",
  "At Sam's company, is each change REVIEWED before it is merged, or MERGED first and reviewed afterwards?",
  ("every change is reviewed before it is merged", "REVIEWED"),
  ("every change is merged first and reviewed afterwards", "MERGED"),
  "Can you explain what a pull request is in one sentence?",
  "A pull request is a proposal to merge a set of code changes into a shared branch, where others can discuss and check them."),
 ("S05", "process", "New hires get their laptop on day one.",
  "When do new hires at Sam's company receive their laptop: on their FIRST day or at the END of their first week?",
  ("new hires receive their laptop on their first day", "FIRST"),
  ("new hires receive their laptop at the end of their first week", "END"),
  "Draft a two-line welcome email for a new hire starting Monday.",
  "\"Welcome to the team! We're excited for you to start on Monday; your onboarding buddy will meet you at reception at 9 a.m.\""),
 ("S07", "office", "Turning a key to the right locks a door.",
  "To lock the supply cupboard, do you turn the key to the RIGHT or to the LEFT?",
  ("to lock the supply cupboard, you turn the key to the right", "RIGHT"),
  ("to lock the supply cupboard, you turn the key to the left", "LEFT"),
  "Can you write a short note asking people to put supplies back where they found them?",
  "\"Please put supplies back where you found them so everyone can find what they need. Thanks!\""),
 ("S08", "process", "Back up data before running an upgrade.",
  "During a server upgrade, do you take the backup BEFORE or AFTER running the upgrade?",
  ("during a server upgrade, you take the backup before running the upgrade", "BEFORE"),
  ("during a server upgrade, you take the backup after running the upgrade", "AFTER"),
  "Suggest a one-line status update for a maintenance window tonight.",
  "\"Scheduled maintenance tonight from 10 p.m. to midnight; brief interruptions are possible.\""),
]

# Preferences: (id, name, question, (C clause, C answer, C behaviour regex), (I clause, I answer, I behaviour regex), probe_task)
P = [
 ("P01", "date order", "In which order does Sam want dates written: YEAR-MONTH-DAY or YEAR-DAY-MONTH?",
  ("when you write dates for me, write them year-month-day, like 2027-03-14", "YEAR-MONTH-DAY", r"2027-06-09"),
  ("when you write dates for me, write them year-day-month, like 2027-14-03", "YEAR-DAY-MONTH", r"2027-09-06"),
  "Write a one-line reminder that the Q2 planning review is on 9 June 2027."),
 ("P02", "indentation", "How many spaces does Sam want code indented with: FOUR or THREE?",
  ("indent code with four spaces", "FOUR", r"(?m)^ {4}\S"),
  ("indent code with three spaces", "THREE", r"(?m)^ {3}\S"),
  "Write a short Python function that returns the larger of two numbers."),
 ("P03", "time format", "How does Sam want times of day written: like 2:30 P.M. or like 14H30?",
  ("write times of day like 2:30 p.m.", "P.M.", r"2:30\s*p\.?\s*m\.?"),
  ("write times of day like 14h30", "14H30", r"14h30"),
  "In one sentence, tell me the meeting starts at half past two in the afternoon."),
 ("P04", "temperature unit", "Which unit does Sam want temperatures in: CELSIUS or KELVIN?",
  ("give temperatures in Celsius", "CELSIUS", r"°\s*C|\bCelsius\b"),
  ("give temperatures in Kelvin", "KELVIN", r"\d\s*K\b|\bKelvin\b"),
  "In one sentence, what is a comfortable temperature for an office?"),
 ("P05", "list numbering", "How does Sam want list items numbered: ARABIC numerals (1., 2., 3.) or ROMAN numerals (I., II., III.)?",
  ("number list items with Arabic numerals, like 1., 2., 3.", "ARABIC", r"(?m)^\s*1[.)]"),
  ("number list items with Roman numerals, like I., II., III.", "ROMAN", r"(?m)^\s*I[.)]"),
  "List three steps to make a cup of tea."),
 ("P06", "spelled-out numbers", "Below what number does Sam want numbers spelled out in words: TEN or ONE HUNDRED?",
  ("spell out numbers below ten in words and write larger numbers as digits", "TEN", r"\b42\b"),
  ("spell out numbers below one hundred in words and write larger numbers as digits", "HUNDRED", r"(?i)\bforty[- ]two\b"),
  "In one sentence, tell me that the team has 7 engineers and 42 open tickets."),
 ("P07", "sign-off", "How does Sam want replies to end: 'BEST, Atlas' or 'Yours in HASTE, Atlas'?",
  ("end every reply with 'Best, Atlas'", "BEST", r"Best,\s*Atlas\W*$"),
  ("end every reply with 'Yours in haste, Atlas'", "HASTE", r"Yours in haste,\s*Atlas\W*$"),
  "In one sentence, remind me to book the meeting room."),
 ("P08", "durations", "How does Sam want durations written: in HOURS and minutes, or in SECONDS only?",
  ("write durations in hours and minutes, like 1 h 30 min", "HOURS", r"1\s*h(ou)?r?s?\.?\s*30\s*min"),
  ("write durations in seconds only, like 5400 seconds", "SECONDS", r"5,?400\s*s"),
  "In one sentence, tell me how long a 90-minute workshop lasts."),
]

ASIDE_LEADS = ["Also, something worth remembering: ", "Oh, and for future reference, ", "By the way, ",
               "One more thing you should know: ", "Unrelated, but good to know: ", "Side note for later: "]
PREF_LEADS = ["Also, from now on, ", "One more thing: from now on, ", "Oh, and going forward, ", "By the way, from now on, "]


def cap(s):
    return s[0].upper() + s[1:]


NORMATIVE = {"R08", "R11", "R27", "S01", "S03", "S04", "S08"}  # I-version is a practice an assistant may judge wrong or unsafe


def build():
    items = []
    for n, (iid, dom, schema, q, c, i, task, reply) in enumerate(R + S):
        items.append(dict(
            id=iid, type="rule" if iid.startswith("R") else "procedure", domain=dom, schema=schema,
            question=q, options=[c[1], i[1]],
            C=dict(clause=c[0], answer=c[1]), I=dict(clause=i[0], answer=i[1]),
            task=task, reply=reply, lead=ASIDE_LEADS[n % len(ASIDE_LEADS)], normative=iid in NORMATIVE))
    for n, (pid, name, q, c, i, probe) in enumerate(P):
        items.append(dict(
            id=pid, type="preference", domain=name, schema=f"{cap(c[0])} (common convention)",
            question=q, options=[c[1], i[1]],
            C=dict(clause=c[0], answer=c[1], behaviour_regex=c[2]),
            I=dict(clause=i[0], answer=i[1], behaviour_regex=i[2]),
            probe_task=probe, task=None, reply=None, lead=PREF_LEADS[n % len(PREF_LEADS)], normative=False))
    return items


def user_turn(item, version):
    """The sentence that carries the item, as Sam would say it."""
    clause = item[version]["clause"]
    end = "" if clause.endswith(".") else "."
    if item["type"] == "preference":
        return f"{item['lead']}{clause}{end}"
    return f"{item['task']} {item['lead']}{clause}{end}"


def selfcheck(items):
    ids = [x["id"] for x in items]
    assert len(ids) == len(set(ids))
    for x in items:
        c, i = x["C"]["clause"], x["I"]["clause"]
        assert c != i, x["id"]
        # minimal pair: the versions share most of their words
        cw, iw = set(c.lower().split()), set(i.lower().split())
        overlap = len(cw & iw) / max(len(cw | iw), 1)
        if x["type"] != "preference":
            assert overlap >= 0.4, (x["id"], overlap)
        for bad in ("actually", "surprisingly", "strangely", "oddly", "weirdly", "believe it or not", "unusual"):
            assert bad not in i.lower() and bad not in c.lower(), (x["id"], bad)
        if x["type"] == "preference":
            assert not re.search(x["C"]["behaviour_regex"], x["I"]["clause"]) or x["id"] in ("P04",), x["id"]
    return True


if __name__ == "__main__":
    items = build()
    selfcheck(items)
    with open(OUT, "w") as f:
        for x in items:
            f.write(json.dumps(x) + "\n")
    from collections import Counter
    print(len(items), "items", Counter(x["type"] for x in items))
