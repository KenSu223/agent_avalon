# Round 1 Review (GPT-5.6-Sol, xhigh)

- threadId: `01a11018-33e7-7f21-a5bb-2958ff49b77f`
- Note: Codex MCP code-mode host is version-mismatched with the installed CLI, so the reviewer has
  no file access. The proposal was inlined into the prompt instead.

## Scores

| Dimension | Score |
|---|---|
| Problem Fidelity | 9 |
| Method Specificity | 5 |
| Contribution Quality | 6 |
| Frontier Leverage | 8 |
| Feasibility | 5 |
| Validation Focus | 5 |
| Venue Readiness | 6 |
| **OVERALL** | **6.4** |

**Verdict: REVISE**

## CRITICAL items
1. Minimal pairs give correlation, not causation: changing "30 seconds" to "6 hours" changes magnitude,
   consequence, lexical form and compressibility too. Add a **same-item prior-shift manipulation**:
   hold the target sentence and value fixed, change only a contextual base-rate frame that makes the
   same value expected vs unexpected. This is the decisive causal test.
2. The dose must be measured **on the actual compactor**, not transferred from Qwen3-8B. Use
   randomized-order structured pairwise choice fitted with Bradley-Terry; split-half for reliability;
   local logprobs demoted to robustness.
3. The three-state stationarity claim is formally unsound: iterated learning does not generally imply
   stationary distribution = prior for an LLM summarization chain; CHANGED is not a Markov state; if
   DROPPED is absorbing the stationary distribution is all-DROPPED. Replace with a **value-level
   copy/drop/replace kernel** over {candidate values, OTHER, VAGUE, ABSENT}, predict p0·K^k, and
   analyse the quasi-stationary distribution conditional on survival.
4. Append-only has **no compression bottleneck**, so it cannot separate generative rewriting from
   generic fixed-capacity loss. Add a deterministic **fixed-budget extractive control**.
5. Tightening B or lengthening the chain after seeing a null is a data-dependent search for an effect.
   Split **development** and **confirmatory** families; freeze the operating point before confirmation.
6. Venue readiness: current language (stationarity governed by the prior, temperature identifying
   learner type, one-step 3x3 matrix predicting 20 steps) overclaims. Reframe as **prior-shaped
   selective survival and replacement under iterated compression**; temperature becomes descriptive.

## IMPORTANT items
- Frozen manifest with Latin-square assignment of levels, positions, entity names, chain composition.
- Operationalize RETAINED/CHANGED/DROPPED precedence, unit equivalence, judge blinding and disagreement policy.
- Staged, not Cartesian, design (the stated grid implies ~129,600 compaction calls); token-level ledger.
- Delete external datasets (MemoryAgentBench, CounterFact) and the Aider-style operator.
- Preferences become one compact application figure, not a third full claim. QA at 1-2 endpoints only.

## Statistical audit (summary)
- Family random intercept alone is misspecified: use family fixed effects or within-family-centred
  surprise, plus random intercepts for item and trajectory/document; k=10 as the preregistered
  primary endpoint; "only under rewriting" needs a surprise x operator interaction plus an
  equivalence test for the control slope.
- Hierarchical bootstrap over families AND complete trajectories.
- The 50% binomial null for prior-ward movement is wrong (unequal numbers of higher/lower-prior
  destinations, asymmetric distance, within-chain dependence, selection on CHANGED). Use
  delta = log p(v_new) - log p(v_old) with clustered bootstrap, plus a within-family destination
  permutation null.
- TVD needs CIs, held-out trajectories and comparison against simple baselines.
- Cohen's kappa insufficient under class imbalance: also report confusion matrix, class-wise and raw
  agreement, and conclusions under each judge separately.
- (acc-g)/(1-g) unstable as g -> 1; prefer acc-g with intervals.
- The 28 pairwise user distances are not independent: user-level permutation or distance-to-centroid.
- Run a simulation-based power calculation under the clustered structure before fixing chain count.

## Confound audit (23 items, condensed)
Value semantics; numeric magnitude / centrality; token length and tokenization; canonical-expression
compressibility; "model treats odd values as typos"; surprise correlated with perceived importance;
latent stereotypes in nonce names; dose measured on the wrong model; sampling noise -> regression to
the mean; stimuli selected after self-testing; between-family rather than within-family variation;
position not truly counterbalanced; position drift after rewrites; high-surprise items clustered in a
chain; distractor interference; truncation / output-length compliance; append-only retrieval
similarity; temperature changing length not "learner type"; regexes favouring common formats; judges
inferring defaults from vague text; destination coding manufacturing prior-ward movement; preference
circularity (same samples for prior and outcome); profile convergence from response style;
surprise-pinning working through salience rather than surprise.

## Drift Warning
The main line does not drift. **The null-result fallback does**: switching to multi-agent shared
memory changes the unit of study and conflicts with the stated non-goal, and "keep the thesis" after
decisive tests fail is unfalsifiable. The reviewer says: delete the fallback; a clean null under
adequate compression and strong controls is a legitimate boundary result.

<details>
<summary>Raw response</summary>

(Stored verbatim in refine-logs/round-1-review-raw.txt)

</details>
