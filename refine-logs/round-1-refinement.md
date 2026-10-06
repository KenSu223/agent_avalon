# Round 1 Refinement

## Problem Anchor
*(Copied verbatim from round 0. Immutable.)*

- **Bottom-line problem**: LLM agents are supposed to keep learning after pretraining by writing things down. In practice an LLM repeatedly rewrites its own memory (summarize → summarize the summary → consolidate across sessions). We do not know what this loop systematically destroys, or why.
- **Must-solve bottleneck**: Memory exists to hold what the model does *not* already expect — a user's idiosyncratic preference, a local fact about this deployment, a lesson from a specific failure. If the rewriting loop pulls memory content back toward what the compacting LLM would have guessed anyway, then memory is worst at keeping exactly the content it exists for, and in-context continual learning has a ceiling that no amount of context length fixes. No controlled test of this exists: prior work either observes degradation without manipulating prior-fit (Zhang et al. 2605.12978; Compaction Cliff 2608.22752), or asserts drift-to-defaults without measuring it (Zahn & Chana 2603.17781).
- **Non-goals**: Not a new memory architecture, framework, or leaderboard. Not security (no attacks/poisoning/adversaries/defenses; mitigations are called *memory design*). Not human-subject work this cycle. Not multi-agent in the main line (designated fallback only).
- **Constraints**: ACL 2027 (ARR, 8-page long paper, anonymous), theme track *Homogenization and knowledge collapse in LLMs*. 1× A10G (24 GB) running Qwen3-8B via vLLM (free, logprobs, non-thinking) + hard $140 hosted budget. No training, no human annotation. Main compactor must be a **strong** hosted model (default qwen3-235b-a22b-2507) so a null cannot be blamed on a weak model; spot-check a second strong family. Own stimuli + MIT/Apache/CC BY data only.
- **Success condition**: A controlled demonstration that, holding content type, length, position, exposure and truth constant, *retention of a memory item falls as its independently measured deviation from the compactor's prior rises*, that this happens only for operators that rewrite memory, that rewrites move content toward the prior, and that a model fitted to one compaction step predicts the state distribution many steps later. Plus an honest statement of where the effect does **not** hold.

## Anchor Check
- **Original bottleneck**: repeated LLM rewriting of memory erases precisely the non-default content memory exists for.
- **Why the revised design still addresses it**: every change strengthens the inference *about that bottleneck*. The same-item prior-shift test makes the claim causal rather than correlational; the value-level kernel makes the dynamics claim formally correct; the fixed-budget extractive controls separate "the LLM rewrote it away" from "it did not fit". Nothing was traded for an easier question.
- **Reviewer suggestions rejected as drift**: none on the main line. One **partial pushback** on the fallback (below).

## Simplicity Check
- **Dominant contribution after revision**: a causal demonstration that prior-fit controls survival of content through LLM memory compaction, with the same-item prior-shift test as the decisive evidence.
- **Components removed or merged**: external datasets (MemoryAgentBench, CounterFact) deleted; Aider-style decay operator deleted; the 4×3×3 Cartesian grid replaced by one primary operating point plus one-factor diagnostics; preferences demoted from a co-equal claim to one application section; QA probes restricted to two endpoints; temperature demoted from "learner-type identification" to descriptive robustness.
- **Added, and why each is load-bearing**: (i) same-item prior-shift — the only way to make the claim causal; (ii) `COPY-RAND` prior-blind extractive control — the only way to rule out that the gradient is produced by capacity pressure or by the coder; (iii) `COPY-LLM` verbatim-selection operator — separates the selection channel from the rewriting channel, which the project's own formalization (§2.2 of the idea doc) demands and which nothing else isolates; (iv) compactor-side Bradley-Terry prior elicitation — the dose must be measured on the learner being studied.
- **Net**: three operators deleted or merged away, three added, each discharging a named confound. The operator set is now a lattice in which every arm removes exactly one mechanism.

## Changes Made

### 1. Causal identification: same-item prior shift (reviewer CRITICAL #1)
- **Reviewer said**: minimal pairs confound prior with magnitude, consequence, lexical form and compressibility; the design yields correlation with measured surprise, not causation.
- **Action**: added **E-SHIFT**. For 12 confirmatory families we fix the target sentence *and its value* and vary only a one-sentence contextual base-rate frame placed in the same slot of the seeding session, in two arms (`F+` makes the value expected, `F−` makes it surprising). Frames are matched for length and syntactic form and both arms contain exactly one frame sentence. The manipulation is *validated before the chains run*: only families where compactor-elicited p(v\*) shifts by at least 0.5 log-odds between arms enter the confirmatory analysis, and the number discarded is reported.
- **Reasoning**: this holds every lexical, numeric and semantic property of the target constant, so a retention difference between arms cannot be attributed to magnitude, token length, compressibility or perceived consequence. It is the single highest-value addition and costs ~1,440 compaction calls (≈$1).
- **Impact**: promotes the headline from "retention correlates with measured surprise" to "retention is controlled by prior-fit", and simultaneously discharges 6 of the 23 audited confounds.

### 2. The dose is measured on the compactor (reviewer CRITICAL #2)
- **Reviewer said**: Qwen3-8B logprobs are not Qwen3-235B's prior; 30 free-form samples give zeros and unstable estimates.
- **Action**: the **primary** prior is now a randomized-order structured **pairwise-choice** elicitation run on the actual compactor: within each family, every unordered level pair in both presentation orders, with replicates, fitted per family with **Bradley-Terry** to a log-odds scale; split-half reliability reported; prior uncertainty propagated into the retention analysis rather than treated as exact. Generative elicitation (T=1 × 30) is retained as a second compactor-side estimate; local Qwen3-8B logprobs are demoted to a robustness check and to the small-model contrast. Spearman ρ among all three is reported.
- **Reasoning**: pairwise choice avoids the zero-count problem entirely, is cheap (~$0.5 for the whole item set), and is measured on the learner whose prior the theory is about.

### 3. Formal model replaced: value-level kernel, not three-state stationarity (reviewer CRITICAL #3)
- **Reviewer said**: iterated learning does not generally imply stationary distribution = prior for an LLM summarization chain; CHANGED is not a Markov state; if DROPPED is absorbing, the stationary distribution is trivially all-DROPPED; predictions must be p₀Kᵏ.
- **Action**: the three-state model is replaced by a **value-level copy/drop/replace kernel** K over states {L1…L5, OTHER, VAGUE, ABSENT}. ABSENT is treated as absorbing *and this is tested* (we measure the empirical regeneration rate out of ABSENT rather than assuming it is zero). We estimate K from k=0→1 on half the trajectories and predict p₀Kᵏ on **held-out** trajectories at k=10/15/20, with bootstrap CIs on TVD and comparison against two baselines (constant one-step retention; pure absorbing-drop). Because ABSENT is near-absorbing, the paper reports the **quasi-stationary distribution conditional on survival**, which is where the prior-shaping claim actually lives.
- **Reasoning**: the reviewer is right and the correction is also scientifically better — "what survives becomes prior-shaped before it eventually disappears" is the true and more interesting statement.
- **Impact**: the headline framing changes from "memory converges to the prior" to **prior-shaped selective survival and replacement under iterated compression**. The thesis is preserved; the overclaim is removed.

### 4. A real bottleneck control (reviewer CRITICAL #4)
- **Reviewer said**: append-only has no compression bottleneck and its stored-text retention is perfect by construction, so it cannot separate generative rewriting from generic capacity loss.
- **Action**: the operator set becomes a lattice in which each arm removes exactly one mechanism:

| id | operator | rewrites text? | LLM selects? | budget B? | prior-blind? |
|---|---|---|---|---|---|
| **O1 ROLL** | rolling rewrite of M_{t−1} + session, neutral prompt (**primary**) | yes | yes | yes | no |
| **O2 COPY-LLM** | LLM selects source sentences and copies them **verbatim**, budget B | no | yes | yes | no |
| **O3 COPY-RAND** | uniform random verbatim subsample to budget B, fixed seed | no | no | yes | **yes** |
| **O4 SRC** | rewrite from all raw sessions each step (never reads its own last version), budget B | yes | yes | yes | no |
| **O5 ANCHOR** | O1 + Codex anti-drift rules (industry mitigation) | yes | yes | yes | no |
| **O6 PIN** | O1 + verbatim pinning of the top-q surprise items (ours) | yes | yes | yes | by design |
| **O7 FULL** | append-only, no budget (access ceiling / probe control) | no | no | no | yes |

  **O3 is the decisive null control**: identical capacity pressure, identical stimuli, identical coder and probes, but selection cannot depend on prior. A surprise gradient in O3 would mean the gradient is an artifact of the coder, the regexes or capacity competition. **O2 vs O1** separates the *selection* channel from the *rewriting* channel, which the project's own formalization requires and which nothing in the prior literature isolates. **O4 vs O1** separates iterated self-reading from one-shot abstraction.
- **Reasoning**: this costs one extra operator arm and buys the two cleanest controls in the paper.

### 5. Preregistered operating point, dev/confirmatory split (reviewer CRITICAL #5)
- **Reviewer said**: tightening B or lengthening the chain after seeing a null is a data-dependent search for an effect.
- **Action**: the 40 mundane fact families split into **dev** (F01–F12) and **confirmatory** (F13–F40), and the 20 preference families into dev (P01–P06) and confirmatory (P07–P20). All operating-point choices — budget B, chain length, compaction prompt wording, coder thresholds, judge prompt — are made on dev families only and then **frozen into `FROZEN_PROTOCOL.md` with a git commit hash** before any confirmatory family is run. The confirmatory analysis is specified in advance: primary endpoint k=10, primary operator contrast O1 vs O3, primary test the surprise × operator interaction.
- **Reasoning**: this is the difference between a result and a search. It costs nothing but discipline.

### 6. Claim language brought back to what the evidence supports (reviewer CRITICAL #6)
- **Reviewer said**: stationarity-equals-prior, temperature-identifies-learner-type, and one-step-predicts-twenty are stronger than the evidence permits.
- **Action**: (i) the formal section states its assumptions explicitly and claims only what the kernel supports; (ii) temperature becomes a **descriptive robustness** factor — we report how the gradient and the destination distribution change with T, and explicitly decline to identify a learner type, noting Cui & Yu's finding that T=1 need not be posterior sampling; (iii) the prediction claim is stated as "a one-step kernel predicts held-out k-step distributions better than two naive baselines", with CIs.
- **Reasoning**: a smaller, defended claim survives review; a large undefended one does not.

### 7. Statistics respecified (reviewer statistical audit)
- **Action**:
  - **Primary model**: logistic regression of RETAINED at k=10 on **within-family-centred** surprise × operator, with **family fixed effects**, and uncertainty from a **hierarchical bootstrap resampling families and whole trajectories**. (Chosen over a GLMM because it is robust, convergence-free, and gives exactly the family-level control and trajectory-level clustering the reviewer asked for.)
  - "Only under rewriting" is tested as a **surprise × operator interaction**, and the O3 control slope additionally gets a **TOST equivalence test** against a prespecified margin, since failure to reject is not evidence of absence.
  - **Direction of replacement**: the 50% binomial null is dropped. We use Δ = log p̂(v_new) − log p̂(v_old) on the Bradley-Terry scale with a family/trajectory-clustered bootstrap, plus a **within-family destination-label permutation** null. Novel values are coded OTHER and scored by a separate compactor-side typicality comparison rather than being snapped onto the nearest canonical level (which would manufacture the result).
  - **Kernel**: held-out trajectories; TVD with bootstrap CIs; two baselines.
  - **Judges**: two families, schema-constrained JSON, **blind to level order, surprise scores and hypotheses**; report confusion matrix, raw and class-wise agreement alongside κ; report every headline conclusion under each judge separately and under agreement-only items.
  - **QA correction**: report acc − g with intervals instead of (acc−g)/(1−g).
  - **Users**: user-level permutation and distance-to-centroid instead of treating 28 pairwise distances as independent.
  - **Power**: a simulation-based power calculation under the clustered structure, run on pilot estimates, fixes the number of chains and seeds before the confirmatory run.

### 8. Scope cuts (reviewer IMPORTANT, feasibility)
- **Action**: deleted MemoryAgentBench FactConsolidation, CounterFact and the Aider operator. The design is staged: **one primary operating point** (strong compactor, T=1.0 as the production-like default, B=300, k=10) carries the confirmatory claims; temperature {0, 0.5, 1.3}, budget {150, 600}, and a second strong family are **one-factor diagnostics** on the O1/O3 subset; the local 8B model is a free small-model contrast. A prospective token-and-dollar ledger is kept in `COST_LOG.md` and every batch over $2 is estimated first.
- **Reasoning**: the deleted items did not manipulate the causal variable, so they cost pages and calls without supporting the claim.

### 9. Pushback: the null-result fallback (reviewer Drift Warning)
- **Reviewer said**: delete the multi-agent fallback; it changes the unit of study, conflicts with a stated non-goal, and "keep the thesis" after decisive tests fail is unfalsifiable.
- **Action — partial accept, with a correction the reviewer is right about**: the fallback is a standing instruction in the Problem Anchor's constraints (PI directive 2) and is not mine to delete, so it remains as a *project-level contingency*. But the reviewer's substantive point is adopted in full and it changes the paper: **a clean null under adequate compression and strong controls will be written up and submitted as a boundary result for this paper**, not relabelled as a success and not used to license a different paper. Concretely: (i) the go/no-go criteria G1–G3 are preregistered and will be reported as passed or failed either way; (ii) if E-SHIFT is null while compression is demonstrably biting (truncation and compression ratio logged), the paper's claim becomes "prior-fit does not control survival in strong compactors at this compression regime, contrary to a widely repeated informal claim", which is a publishable and useful result; (iii) the multi-agent direction, if the PI later elects it, is a *different* paper and will be labelled as such.
- **Reasoning**: the Anchor's constraints bind, but the Anchor's non-goals bind too, and honest reporting of nulls is itself an explicit PI directive. This reconciliation satisfies both.

---

## Revised Proposal

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
