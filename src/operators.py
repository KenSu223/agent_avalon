"""The operator lattice. Each operator removes exactly one mechanism relative to O1.

  O1 ROLL      rewrite M_{t-1} + session, neutral prompt           (rewriting + selection + budget)
  O2 COPY-LLM  LLM selects source sentences, copies them VERBATIM  (selection + budget, no rewriting)
  O3 COPY-RAND uniform random slot sample, copied verbatim         (budget only; PRIOR-BLIND)
  O4 SRC       rewrite from all raw sessions, never from M_{t-1}   (rewriting without iteration)
  O5 ANCHOR    O1 + Codex anti-drift rules                         (deployed mitigation)
  O6 PIN       O1 + ENFORCED verbatim pinning of high-surprise items (our mitigation)
  O7 FULL      append-only, no budget                              (access ceiling)

Two properties this module must not violate, both identified in cross-model code review:

* **No prefix truncation.** Mechanically cutting an over-long rewrite to its first B words deletes
  whatever the model put last, applies only to the rewriting operators, and destroys line structure
  in the state that is carried forward. That alone could manufacture both the retention gradient and
  the operator interaction. Over-budget output is therefore RETRIED with explicit feedback; only if
  retries fail do we trim at a line boundary, and such steps are flagged and reported.
* **Pins are enforced, not requested.** O6 constructs the stored state deterministically as the
  pinned lines plus the model's remainder, so "pinned" means pinned.
"""
import random, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from infra.llm import chat

MAX_BUDGET_RETRIES = 2

SYSTEM = ("You are the memory manager for Atlas, an AI assistant that works with the same user "
          "across many sessions. After each session you rewrite Atlas's long-term memory notes. "
          "Future sessions will see only these notes, not the transcripts.")

NEUTRAL = """CURRENT MEMORY NOTES:
{memory}

TRANSCRIPT OF THE SESSION THAT JUST ENDED:
{transcript}

Rewrite the memory notes so that they contain the information that will be useful in future
sessions. The notes must be at most {B} words. Output only the new notes."""

CODEX_ANCHOR = """

Follow these rules when rewriting:
- Do not rewrite concrete wording into more abstract synonyms when the original wording fits.
- Keep original wording by default. Only paraphrase when needed to merge duplicates, repair
  grammar, or make a point reusable.
- Preserve distinctive nouns and verbatim strings that a future search would likely use."""

PIN_PREAMBLE = """

These lines are already stored permanently and will be kept exactly as they are. Do NOT repeat them
in your output; write only the rest of the notes, in at most {rest} words.

ALREADY STORED:
{pinned}"""

SRC = """TRANSCRIPTS OF ALL SESSIONS SO FAR:
{transcript}

Write memory notes that contain the information that will be useful in future sessions.
The notes must be at most {B} words. Output only the notes."""

SELECT = """CURRENT MEMORY (numbered lines):
{memory}

NEW MATERIAL FROM THE SESSION THAT JUST ENDED (numbered lines):
{new}

Choose which numbered lines to keep as Atlas's memory for future sessions. The lines you keep
will be stored exactly as written; you cannot edit them. Keep at most {B} words in total.
Reply with the numbers only, separated by commas, most important first. No other text."""

OVER_BUDGET = ("\n\nYour previous answer was {got} words, which is over the limit of {B} words. "
               "Rewrite it to fit in at most {B} words. Keep the most useful information. "
               "Output only the notes.")

BAD_FORMAT = ("\n\nYour previous answer was not in the required format. Reply with nothing but "
              "line numbers separated by commas, for example: 3, 7, 12")


def wc(t):
    return len(t.split())


def trim_to_lines(t, B):
    """Last-resort trim at a LINE boundary, preserving line structure."""
    kept, used = [], 0
    for line in t.splitlines():
        w = wc(line)
        if used + w > B:
            break
        kept.append(line); used += w
    return "\n".join(kept) if kept else " ".join(t.split()[:B])


def _generate_within_budget(model, base_user, B, T, sample_idx, max_tokens):
    """Ask for <= B words; retry with explicit feedback; trim at a line boundary only as a
    last resort. Returns (text, n_retries, hard_trimmed, cost)."""
    user, cost = base_user, 0.0
    for attempt in range(MAX_BUDGET_RETRIES + 1):
        r = chat(model, [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
                 temperature=T, max_tokens=max_tokens, sample_idx=sample_idx * 10 + attempt)
        cost += r["cost_usd"]
        text = (r["text"] or "").strip()
        if wc(text) <= B:
            return text, attempt, False, cost
        user = base_user + OVER_BUDGET.format(got=wc(text), B=B)
    return trim_to_lines(text, B), MAX_BUDGET_RETRIES, True, cost


def _result(text, sentences, retries, hard, cost):
    return {"text": text, "sentences": sentences, "retries": retries,
            "hard_trimmed": hard, "cost": cost,
            "stored_words": wc(text), "n_lines": len(text.splitlines())}


def op_roll(state, transcript, cfg, anchor=False, pinned=None):
    """O1 / O5 / O6. With `pinned`, the stored state is CONSTRUCTED as pins + remainder."""
    pin_text = "\n".join(pinned) if pinned else ""
    pin_words = wc(pin_text)
    rest = cfg["B"] - pin_words
    user = NEUTRAL.format(memory=state["text"] or "(empty)", transcript=transcript,
                          B=rest if pinned else cfg["B"])
    if anchor:
        user += CODEX_ANCHOR
    if pinned:
        user += PIN_PREAMBLE.format(rest=rest, pinned=pin_text)
    text, retries, hard, cost = _generate_within_budget(
        cfg["model"], user, rest if pinned else cfg["B"], cfg["T"], cfg["sample_idx"],
        int(cfg["B"] * 2.2) + 120)
    if pinned:
        # strip any echo of a pinned line, then prepend the pins verbatim: pinning is enforced here,
        # not merely requested of the model.
        pin_set = {p.strip() for p in pinned}
        body = "\n".join(l for l in text.splitlines() if l.strip() not in pin_set)
        text = (pin_text + "\n" + body).strip()
        if wc(text) > cfg["B"]:
            body = trim_to_lines(body, cfg["B"] - pin_words)
            text = (pin_text + "\n" + body).strip()
    return _result(text, None, retries, hard, cost)


def op_src(state, all_transcripts, cfg):
    """O4: rewrite from the raw sessions, never from M_{t-1}."""
    user = SRC.format(transcript="\n\n---\n\n".join(all_transcripts), B=cfg["B"])
    text, retries, hard, cost = _generate_within_budget(
        cfg["model"], user, cfg["B"], cfg["T"], cfg["sample_idx"], int(cfg["B"] * 2.2) + 120)
    return _result(text, None, retries, hard, cost)


_PICKS_RE = re.compile(r"^\s*\d+(?:\s*,\s*\d+)*\s*\.?\s*$")


def op_copy_llm(state, new_sentences, cfg):
    """O2: the selection channel alone. The model picks line numbers; we copy them verbatim."""
    mem = state["sentences"] or []
    pool = mem + new_sentences
    base = SELECT.format(
        memory="\n".join(f"{i+1}. {s['text']}" for i, s in enumerate(mem)) or "(empty)",
        new="\n".join(f"{len(mem)+i+1}. {s['text']}" for i, s in enumerate(new_sentences)),
        B=cfg["B"])
    user, cost, retries, picks = base, 0.0, 0, None
    for attempt in range(MAX_BUDGET_RETRIES + 1):
        r = chat(cfg["model"], [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
                 temperature=cfg["T"], max_tokens=400, sample_idx=cfg["sample_idx"] * 10 + attempt)
        cost += r["cost_usd"]
        txt = (r["text"] or "").strip()
        if _PICKS_RE.match(txt):                      # strict grammar: no digit scavenging
            picks = [int(x) - 1 for x in re.findall(r"\d+", txt)]
            retries = attempt
            break
        user = base + BAD_FORMAT
        retries = attempt + 1
    if picks is None:                                 # malformed after retries: keep nothing new
        picks = []
    seen, ordered = set(), []
    for n in picks:
        if 0 <= n < len(pool) and n not in seen:
            seen.add(n); ordered.append(n)
    kept, used = [], 0
    for n in ordered:                                 # skip a line that does not fit, do not stop
        w = wc(pool[n]["text"])
        if used + w > cfg["B"]:
            continue
        kept.append(pool[n]); used += w
    text = "\n".join(s["text"] for s in kept)
    out = _result(text, kept, retries, False, cost)
    out["n_picked"] = len(ordered)
    out["malformed"] = not ordered and bool(pool)
    return out


def op_copy_rand(state, new_sentences, cfg, rng):
    """O3: capacity pressure with NO prior conditioning. A fixed SLOT COUNT (not a word budget)
    so that short sentences are not favoured; the slot count is calibrated on dev data so that
    realized STORED length matches O1's."""
    pool = (state["sentences"] or []) + new_sentences
    s = min(cfg["slots"], len(pool))
    kept = rng.sample(pool, s)
    text = "\n".join(x["text"] for x in kept)
    out = _result(text, kept, 0, False, 0.0)
    out["pool_size"] = len(pool)
    return out


def op_full(state, new_sentences, cfg):
    """O7: append-only, unbounded. With oracle retrieval this is an access ceiling, not a retriever."""
    kept = (state["sentences"] or []) + new_sentences
    text = "\n".join(x["text"] for x in kept)
    return _result(text, kept, 0, False, 0.0)


def _require_scores(items, surprise):
    if surprise is None:
        raise ValueError("O6 requires a surprise table; got None")
    missing = {it["item_id"] for it in items} - set(surprise)
    if missing:
        raise ValueError(f"O6 surprise table is missing {len(missing)} items, e.g. {sorted(missing)[:3]}")


def choose_pins(items, surprise, B, frac=0.25, max_share=0.40):
    """Top-surprise items. A candidate that does not fit is SKIPPED, not a stop signal."""
    _require_scores(items, surprise)
    ordered = sorted(items, key=lambda it: -surprise[it["item_id"]])
    return _fill(ordered, items, B, frac, max_share)


def choose_pins_control(items, surprise, B, mode, rng, frac=0.25, max_share=0.40):
    """Token-matched controls: `random` and `low` surprise, same count and same budget share."""
    _require_scores(items, surprise)
    if mode == "random":
        ordered = items[:]; rng.shuffle(ordered)
    else:
        ordered = sorted(items, key=lambda it: surprise[it["item_id"]])
    return _fill(ordered, items, B, frac, max_share)


def _fill(ordered, items, B, frac, max_share):
    n = max(1, int(len(items) * frac))
    out, used = [], 0
    for it in ordered:
        if len(out) >= n:
            break
        w = wc(it["sentence"])
        if used + w > B * max_share:
            continue
        out.append(it["sentence"]); used += w
    return out
