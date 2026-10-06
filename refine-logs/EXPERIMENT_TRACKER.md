# Experiment Tracker

Status: TODO / RUNNING / DONE / BLOCKED / CUT. Cost = hosted USD actually spent (local = $0).

| Run ID | MS | Purpose | System / variant | Split | Metrics | Priority | Status | Cost | Notes |
|---|---|---|---|---|---|---|---|---|---|
| R001 | M0 | stimuli rebuild: name parameterization + 5x5 Latin square | - | all | leak count | MUST | TODO | | `{{COMPANY}}`/`{{TOWN}}` |
| R002 | M0 | 30 distractor sessions + automated scrub | gen: qwen3-235b T=0.7 | - | 0 leaks vs all level regexes | MUST | TODO | | frozen after generation |
| R003 | M0 | three-state coder unit tests | regex + normalizer | synthetic | all pass | MUST | TODO | | paraphrase / unit / negation cases |
| R004 | M0 | compactor token-length audit of all level values | tokenizer | all | token counts in manifest | MUST | TODO | | nuisance covariate source |
| R010 | M1 | P1 prior: pairwise Bradley-Terry, both orders, replicated | qwen3-235b T=0 | all families | BT log-odds, split-half rho | MUST | TODO | | primary dose |
| R011 | M1 | P2 prior: generative elicitation | qwen3-235b T=1 x30 | all families | empirical p(level) | MUST | TODO | | second compactor-side estimate |
| R012 | M1 | P3 prior: token logprobs | local:qwen3-8b | all families | sum/mean logprob | MUST | TODO | $0 | robustness + small-model contrast |
| R013 | M1 | P4 default-behaviour rate | qwen3-235b | prefs | compliance rate | MUST | TODO | | disjoint prompts from B9 eval |
| R014 | M1 | prior-method agreement | - | - | Spearman rho P1/P2/P3 | MUST | TODO | $0 | Table A1 |
| R020 | M2 | dev sweep: budget x temperature | O1, qwen3-235b, B in {150,300,600} x T in {0,1.0} | dev F01-F12 | retention@10, realized length, truncation | MUST | TODO | | selects operating point |
| R021 | M2 | O7 ceiling on dev (oracle retrieval) | O7 | dev | retention@10 | MUST | TODO | | adequacy condition reference |
| R022 | M2 | O3 slot-count calibration (A3) | O3 | dev | realized length vs W1, retention@10 | MUST | TODO | $0 | tolerance + non-degeneracy re-check |
| R023 | M2 | dev E-SHIFT variance components (A1) | O1 | dev frames | s_fam, s_seed | MUST | TODO | | feeds power sim |
| R024 | M2 | power simulation + table | - | - | power grid, SESOI | MUST | TODO | $0 | A1 step 2-5 |
| R025 | M2 | freeze FROZEN_PROTOCOL.md + commit hash | - | - | - | MUST | TODO | $0 | **gate to confirmatory** |
| R030 | M3 | E-SHIFT frame authoring + leak check | - | confirm | 0 leaks | MUST | TODO | $0 | value-free role cues |
| R031 | M3 | E-SHIFT frame parity screening | 2 blind judges | confirm | importance/authority/relevance parity | MUST | TODO | | drop/rewrite failures, report count |
| R032 | M3 | E-SHIFT eligibility (Half A) + achieved shift (Half B) | qwen3-235b | confirm | log-odds shift per family | MUST | TODO | | split-half, winner's-curse guard |
| R033 | M3 | **E-SHIFT confirmatory chains** | O1, both arms | confirm | d_f at k=10 | MUST | TODO | | **C1, gate 1** |
| R034 | M3 | E-SHIFT frame control | O3, both arms | confirm | d_f at k=10, +/-5pp equivalence | MUST | TODO | | residual-interference flag |
| R040 | M4 | **main chains, operator lattice** | O1,O2,O3,O4,O5,O6 x 7 chains x 3+ seeds x 20 steps | confirm F13-F40 | 3-state labels at 9 checkpoints | MUST | TODO | | **C2, C3, C4** |
| R041 | M4 | O7 ceiling + embedding-retrieval baseline | O7 | confirm | retention@10 | MUST | TODO | | labelled separately |
| R042 | M4 | three-state coding of all snapshots | regex-first, 2 judges on ambiguous | confirm | labels + judge agreement | MUST | TODO | | feeds everything |
| R043 | M4 | value-level kernel, held-out prediction | - | confirm | paired dTVD vs 2 baselines | MUST | TODO | $0 | **C6** |
| R044 | M4 | replacement direction | + BT augmentation for OTHER values | confirm | delta, permutation p | MUST | TODO | | **C5** |
| R045 | M4 | pinning ladder | O6 vs O5 vs O1 + token-matched random / low-surprise | confirm | retention recovered per token | MUST | TODO | | **C7** |
| R050 | M5 | temperature diagnostic | O1,O3 x T in {0,0.5,1.3} | confirm subset | slope by T | NICE | TODO | | descriptive only |
| R051 | M5 | budget diagnostic | O1,O3 x B in {150,600} | confirm subset | slope by B | NICE | TODO | | |
| R052 | M5 | second strong family | llama3.3-70b, O1+O3 | confirm subset | slope | NICE | TODO | | generalization |
| R053 | M5 | small-model contrast | local:qwen3-8b, O1+O3 | confirm subset | slope | NICE | TODO | $0 | weak-vs-strong |
| R054 | M5 | prior rank stability at k=1, k=10 | masked contexts | diagnostic subset | rank correlation | NICE | TODO | | limitation evidence |
| R060 | M5 | preference chains | O1, 8 users x 3 seeds x 20 | confirm P07-P20 | coded memory + A/B/C behaviour | NICE | TODO | | **A1** |
| R061 | M5 | cross-user homogenization | - | - | distance-to-centroid over k | NICE | TODO | $0 | memory first, behaviour second |
| R070 | M5 | judge agreement report | 2 judges | all coded | kappa, confusion, class-wise | MUST | TODO | $0 | Table A5 |
| R071 | M5 | archive stratified 150-item human-validation sample | - | all coded | - | MUST | TODO | $0 | `human_validation/`, unused in inference |
