# COST_LOG

Hard cap $140 (PI absolute limit $150). Budget plan: pilot <= $25, full experiments <= $90, reserve >= $15.

| Date | Purpose | Model | Calls | Est. cost | Actual cum. spend | Note |
|---|---|---|---|---|---|---|
| 2026-10-06 | infra smoke test (pre-existing) | several | 6 | - | $0.0001 | scaffold check |
| 2026-10-06 | B0 distractor generation + scrub (30 sessions x 4 drafts) | qwen3-235b | 120 | $0.022 | $0.031 | 24/30 passed the attribute scrub; frozen |
| 2026-10-06 | B1 priors P1 pairwise Bradley-Terry (50 families, 4 worlds x 2 orders x 2 samples) | qwen3-235b | 6112 | $0.191 | - | primary dose, measured on the compactor itself |
| 2026-10-06 | B1 priors P2 generative elicitation (T=1 x 30) | qwen3-235b | 1500 | $0.058 | - | second compactor-side estimate |
| 2026-10-06 | B1 priors P3 local token logprobs | local:qwen3-8b | 192 | $0 | - | robustness + O6 write-time pinning signal |
| 2026-10-06 | M2 dev pilot: O1 budget x temperature sweep (B in {150,300,600} x T in {0,1}), 5 dev chains x 2 seeds x 21 steps | qwen3-235b | 1260 | $0.74 | - | operating-point selection; O7 and the O3 slot sweep are free |
| 2026-10-06 | B3 E-SHIFT frame authoring + Half-A selection + Half-B estimation (14 drafts/family) | qwen3-235b | ~22000 | $0.75 | - | selection on Half A, estimate on Half B: winner's curse cannot reach the reported shift |
| 2026-10-06 | M2 dev pilot protocol v2 (soft word target below the hard cap; v1 had 8.2 hard trims/traj, v2 has 1.2) | qwen3-235b | ~2500 | $0.99 actual | $2.6 | v1 data kept as chains_dev_protocolv1.jsonl |
| 2026-10-06 | M2 dev E-SHIFT (8 dev families x 2 arms x 3 seeds) for A1 variance components | qwen3-235b | 1008 | $0.59 | $4.0 | feeds the power table |
| 2026-10-06 | M3 confirmatory E-SHIFT (18 families x 2 arms x 8 seeds, O1 paid + O3 free) | qwen3-235b | 6048 | $1.80 | - | the causal test |
| 2026-10-06 | M4 confirmatory main chains (7 paid operators x 11 chains x 3 seeds x 21 steps) | qwen3-235b | 4851 | $1.50 | - | C2/C3/C4/C7 |
| 2026-10-06 | B9 preferences: 8 users x 3 seeds x 21 steps + A/B/C behaviour probes | qwen3-235b | ~2200 | $0.60 | - | exploratory application (Fig 4) |
| 2026-10-06 | B8 diagnostics: llama3.3-70b second family, local qwen3-8b, T=0 (T=1.3 refused by Bedrock, cap 1.0) | llama3.3-70b / local | 1386+924 | $1.96 | - | the null replicates |
| 2026-10-06 | coding of all confirmatory + diagnostic snapshots (2 blind judges) | gpt-oss-120b + gemma-3-27b | ~40000 | ~$5 | - | kappa 0.880 (main), 0.697 (E-SHIFT targets) |

**Total: see `curl 127.0.0.1:8787/v1/budget`. Well inside the $140 cap; the pilot+full envelope
($25 + $90) was not approached because the operating point that makes compression bite is a tight
budget, which makes every call cheap.**
