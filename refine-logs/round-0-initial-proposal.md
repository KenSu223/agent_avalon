# Research Proposal: Agents Forget What Surprised Them — Memory Compaction as Iterated Learning

## Problem Anchor

*(Immutable. Copied verbatim into every round.)*

- **Bottom-line problem**: LLM agents are supposed to keep learning after pretraining by writing things down. In practice an LLM repeatedly rewrites its own memory (summarize → summarize the summary → consolidate across sessions). We do not know what this loop systematically destroys, or why.
- **Must-solve bottleneck**: Memory exists to hold what the model does *not* already expect — a user's idiosyncratic preference, a local fact about this deployment, a lesson from a specific failure. If the rewriting loop pulls memory content back toward what the compacting LLM would have guessed anyway, then memory is worst at keeping exactly the content it exists for, and in-context continual learning has a ceiling that no amount of context length fixes. No controlled test of this exists: prior work either observes degradation without manipulating prior-fit (Zhang et al. 2605.12978; Compaction Cliff 2608.22752), or asserts drift-to-defaults without measuring it (Zahn & Chana 2603.17781).
- **Non-goals**:
  - Not a new memory architecture, not a new agent framework, not a leaderboard.
  - Not security: no attacks, no poisoning, no adversaries, no defenses. Mitigations are called *memory design*.
  - Not human-subject work in this cycle (no κ annotation, no IRB, no crowdworkers).
  - Not multi-agent in the main line (held as the designated fallback angle only).
- **Constraints**:
  - Venue ACL 2027 (ARR, 8-page long paper, anonymous). Primary track: special theme *Homogenization and knowledge collapse in LLMs*.
  - Compute: 1× A10G (24 GB) running Qwen3-8B via vLLM (free, logprobs, non-thinking) + a hard $140 Bedrock budget through a local proxy. No training. No human annotation.
  - PI directive: the main compactor must be a **strong** hosted model (default `qwen.qwen3-235b-a22b-2507-v1:0`) so a null cannot be blamed on a weak model; spot-check a second strong family.
  - Data: own stimuli + MIT/Apache/CC BY sources only. No ClashEval redistribution, no CC BY-NC data.
- **Success condition**: A controlled demonstration that, holding content type, length, position, exposure and truth constant, *retention of a memory item falls as its independently measured deviation from the compactor's prior rises*, that this happens only for operators that rewrite memory, that rewrites move content toward the prior, and that a model fitted to one compaction step predicts the state distribution many steps later. Plus an honest statement of where the effect does **not** hold.

---

## Technical Gap

**What current systems do.** A survey of 30+ production and research memory systems (`docs/idea/idea1_survey/`) establishes that summary-of-a-summary is the norm, not an edge case: every open-source coding agent checked (Codex, OpenHands, Aider, Cline, Gemini CLI), the Anthropic API compaction endpoint ("the new block summarizes the old summary and everything after it"), Letta/MemGPT, Graphiti's entity summaries, and LangMem all generate M_{t+1} from M_t plus new material. There are two timescales: within-session compaction (triggered at 1/16 to 90% of the window) and cross-session consolidation (Codex Memories, Claude Code auto memory, ChatGPT memory), and the second has **no bound on chain length** — it is exactly the continual-learning setting.

**Where this breaks, and why nobody has shown it cleanly.**
1. Zhang et al. (2605.12978) measure that continual consolidation makes memory *worse than no memory* and that in-place rewriting is the single most harmful operator (43.2 vs 76.6 for raw traces, their Table 5). But their PropWorld deliberately uses nonce attributes with arbitrary mappings, which **removes the prior as a variable**. They attribute the loss to over-generalization. Their project page states the prior intuition informally; the paper contains no iterated-learning derivation, no Markov analysis, no temperature manipulation.
2. Compaction Cliff (2608.22752) measures constraint recall collapsing 53% → 10% over 5 compactions, but their materials have no prior-fit dimension.
3. Zahn & Chana (2603.17781) *claim* non-default constraints "drift toward plausible defaults" after 3 self-summarization rounds (46% fully correct), but publish no per-item data, never record what constraints were replaced *with*, and release neither code nor data.
4. The knowledge-conflict literature (ClashEval, Xie et al., Du et al., Sun et al.) does manipulate plausibility, but only for **one step**, and only for parametric memory about real entities. Kochelka et al. (2609.09363) find the single-step effect is weak (−0.05 on a 5-point scale) — which is precisely the argument for studying accumulation.

**Why naive fixes are insufficient.** Longer context does not help: cross-session consolidation chains are unbounded by construction, and the compaction trigger is a fraction of whatever the window is. Better retrieval does not help: the original text is *gone* in rolling-rewrite systems. "Just prompt it to preserve wording" is already deployed (Codex's consolidation rules) and has never been evaluated — we evaluate it.

**The missing mechanism.** Nobody has (a) made deviation-from-prior an **independent variable** in a memory chain, (b) identified the loop as iterated learning and taken the formal consequences seriously, or (c) turned a single compaction step into a quantitative predictor of long-run memory state.

---

## Method Thesis

- **One-sentence thesis**: LLM-driven memory compaction is an instance of **iterated learning**, so the stationary distribution of a memory item is governed by the compactor's prior rather than by what was written — and therefore retention decreases monotonically in independently measured surprise, only along rewriting operators, with rewrites moving content toward the prior.
- **Why this is the smallest adequate intervention**: We change exactly one thing relative to existing degradation studies — we grade and independently measure the prior-fit of each memory item, holding everything else fixed with minimal pairs. No new model, no new architecture, no training. The theory supplies the prediction; the instrument supplies the test.
- **Why timely**: Cross-session LLM-written memory shipped in 2025–26 in every major agent product. The ACL 2027 theme track asks for mechanisms of homogenization and knowledge collapse; this is an **inference-time, in-context** mechanism that has not been described, and it predicts personalization collapse (every user's assistant converges to the average user's assistant) as a corollary rather than as a separate story.

---

## Contribution Focus

- **Dominant contribution**: The first controlled test that memory-compaction retention is governed by the compactor's prior — delivered through *MemPrior*, a minimal-pair testbed whose items are matched on content type, length, position, exposure count and truth, and differ only in independently measured surprise.
- **Supporting contribution**: A **three-state compaction model** (RETAINED / CHANGED / DROPPED) fitted to a single compaction step that predicts the state distribution 10–20 steps later, which converts the finding from a curve into a design tool; plus the memory-design consequence it implies (surprise-pinning), benchmarked against the anchoring prompt that industry already ships.
- **Explicit non-contributions**: no new memory system; no new agent; no claim to have *discovered* that memory drifts (Zhang et al. stated the intuition informally — we cite them in the first paragraph and position as explanation + controlled test); no human-subject comparison this cycle.

---

## Proposed Method

### Complexity Budget
- **Frozen / reused**: all models used off the shelf (hosted `qwen3-235b-a22b-2507` as the main strong compactor per PI directive; `local:qwen3-8b` for logprob priors and the small-model contrast; a second strong family for replication; a different-family judge). Stimuli already built and self-tested (`docs/idea/idea1_pilot/stimuli/`). Compaction prompts taken verbatim or minimally adapted from real systems (Aider `summarize`, Codex consolidation rules) under Apache-2.0.
- **New**: (1) the graded-surprise minimal-pair item set with per-level regexes and an independent prior measurement; (2) the three-state coder; (3) the three-state Markov fit; (4) surprise-pinning as a one-line memory-design change.
- **Deliberately excluded**: training a rewriter; a new retrieval stack; multi-agent shared memory (fallback only); cross-lingual evidentials (next paper); human transmission chains (no humans available).

### System Overview

```
 stimuli: minimal-pair families Fi, levels L1..L5     prior measurement (independent, same context)
 (all true, same source, stated once, matched)     ->  (a) local logprob over level values
          |                                            (b) T=1 generative elicitation, 30 samples
          v                                            (c) default-behaviour rate (preferences)
  seeding session  --C-->  M_0                              |
                                                            v
  distractor session 1 --C--> M_1                    surprise(item) = -log p(level)
  ...                                                       |
  distractor session k --C--> M_k   ------------------------+
          |
          +--> three-state coding of M_k per item:  RETAINED / CHANGED{specific,vague} / DROPPED
          +--> QA probe (guessability-corrected)
          +--> behaviour probe (preferences; conditions A=raw instructions / B=M_k / C=nothing)

  operators C:  rolling-rewrite (main) | append-only+retrieval (control) | rewrite-from-source (control)
                | anchored rewrite (Codex rules) | Aider-style decay | surprise-pinned (ours)
```

### Core Mechanism (the instrument)

- **Input / output**: an item is a (family, level) pair, e.g. "Veltrix's internal billing API times out after {30 seconds | 2 minutes | 5 seconds | 20 minutes | 6 hours}". Output per (item, operator, k) is a three-state label plus, when CHANGED, the level it moved to.
- **Why minimal pairs are load-bearing**: surprise is confounded with length, specificity, salience and topic in any naturalistic corpus. Within a family, only the value changes; the template, question, position-in-session, exposure count and source are identical. The level ordering is a *design-time* balance device only — analysis uses the **measured** prior as a continuous variable, so a mis-ordered family costs balance, not validity.
- **Fictional entities** (Veltrix / Northvale) sever pretrained memory of specific entities, isolating general commonsense priors (after Sivaprasad et al., ACL 2025).
- **Independent prior measurement, in the same frame**: priors are conditioned on the instruction prompt (Ren et al. 2024), so (a)/(b)/(c) reuse the compaction chain's system role, memory-notes format and entity introduction. We report Spearman ρ between methods and use (a) as primary where available, (b) elsewhere.
- **Why this is the novelty**: it converts an anecdote ("summaries drift to defaults") into a dose–response curve with a measured dose.

### Supporting Component (the three-state model)
- Estimate the 3×3 transition matrix **T** from k=0→1 only, separately per surprise tercile and operator. Predict the state distribution at k=10, 15, 20 as **T^k**, and report total-variation distance to the observed distribution. A good fit means a practitioner can characterize an operator with one cheap step instead of a 20-step run; a bad fit is itself informative (non-Markov / absorbing-state structure) and will be reported as such.
- This does not create sprawl: it is the same labels as the main DV, read a second way.

### Modern Primitive Usage
- The LLM is the **object of study**, not a component we bolt on: it plays the role of the learner in an iterated-learning chain. Decoding temperature is the handle that distinguishes learner types (sampler vs MAP), which is only available because the learner is an LLM.
- The local model's **logprobs** give a per-token prior that the hosted compactors cannot provide; hosted priors use sampling (b) and default-behaviour rates (c). We report agreement between the two routes rather than assuming transfer.

### Integration into the pipeline
- Operators are drop-in replacements for C. Everything else — stimuli, distractors, probes, coder — is held fixed, so the operator contrast is clean.
- `append-only + retrieval` is the critical control: it has the same probe, the same stimuli and the same reading model, but no LLM rewrite. If the surprise gradient appears there too, the effect is in the probe or the retriever, not in compaction.
- `rewrite-from-source` separates "reading your own last version" (iterated learning) from "abstracting from raw material" (one-shot summarization).

### Training Plan
None. No gradients anywhere. All compute is inference; all calls are content-hash cached on disk.

### Failure Modes and Diagnostics

| Failure mode | Detection | Fallback |
|---|---|---|
| Strong model loses nothing (cf. *Faithful, Not Corrective* 2607.09678) | truncation rate and compression ratio logged per step; retention at k=20 near ceiling | tighten budget B (300→200 words), lengthen chain (20→30), report the compression ratio at which the effect appears — "when does it bite" is part of the result |
| Typical values are guessed back at probe time | no-memory baseline g per item; report (acc−g)/(1−g) | memory-text three-state label is the primary DV and is immune |
| Prompt-mandated generalization is mistaken for prior drift | main condition uses a deliberately neutral prompt that never says "generalize" or "use synonyms" | report Aider-style (decay-mandating) and Codex-anchored prompts separately |
| T=1 is not a sampling learner (Cui & Yu 2506.10268) | starting-value test: the same family enters 5 chains at 5 different levels | the premise is *measured*, not assumed; either outcome is reportable |
| Judge unreliable, and no humans available | two independent LLM judges from different families; report agreement (Cohen's κ) between them | rule-based regex decides the majority of cases; a stratified 150-item sample is saved to `human_validation/` for later human adjudication, and the limitation is stated in the paper |
| Null core effect | pre-registered go/no-go (G1–G3) | PI directive 2: keep the iterated-learning thesis, first rule out weak-model / no-bottleneck explanations, then move to multi-agent shared memory with a wisdom-of-crowds collapse framing |

### Novelty and Elegance Argument
Closest work, and the exact difference:
- **Zhang et al. 2605.12978** — measures that rewriting hurts; removes the prior by construction. We make the prior the independent variable and supply the theory.
- **Zahn & Chana 2603.17781** — asserts drift-to-defaults; no per-item data, no record of the replacement value. We measure the replacement value and its prior.
- **Compaction Cliff 2608.22752** — measures multi-round constraint decay; no prior dimension.
- **Zhu & Griffiths (CogSci 2025)** — elicits LLM priors by iterated ICL. We borrow their elicitation method and apply it to memory, which they do not study.
- **ClashEval / knowledge conflict** — graded plausibility, single step, real entities. We study accumulation over a chain in a fictional world.

The contribution is one mechanism claim plus one instrument, not a module pile-up.

---

## Claim-Driven Validation Sketch

### Claim 1 (dominant): Retention falls with measured surprise, and only under rewriting operators.
- **Minimal experiment**: 10 fact chains × {rolling-rewrite, append-only} × {T=0, T=1} × {B=300, B=600} × 3 seeds × 20 steps, strong hosted compactor. Three-state coding at k ∈ {0,1,2,3,5,7,10,15,20}.
- **Baselines / ablations**: append-only+retrieval (no-rewrite control); rewrite-from-source (no-self-reading control).
- **Metric**: RETAINED rate by surprise tercile; slope of retention on continuous surprise (mixed-effects logistic with family random effects); bootstrap CI over families.
- **Expected evidence**: ≥10 pp gap between low- and high-surprise terciles at k=10 under rolling-rewrite, <5 pp under append-only.

### Claim 2 (supporting): Rewrites move toward the prior, and one step predicts twenty.
- **Minimal experiment**: same runs, no extra calls. (i) For every CHANGED-specific event, test whether the new value's prior exceeds the old value's prior. (ii) Fit T on k=0→1; predict k=10/15/20.
- **Metric**: (i) fraction prior-ward, binomial test against 50%; (ii) total-variation distance between T^k and observed.
- **Expected evidence**: ≥60% prior-ward; TVD ≤ 0.10 at k=10 for rewriting operators.

### Claim 3 (theme-track payload + design consequence): Preferences homogenize across users, and surprise-pinning recovers retention cheaply.
- **Minimal experiment**: 8 simulated users × 20 preferences, three-condition probe (A raw / B memory at k / C nothing) to split **storage loss** from **execution loss**; pairwise distance between user preference profiles at k=0 vs k=20; then the mitigation ladder (neutral / Codex-anchored / surprise-pinned) on the same chains.
- **Metric**: storage loss vs deviation-from-default; mean pairwise profile distance and distance-to-model-default over k; retention recovered per extra token of memory budget.
- **Expected evidence**: storage loss rises with deviation from default; profiles converge toward the model default; pinning recovers a substantial share of the high-surprise loss at modest cost.

---

## Experiment Handoff Inputs
- **Must-prove claims**: C1 surprise gradient under rewriting; C1b absent under append-only; C2 prior-ward rewrite direction; C3 cross-user homogenization.
- **Must-run ablations**: operator family (6); temperature (0 / 0.5 / 1.0 / 1.3); budget B (200 / 300 / 600); backbone (local 8B / strong 235B / second strong family); starting-level test for learner-type discrimination.
- **Critical datasets / metrics**: own minimal-pair stimuli (primary); MemoryAgentBench FactConsolidation (MIT) and CounterFact (MIT) for external validity; three-state label as primary DV; guessability-corrected QA and rule-checked behaviour as secondary.
- **Highest-risk assumptions**: (i) a strong compactor under a 300-word budget actually loses content; (ii) the measured prior from sampling agrees well enough with logprob priors to serve as the dose; (iii) regex + 2-judge coding is accurate enough without human adjudication.

## Compute & Timeline Estimate
- **GPU**: 1× A10G for Qwen3-8B (priors, small-model contrast, append-only retrieval embeddings). No training.
- **API**: hard cap $140. Plan: pilot ≤ $25, full ≤ $90, ≥ $15 reserve. Compaction with the 235B model costs ≈$0.0006/call at B=300, so a 2,400-call pilot chain sweep is ≈$1.5; probes and judging dominate and are routed to the cheapest adequate model.
- **Timeline (this run)**: pilot → go/no-go → full experiments → review loop → paper, unattended, single session.
