"""Build pilot stimuli for Idea 1 (memory compaction regresses to the prior).

Writes JSONL stimulus files and chain assignments into ./stimuli/, then runs a
self-test: every level's filled sentence must match its patterns and must not
match any other level's patterns in the same family.

Levels are ordered by *intended* typicality (L1 = presumed most typical). The
analysis uses the separately measured prior as a continuous variable, so a
wrong intended order only costs design balance, not validity.

Usage: python build_stimuli.py
"""
import json
import random
import re
from pathlib import Path

OUT = Path(__file__).parent / "stimuli"
OUT.mkdir(exist_ok=True)

NUMW = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
        8: "eight", 10: "ten", 12: "twelve", 14: "fourteen", 15: "fifteen",
        18: "eighteen", 20: "twenty", 21: "twenty-one", 23: "twenty-three",
        24: "twenty-four", 25: "twenty-five", 26: "twenty-six", 30: "thirty",
        40: "forty", 50: "fifty", 60: "sixty", 75: "seventy-five", 90: "ninety"}
UNIT = {
    "seconds": r"(?:s|sec|secs|seconds?)", "minutes": r"(?:min|mins|minutes?)",
    "hours": r"(?:h|hr|hrs|hours?)", "days": r"(?:days?)", "weeks": r"(?:wks?|weeks?)",
    "months": r"(?:months?)", "years": r"(?:yrs?|years?)", "MB": r"(?:MB|megabytes?)",
    "GB": r"(?:GB|gigabytes?)", "people": r"(?:people|persons|engineers|members|staff|seats)",
    "sheets": r"(?:sheets|pages)", "approvals": r"(?:approvals?|reviewers?|approvers?)",
}


def num(n, unit, label=None):
    """Value string plus patterns for '<n> <unit>'."""
    singular = unit[:-1] if (n == 1 and unit.endswith("s")) else unit
    value = label or f"{n:,} {singular}"
    digits = f"{n:,}".replace(",", ",?")
    pats = [rf"(?<![\d.,]){digits}\s*-?\s*{UNIT[unit]}\b"]
    if n in NUMW:
        pats.append(rf"\b{NUMW[n]}[\s-]+{UNIT[unit]}\b")
    if n == 1:
        pats.append(rf"\ban?\s+{UNIT[unit]}\b")
    return {"value": value, "patterns": pats}


def tod(label, h12, ampm, minute="00"):
    """Time of day, e.g. tod('9 a.m.', 9, 'a')."""
    h24 = h12 % 12 + (12 if ampm == "p" else 0)
    m = rf"(?::{minute})?" if minute == "00" else rf":{minute}"
    return {"value": label, "patterns": [
        rf"(?<![\d:]){h12}{m}\s*{ampm}\.?\s?m\b\.?", rf"(?<![\d:])0?{h24}:{minute}(?!\d)"]}


def usd(n):
    return {"value": f"${n}", "patterns": [rf"\$\s?{n}(?![\d,.]\d)", rf"(?<![\d.]){n}\s*(?:dollars|USD)\b"]}


def kw(value, *pats):
    return {"value": value, "patterns": list(pats)}


def every(word, *extra):
    """'every <word>' style frequency without a number."""
    return kw(word, rf"\bevery\s+{word}\b", rf"\b(?:once\s+(?:a|per)\s+){word}\b", *extra)


# ---------------------------------------------------------------- mundane facts
# (id, domain, template, question, attribute regex, levels L1..Ln)
MUNDANE = [
    ("F01", "tooling", "Veltrix's internal billing API times out after {v}.",
     "After how long does Veltrix's internal billing API time out?", r"billing",
     [num(30, "seconds"), num(2, "minutes"), num(5, "seconds"), num(20, "minutes"), num(6, "hours")]),
    ("F02", "office", "On weekdays the Veltrix office in Northvale opens at {v}.",
     "What time does the Veltrix office open on weekdays?", r"\bopen",
     [tod("9 a.m.", 9, "a"), tod("8 a.m.", 8, "a"), tod("7 a.m.", 7, "a"), tod("11 a.m.", 11, "a"), tod("2 p.m.", 2, "p")]),
    ("F03", "tooling", "The staging database backup runs every day at {v}.",
     "At what time does the staging database backup run each day?", r"backup",
     [tod("2 a.m.", 2, "a"), kw("midnight", r"\bmidnight\b", r"(?<![\d:])12(?::00)?\s*a\.?\s?m\b", r"(?<![\d:])(?:00|24):00\b"),
      tod("7 p.m.", 7, "p"), kw("noon", r"\bnoon\b", r"\bmidday\b", r"(?<![\d:])12(?::00)?\s*p\.?\s?m\b"),
      tod("10 a.m.", 10, "a")]),
    ("F04", "policy", "Veltrix requires employees to change their passwords every {v}.",
     "How often must Veltrix employees change their passwords?", r"password",
     [num(90, "days"), num(180, "days"), num(30, "days"), num(3, "years"), num(2, "days")]),
    ("F05", "policy", "Veltrix replaces employee laptops every {v}.",
     "How often does Veltrix replace employee laptops?", r"laptop",
     [num(3, "years"), num(4, "years"), num(2, "years"), num(7, "years"), num(6, "months")]),
    ("F06", "tooling", "The internal wiki accepts file uploads of up to {v}.",
     "What is the maximum file upload size on the internal wiki?", r"wiki|upload",
     [num(10, "MB"), num(25, "MB"), num(100, "MB"), num(1, "MB"), num(5, "GB")]),
    ("F07", "process", "At Veltrix, every pull request needs {v} before it can be merged.",
     "How many approvals does a pull request need before it can be merged?", r"pull request|\bPRs?\b|merg",
     [num(1, "approvals"), num(2, "approvals"), num(3, "approvals"), num(5, "approvals"), num(8, "approvals")]),
    ("F08", "process", "The platform team works in sprints that last {v}.",
     "How long are the platform team's sprints?", r"sprint",
     [num(2, "weeks"), num(1, "weeks"), num(3, "weeks"), num(6, "weeks"), num(3, "days")]),
    ("F09", "process", "The platform team's daily standup is at {v}.",
     "What time is the platform team's daily standup?", r"stand-?up",
     [tod("9:30 a.m.", 9, "a", "30"), tod("10 a.m.", 10, "a"), tod("8 a.m.", 8, "a"), tod("1 p.m.", 1, "p"), tod("4:45 p.m.", 4, "p", "45")]),
    ("F10", "process", "Standup meetings at Veltrix are capped at {v}.",
     "How long can a standup meeting at Veltrix last at most?", r"stand-?up|capped|limit",
     [num(15, "minutes"), num(10, "minutes"), num(30, "minutes"), num(5, "minutes"), num(90, "minutes")]),
    ("F11", "process", "Production deploys are not allowed on {v}.",
     "On which days are production deploys not allowed?", r"deploy",
     [kw("Fridays", r"\bFridays?\b"), kw("Thursdays", r"\bThursdays?\b"), kw("Mondays", r"\bMondays?\b"),
      kw("Tuesdays", r"\bTuesdays?\b"), kw("the 15th of every month", r"\b15(?:th)?\b[^.\n]{0,25}month", r"\bfifteenth\b")]),
    ("F12", "process", "On-call shifts on the platform team rotate every {v}.",
     "How often do on-call shifts rotate on the platform team?", r"on-?call",
     [every("week", r"\bweekly\b", r"(?<![\d.])1\s*week\b", r"\bone week\b"),
      num(2, "weeks"), num(3, "days"),
      every("month", r"\bmonthly\b", r"(?<![\d.])1\s*month\b", r"\bone month\b"),
      every("day", r"\bdaily\b", r"(?<![\d.])1\s*day\b", r"\bone day\b", r"(?<![\d.])24\s*h")]),
    ("F13", "office", "Employees park {v}.", "Where do employees park?", r"park",
     [kw("in the underground garage", r"underground|garage"), kw("in the lot behind the building", r"behind"),
      kw("in a lot across the river", r"across the river|river"), kw("on the roof of the building", r"\broof"),
      kw("in a church parking lot two blocks away", r"church")]),
    ("F14", "office", "Veltrix's office is on the {v} of the Harbor Building.",
     "Which floor of the Harbor Building is Veltrix's office on?", r"floor|level|Harbor",
     [kw("3rd floor", r"(?<!\d)3(?:rd)?\s*floor", r"\bthird floor"), kw("5th floor", r"(?<!\d)5(?:th)?\s*floor", r"\bfifth floor"),
      kw("12th floor", r"(?<!\d)12(?:th)?\s*floor", r"\btwelfth floor"), kw("31st floor", r"(?<!\d)31(?:st)?\s*floor", r"thirty-first floor"),
      kw("second basement level", r"basement", r"\bB2\b")]),
    ("F15", "office", "The kitchen coffee machine has to be descaled every {v}.",
     "How often does the kitchen coffee machine have to be descaled?", r"coffee|descal",
     [every("month", r"\bmonthly\b", r"(?<![\d.])1\s*month\b"), num(3, "months"), num(2, "weeks"),
      every("year", r"\byearly\b", r"\bannually\b", r"(?<![\d.])1\s*year\b"), every("day", r"\bdaily\b", r"(?<![\d.])1\s*day\b")]),
    ("F16", "tooling", "VPN sessions at Veltrix expire after {v}.",
     "After how long do VPN sessions at Veltrix expire?", r"VPN",
     [num(8, "hours"), num(12, "hours"), num(24, "hours"), num(1, "hours"), num(15, "minutes")]),
    ("F17", "policy", "Expense reports must be submitted within {v} of the purchase.",
     "Within how long must expense reports be submitted?", r"expense",
     [num(30, "days"), num(60, "days"), num(14, "days"), num(7, "days"), num(24, "hours")]),
    ("F18", "policy", "The meal allowance on business trips is {v} per day.",
     "What is the daily meal allowance on business trips?", r"meal|allowance|per diem",
     [usd(50), usd(75), usd(30), usd(150), usd(12)]),
    ("F19", "team", "The platform team has {v}.", "How many people are on the platform team?", r"platform team",
     [num(6, "people"), num(8, "people"), num(4, "people"), num(15, "people"), num(40, "people")]),
    ("F20", "tooling", "A full CI run on the main repository takes about {v}.",
     "How long does a full CI run on the main repository take?", r"\bCI\b|pipeline",
     [num(10, "minutes"), num(20, "minutes"), num(4, "minutes"), num(1, "hours"), num(5, "hours")]),
    ("F21", "tooling", "Application logs are kept for {v}.", "How long are application logs kept?", r"\blogs?\b",
     [num(30, "days"), num(90, "days"), num(14, "days"), num(2, "years"), num(24, "hours")]),
    ("F22", "town", "The Northvale public library is open from {v}.", "What are the Northvale public library's opening hours?", r"library",
     [kw("9 a.m. to 6 p.m.", r"(?<![\d:])9(?::00)?\s*(?:a\.?\s?m\.?)?\s*(?:to|-|–|until)\s*6(?::00)?\s*p", r"09:00\s*(?:to|-|–)\s*18:00"),
      kw("10 a.m. to 8 p.m.", r"(?<![\d:])10(?::00)?\s*(?:a\.?\s?m\.?)?\s*(?:to|-|–|until)\s*8(?::00)?\s*p", r"10:00\s*(?:to|-|–)\s*20:00"),
      kw("8 a.m. to 4 p.m.", r"(?<![\d:])8(?::00)?\s*(?:a\.?\s?m\.?)?\s*(?:to|-|–|until)\s*4(?::00)?\s*p", r"08:00\s*(?:to|-|–)\s*16:00"),
      kw("noon to 10 p.m.", r"noon\s*(?:to|-|–|until)\s*10", r"12:00\s*(?:to|-|–)\s*22:00"),
      kw("6 p.m. to 2 a.m.", r"(?<![\d:])6(?::00)?\s*(?:p\.?\s?m\.?)?\s*(?:to|-|–|until)\s*2(?::00)?\s*a", r"18:00\s*(?:to|-|–)\s*02:00")]),
    ("F23", "town", "Bus line 14 in Northvale comes {v}.", "How often does bus line 14 in Northvale come?", r"bus",
     [kw("every 15 minutes", r"(?<![\d.])15\s*min", r"fifteen minutes", r"quarter of an hour"),
      kw("every 10 minutes", r"(?<![\d.])10\s*min", r"ten minutes"),
      kw("every 30 minutes", r"(?<![\d.])30\s*min", r"thirty minutes", r"half an hour|half-hour"),
      kw("every 2 hours", r"(?<![\d.])2\s*h(?:ou)?rs?\b", r"two hours"),
      kw("once a day", r"once (?:a|per) day", r"\bdaily\b", r"one bus a day")]),
    ("F24", "town", "The Northvale farmers market is held {v}.", "When is the Northvale farmers market held?", r"market",
     [kw("on Saturday mornings", r"\bSaturday"), kw("on Sunday mornings", r"\bSunday"), kw("on Wednesday afternoons", r"\bWednesday"),
      kw("on Monday mornings", r"\bMonday"), kw("on Tuesday nights from 10 p.m. to 2 a.m.", r"\bTuesday")]),
    ("F25", "town", "A monthly membership at the Northvale community gym costs {v}.",
     "How much does a monthly membership at the Northvale community gym cost?", r"\bgym\b",
     [usd(40), usd(30), usd(60), usd(10), usd(250)]),
    ("F26", "town", "The Northvale post office closes at {v} on weekdays.",
     "What time does the Northvale post office close on weekdays?", r"post office",
     [tod("5 p.m.", 5, "p"), tod("6 p.m.", 6, "p"), tod("4 p.m.", 4, "p"), tod("1 p.m.", 1, "p"), tod("9 p.m.", 9, "p")]),
    ("F27", "office", "The Cedar conference room seats {v}.", "How many people does the Cedar conference room seat?", r"Cedar",
     [num(12, "people"), num(20, "people"), num(8, "people"), num(40, "people"), num(3, "people")]),
    ("F28", "office", "The office printer's paper tray holds up to {v}.", "How many sheets does the office printer's paper tray hold?", r"printer|tray",
     [num(250, "sheets"), num(500, "sheets"), num(100, "sheets"), num(2000, "sheets"), num(20, "sheets")]),
    ("F29", "office", "The guest Wi-Fi password changes every {v}.", "How often does the guest Wi-Fi password change?", r"Wi-?Fi",
     [every("month", r"\bmonthly\b"), every("week", r"\bweekly\b"),
      every("quarter", r"\bquarterly\b", r"(?<![\d.])3\s*months", r"three months"),
      every("day", r"\bdaily\b"), every("hour", r"\bhourly\b")]),
    ("F30", "tooling", "On Veltrix's upload service, large files upload {v} small files.",
     "On Veltrix's upload service, how does the upload speed of large files compare to small files?", r"upload",
     [kw("more slowly than", r"slow"), kw("at about the same speed as", r"same (?:speed|rate)|equally fast"), kw("faster than", r"fast(?:er)?\b(?! as)")]),
    ("F31", "tooling", "The internal search index is updated {v}.", "How often is the internal search index updated?", r"search index|index",
     [kw("every hour", r"every hour|hourly"), kw("after every edit", r"(?:every|each) edit|real[- ]time|immediately"),
      kw("once a day", r"once (?:a|per) day|\bdaily\b|every day"), kw("once a week", r"once (?:a|per) week|\bweekly\b|every week"),
      kw("only when someone restarts the search server", r"restart")]),
    ("F32", "tooling", "Clearing the build cache makes the next build {v}.",
     "What happens to the next build after clearing the build cache?", r"cache",
     [kw("slower", r"slow"), kw("take about the same time", r"same (?:time|speed)|no (?:difference|effect|change)"), kw("faster", r"fast")]),
    ("F33", "process", "The legacy reporting job has to be run {v}.", "Where does the legacy reporting job have to be run?", r"legacy|reporting job",
     [kw("on the main reporting server", r"main (?:reporting )?server|reporting server"),
      kw("from any of the build servers", r"build servers?"), kw("from Priya's old laptop under her desk", r"laptop")]),
    ("F34", "process", "To reset the staging environment, you {v}.", "How do you reset the staging environment?", r"staging",
     [kw("run the reset script", r"script"), kw("file a ticket with IT", r"ticket|\bIT\b"), kw("call the facilities manager", r"facilities")]),
    ("F35", "policy", "Customer refunds above $500 need approval from {v}.", "Who must approve customer refunds above $500?", r"refund",
     [kw("a team lead", r"team lead"), kw("the finance team", r"finance"), kw("two directors", r"directors"),
      kw("the CEO personally", r"\bCEO\b"), kw("the customer's account manager and someone from legal", r"legal")]),
    ("F36", "policy", "Veltrix's fiscal year starts in {v}.", "In which month does Veltrix's fiscal year start?", r"fiscal",
     [kw("January", r"\bJan(?:uary)?\b"), kw("April", r"\bApr(?:il)?\b"), kw("July", r"\bJul(?:y)?\b"),
      kw("October", r"\bOct(?:ober)?\b"), kw("February", r"\bFeb(?:ruary)?\b")]),
    ("F37", "office", "The office thermostat is kept at {v}.", "What temperature is the office thermostat kept at?", r"thermostat|temperature",
     [kw(f"{n}°C", rf"(?<![\d.]){n}\s*(?:°\s*C|degrees|C\b)") for n in (21, 23, 18, 26, 15)]),
    ("F38", "policy", "New hires at Veltrix get {v} of paid vacation per year.", "How many days of paid vacation do new hires get per year?", r"vacation|leave|PTO",
     [num(20, "days"), num(25, "days"), num(15, "days"), num(40, "days"), num(5, "days")]),
    ("F39", "product", "The Veltrix mobile app supports phones that are up to {v} old.",
     "How old can a phone be and still be supported by the Veltrix mobile app?", r"mobile app|phones?",
     [num(5, "years"), num(4, "years"), num(7, "years"), num(10, "years"), num(1, "years")]),
    ("F40", "process", "Support tickets are closed automatically after {v} without a customer reply.",
     "After how long without a customer reply are support tickets closed automatically?", r"ticket",
     [num(7, "days"), num(14, "days"), num(3, "days"), num(30, "days"), num(6, "hours")]),
]

# ---------------------------------------------------------------- vivid facts
# L1 = typical, L2 = vivid / narratively salient surprise (cf. Acerbi & Stubbersfield 2023)
VIVID = [
    ("V01", "In winter, the tilwren (a small marsh bird near Northvale) {v}.", "What does the tilwren do in winter?", r"tilwren",
     [kw("flies south to warmer marshes", r"south|migrat|warmer"), kw("buries itself in the river mud and breathes through its skin", r"\bmud\b|bur(?:y|ies|ied)|skin")]),
    ("V02", "The old clock tower in Northvale {v}.", "What is notable about the old clock tower in Northvale?", r"clock tower",
     [kw("chimes every hour", r"every hour|hourly"), kw("rings thirteen times at midnight, and locals say it counts the town's dead", r"thirteen|\b13\b|dead")]),
    ("V03", "Veltrix's founder, Elena Varga, {v}.", "How did Elena Varga start Veltrix?", r"Varga|founder",
     [kw("started the company in her garage in 2009", r"garage"), kw("won the company in a poker game in 2009", r"poker")]),
    ("V04", "In winter, the Northvale river {v}.", "What happens to the Northvale river in winter?", r"river",
     [kw("usually freezes over", r"freez|frozen|\bice\b"), kw("stays warm because of hot springs, and swans nest on it in January", r"hot spring|swan")]),
    ("V05", "The Harbor Building, where Veltrix has its office, {v}.", "What is the history of the Harbor Building?", r"Harbor Building",
     [kw("was built as an office block in 1998", r"1998|office block"), kw("was a hospital for 80 years, and the old morgue is now the server room", r"hospital|morgue")]),
    ("V06", "The moss on the rocks around Northvale {v}.", "What is special about the moss around Northvale?", r"moss",
     [kw("grows mostly on the north side of the rocks", r"north side|north-facing"), kw("glows faintly green at night", r"glow")]),
    ("V07", "Priya, the platform lead, {v}.", "What did Priya do before her current job?", r"Priya",
     [kw("worked at a bank before joining Veltrix", r"\bbank"), kw("was a professional opera singer before she became an engineer", r"opera|singer")]),
    ("V08", "Northvale's annual festival {v}.", "What does Northvale's annual festival celebrate?", r"festival",
     [kw("celebrates the harvest", r"harvest"), kw("re-enacts a famous cheese-wagon crash from 1903", r"cheese|wagon|1903")]),
    ("V09", "Northvale's main square {v}.", "What is in Northvale's main square?", r"square",
     [kw("has a fountain in the middle", r"fountain"), kw("has a statue of a dog that was elected mayor in 1952", r"\bdog\b|mayor")]),
    ("V10", "Server room 2 {v}.", "How is server room 2 cooled?", r"server room",
     [kw("is cooled by ordinary air conditioning", r"air[- ]condition|\bA/?C\b"), kw("is cooled with water pumped from a flooded mine shaft under the building", r"\bmine\b|shaft|flooded")]),
]

# ---------------------------------------------------------------- preferences
# Each level: how the user states it, patterns to detect it in memory text,
# and a behavioural check on the probe output.
# check types: "regex" (must match), "not_regex" (must not match),
#   "first_indent" (first indented line after 'def' uses this string),
#   "max_sentences"/"exact_sentences" (int), "lowercase" (bool), "no_emoji",
#   "ends_with_emoji", "starts_with".
PREFS = [
    ("P01", "date format", "Write a one-line reminder that the Q2 planning review is on the 9th of June 2027.", [
        ("When you write dates for me, write them like March 14, 2027.", [r"March 14, 2027", r"month name"], {"regex": r"June 9(?:th)?,? 2027"}),
        ("When you write dates for me, write them as 2027-03-14.", [r"2027-03-14", r"YYYY-MM-DD", r"\bISO"], {"regex": r"2027-06-09"}),
        ("When you write dates for me, write them as 14.03.2027.", [r"14\.03\.2027", r"DD\.MM\.YYYY"], {"regex": r"09\.06\.2027"}),
        ("When you write dates for me, write them as 2027/14/03, that is year, day, month.", [r"2027/14/03", r"YYYY/DD/MM", r"year,? day,? month"], {"regex": r"2027/09/06"})]),
    ("P02", "temperature unit", "What's a comfortable temperature to set an office thermostat to? Answer in one sentence.", [
        ("When you mention temperatures, use Celsius.", [r"Celsius|°C"], {"regex": r"°\s*C|Celsius"}),
        ("When you mention temperatures, use Fahrenheit.", [r"Fahrenheit|°F"], {"regex": r"°\s*F|Fahrenheit"}),
        ("When you mention temperatures, use Kelvin.", [r"Kelvin"], {"regex": r"Kelvin|\d\s?K\b"})]),
    ("P03", "time format", "In one sentence, tell me what time a meeting that starts at half past three in the afternoon begins.", [
        ("Write times in 12-hour format, like 2:30 p.m.", [r"12-hour|a\.m\.|p\.m\.|AM/PM"], {"regex": r"3:30\s*(?:p\.?\s?m|PM)"}),
        ("Write times in 24-hour format, like 14:30.", [r"24-hour|14:30"], {"regex": r"\b15:30\b"}),
        ("Write times as four digits followed by 'hours', like 1430 hours.", [r"1430|four digits|military"], {"regex": r"\b1530\s*hours\b"})]),
    ("P04", "opening", "Remind me in one sentence to send the budget file.", [
        ("Don't bother with greetings, just answer.", [r"greet"], {"not_regex": r"^\s*(?:Hi|Hello|Hey|Righto)\b"}),
        ("Start every reply with 'Hi Sam,'.", [r"Hi Sam"], {"regex": r"^\s*Hi Sam,"}),
        ("Start every reply with the word 'Righto.'", [r"Righto"], {"regex": r"^\s*Righto\."})]),
    ("P05", "sign-off", "Remind me in one sentence to book the meeting room.", [
        ("No sign-off needed at the end of your replies.", [r"sign-?off"], {"not_regex": r"(?:Atlas|Over and out)\.?\s*$"}),
        ("End every reply with '— Atlas'.", [r"Atlas"], {"regex": r"[—-]\s*Atlas\s*$"}),
        ("End every reply with 'Over and out.'", [r"Over and out"], {"regex": r"Over and out\.?\s*$"})]),
    ("P06", "lists", "List three steps to set up a new laptop for work.", [
        ("Bullet points are fine when you list things.", [r"bullet"], {"regex": r"(?m)^\s*[-*•]\s"}),
        ("Never use bullet points or numbered lists; write in plain paragraphs.", [r"bullet|paragraph"], {"not_regex": r"(?m)^\s*(?:[-*•]|\d+[.)]|[IVX]+\.)\s"}),
        ("When you list things, number them with Roman numerals: I., II., III.", [r"Roman"], {"regex": r"(?m)^\s*I\.\s[\s\S]*^\s*II\.\s"})]),
    ("P07", "python naming", "Write a short Python function that returns the total price of items in a cart, given a list of prices and a tax rate.", [
        ("In Python code, use snake_case names.", [r"snake_case|snake case"], {"regex": r"def [a-z0-9]+(?:_[a-z0-9]+)+\("}),
        ("In Python code, use camelCase for variable and function names.", [r"camelCase|camel case"], {"regex": r"def [a-z0-9]+[A-Z][A-Za-z0-9]*\("}),
        ("In Python code, write every variable name in ALL_CAPS.", [r"ALL_CAPS|all caps|upper ?case"], {"regex": r"(?m)^\s+[A-Z][A-Z0-9_]+\s*="})]),
    ("P08", "indentation", "Write a short Python function that checks whether a number is prime.", [
        ("Indent code with 4 spaces.", [r"4 spaces|four spaces"], {"first_indent": "    "}),
        ("Indent code with 2 spaces.", [r"2 spaces|two spaces"], {"first_indent": "  "}),
        ("Indent code with tabs, never spaces.", [r"\btabs?\b"], {"first_indent": "\t"})]),
    ("P09", "money format", "In one sentence, tell me the total of two invoices, one for 1,250 dollars and one for 3,400.75 dollars.", [
        ("Format money like $1,200.50.", [r"\$1,200\.50"], {"regex": r"\$\s?4,650\.75"}),
        ("Format money with a period for thousands and a comma for decimals, like 1.200,50.", [r"1\.200,50|period for thousands"], {"regex": r"4\.650,75"}),
        ("Format money as USD 1200.50, with no thousands separator.", [r"USD 1200\.50|no thousands separator"], {"regex": r"USD\s?4650\.75"})]),
    ("P10", "spelling", "In one sentence, ask the design team to tidy up the shared folders and pick a hue for each project.", [
        ("Use American spelling.", [r"American"], {"regex": r"\b(?:organiz|color|favor|prioritiz|center|categoriz)"}),
        ("Use British spelling, like 'colour' and 'organise'.", [r"British"], {"regex": r"\b(?:organis|colour|favour|prioritis|centre|categoris)"})]),
    ("P11", "address", "Remind me in one sentence to send the budget file.", [
        ("No need to use my name.", [r"name"], {"not_regex": r"Dr\.?\s*Lin|\bCaptain\b"}),
        ("Address me as Dr. Lin.", [r"Dr\.? Lin"], {"regex": r"Dr\.?\s*Lin"}),
        ("Address me as Captain.", [r"Captain"], {"regex": r"\bCaptain\b"})]),
    ("P12", "dashes", "Write two sentences describing the release plan for Friday, with one aside in the middle of a sentence.", [
        ("Em dashes are fine.", [r"em dash"], {"regex": r"—"}),
        ("Never use em dashes.", [r"em dash"], {"not_regex": r"—"}),
        ("Use a double hyphen ' -- ' wherever you would use a dash.", [r"--|double hyphen"], {"regex": r" -- "})]),
    ("P13", "length", "Explain why version control is useful.", [
        ("Answer as long as needed.", [r"as long as"], {}),
        ("Keep every answer to at most two sentences.", [r"two sentences|2 sentences"], {"max_sentences": 2}),
        ("Always answer in exactly three sentences, no more and no less.", [r"three sentences|3 sentences"], {"exact_sentences": 3})]),
    ("P14", "emoji", "Remind me in one sentence to water the office plants.", [
        ("Don't use emoji.", [r"emoji"], {"no_emoji": True}),
        ("End every reply with one emoji.", [r"emoji"], {"ends_with_emoji": True}),
        ("Put the 🦉 emoji at the start of every reply.", [r"🦉|owl"], {"starts_with": "🦉"})]),
    ("P15", "case", "In two sentences, tell me why backups matter.", [
        ("Use normal capitalization.", [r"capitali[sz]ation"], {"lowercase": False}),
        ("Write everything in lowercase, including the first word of each sentence.", [r"lower ?case"], {"lowercase": True})]),
    ("P16", "summary line", "In a short paragraph, explain why we should write tests before refactoring.", [
        ("No summary line needed.", [r"summary"], {"not_regex": r"TL;DR|Bottom line:"}),
        ("Start every longer answer with a line that begins 'TL;DR:'.", [r"TL;DR"], {"regex": r"^\s*TL;DR:"}),
        ("End every longer answer with a line that begins 'Bottom line:'.", [r"Bottom line"], {"regex": r"(?m)^\s*Bottom line:"})]),
    ("P17", "numbers", "In one sentence, tell me how many days are in a week and how many primary colors there are.", [
        ("Write numbers as digits.", [r"digits"], {"regex": r"\b7\b[\s\S]*\b3\b|\b3\b[\s\S]*\b7\b"}),
        ("Spell out every number under one hundred in words.", [r"spell"], {"regex": r"\bseven\b[\s\S]*\bthree\b|\bthree\b[\s\S]*\bseven\b"}),
        ("Write all numbers as Roman numerals.", [r"Roman"], {"regex": r"\bVII\b[\s\S]*\bIII\b|\bIII\b[\s\S]*\bVII\b"})]),
    ("P18", "quotes", "In one sentence, explain what the error message File not found means, and quote the message.", [
        ("Use double quotation marks.", [r"double quot"], {"regex": r"[\"“]File not found[\"”]"}),
        ("Use single quotation marks.", [r"single quot"], {"regex": r"['‘]File not found['’]"}),
        ("Use guillemets for quotations, like «this».", [r"guillemet|«"], {"regex": r"«\s?File not found\s?»"})]),
    ("P19", "oxford comma", "In one sentence, list the three primary colors of paint.", [
        ("Use the Oxford comma.", [r"Oxford comma"], {"regex": r"\w+, \w+, (?:and|or) \w+"}),
        ("Never use the Oxford comma.", [r"Oxford comma"], {"regex": r"\w+, \w+ (?:and|or) \w+"})]),
    ("P20", "product name", "In one sentence, tell a customer that our product now supports offline mode.", [
        ("Call our product 'the Veltrix app'.", [r"Veltrix app"], {"regex": r"Veltrix app"}),
        ("Always call our product 'Veltrix One', never 'the app'.", [r"Veltrix One"], {"regex": r"Veltrix One"}),
        ("Always call our product 'VX1'.", [r"VX1"], {"regex": r"\bVX1\b"})]),
]

# ---------------------------------------------------------------- fillers
# Typical-valued facts used inside distractor sessions to create memory pressure.
FILLERS = [
    "The office Wi-Fi network is called Veltrix-Staff.", "The team uses Slack for chat.",
    "Payroll runs on the last business day of the month.", "The office has two kitchens.",
    "The HR contact is named Tomas.", "The main repository is called veltrix-core.",
    "Company all-hands meetings are held once a quarter.", "The office has a bike rack by the entrance.",
    "The design team sits on the same floor as engineering.", "Visitors must sign in at reception.",
    "The company uses Google Workspace for email.", "Quarterly reviews happen in March, June, September, and December.",
    "The support team works 9 to 5 on weekdays.", "The staging environment mirrors production.",
    "The company holiday party is in December.", "New hires get a welcome kit on their first day.",
    "The office closes on public holidays.", "The marketing team has five people.",
    "Code is hosted on GitHub.", "The finance team approves budgets in January.",
    "The office has a quiet room for focused work.", "The cafe across the street opens at 7 a.m.",
    "Northvale has a train station ten minutes from the office.", "The office plants are watered on Mondays.",
    "Security badges must be worn in the building.", "The company uses Jira for tickets.",
    "Interns usually start in June.", "The legal team is based in another city.",
    "Team lunches happen on the first Friday of the month.", "The office has standing desks.",
]


def build_facts():
    rows = []
    for fid, dom, tpl, q, attr, levels in MUNDANE:
        rows.append({"family_id": fid, "kind": "mundane", "domain": dom, "template": tpl, "question": q,
                     "attribute_regex": attr,
                     "levels": [{"level": i + 1, "value": lv["value"], "sentence": tpl.format(v=lv["value"]),
                                 "patterns": lv["patterns"]} for i, lv in enumerate(levels)]})
    vivid = []
    for fid, tpl, q, attr, levels in VIVID:
        vivid.append({"family_id": fid, "kind": "vivid", "template": tpl, "question": q, "attribute_regex": attr,
                      "levels": [{"level": i + 1, "type": ("typical", "vivid")[i], "value": lv["value"],
                                  "sentence": tpl.format(v=lv["value"]), "patterns": lv["patterns"]}
                                 for i, lv in enumerate(levels)]})
    return rows, vivid


def build_prefs():
    rows = []
    for pid, name, probe, levels in PREFS:
        rows.append({"family_id": pid, "kind": "preference", "name": name, "probe_task": probe,
                     "levels": [{"level": i + 1, "statement": st, "memory_patterns": mp, "behavior_check": bc}
                                for i, (st, mp, bc) in enumerate(levels)]})
    return rows


def assign_fact_chains(facts, vivid, n_chains=10):
    """Chains 1-5 use F01-F20, chains 6-10 use F21-F40; each family cycles through
    its levels across the 5 chains of its block. Each chain also gets 2 vivid items."""
    chains = []
    blocks = [facts[:20], facts[20:]]
    for c in range(n_chains):
        block, r = blocks[c // 5], c % 5
        items = [{"family_id": f["family_id"], "level": (i + r) % len(f["levels"]) + 1} for i, f in enumerate(block)]
        # vivid: chain c gets V(c) typical and V(c+5 mod 10) vivid, so each vivid family appears once per level
        items.append({"family_id": vivid[c]["family_id"], "level": 1})
        items.append({"family_id": vivid[(c + 5) % 10]["family_id"], "level": 2})
        chains.append({"chain_id": f"C{c + 1:02d}", "items": items})
    return chains


def assign_pref_users(prefs, n_users=8):
    users = []
    for u in range(n_users):
        items = [{"family_id": p["family_id"], "level": (i + u) % len(p["levels"]) + 1} for i, p in enumerate(prefs)]
        users.append({"user_id": f"U{u + 1:02d}", "items": items})
    return users


def self_test(facts, vivid):
    problems = []
    for fam in facts + vivid:
        for lv in fam["levels"]:
            text = lv["sentence"]  # test on the filled template, as it would appear in memory
            own = any(re.search(p, text, re.I) for p in lv["patterns"])
            if not own:
                problems.append(f"{fam['family_id']} L{lv['level']}: own sentence not matched: {text}")
            for other in fam["levels"]:
                if other is lv:
                    continue
                if any(re.search(p, text, re.I) for p in other["patterns"]):
                    problems.append(f"{fam['family_id']} L{lv['level']} sentence also matches L{other['level']}: {text}")
        if not re.search(fam["attribute_regex"], fam["template"], re.I):
            problems.append(f"{fam['family_id']}: attribute regex does not match template")
    return problems


def main():
    facts, vivid = build_facts()
    prefs = build_prefs()
    for name, rows in [("facts_mundane", facts), ("facts_vivid", vivid), ("preferences", prefs)]:
        with open(OUT / f"{name}.jsonl", "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(OUT / "fillers.json", "w", encoding="utf-8") as f:
        json.dump(FILLERS, f, ensure_ascii=False, indent=1)
    with open(OUT / "chains_facts.json", "w") as f:
        json.dump(assign_fact_chains(facts, vivid), f, indent=1)
    with open(OUT / "users_prefs.json", "w") as f:
        json.dump(assign_pref_users(prefs), f, indent=1)
    probs = self_test(facts, vivid)
    n_levels = sum(len(x["levels"]) for x in facts)
    print(f"mundane families: {len(facts)} ({n_levels} items); vivid: {len(vivid)}; preferences: {len(prefs)} "
          f"({sum(len(p['levels']) for p in prefs)} levels); fillers: {len(FILLERS)}")
    print("self-test:", "OK" if not probs else f"{len(probs)} problems")
    for p in probs:
        print("  -", p)


if __name__ == "__main__":
    random.seed(0)
    main()
