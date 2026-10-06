# Review Summary

**Problem**: LLM-driven agent memory compaction is iterated learning, so memory drifts to the compactor's prior: surprising content is forgotten, plausible/unsurprising content is kept.
**Initial approach**: graded-surprise minimal-pair memory chains + independently measured prior + three-state coding.
**Date**: 2026-10-06. **Rounds**: 5 / 5. **Final score**: 9.5 / 10. **Final verdict**: READY.
**Reviewer**: GPT-5.6-Sol via Codex MCP, `model_reasoning_effort: xhigh`, thread `01a11018-33e7-7f21-a5bb-2958ff49b77f`.
**Note**: the Codex code-mode host is version-mismatched with the installed CLI, so the reviewer had no file
access; every round was conducted with the material inlined in the prompt.

## Problem Anchor
Repeated LLM rewriting of agent memory erases precisely the non-default content memory exists for.
Confirmed **preserved** by the reviewer at rounds 2, 3 and 5. No paper-level drift at any round.

## Round-by-round resolution log

| Round | Main reviewer concerns | What this round changed | Solved? | Remaining risk |
|---|---|---|---|---|
| 1 (6.4) | Minimal pairs give correlation not causation; dose measured on the wrong model; three-state stationarity claim formally unsound; append-only has no bottleneck so it cannot be the control; data-dependent operating-point search; overclaiming | Added E-SHIFT same-item prior manipulation; moved the prior to compactor-side Bradley-Terry; replaced the three-state model with a value-level copy/drop/replace kernel; added COPY-RAND and COPY-LLM; dev/confirmatory split; reframed headline to prior-shaped selective survival | yes | 23 confounds audited |
| 2 (8.6) | E-SHIFT frames could leak the answer or shift salience; winner's curse from eligibility screening; token length; O3 randomization; entity names; measured-surprise balance; distractor hygiene; O7 is retrieval not a ceiling; preference circularity; crossed-cluster inference; logistic separation; kernel state alignment | Frames became value-free role cues with judge screening; split-half eligibility + ITT; token audit + nuisance covariates + matched subset; slot-ID sampling with 3 seeds; name rotation; constrained randomization on frozen BT estimates; distractor scrub; oracle retrieval; preferences demoted to exploratory with disjoint prompts; linear probability model + two-way crossed bootstrap; rank-based kernel states with Dirichlet smoothing | yes | E-SHIFT power, C1 decision rule, O3 capacity |
| 3 (9.1) | E-SHIFT underpowered at 12 families; C1 decision rule not frozen; O3 capacity not matched prospectively | Amendments A1 (power procedure), A2 (complete decision rule), A3 (prospective capacity matching) | mostly | 3 clauses |
| 4 (8.9) | `n_families` ambiguous w.r.t. eligibility; positive-support and boundary-evidence overlap; E-SHIFT clustering is nested not crossed; A3 tolerance not re-checked after non-degeneracy reduction | Eligibility attrition budgeted with fallback SESOI X; four mutually exclusive outcomes in precedence order; family bootstrap with paired seeds within family for E-SHIFT (crossed bootstrap reserved for the main chains); automatic relabel of O3 if the reduced slot count breaks tolerance | yes | none blocking |
| 5 (9.5) | — | — | **READY** | — |

## Overall evolution
- **More concrete**: from "measure retention vs surprise" to a fully preregistered protocol with a frozen
  manifest, a named primary estimator, a named clustering scheme, prespecified SESOIs, and a four-outcome
  decision rule.
- **More focused**: the claim list went from a flat eight to 3 gatekept confirmatory + 4 secondary +
  1 exploratory application. External datasets and the Aider operator were deleted.
- **Complexity removed**: the Cartesian grid (~129,600 compaction calls as originally written) became one
  primary operating point plus one-factor diagnostics.
- **Overclaiming removed**: "memory converges to the prior" became "prior-shaped selective survival and
  replacement under iterated compression"; temperature was demoted from learner-type identification to
  descriptive robustness.
- **Drift avoided**: the only drift the reviewer found was in the PI-mandated null-result fallback. That was
  reconciled rather than deleted: the fallback remains a project contingency, but a clean null is written up
  and submitted as a scoped boundary result for *this* paper. The reviewer withdrew the objection.

## Final status
- **Anchor**: preserved.
- **Focus**: tight.
- **Modernity**: appropriately frontier-aware (LLM as the object of study; compactor-side prior elicitation;
  structured cross-family judging; no training, no new architecture).
- **Strongest parts**: E-SHIFT (same-item causal manipulation); the operator lattice where each arm removes
  exactly one mechanism; compactor-side Bradley-Terry dose.
- **Remaining weaknesses**: A1 and A3 require dev-data measurements that the pilot produces; representational
  compressibility cannot be fully separated from semantic prior; E-SHIFT identifies a context-conditioned
  prior rather than parametric knowledge; no human validation this cycle; generalization beyond the main
  compactor rests on one second-family diagnostic.
