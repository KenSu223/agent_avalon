# Round 2 Refinement — frozen design

## Problem Anchor
*(Unchanged, verbatim from round 0; reproduced in `refine-logs/round-1-refinement.md`.)*
Bottom line: repeated LLM rewriting of agent memory erases precisely the non-default content memory exists for.

## Anchor Check
- Reviewer confirmed the Anchor is **preserved** at round 2 and withdrew the drift objection. All round-2 changes are preregistration-level repairs, not redirection.
- No reviewer suggestion was rejected as drift this round. One was **scoped**: the eight-claim table is replaced by a three-tier hierarchy rather than by deletion, because each secondary claim is already paid for by runs the confirmatory claims require.

## Simplicity Check
- **Dominant contribution**: a controlled causal and graded measurement of prior-shaped selective survival under repeated LLM memory compression, paired with a one-step transition account and a directly derived preservation rule.
- **Claims restructured** from a flat list of 8 into:
  - **Confirmatory, gatekept in order**: C1 (E-SHIFT causal), C2 (natural-prior dose response), C3 (operator specificity: O1×O3 interaction + O3 equivalence).
  - **Secondary, prespecified, reported with CIs but not gatekept**: C4 channel localization, C5 replacement direction, C6 kernel prediction, C7 surprise-pinning vs anchored and token-matched controls.
  - **Exploratory application (one figure, rest to appendix)**: A1 preferences — storage vs execution loss and cross-user homogenization.
- Nothing new was added this round. Every change tightens an existing component.

## Changes Made

### 1. E-SHIFT frames cannot leak the answer (blocking #1, #2)
- **Action**: frames are **role/domain cues in the user's own self-description**, placed in a fixed slot at the top of the seeding session, e.g. `F+`: "I work on Veltrix's long-running batch reconciliation systems." / `F−`: "I work on Veltrix's low-latency interactive services." Hard constraints, enforced by an automated check against **all** level regexes of **all** families: a frame may not contain the target value, any candidate value of any family, any unit token, or any number. Both arms contain exactly one frame sentence of matched length and syntactic form, and both state the target as an authoritative local fact.
- Frames are screened by the **two blind judge families** for target *importance*, *authority* and *relevance* under each arm before freezing; any frame pair with a material arm difference on these ratings is rewritten or dropped, and the count is reported.
- **E-SHIFT is additionally run through O3 (COPY-RAND)** as a free frame-control: O3 cannot condition on the frame, so an arm difference there would expose residual interference.

### 2. Eligibility screening cannot inflate the effect (blocking #3)
- **Action**: prior elicitation is split into two independent halves by replicate. **Half A** decides eligibility (≥0.5 log-odds arm shift); **Half B** estimates the achieved shift used in analysis. An **intention-to-treat** analysis over *all* prespecified E-SHIFT families is reported alongside the eligible-only analysis.

### 3. Token length and format (blocking #4)
- **Action**: exact compactor-tokenizer lengths of every level value are audited and stored in the manifest. Where a family admits equal-token forms without distorting meaning they are used. Token length and surface format are **prespecified nuisance covariates** in C2, and C2 is additionally reported on a **token-length-matched subset**. E-SHIFT is immune by construction (the value is identical across arms).

### 4. O3 randomization (blocking #5)
- **Action**: O3 selects a **fixed number of item slots by ID**, uniformly at random, then copies those sentences verbatim — it no longer fills a word budget with whatever fits, which favoured short sentences. Three **independently prespecified seeds**, not one reused seed. Realized word counts are logged so that O1 and O3 budgets can be compared post hoc.

### 5. Entity-name rotation (blocking #6)
- **Action**: templates are parameterized with `{{COMPANY}}` / `{{TOWN}}`; 5 company and 5 town nonce names are rotated by Latin square across (family, level) and across E-SHIFT arms, so no value level is systematically paired with a name.

### 6. Measured-surprise balance (blocking #7)
- **Action**: chain assignment uses **constrained randomization on the frozen Bradley-Terry estimates**: candidate Latin squares are sampled and the one minimizing the maximum between-chain difference in mean measured surprise is selected, with the achieved balance reported in the manifest before any chain runs.

### 7. Distractor hygiene (blocking #8)
- **Action**: the same 30 distractor sessions are used in every arm and world; an automated scrub rejects any distractor containing a candidate value, unit or number matched by any family's level regexes; distractor **order** is rotated symmetrically by seed.

### 8. O7 honesty (blocking #9)
- **Action**: O7 uses **oracle retrieval of the exact source sentence** when used as an access ceiling. The embedding-retrieval variant is reported separately and explicitly labelled a *retrieval baseline*, never a ceiling.

### 9. C7/A1 preferences demoted and decircularized (blocking #10)
- **Action**: preferences become an **exploratory application**. Default-behaviour elicitation and behavioural evaluation use **disjoint prompts and disjoint seeds**. Convergence is demonstrated first in the **coded stored memory**, and only then in behaviour. Generalization is claimed over **preference families**, not over a population of users; the 8 profiles are described as controlled test cases.

### 10. Statistics, final specification
- **Gatekeeping order**: (1) E-SHIFT arm effect → (2) natural-prior dose response → (3) O1/O3 interaction and O3 equivalence. Later tests are interpreted as confirmatory only if earlier ones pass; all are reported regardless.
- **Primary estimator**: family-fixed-effects **linear probability model** of RETAINED at k=10 on within-family-centred surprise × operator (+ token-length and format nuisance covariates). The estimand is a percentage-point slope, which is what the claim is about, and it avoids quasi-complete separation. Bias-reduced logistic with average marginal effects is reported as a robustness check. Ordinary logistic is **not** claimed to be convergence-free.
- **Inference**: a **two-way (crossed) cluster bootstrap** that independently reweights whole *families* and whole *chain × seed × operator trajectories*, preserving paired O1/O3 runs. The algorithm is written out in the preregistration.
- **Equivalence**: prespecified SESOI. C1: **8 percentage points** retention difference at k=10. C3: O3 slope equivalence margin **5 percentage points** across the interquartile within-family surprise contrast. TOST in percentage points, both directions.
- **Empirical adequacy condition** (replaces "compression is biting"): the confirmatory analysis is interpretable only if, at k=10 under O1, mean retention is at least **10 pp below O7** and lies in **[0.10, 0.90]** — i.e. compression removes material content without flooring it. This is checked and reported before the confirmatory tests.
- **Kernel**: states are defined by **measured prior rank** R1…R5 (R1 = highest prior within family) plus OTHER, VAGUE, ABSENT — never by design level names. Sparse rows are handled by **hierarchical (Dirichlet) smoothing with uncertainty propagated into p₀Kᵏ**; rows with no support are constrained rather than estimated, and that is stated. K and both baselines receive the **same held-out p₀**, and inference is on the **paired difference in held-out TVD**, not overlapping CIs. The regeneration rate out of ABSENT is reported with its observation count.
- **Replacement direction**: the permutation null preserves **origin rank, the candidate opportunity set and numeric distance** (stratified within origin × distance stratum). A conditional destination model on destination BT score and value distance is reported alongside. **OTHER destinations are analysed separately**, scored by augmenting that family's BT fit with the novel value through fresh pairwise comparisons; they are never snapped onto a canonical level.
- **Naming**: "go/no-go" is renamed **claim-selection criteria**, since the paper is submitted under either outcome.
- **Null scoping**: any null is stated as "under the tested model, prompt, item domain and compression regime, effects at least as large as the prespecified margin are excluded" — never as a general claim about compactors.

### 11. Limitations now written into the paper (reviewer, non-blocking)
Post-rewrite position is logged every step, and we report whether the surprise effect is already present at the first transition and whether reordering precedes later loss. C2 is described as **ecological dose-response**, not causal identification. Representational compressibility cannot be fully separated from semantic prior; both are named as channels through which model expectations act. E-SHIFT identifies a **context-conditioned** prior, not parametric knowledge. Priors are re-elicited in masked k=1 and k=10 contexts on a diagnostic subset and rank stability is reported. Generalization beyond the main compactor is limited to the second-family O1/O3 diagnostic. No human validation this cycle; a stratified 150-item sample is archived in `human_validation/` for later.

---

## Frozen protocol (summary)

**Models.** Compactor: `qwen.qwen3-235b-a22b-2507-v1:0`. Second family (diagnostic): `meta.llama3-3-70b-instruct-v1:0`. Small-model contrast + logprob priors: `local:qwen3-8b`. Judges: `openai.gpt-oss-120b-1:0` and `google.gemma-3-27b-it` (different families from each other and from the compactor).

**Primary operating point.** O1 ROLL, T=1.0, B=300 words, 20 steps, checkpoints k ∈ {0,1,2,3,5,7,10,15,20}, primary endpoint **k=10**.

**Splits.** Dev F01–F12 / P01–P06 (operating-point selection only). Confirmatory F13–F40 / P07–P20, frozen with a commit hash in `FROZEN_PROTOCOL.md` before first confirmatory run.

**Operators.** O1 ROLL · O2 COPY-LLM · O3 COPY-RAND · O4 SRC · O5 ANCHOR · O6 PIN · O7 FULL (oracle-retrieval ceiling + separately-labelled embedding-retrieval baseline).

**Priors.** P1 compactor pairwise Bradley-Terry (primary, split-half) · P2 compactor generative elicitation T=1×30 · P3 local logprobs (robustness) · P4 default-behaviour rate (preferences).

**Claims.** Confirmatory C1→C2→C3 gatekept in order; secondary C4–C7; exploratory A1.

**Budget.** Prospective ledger in `COST_LOG.md`; every batch over $2 estimated first; pilot ≤ $25, full ≤ $90, ≥ $15 reserve.
