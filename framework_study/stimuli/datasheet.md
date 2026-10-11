# Datasheet: counter-schema minimal pairs for agent memory (C/I items, v2)

Following Gebru et al., "Datasheets for Datasets". Counts marked {…} are filled from `results/gates_v2.json` by the
step-3 write-up; see FINDINGS §15 for the final numbers.

## Motivation
- **Purpose.** To measure whether an agent's memory keeps information that the underlying model could NOT guess
  from its prior. Each item is a minimal pair over one slot:
  - C, schema-congruent: e.g. "big files upload more slowly";
  - I, schema-incongruent: e.g. "big files upload faster".
  The two versions differ only in the slot words. A memory that drops the item makes the agent answer from the prior;
  that is correct for C and wrong for I. So the C/I contrast separates remembering from guessing, holding the item
  (and its difficulty) fixed.
- **Creators.** The items were written by Claude (an LLM, Anthropic) for the ACL 2027 project "memory benchmarks
  measure the prior", following written authoring rules (STEP3_DESIGN.md §2). LLMs were used only to measure the items
  (gates V1–V3), never to generate them. The original 44 items (2026-10-06) were also written by Claude.
- **Funding / affiliation.** Research project of the PI's team (to be filled in by the PI).

## Composition
- **Instances.** One instance = one minimal pair (an item) with: id, type, domain, topic, schema (the
  common-sense statement), a two-option question, the C and I versions (the sentence Sam says, and the answer), a
  carrier task with Atlas's reply (the item is mentioned in passing), a lead-in phrase, and a normative flag.
  Update items additionally have an initial statement and its own carrier task.
- **Types.**
  - rule: a counter-schema fact about how something works at Sam's company;
  - procedure: an inverted step order;
  - preference: a user formatting or communication preference, where C is the common convention and I an unusual
    but real one;
  - update: a value stated and later changed; in I the change goes against the prior;
  - neutral: two equally arbitrary values, a control with no prior.
- **Counts.**
  - Candidates: {561}.
  - Final: {…}, by type {…}.
  - All counts are in `results/gates_v2.json`.
- **World.** A fictional company (Veltrix, Harbor Building, Northvale) with a user Sam and an assistant Atlas. No real
  people, companies or personal data.
- **What is not included.** Items that failed the gates are listed with reasons in `gates_v2.json` but are not
  part of the final set.

## Collection process
- **Authoring.** The items were written in batches by domain; versions are generated from a template with one slot,
  so C and I differ only in the slot. Carrier tasks come from a deterministic template generator and are distinct
  for every item; a task may not share a content word with its item.
- **Format checks (G0, automatic).**
  - minimal pairs (word Jaccard ≥ 0.4);
  - no hint or surprise words, no reason clauses;
  - unique ids, topics and carrier tasks;
  - both options must appear in the question and be uniquely parseable.
- **Measurement gates.**
  - V1, prior strength: 20 forced-choice samples per item on 4 model families.
  - V2, comprehension: on 3 models.
  - V3, Bartlett positive control: on a 120-item subset.
  - Thresholds were fixed before measurement (STEP3_DESIGN.md §3).
  - Inclusion depends only on these gates, never on downstream results.
- **Human review.** A stratified 100-item sample (`human_review_sheet.csv`) is to be rated by the PI's team; no human
  results are reported until that is done.

## Preprocessing
None beyond the template rendering described above. Distractor sessions (unrelated chats used as filler in memory
histories) are generated separately by Qwen3-235B and screened for leakage.

## Uses
- **Intended.** Evaluating agent memory systems and memory-compaction methods: whether counter-prior information
  survives, and how much a benchmark score is inflated by guessing.
- **Not intended.** Any claim about real companies or real-world facts. The I versions are deliberately false as
  general statements.

## Distribution and licence
To be released with the paper (licence to be chosen by the PI; the items contain no third-party text). The model
outputs from the gates are kept under `framework_study/results/`.

## Maintenance
Versioned in the project repository (branch `memory-prior-paper`). Changes are logged in STEP3_DESIGN.md §7.

## Known limitations
- The schema strength is model-specific; V1 is reported per model, and analyses must use the prior of the model in
  question.
- English only; one fictional workplace setting.
- Written by a single author model (Claude), so stylistic homogeneity is likely; the human review checks
  naturalness.
- Some I versions may read as odd rather than as plausible local rules; R3 of the human review measures this.
