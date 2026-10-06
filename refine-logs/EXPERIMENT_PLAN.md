# Experiment Plan

**Problem**: LLM agents keep what they learn in memory that an LLM repeatedly rewrites. The loop erases precisely the non-default content memory exists for.
**Method thesis**: Iterated LLM compaction is selection plus replacement whose kernel is shaped by the compactor's prior; survival falls with prior-surprise, replacements move up the prior, and this requires rewriting rather than capacity pressure.
**Date**: 2026-10-06. **Venue**: ACL 2027 theme track. **Source**: `refine-logs/FINAL_PROPOSAL.md` (refine score 9.5/10, READY).

---

## Claim Map

| Claim | Tier | Why it matters | Minimum convincing evidence | Blocks |
|---|---|---|---|---|
| **C1** Prior-fit *causes* loss | Confirmatory, gate 1 | Everything else is correlational without it | E-SHIFT: same sentence, same value, only a value-free base-rate frame differs; paired family contrast at k=10 with a prespecified SESOI and a four-outcome decision rule | B3 |
| **C2** Graded dose–response under rewriting | Confirmatory, gate 2 | Shows the effect is graded and ecological, not a two-point artifact | Slope of RETAINED at k=10 on within-family-centred Bradley-Terry surprise, family FE + two-way crossed bootstrap | B4 |
| **C3** Operator specificity | Confirmatory, gate 3 | Rules out capacity pressure, coder artifacts and retrieval | surprise x operator interaction (O1 vs O3) **plus** TOST equivalence on the O3 slope | B4 |
| **C4** Which channel: selection vs rewriting | Secondary | Localizes the mechanism; nothing in the literature separates these | Per-operator slopes for O1 / O2 / O4 with CIs | B4 |
| **C5** Replacements move up the prior | Secondary | Direction is what makes it "regression to the prior" rather than noise | Δ = log p̂(new) − log p̂(old) on the BT scale, clustered bootstrap + stratified permutation null | B6 |
| **C6** One step predicts many | Secondary | Turns the finding into a design tool | Value-level kernel over prior-rank states, held-out trajectories, paired ΔTVD vs two baselines | B5 |
| **C7** Surprise-pinning is a real fix | Secondary | The memory-design payload; must beat salience | O6 vs O5 vs O1 and vs token-matched random / low-surprise pinning | B7 |
| **A1** Preferences: storage vs execution, cross-user homogenization | Exploratory application | ACL theme-track payload | Storage loss vs deviation-from-default; distance-to-centroid over k, shown in coded memory **before** behaviour | B9 |

**Anti-claims to rule out** (each owned by a block):
- "It is just capacity pressure" → **O3 COPY-RAND**, prior-blind, capacity-matched (B4).
- "It is the coder / the regexes favour common formats" → O3 again, plus two blind cross-family judges (B10).
- "It is magnitude / token length / compressibility, not prior" → **E-SHIFT** holds the value fixed (B3); token length is a prespecified nuisance covariate and C2 is repeated on a token-matched subset (B4).
- "It is retrieval, not storage" → O7 with **oracle retrieval** as ceiling; embedding retrieval reported separately as a baseline (B4).
- "Pinning works by salience, not surprise" → token-matched random / low-surprise pinning (B7).
- "It only happens to weak models" → strong hosted compactor is the primary; 8B is the contrast, not the headline (B8).

---

## Paper storyline

- **Main paper must prove**: C1 (Fig. 1), C2 + C3 (Fig. 2 + Table 1), C5 (Fig. 3), C7 (Fig. 5). A1 gets one compact panel (Fig. 4).
- **Appendix supports**: C4 channel decomposition, C6 kernel fit and power table, temperature/budget/second-family diagnostics, prior-method agreement, judge agreement, token-length audit, frozen manifest.
- **Intentionally cut**: MemoryAgentBench FactConsolidation, CounterFact, ClashEval (licence), Aider-style decay operator, the full Cartesian grid, human transmission chains, cross-lingual evidentials, multi-agent.

---

## Experiment Blocks

### B0 — Sanity and instrument build  *(MUST-RUN)*
- **Claim tested**: none; protects every other block.
- **Why**: a broken coder or a leaky distractor invalidates all downstream inference.
- **Work**: rebuild stimuli with `{{COMPANY}}`/`{{TOWN}}` parameterization and a 5x5 name Latin square; generate 30 distractor sessions and **scrub** them against every family's level regexes (reject any distractor containing a candidate value, unit or number); unit-test the three-state coder on synthetic paraphrases, unit variants and negations; audit compactor-tokenizer lengths of all level values.
- **Success criterion**: zero distractor leaks; coder agrees with hand-written expectations on all unit tests; token-length audit stored in the manifest.
- **Failure interpretation**: fix before anything else runs.
- **Target**: Appendix (instrument description) + `FROZEN_PROTOCOL.md`.

### B1 — Prior measurement  *(MUST-RUN)*
- **Claim tested**: supplies the dose for C1, C2, C5, C6, C7.
- **Compared systems**: P1 compactor pairwise Bradley-Terry (**primary**, split-half A/B) · P2 compactor generative elicitation T=1 x 30 · P3 local Qwen3-8B logprobs (robustness + small-model contrast) · P4 default-behaviour rate (preferences).
- **Metrics**: per-family BT log-odds; split-half reliability; Spearman ρ among P1/P2/P3.
- **Setup**: same system role, memory-notes format and entity introduction as the compaction chain (priors are prompt-conditioned). Randomized presentation order, both orders per pair, replicated. Temperature 0 for the choice itself.
- **Success criterion**: split-half ρ ≥ 0.7 within family; P1–P2 Spearman reported whatever it is.
- **Failure interpretation**: if split-half reliability is poor, add replicates before freezing — this is dev-stage work, so it does not contaminate confirmation.
- **Target**: Table A1, Fig. A1.

### B2 — Pilot on dev families, operating-point selection  *(MUST-RUN)*
- **Claim tested**: none; discharges amendments A1 and A3 and selects the frozen operating point.
- **Dataset**: dev families **F01–F12**, preferences **P01–P06** only.
- **Runs**: O1 at B ∈ {150, 300, 600} x T ∈ {0, 1.0}; O3 slot-count calibration; a dev E-SHIFT run for variance components.
- **Decisions produced** (then frozen with a commit hash):
  1. budget B and temperature for the primary operating point;
  2. `W1` = mean realized memory length, and O3 slot count `s*` with the 10% tolerance and non-degeneracy re-check (**A3**);
  3. between-family and within-family SD of the E-SHIFT paired difference → simulation power table → final (n_families, n_seeds) and the operative SESOI (**A1**);
  4. eligible fraction `r` for E-SHIFT, so the prepared pool is `ceil(n_families / r)`.
- **Success criterion**: the **empirical adequacy condition** is achievable — at k=10 under O1, mean retention at least 10 pp below O7 and within [0.10, 0.90].
- **Failure interpretation**: if no (B, T) in the dev grid satisfies adequacy at the strong compactor, that is itself the headline result ("a strong compactor does not lose this content at any tested compression"), and it is reported as a scoped boundary result rather than papered over.
- **Target**: Table A2 (power table), `FROZEN_PROTOCOL.md`.

### B3 — E-SHIFT, the causal test  *(MUST-RUN, gate 1)*
- **Claim tested**: **C1**.
- **Dataset**: confirmatory families, pool size `ceil(n_families / r)` capped at 28; two arms per family (`F+` expected / `F−` surprising); frames are value-free role cues in the user's self-description, length- and form-matched, screened by both blind judges for importance / authority / relevance parity.
- **Compared systems**: O1 (primary) and O3 (frame control, free of prior conditioning).
- **Metrics**: `d_f` = retention(F+) − retention(F−) at k=10 in percentage points; mean over eligible families.
- **Setup**: eligibility from prior-elicitation **Half A**, achieved shift from **Half B**; family bootstrap with arm-paired seed blocks resampled within family, 10,000 replicates.
- **Success criterion**: the frozen four-outcome rule — positive support / positive-but-below-SESOI / boundary evidence / inconclusive.
- **Failure interpretation**: boundary evidence is a publishable scoped null; inconclusive triggers reporting the minimum detectable effect, not a search for a bigger effect.
- **Target**: **Figure 1** + Table 1.

### B4 — Main chains: dose–response and operator lattice  *(MUST-RUN, gates 2–3)*
- **Claims tested**: **C2, C3, C4** (and supplies data for C5, C6).
- **Dataset**: confirmatory families F13–F40, 7 chains x 20 items (each (family, level) once; 4 items per level per chain; constrained randomization on frozen BT estimates for measured-surprise balance), 3+ seeds.
- **Compared systems**: O1 ROLL (primary) · O2 COPY-LLM · O3 COPY-RAND · O4 SRC · O5 ANCHOR · O6 PIN · O7 FULL (oracle retrieval = ceiling; embedding retrieval reported separately as a baseline).
- **Metrics**: RETAINED at k=10 (primary); full k ∈ {0,1,2,3,5,7,10,15,20} curves; slope on within-family-centred surprise per operator.
- **Setup**: family-FE **linear probability model** with token-length and format nuisance covariates; **two-way crossed cluster bootstrap** over families and chain x seed blocks (blocks carry all paired operators); bias-reduced logistic with AMEs as robustness.
- **Success criterion**: C2 slope CI excludes 0 under O1; C3 interaction CI excludes 0 **and** the O3 slope is equivalent to zero within ±5 pp.
- **Failure interpretation**: an O3 slope matching O1 means the gradient is an artifact of the coder or capacity, and the paper says so.
- **Target**: **Figure 2**, **Table 1**.

### B5 — Value-level kernel  *(MUST-RUN, no new model calls)*
- **Claim tested**: **C6**. Reuses B4 trajectories.
- **Setup**: states = measured prior rank R1…R5 + OTHER + VAGUE + ABSENT; K estimated from k=0→1 on half the trajectories; Dirichlet smoothing with uncertainty propagated; unsupported rows constrained and declared; prediction p₀Kᵏ on **held-out** trajectories at k=10/15/20; same held-out p₀ for K and both baselines (constant one-step retention; pure absorbing-drop); inference on the **paired ΔTVD**.
- **Success criterion**: paired ΔTVD favours K over both baselines with a CI excluding 0.
- **Failure interpretation**: reported as evidence the process is non-Markov at value level — still informative.
- **Target**: Figure A2, Table A3.

### B6 — Replacement direction  *(MUST-RUN, small extra BT calls)*
- **Claim tested**: **C5**. Reuses B4 CHANGED-specific events.
- **Setup**: Δ = log p̂(v_new) − log p̂(v_old) on the BT scale; permutation null stratified within origin-rank x numeric-distance stratum, preserving the candidate opportunity set; conditional destination model on destination BT score and value distance reported alongside. **OTHER destinations analysed separately**, scored by augmenting that family's BT fit with the novel value through fresh pairwise comparisons — never snapped onto a canonical level.
- **Success criterion**: mean Δ > 0 with a clustered-bootstrap CI excluding 0 and a permutation p < .05.
- **Target**: **Figure 3**.

### B7 — Surprise-pinning vs the industry prompt  *(MUST-RUN)*
- **Claim tested**: **C7**.
- **Compared systems**: O1 (no mitigation) · O5 ANCHOR (Codex anti-drift rules, the deployed mitigation) · O6 PIN (top-q measured-surprise items pinned verbatim) · **token-matched random pinning** · **token-matched low-surprise pinning**.
- **Metrics**: retention at k=10 by surprise tercile; retention recovered per extra token of memory budget.
- **Success criterion**: O6 recovers materially more high-surprise retention than O1 **and** than both token-matched controls at equal token cost.
- **Failure interpretation**: if random pinning does as well, the mechanism is salience not surprise, and the paper reports that instead.
- **Target**: **Figure 5**.

### B8 — Robustness diagnostics  *(NICE-TO-HAVE, cheap)*
- **Claims**: scope conditions for C2/C3.
- **Runs**: temperature T ∈ {0, 0.5, 1.3} on the O1/O3 subset; budget B ∈ {150, 600}; second strong family `meta.llama3-3-70b-instruct-v1:0` on O1/O3; `local:qwen3-8b` small-model contrast (free); prior re-elicitation in masked k=1 and k=10 contexts for rank stability.
- **Setup note**: temperature is **descriptive robustness**, not learner-type identification.
- **Target**: Table A4, Fig. A3.

### B9 — Preferences, exploratory application  *(NICE-TO-HAVE)*
- **Claim**: **A1**.
- **Setup**: 8 simulated users x 20 preferences; three-condition probe A (raw instructions) / B (memory at k) / C (nothing) at k ∈ {0, 10, 20}; **disjoint prompts and seeds** for default elicitation vs behavioural evaluation; convergence shown in **coded stored memory first**, then behaviour; user-level permutation and distance-to-centroid rather than 28 dependent pairwise distances. Generalization claimed over preference families, not over users.
- **Target**: **Figure 4** (one panel), rest to appendix.

### B10 — Coding reliability  *(MUST-RUN)*
- **Setup**: two judges from different families (`openai.gpt-oss-120b-1:0`, `google.gemma-3-27b-it`), schema-constrained JSON, blind to level order, surprise and hypotheses. Report κ, confusion matrix, raw and class-wise agreement; repeat every headline conclusion under each judge separately and on agreement-only items. Archive a stratified 150-item sample to `human_validation/` for later human adjudication (**not** used in this paper's inference).
- **Target**: Table A5; Limitations.

---

## Run Order and Milestones

| Milestone | Goal | Runs | Decision gate | Est. cost | Risk |
|---|---|---|---|---|---|
| **M0** | Instrument correct | B0 | zero distractor leaks; coder unit tests pass | ~$0 (local) | leaky distractors invalidate everything |
| **M1** | Dose exists and is reliable | B1 | split-half ρ ≥ 0.7; P1/P2 agreement reported | ~$1 | unreliable priors ⇒ add replicates (dev stage) |
| **M2** | Operating point frozen | B2 | **empirical adequacy** achievable; A1 + A3 discharged; `FROZEN_PROTOCOL.md` committed | ~$6 | strong model may not lose content at any B ⇒ scoped boundary result |
| **M3** | Causal claim | B3 | four-outcome rule on C1 | ~$9 | underpowered ⇒ A1 raises families/seeds or freezes SESOI X |
| **M4** | Dose–response + operator lattice | B4, B5, B6, B7 | C2 slope; C3 interaction + O3 equivalence | ~$12 | O3 gradient ⇒ artifact, report honestly |
| **M5** | Scope, application, reliability | B8, B9, B10 | none; all reported | ~$12 | — |

Gates are **claim-selection criteria**, not publication gates: the paper is written and submitted under either outcome.

## Compute and Data Budget
- **GPU**: 1x A10G running Qwen3-8B (P3 logprobs, small-model contrast, retrieval embeddings). No training, no GPU-hours beyond inference.
- **Hosted**: projected **≈$40** total against a $140 cap — M0 ~$0, M1 ~$1, M2 ~$6, M3 ~$9, M4 ~$12, M5 ~$12. Every batch over $2 is cost-estimated into `COST_LOG.md` first. Headroom is deliberately reserved for raising seeds after the power simulation and for review-driven additions.
- **Data prep**: stimuli rebuild + 30 distractor sessions + E-SHIFT frame authoring and screening.
- **Human evaluation**: **none** (hard constraint). Two cross-family LLM judges substitute; a stratified 150-item sample is archived for later.
- **Biggest bottleneck**: judge/probe call volume, not compaction. Mitigated by regex-first coding and batching.

## Risks and Mitigations
- **Strong compactor loses nothing** → B2 sweeps B and T on dev before confirming; if adequacy fails everywhere, report the scoped boundary result (PI directive 2 explicitly requires honest nulls).
- **Coder artifact** → O3 prior-blind control + two blind judges + per-judge reporting.
- **Winner's curse on E-SHIFT eligibility** → split-half eligibility (Half A) vs estimate (Half B) + ITT sensitivity.
- **Underpowered causal test** → prespecified power simulation; fall back to a frozen SESOI X rather than claiming an unpowered null.
- **Budget overrun** → prospective ledger, cheapest-adequate model per role, local model for everything free.
- **Scooping (Zhang et al.)** → introduction cites them explicitly and positions this as theory + controlled causal test; nothing in the plan depends on their data.

## Final Checklist
- [x] Main paper tables covered (Fig 1–5, Table 1)
- [x] Novelty isolated (E-SHIFT holds the item fixed; O2/O4 localize the channel)
- [x] Simplicity defended (external datasets, Aider operator and the Cartesian grid deleted; each operator removes exactly one mechanism)
- [x] Frontier contribution justified (LLM as the object of study; compactor-side prior elicitation; no training, no new architecture)
- [x] Nice-to-have separated from must-run
- [x] Null outcome has a prespecified, publishable form
