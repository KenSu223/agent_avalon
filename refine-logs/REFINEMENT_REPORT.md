# Refinement Report

**Problem**: LLM-driven agent memory compaction is iterated learning, so memory drifts to the compactor's prior.
**Date**: 2026-10-06. **Rounds**: 5 / 5. **Final score**: 9.5 / 10. **Final verdict**: READY.

## Output files
- Review summary: `refine-logs/REVIEW_SUMMARY.md`
- Final proposal: `refine-logs/FINAL_PROPOSAL.md`
- Per-round: `round-0-initial-proposal.md`, `round-{1,2,3}-review.md`, `round-{1,2,3}-refinement.md`
- Scores: `refine-logs/score-history.md`

## Score evolution
See `score-history.md`. 6.4 -> 8.6 -> 9.1 -> 8.9 -> **9.5**.
(The round-4 dip is the reviewer re-scoring Method Specificity down after spotting three clause-level
inconsistencies in the amendments; fixing them produced the round-5 READY.)

## Final proposal in five bullets
1. LLM memory compaction is a selection-plus-replacement process whose kernel is shaped by the compactor's prior.
2. The decisive evidence is **E-SHIFT**: the same target sentence and the same value, with only a value-free
   contextual base-rate frame changed, so magnitude, lexis, token length and consequence are held exactly fixed.
3. An operator lattice (O1 ROLL / O2 COPY-LLM / O3 COPY-RAND / O4 SRC / O5 ANCHOR / O6 PIN / O7 FULL) in which
   each arm removes exactly one mechanism localizes the effect to rewriting rather than capacity pressure,
   coder artifacts, or retrieval.
4. A value-level copy/drop/replace kernel over measured-prior-rank states, fitted on one step, predicts
   held-out k-step distributions; because deletion is near-absorbing, the claim is about the
   **quasi-stationary distribution conditional on survival**, not about convergence to the prior.
5. The design consequence is **surprise-pinning**, benchmarked against the anchoring prompt industry already
   ships (Codex consolidation rules) and against token-matched random / low-surprise pinning controls.

## Method evolution highlights
1. **Most important focusing move**: replacing a flat eight-claim table with a gatekept
   C1 -> C2 -> C3 confirmatory chain plus clearly labelled secondary and exploratory results.
2. **Most important mechanism upgrade**: E-SHIFT, which converts the headline from a dose-response
   correlation into a causal manipulation and simultaneously discharges six audited confounds.
3. **Most important correctness fix**: abandoning "stationary distribution = prior" for a value-level kernel
   with an absorbing ABSENT state and a quasi-stationary reading. The original claim was formally wrong.

## Pushback / drift log
| Round | Reviewer said | Author response | Outcome |
|---|---|---|---|
| 1 | Delete the multi-agent null-result fallback; it changes the unit of study and "keep the thesis" is unfalsifiable | The fallback is a standing PI directive inside the Anchor's constraints and is not mine to delete, so it stays as a *project* contingency. But the substantive point is adopted in full: a clean null under adequate compression and strong controls is written up and submitted as a scoped boundary result for this paper, the claim-selection criteria are preregistered and reported either way, and the multi-agent direction would be a different paper, labelled as such | Reviewer withdrew the drift objection at round 2 |
| 1 | Make the prior the compactor's, not the local model's | Accepted in full; local logprobs demoted to robustness and the small-model contrast | Accepted |
| 2 | Demote preferences or complete their prior/outcome separation | Did both: demoted to exploratory application *and* separated prompts and seeds | Accepted |

## Remaining weaknesses (honest)
- A1 (power) and A3 (O3 capacity) are frozen **procedures** whose numeric outputs come from dev data; they are
  only fully discharged at the end of the pilot.
- Representational compressibility cannot be fully separated from semantic prior; both are named as channels.
- E-SHIFT identifies a context-conditioned prior, not parametric knowledge.
- No human validation this cycle (hard constraint); two cross-family LLM judges substitute, and a stratified
  150-item sample is archived for later human adjudication.
- Generalization beyond the main compactor rests on one second-family O1/O3 diagnostic.

## Next steps
READY -> proceed to `/experiment-plan`, building on `docs/idea/idea1_pilot/PILOT_PLAN.md` and this proposal.
