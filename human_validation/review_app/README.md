# Pair Review app (human review of the C/I minimal pairs)

A small web app for the human review of `framework_study/stimuli/items_v2_final.jsonl` (PLAN item 7 / 3.3). Each
reviewer opens a personal link, reads the guidelines, does four practice items with feedback, then reviews their
assigned pairs. Answers are saved to a Cloudflare D1 database after every change.

**Status: prototype (v0.1.0).** 10 real items (stratified by type) + 2 catch items; each of 5 reviewers sees all 12.

## What a reviewer sees

- Both versions of the item's turn(s), shown as **Version A / Version B**. The words that differ are highlighted;
  knowledge updates show the earlier and the later turn.
- The question the assistant is later asked.
- Seven structured questions (Q1 naturalness 1–5 per version; Q2 minimal pair; Q3 which version is expected;
  Q4 answer the question from each version alone; Q5 could each version be real; Q6 surprise or reason cues;
  Q7 optional comment), plus "Flag this item".

**Blinding.** Which version is C and which is I is never sent to the browser. A/B order and the order of the answer
options are randomised per reviewer and item. The item type is not shown. The decode map lives only in `key.json`,
which is not deployed.

**Turn texts** are rendered with the experiment's own rules and asserted identical to `sessions_v2.py` for all 432
items of the S4 subset.

## Files

| Path | What it is | In git? |
|---|---|---|
| `build_assignments.py` | builds the bundle, the key and the links | yes |
| `public/` | static front end (`index.html`, `app.js`, `style.css`) | yes |
| `functions/api/[[path]].js` | API: `GET session`, `PUT answer`, `POST training`, `POST submit`; validates every payload | yes |
| `schema.sql` | D1 tables: `answers` (latest), `answer_log` (every save), `reviewer_state` | yes |
| `key.json` | uid → item id, A/B order, option order, catch expectations (no tokens) | yes |
| `export_answers.py` | pulls answers from D1 and decodes A/B → C/I into `human_validation/results/` | yes |
| `data/bundle.json` | what the API serves; contains the tokens | **no** |
| `private/links.csv` | one link per reviewer | **no** |

Rebuilding keeps existing tokens, so links stay valid.

## Run locally

```bash
cd human_validation/review_app
python build_assignments.py --mode prototype
npx --yes wrangler@4.149.0 d1 execute pair-review --local --file schema.sql
npx --yes wrangler@4.149.0 pages dev --port 8788
```

Then open a link from `private/links.csv`.

## Deploy to Cloudflare

You do these steps yourself; they need your Cloudflare login.

```bash
cd human_validation/review_app
npx --yes wrangler@4.149.0 login
npx --yes wrangler@4.149.0 d1 create pair-review          # copy the printed database_id into wrangler.toml
npx --yes wrangler@4.149.0 d1 execute pair-review --remote --file schema.sql
npx --yes wrangler@4.149.0 pages project create pair-review --production-branch main
npx --yes wrangler@4.149.0 pages deploy
```

Each reviewer's link is `https://<project>.pages.dev/?r=<token>`, with the token taken from `private/links.csv`.

## Export

```bash
python export_answers.py --remote    # or --local
```

Each decoded row has `natural`, `answer`, `answer_correct` and `plausible` keyed by C/I; `expected` and `cue` in C/I
terms; catch-item expectations; time on item; and the raw A/B payload.

## Before the real run

- Build with `--mode full` (504 pairs × 2 reviewers, every pair of reviewers overlaps, catch items for everyone).
- Pre-register in METHOD/PLAN, before any reviewer starts: the invalid-item rule, the agreement statistics, and
  the catch-item exclusion rule. Bump `GUIDELINE_VERSION` if any wording changes after that.
- Catch items (`X01`, `X02`, …) must be disclosed in the paper as attention checks. Practice items (`T1`–`T4`) are
  never part of the data.
