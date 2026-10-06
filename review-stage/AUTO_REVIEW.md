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
