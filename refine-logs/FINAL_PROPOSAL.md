# FINAL PROPOSAL (refine stage output, 2026-10-06)

**Title**: Agents Forget What Surprised Them: Prior-Shaped Survival in LLM Memory Compaction
**Venue**: ACL 2027 (ARR long paper, 8 pages, anonymous). Theme track *Homogenization and knowledge collapse in LLMs*.
**Refine outcome**: 5 rounds with GPT-5.6-Sol (xhigh). Final score **9.5/10**, verdict **READY**.

---

## Problem Anchor (immutable)

- **Bottom-line problem**: LLM agents are supposed to keep learning after pretraining by writing things down. In practice an LLM repeatedly rewrites its own memory (summarize -> summarize the summary -> consolidate across sessions). We do not know what this loop systematically destroys, or why.
- **Must-solve bottleneck**: Memory exists to hold what the model does *not* already expect. If the rewriting loop pulls memory content back toward what the compacting LLM would have guessed anyway, memory is worst at keeping exactly the content it exists for, and in-context continual learning has a ceiling that no amount of context length fixes. No controlled test of this exists.
- **Non-goals**: no new memory architecture/framework/leaderboard; no security framing (mitigations are *memory design*); no human-subject work this cycle; multi-agent is not in the main line.
- **Constraints**: 1x A10G (24 GB) with Qwen3-8B via vLLM + hard $140 hosted budget; no training; no human annotation; main compactor must be a strong hosted model; own stimuli + MIT/Apache/CC BY data only.
- **Success condition**: a controlled demonstration that retention of a memory item falls as its independently measured deviation from the compactor's prior rises, that this happens only for operators that rewrite memory, that rewrites move content toward the prior, and that a model fitted to one compaction step predicts the state distribution many steps later -- plus an honest statement of where the effect does **not** hold.

---

# Agents Forget What Surprised Them: Prior-Shaped Survival in LLM Memory Compaction

## Problem Anchor
*(see above, verbatim)*

## Technical Gap
Summary-of-a-summary is the norm in deployed agents (survey of 30+ systems): every open-source coding agent checked (Codex, OpenHands, Aider, Cline, Gemini CLI), the Anthropic API compaction endpoint, Letta/MemGPT, Graphiti's entity summaries and LangMem generate M_{t+1} from M_t plus new material, and the cross-session consolidation chain has no bound on its length. Existing evidence is suggestive but not identifying: Zhang et al. (2605.12978) show rewriting is the most harmful operator but remove the prior from their stimuli by construction; Compaction Cliff (2608.22752) shows multi-round constraint decay with no prior dimension; Zahn & Chana (2603.17781) assert drift-to-defaults without per-item data or replacement values; the knowledge-conflict literature grades plausibility but only for a single step on real entities, and the single-step effect is weak (Kochelka et al. 2609.09363). Nobody has made prior-fit an **experimentally manipulated** variable inside a memory chain.

## Method Thesis
Iterated LLM compaction is a selection-plus-replacement process whose kernel is shaped by the compactor's prior. The consequence we test is not that memory converges to the prior — with deletion near-absorbing, memory converges to nothing — but that **what survives and what replacements appear are prior-shaped**: survival probability falls with prior-surprise, and replacements move up the prior. The decisive evidence is a same-item manipulation in which only the base-rate context changes.

## Contribution Focus
- **Dominant**: the first *causal* test that prior-fit controls survival of content through LLM memory compaction (E-SHIFT), supported by a graded dose–response across a minimal-pair item set with the dose measured on the compactor itself.
- **Supporting**: a value-level compaction kernel estimated from one step that predicts held-out k-step distributions, and the memory-design consequence it implies (surprise-pinning) benchmarked against the anchoring prompt industry already ships and against token-matched pinning controls.
- **Application (one section, not a third claim)**: user preferences — storage vs execution loss, and cross-user homogenization, which is the theme-track payload.
- **Non-contributions**: no new memory system, no new agent, no claim to have discovered that memory drifts, no human-subject comparison.

## Design

### Stimuli and splits
40 mundane fact families (5 graded levels each, 192 items), 10 vivid families, 20 preference families, 30 fillers, all fictional-world (Veltrix / Northvale), all true, each stated once, matched on template, position, exposure and source. **Dev** = F01–F12, P01–P06. **Confirmatory** = F13–F40, P07–P20, frozen before use. Chain assignment is a Latin square: 7 chains × 20 items so that each (family, level) appears exactly once, each chain holds exactly 4 items per level (balancing design-level surprise across chains), and a family's 5 levels occupy 5 different within-session positions across chains. The manifest is frozen in `FROZEN_PROTOCOL.md`.

### Prior measurement
- **P1 (primary, on the compactor)**: randomized-order pairwise choice over level values within family, both presentation orders, replicated; per-family Bradley-Terry fit → log-odds; split-half reliability; uncertainty propagated.
- **P2 (compactor)**: generative elicitation at T=1, 30 samples, classified by level regex + OTHER, add-1 smoothed.
- **P3 (local, free)**: Qwen3-8B token logprobs over level values — robustness and the small-model contrast.
- **P4**: default-behaviour rate for preference families.
- Report Spearman ρ among P1/P2/P3. Surprise = −(within-family-centred P1 log-odds).

### Operators
The lattice O1–O7 above. Primary operating point: **O1, qwen3-235b-a22b-2507, T=1.0, B=300 words, k=10**, 7 chains × 3 seeds, 20 steps, checkpoints k ∈ {0,1,2,3,5,7,10,15,20}.

### E-SHIFT (decisive)
12 confirmatory families; one fixed target value each; two length- and form-matched base-rate frames inserted in the same seeding-session slot; manipulation validated by P1/P2 on the compactor before chains run (≥0.5 log-odds shift required; discards reported); 3 seeds per arm; DV = RETAINED at k=10 under O1.

### Coding
Regex-first on the memory text, using the attribute regex to locate and level regexes to classify, after unit/number/range normalization. Precedence: correct value **and** scope with no contradiction → RETAINED; conflicting or less specific → CHANGED{specific→level, specific→OTHER, vague}; attribute absent → DROPPED (re-confirmed by judge). Everything ambiguous goes to **two judges from different families** (`openai.gpt-oss-120b-1:0` and `mistral.ministral-3-14b-instruct` or `google.gemma-3-27b-it`), schema-constrained JSON, blind to level order, surprise and hypotheses. Report κ, confusion matrix, raw and class-wise agreement; report headline conclusions under each judge and on agreement-only items. A stratified 150-item sample is written to `human_validation/` for later human adjudication (not used in this paper's inference), and the absence of human validation is stated as a limitation.

### Analysis
As respecified in change 7 above. Primary: logistic regression of RETAINED at k=10 on within-family-centred surprise × operator with family fixed effects and a hierarchical bootstrap over families and trajectories; E-SHIFT as a within-item arm contrast; Δ-on-the-BT-scale for replacement direction with a within-family permutation null; held-out kernel prediction with TVD CIs against two baselines.

## Claim-Driven Validation

| # | Claim | Experiment | Decisive metric | Falsifier |
|---|---|---|---|---|
| **C1** | Prior-fit *causes* loss | E-SHIFT, 12 families × 2 frames × 3 seeds, O1 | retention(F+) − retention(F−) at k=10 | CI contains 0 while compression is demonstrably biting |
| **C2** | Graded dose–response under rewriting | 7 chains × 3 seeds, O1 | slope of RETAINED on within-family-centred surprise | slope CI contains 0 |
| **C3** | Absent under prior-blind capacity pressure | O3 COPY-RAND, same stimuli/coder | surprise × operator interaction + TOST on the O3 slope | O3 shows the same slope ⇒ artifact, not compaction |
| **C4** | Which channel: selection vs rewriting | O2 COPY-LLM vs O1 vs O4 SRC | slope per operator | — (descriptive; either answer is a result) |
| **C5** | Replacements move up the prior | all CHANGED-specific events | Δ = log p̂(new) − log p̂(old), clustered bootstrap + permutation null | Δ CI contains 0 |
| **C6** | One step predicts many | value-level kernel, held-out trajectories | TVD(p₀Kᵏ, observed) vs 2 baselines | no better than baselines ⇒ reported as non-Markov |
| **C7** | Preferences: storage vs execution, homogenization | 8 users × 20 prefs, A/B/C probes at k ∈ {0,10,20} | storage loss vs deviation-from-default; distance-to-centroid over k | — |
| **C8** | Surprise-pinning is a real fix | O6 vs O5 vs O1, plus token-matched random/low-surprise pinning | retention recovered per extra token | pinning works equally when pinning random items ⇒ salience, not surprise |

## Compute and Budget
No training. Local A10G/Qwen3-8B for P3, the small-model contrast and retrieval embeddings. Hosted spend, prospective ledger: prior elicitation ≈ $0.6; confirmatory chains (6 LLM operators × 21 trajectories × 20 steps ≈ 2,520 calls) ≈ $1.6; E-SHIFT ≈ $1.0; preferences + behaviour probes ≈ $1.0; one-factor diagnostics (temperature, budget, second family) ≈ $4; coding/judging ≈ $10–20. Total projected well inside the pilot ≤ $25 / full ≤ $90 envelope, leaving headroom to raise seeds after the power simulation rather than leaving the budget unused.


---

# Round-2 hardening (every item is part of the frozen design)


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


---

# Preregistration amendments A1-A3 (final, reviewer-approved)

## Amendment A1 — E-SHIFT sizing, frozen procedure

**Why**: 12 families x 3 seeds yields 12 independent stimulus clusters, which is likely underpowered for an
8 pp SESOI.

**Frozen procedure** (executed on dev data before any confirmatory chain runs):
1. Run E-SHIFT on the **dev** families (F01-F12) at the primary operating point to estimate two variance
   components: between-family SD of the paired arm difference, `s_fam`, and within-family (seed) SD, `s_seed`.
2. Simulate the frozen primary analysis (paired family-level contrast + paired family bootstrap, A2) under a
   true effect of exactly **8 pp**, for every (n_families, n_seeds) in
   {12, 16, 20, 24, 28} x {3, 4, 5, 6}, 2000 simulations each.
   **`n_families` means ELIGIBLE families** — families surviving the Half-A eligibility screen — because the
   primary population is eligible-only.
3. Choose the **smallest** (n_families, n_seeds) reaching **power >= 0.80**, preferring more families over
   more seeds at equal power. Publish the full power table in the appendix.
4. **Eligibility attrition is budgeted for**: let `r` be the eligible fraction observed on dev. The pool of
   families actually prepared and run is `ceil(n_families / r)`, capped at the 28 confirmatory families. The
   observed `r` and the realized eligible count are reported.
5. If no cell in the grid reaches 0.80 for 8 pp **at the realized eligible count**, use the maximum
   affordable cell and **freeze X, the minimum detectable effect at 0.80 under that cell, as the new SESOI**.
   A2's equivalence bounds then become **+/- X, not +/- 8 pp**, and the paper states X explicitly wherever it
   states the SESOI.
6. The chosen cell and the operative SESOI are written into `FROZEN_PROTOCOL.md` with a commit hash
   **before** any confirmatory E-SHIFT chain is run. The same (n_families, n_seeds) applies to both arms and
   to the O3 frame control.

**Budget impact**: the maximum cell (28 families x 2 arms x 6 seeds x 20 steps x 2 operators) is 13,440
compaction calls ~= $8.3 at the compactor's measured rate. Affordable; no design is sacrificed for power.

---

## Amendment A2 — complete C1 decision rule, frozen

**Primary population**: **eligible-only** — families whose arm shift reaches >= 0.5 log-odds on prior-elicitation
**Half A**. Eligibility therefore uses data independent of the achieved-shift estimate (Half B) and of the
retention outcome. **Intention-to-treat** over all prespecified E-SHIFT families is reported as sensitivity;
if ITT and eligible-only disagree in direction or decision, the paper reports both and declares C1
inconclusive.

**Estimator**: for family *f*, `d_f = mean_seeds[ retained(F+, k=10) ] - mean_seeds[ retained(F-, k=10) ]`
in percentage points, under O1. The primary statistic is the unweighted mean of `d_f` over eligible families.

**Clustering**: in E-SHIFT, trajectories are **nested within families** (each family has its own arm x seed
chains), so the primary inference uses a **family bootstrap with paired seeds resampled within family**:
families are resampled with replacement, and within each resampled family its arm-paired seed blocks are
resampled, keeping F+ / F- and O1 / O3 together in every block. 10,000 replicates. The **two-way crossed**
family x trajectory bootstrap is reserved for the multi-item main-chain experiment (C2, C3), where families
and chains genuinely cross.

**Decision rule** (four mutually exclusive outcomes, evaluated in this precedence order):
1. **Positive support for C1**: the 95% bootstrap CI for mean `d_f` excludes 0, lies in the predicted
   direction (`d > 0`), **and** the equivalence interval is *not* wholly inside +/- SESOI.
2. **Positive but below the SESOI**: the 95% CI excludes 0 in the predicted direction **and** the 90%
   equivalence interval lies wholly inside +/- SESOI. Reported as a real but practically small effect; it does
   **not** open the gate to C2/C3 as a confirmatory chain.
3. **Boundary evidence (informative null)**: the 95% CI includes 0 **and** the 90% equivalence interval
   (TOST at alpha = .05, both bounds) lies entirely inside **+/- SESOI**.
4. **Inconclusive**: none of the above. Reported as such, with the minimum detectable effect.

(SESOI = 8 pp unless amended to X by A1 step 5.)

**E-SHIFT O3 frame control**: equivalence margin **+/- 5 pp**. If the O3 arm difference is not equivalent to
zero within that margin, the paper flags possible residual frame interference and down-weights C1 accordingly;
this flag is reported whatever the O1 result is.

**Scoping**: a null is reported as "under the tested model, prompt, item domain and compression regime,
effects at least as large as 8 pp are excluded", never as a general claim about compactors.

---

## Amendment A3 — prospective O3 capacity matching, frozen

**Why**: a fixed slot count removes sentence-length selection bias but does not by itself establish that O3
felt the same capacity pressure as the 300-word O1 condition.

**Frozen procedure** (on dev data, before confirmatory runs):
1. Run O1 at B=300 on dev families; record `W1` = mean realized memory length in words at k=10.
2. From the dev source-sentence length distribution, compute expected realized O3 length as a function of
   slot count `s`, and set `s* = argmin_s |E[len(s)] - W1|`.
3. **Tolerance**: `|mean realized O3 length - W1| <= 0.10 * W1`.
   - If met → O3 is described as an **identical-capacity, prior-blind control**.
   - If not met → O3 is relabelled a **prior-blind deletion control** and the capacity claim is dropped from
     the text. Either way the number is reported.
4. **Non-degeneracy**: require O3 retention at k=10 in `[0.10, 0.90]`. If O3 retention is at ceiling, the
   slot count is too generous for the control to be informative, and `s*` is reduced to the largest value
   satisfying the non-degeneracy bound — chosen on **dev data only**, then frozen.
5. `s*`, `W1`, the achieved tolerance and the non-degeneracy check are written into `FROZEN_PROTOCOL.md`
   with a commit hash before the first confirmatory run.

---

## Status after A1-A3
All three of the reviewer's remaining blockers are discharged at the specification level. A1 and A3 require
**dev-data measurements**, which the pilot produces by design; their numeric outputs are filled into
`FROZEN_PROTOCOL.md` at the end of the pilot and before any confirmatory family is touched. A2 is fully
frozen now and requires no data.
