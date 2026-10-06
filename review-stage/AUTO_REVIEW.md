# Auto Review Loop

Reviewer: GPT-5.6-Sol via Codex MCP, `model_reasoning_effort: xhigh`.
Note: the Codex code-mode host is version-mismatched with the installed CLI, so the reviewer has no
file access; the full paper and a verbatim dump of every result number were inlined in each prompt.

## Round 1 (2026-10-06) — Score 4/10, verdict: not ready

### Key criticisms
1. O3 falsely described as a capacity-matched control (frozen protocol says the capacity claim was dropped; 613 vs 129 words).
2. The null headline is broader than the evidence; equivalence is obtained only after replacing the 8 pp SESOI with the design's MDE.
3. E-SHIFT does not isolate prior-fit from other effects of context.
4. O4-O1 is real but "iteration itself drives loss" is not identified; O5 shows iteration is not sufficient; the claim conflicts with §4.1.
5. Protocol failures (7.4 retries/trajectory) and unresolved outcomes need sensitivity analyses; E-SHIFT has 3.2% unresolved and kappa 0.697, not the 1.0% impression given.
6. The cross-model "replication" is not a replication of the causal null.
7. The pinning result is overclaimed (CI includes zero); no direct O6 vs O6-random contrast.
8. The preference finding is descriptive and confounded; no clustered inference.
9. Confirmatory status and multiplicity insufficiently clear.

### Actions taken (all nine addressed)
- **New run — capacity-matched prior-blind control** (`O3W`, random packing to the 150-word budget):
  retains 0.5%, i.e. at the rewriting arm's own capacity random selection keeps nothing. Both controls
  now reported, each labelled by what it is matched on.
- **New run — blind frame-parity check** (`results/frame_parity.json`). **It fails**: the
  expected-value frame is rated 0.69 lower on importance (CI [-1.36,-0.03]) and 0.50 lower on
  authority (CI [-0.84,-0.16]). This is reported as its own subsection and as a limitation; the
  estimand is restated as an expectation-shifting *context* manipulation and the headline is reduced
  to the one-sided exclusion.
- **Sensitivity suite** (`results/sensitivity.json`): C1 under each judge separately (-4.5 / -3.7 pp)
  and with unresolved cases bounded in both directions (-5.9 / -2.1 pp); unresolved rate by arm;
  protocol compliance by operator; direct paired contrasts; dose-response expressed in pp over the
  IQR with its CI; preference contrast clustered over preference families and baseline-adjusted.
- **Reframing**: title drops the "Iteration, Not Prior-Fit" dichotomy; O4 recast as
  reconstruction-versus-recursion with every other difference named; operator contrasts labelled
  exploratory and not multiplicity-corrected; cross-model runs relabelled portability diagnostics;
  pinning restated as "no detected benefit" with the direct O6 vs O6-random contrast
  (-7.0 pp, CI [-25.4,+11.0]); the §4.1 / §4.4 tension resolved explicitly.
- **Newly disclosed**: ANCHOR reaches its result through 43.4 budget regenerations and 12.9 trims per
  trajectory against 8.7 and 1.1 for the neutral prompt.
- Fixed: a stale discussion paragraph that asserted profiles drift toward an average user, which
  contradicts our own result; two macro-generated sentences with wrong referents; and a CI quoted
  from a second bootstrap run.

## Round 2 (2026-10-06) — Score 6/10, verdict: almost

Reviewer: "The new analyses are unusually candid and resolve most of the original
statistical/reporting problems. The remaining obstacle is conceptual: the paper still presents
prior-drift as rejected even though the new parity check shows that the causal manipulation cannot
identify the effect of prior-fit."

### Seven remaining items, all addressed
1. **Title/headline outran the admitted identification failure** -> title is now
   "Testing Prior-Drift in LLM Memory Compaction: An Expectation-Shifting Manipulation Does Not
   Improve Retention"; abstract, intro, results and conclusion all say the study bounds a compound
   context manipulation and does not identify prior-fit in isolation, and call it an informative
   failed test rather than a refutation.
2. **Do not attribute the -4 pp estimate to perceived importance** -> changed to "compatible with
   confounding by perceived importance/authority"; no mediation adjustment is attempted.
3. **ANCHOR hard to interpret** -> new analysis. More trimming is associated with *higher* retention
   (+8.6 pp per trim under the neutral prompt; 92.1% vs 96.7% for ANCHOR trajectories below/above the
   median trim count), and surviving targets sit near the top of the notes (relative position 0.08),
   so trimming does not reach them. The earlier claim that the differences "work against" ANCHOR was
   wrong and is retracted in the text. ANCHOR is now an exploratory pipeline-level result at "the same
   storage cap but several times the generation cost".
4. **Neither random control is a clean counterfactual** -> O3 is now "retention-calibrated on the
   development set", never retention-matched; the text states plainly that capacity matching destroys
   overlap while approximate outcome matching costs far more storage, that neither is decisive, and
   that the preregistered interaction remains inconclusive.
5. **Conservative bound is ~6 pp, not 4.1** -> a new macro reads the upper CI limit of the
   most-favourable unresolved-case variant (+5.9). Abstract, intro, results and conclusion now quote
   "+4.3 to +5.9 pp". (This also caught a real error: a mean was being quoted where an upper bound
   belongs.)
6. **"Indistinguishable from SRC"** -> "no difference detected ... a nonsignificant contrast, not an
   equivalence result".
7. **Preference result associational** -> added a within-family contrast over the 16 families that
   contain both a default-matching and a non-default level: +19.7 pp, 95% CI [+9.5, +29.8], free of
   between-family composition. Labelled a robust descriptive association, not attached causally to the
   prior mechanism.

The paper body was also brought back inside the ACL 8-page limit (Conclusion and Limitations both
begin on page 8; references and appendices follow).
