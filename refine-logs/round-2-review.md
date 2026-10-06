# Round 2 Review (GPT-5.6-Sol, xhigh) — thread 01a11018-33e7-7f21-a5bb-2958ff49b77f

| Dimension | R1 | R2 |
|---|---|---|
| Problem Fidelity | 9 | **10** |
| Method Specificity | 5 | **8** |
| Contribution Quality | 6 | **8** |
| Frontier Leverage | 8 | **9** |
| Feasibility | 5 | **9** |
| Validation Focus | 5 | **8** |
| Venue Readiness | 6 | **8** |
| **OVERALL** | 6.4 | **8.6** |

**Verdict: REVISE** (close to READY). Anchor **preserved**, no paper-level drift. Drift objection on the
null-result contingency **withdrawn** — the reconciliation is accepted as falsifiable.

## Blocking (must fix before confirmatory chains)
1. **E-SHIFT frame contamination**: frames must never contain the target or any candidate value; prefer
   non-memory contextual metadata; run E-SHIFT through O3 as a free frame-control.
2. **E-SHIFT frame semantics**: length/syntax matching does not establish semantic matching. Have the two
   blind judge families rate target importance / authority / relevance per arm before freezing; exclude or
   rewrite frames with material arm differences; state the target is authoritative in both arms.
3. **Winner's curse** from >=0.5 log-odds eligibility screening: use one independent half of the prior
   elicitation for eligibility and the other for the achieved-shift estimate; add an all-prespecified-families
   intention-to-treat sensitivity analysis.
4. **Token length / tokenization** still vary across natural levels: audit exact compactor-token lengths,
   use equal-token forms where possible, and prespecify length/format as nuisance variables.
5. **O3 randomization**: sampling sentences until a word budget favours short sentences, and one reused seed
   collapses replication. Sample fixed item IDs / fixed-size slots; three independently prespecified seeds.
6. **Entity names** must be rotated across values and frame arms (Latin square currently covers only levels
   and positions).
7. **Measured-surprise balance** across chains: four items per nominal level need not balance BT surprise.
   Use constrained randomization on frozen prior estimates, or verify and report balance before running.
8. **Distractor interference**: identical distractors across paired worlds, scrub candidate values and units,
   freeze or symmetrically rotate order.
9. **O7** measures retrieval quality unless oracle retrieval is used — otherwise call it a retrieval baseline,
   not an access ceiling.
10. **C7** either demoted to exploratory application, or its default-elicitation and behavioural-evaluation
    prompts/seeds must be disjoint and stored-memory convergence shown before behaviour.

## Statistical corrections
- **Gatekeeping order** (resolves which claim is confirmatory): 1. E-SHIFT arm effect; 2. natural-prior dose
  response; 3. O1/O3 interaction + O3 equivalence.
- **Crossed, not nested, clustering**: families x trajectories are crossed. Use a two-way cluster bootstrap
  that independently reweights whole families and whole chain x seed x operator trajectories, preserving
  paired O1/O3 runs. Write it algorithmically in the preregistration.
- **Logistic FE is not convergence-free**: quasi-complete separation is plausible at k=10. Use a family-FE
  **linear probability model** with crossed-cluster inference as primary (the estimand is a percentage-point
  slope anyway), or bias-reduced logistic with average marginal effects. TOST margin in **percentage points**
  over a prespecified surprise contrast.
- **Kernel state alignment**: define states by measured prior **rank** (R1..R5) or prespecified BT bins, not
  design level names, otherwise L2->L3 has no consistent cross-family meaning. OTHER/VAGUE/ABSENT rows will
  be sparse at k=0->1: either seed calibration inputs in those states, use hierarchical smoothing with
  uncertainty propagated into p0 K^k, or constrain unsupported rows. Give K and both baselines the **same
  held-out p0** and test the **paired difference** in held-out TVD, not overlapping CIs.
- **Permutation null** must preserve origin rank, the candidate opportunity set and numeric-distance
  structure; stratify or condition on origin and distance, or fit a conditional destination model on
  destination BT score and value distance. OTHER destinations are not automatically on the BT scale: augment
  that family's BT fit with the novel value via new pairwise comparisons, or analyse OTHER separately.
- **"CI contains zero" is not a falsifier**: E-SHIFT needs a prespecified smallest effect of interest and an
  equivalence test, like O3.
- **"Compression is biting" cannot be shown by truncation/compression ratio alone**: prespecify an empirical
  adequacy condition (O1 retention materially below O7 and below ceiling, but above floor).
- Null conclusions must be **scoped to the tested regime**; rename "go/no-go" to **claim-selection criteria**.
- Eight simulated users are controlled test cases: generalize over **preference families**, not over users.
- Eight numbered claims communicate breadth, not parsimony.

## Remaining limitations to state (not blockers)
Post-rewrite position may mediate later loss (log item order/section each step; report whether the effect
exists already at the first transition). Natural graded levels still differ in magnitude/semantics (C2 is
ecological dose-response, not causal identification — E-SHIFT carries causality). Representational
compressibility cannot be fully separated from semantic prior. E-SHIFT identifies a **context-conditioned**
prior, not parametric knowledge. The operative prior may drift with k (re-elicit in masked k=1 / k=10
contexts on a diagnostic subset, report rank stability). Generalization beyond the main model is limited.
