# FROZEN PROTOCOL

Frozen 2026-10-06T09:51:06 at commit `268e406bdd1481fd053096c695e31c221378724b`.

No confirmatory family was run before this file existed. Every choice below was made on
dev families (F01-F12, P01-P06) only.

- **Compactor**: `qwen.qwen3-235b-a22b-2507-v1:0`, T=1.0, budget B=150 words, K=20 steps
- **Primary endpoint**: k=10; checkpoints [0, 1, 2, 3, 5, 7, 10, 15, 20]
- **Seeds**: 8
- **O3 slot count** (amendment A3): 60, realized stored length 613 words vs O1's 129 (within 10% tolerance: False)
- **O3 is described as**: prior-blind deletion control (capacity claim dropped; see A3)
- **Empirical adequacy** (replaces 'compression is biting'): O1 retention@10 0.667, O7 ceiling 1.000, gap 33.3 pp -> adequate: True
- **E-SHIFT**: 26 eligible families (r=0.74), threshold 0.5 log-odds on elicitation Half A, achieved shift estimated on the independent Half B; operative SESOI 15.9 pp

## Analysis, frozen

- **primary_estimator**: family-fixed-effects linear probability model of RETAINED at k=10 on within-family-centred Bradley-Terry surprise x operator, with token-length and digit-format nuisance covariates
- **main_chain_inference**: two-way crossed cluster bootstrap over families and chain x seed blocks, blocks carrying all paired operators
- **eshift_inference**: family bootstrap with arm-paired seed blocks resampled within family (trajectories are nested within families there)
- **gatekeeping_order**: ['C1 E-SHIFT arm effect', 'C2 natural-prior dose response', 'C3 O1xO3 interaction + O3 equivalence']
- **C1_decision_rule**: ['POSITIVE_SUPPORT', 'POSITIVE_BELOW_SESOI', 'BOUNDARY_EVIDENCE', 'INCONCLUSIVE']
- **O3_equivalence_margin_pp**: 5.0
- **C1_primary_population**: eligible-only (Half-A screen); ITT reported as sensitivity; C1 declared inconclusive if they disagree in direction
