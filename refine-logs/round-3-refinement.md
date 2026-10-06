# Round 3 Refinement — preregistration amendment (A1–A3)

## Problem Anchor
*(Unchanged, verbatim from round 0.)* Bottom line: repeated LLM rewriting of agent memory erases precisely
the non-default content memory exists for.

## Anchor Check
Preserved; the reviewer confirmed this at rounds 2 and 3. These amendments are decision-rule freezes, not
design changes. No reviewer suggestion was rejected.

## Simplicity Check
Nothing added. A1 may *increase the number of families used* in E-SHIFT, which is a power change, not a
complexity change. The operator set, prior measurement, coding scheme and claim hierarchy are untouched.

---

## Amendment A1 — E-SHIFT sizing, frozen procedure

**Why**: 12 families x 3 seeds yields 12 independent stimulus clusters, which is likely underpowered for an
8 pp SESOI.

**Frozen procedure** (executed on dev data before any confirmatory chain runs):
1. Run E-SHIFT on the **dev** families (F01-F12) at the primary operating point to estimate two variance
   components: between-family SD of the paired arm difference, `s_fam`, and within-family (seed) SD, `s_seed`.
2. Simulate the frozen primary analysis (paired family-level contrast + paired family bootstrap, A2) under a
   true effect of exactly **8 pp**, for every (n_families, n_seeds) in
   {12, 16, 20, 24, 28} x {3, 4, 5, 6}, 2000 simulations each.
   **`n_families` means ELIGIBLE families** — families surviving the Half-A eligibility screen — because the
   primary population is eligible-only.
3. Choose the **smallest** (n_families, n_seeds) reaching **power >= 0.80**, preferring more families over
   more seeds at equal power. Publish the full power table in the appendix.
4. **Eligibility attrition is budgeted for**: let `r` be the eligible fraction observed on dev. The pool of
   families actually prepared and run is `ceil(n_families / r)`, capped at the 28 confirmatory families. The
   observed `r` and the realized eligible count are reported.
5. If no cell in the grid reaches 0.80 for 8 pp **at the realized eligible count**, use the maximum
   affordable cell and **freeze X, the minimum detectable effect at 0.80 under that cell, as the new SESOI**.
   A2's equivalence bounds then become **+/- X, not +/- 8 pp**, and the paper states X explicitly wherever it
   states the SESOI.
6. The chosen cell and the operative SESOI are written into `FROZEN_PROTOCOL.md` with a commit hash
   **before** any confirmatory E-SHIFT chain is run. The same (n_families, n_seeds) applies to both arms and
   to the O3 frame control.

**Budget impact**: the maximum cell (28 families x 2 arms x 6 seeds x 20 steps x 2 operators) is 13,440
compaction calls ~= $8.3 at the compactor's measured rate. Affordable; no design is sacrificed for power.

---

## Amendment A2 — complete C1 decision rule, frozen

**Primary population**: **eligible-only** — families whose arm shift reaches >= 0.5 log-odds on prior-elicitation
**Half A**. Eligibility therefore uses data independent of the achieved-shift estimate (Half B) and of the
retention outcome. **Intention-to-treat** over all prespecified E-SHIFT families is reported as sensitivity;
if ITT and eligible-only disagree in direction or decision, the paper reports both and declares C1
inconclusive.

**Estimator**: for family *f*, `d_f = mean_seeds[ retained(F+, k=10) ] - mean_seeds[ retained(F-, k=10) ]`
in percentage points, under O1. The primary statistic is the unweighted mean of `d_f` over eligible families.

**Clustering**: in E-SHIFT, trajectories are **nested within families** (each family has its own arm x seed
chains), so the primary inference uses a **family bootstrap with paired seeds resampled within family**:
families are resampled with replacement, and within each resampled family its arm-paired seed blocks are
resampled, keeping F+ / F- and O1 / O3 together in every block. 10,000 replicates. The **two-way crossed**
family x trajectory bootstrap is reserved for the multi-item main-chain experiment (C2, C3), where families
and chains genuinely cross.

**Decision rule** (four mutually exclusive outcomes, evaluated in this precedence order):
1. **Positive support for C1**: the 95% bootstrap CI for mean `d_f` excludes 0, lies in the predicted
   direction (`d > 0`), **and** the equivalence interval is *not* wholly inside +/- SESOI.
2. **Positive but below the SESOI**: the 95% CI excludes 0 in the predicted direction **and** the 90%
   equivalence interval lies wholly inside +/- SESOI. Reported as a real but practically small effect; it does
   **not** open the gate to C2/C3 as a confirmatory chain.
3. **Boundary evidence (informative null)**: the 95% CI includes 0 **and** the 90% equivalence interval
   (TOST at alpha = .05, both bounds) lies entirely inside **+/- SESOI**.
4. **Inconclusive**: none of the above. Reported as such, with the minimum detectable effect.

(SESOI = 8 pp unless amended to X by A1 step 5.)

**E-SHIFT O3 frame control**: equivalence margin **+/- 5 pp**. If the O3 arm difference is not equivalent to
zero within that margin, the paper flags possible residual frame interference and down-weights C1 accordingly;
this flag is reported whatever the O1 result is.

**Scoping**: a null is reported as "under the tested model, prompt, item domain and compression regime,
effects at least as large as 8 pp are excluded", never as a general claim about compactors.

---

## Amendment A3 — prospective O3 capacity matching, frozen

**Why**: a fixed slot count removes sentence-length selection bias but does not by itself establish that O3
felt the same capacity pressure as the 300-word O1 condition.

**Frozen procedure** (on dev data, before confirmatory runs):
1. Run O1 at B=300 on dev families; record `W1` = mean realized memory length in words at k=10.
2. From the dev source-sentence length distribution, compute expected realized O3 length as a function of
   slot count `s`, and set `s* = argmin_s |E[len(s)] - W1|`.
3. **Tolerance**: `|mean realized O3 length - W1| <= 0.10 * W1`.
   - If met → O3 is described as an **identical-capacity, prior-blind control**.
   - If not met → O3 is relabelled a **prior-blind deletion control** and the capacity claim is dropped from
     the text. Either way the number is reported.
4. **Non-degeneracy**: require O3 retention at k=10 in `[0.10, 0.90]`. If O3 retention is at ceiling, the
   slot count is too generous for the control to be informative, and `s*` is reduced to the largest value
   satisfying the non-degeneracy bound — chosen on **dev data only**, then frozen.
5. `s*`, `W1`, the achieved tolerance and the non-degeneracy check are written into `FROZEN_PROTOCOL.md`
   with a commit hash before the first confirmatory run.

---

## Status after A1-A3
All three of the reviewer's remaining blockers are discharged at the specification level. A1 and A3 require
**dev-data measurements**, which the pilot produces by design; their numeric outputs are filled into
`FROZEN_PROTOCOL.md` at the end of the pilot and before any confirmatory family is touched. A2 is fully
frozen now and requires no data.
