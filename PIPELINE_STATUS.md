# PIPELINE_STATUS

Unattended ARIS run. Started 2026-10-06. Branch `memory-prior-paper`.
Settings: effort balanced, assurance conference-ready, AUTO_PROCEED true, human checkpoint false, venue ACL.

## Stage ledger

| Stage | Status | Notes |
|---|---|---|
| /research-refine | **done** | 5 rounds w/ GPT-5.6-Sol xhigh. 6.4 -> 8.6 -> 9.1 -> 8.9 -> **9.5 READY**. Output: `refine-logs/FINAL_PROPOSAL.md` |
| /experiment-plan | **done** | `refine-logs/EXPERIMENT_PLAN.md`, 11 blocks, 6 milestones, ~$40 projected |
| /experiment-bridge M0 instrument | **done** | regexes tightened, distractors scrubbed, coder unit + metamorphic tests pass |
| /experiment-bridge M1 priors | **done** | compactor-side Bradley-Terry, split-half rho 0.948 |
| /experiment-bridge M2 dev pilot | **done** | operating point B=150 T=1.0 frozen; O3 calibrated to 60 slots; coding kappa 0.854 |
| claim-selection (was go/no-go) | **done** | adequacy met at B=150 only; see D10 |
| /experiment-bridge M3 E-SHIFT | running | 18 families x 2 arms x 8 seeds |
| /experiment-bridge M4 main chains | running | 11 chains x 3 seeds x 9 operators |
| go/no-go | pending | |
| /experiment-bridge (full) | pending | |
| /auto-review-loop | pending | |
| /paper-writing | pending | |

## Infrastructure (checked at start)
- Bedrock budget proxy up. Spend $0.0001 / cap $140.
- vLLM `local:qwen3-8b` up at 127.0.0.1:8001. logprobs verified via `score_continuations`.

## Decisions log

**D1 (infra).** The Codex MCP reviewer was broken on arrival: `/home/ubuntu/.local/bin/codex-code-mode-host`
was a dangling symlink to a removed VS Code extension build. Repointed it at the installed
`openai.chatgpt-26.930.51102-linux-x64` host. That cleared "host is missing" but exposed a protocol mismatch
(`unknown field code_mode_host_duration_ns`) between the Sept-30 host and the Aug-29 `codex` CLI, so the
reviewer has **no file access**. Workaround: every review round is run with the material **inlined in the
prompt**. Verified the model itself answers normally. No other file outside the worktree was touched.

**D2 (scope, from review round 1).** Deleted the external-validity datasets (MemoryAgentBench
FactConsolidation, CounterFact) and the Aider-style decay operator. They do not manipulate the causal
variable, so they cost pages and calls without supporting the claim.

**D3 (design, from review round 1).** Added **E-SHIFT**, a same-item prior manipulation: the target sentence
and its value are held fixed and only a value-free contextual base-rate frame changes. This is now the
headline causal evidence; the graded minimal-pair dose-response is demoted to *ecological* evidence.

**D4 (theory correction).** The original "stationary distribution = prior" claim is formally wrong once
deletion is near-absorbing. Replaced by a value-level copy/drop/replace kernel over measured-prior-rank
states, with the claim stated about the **quasi-stationary distribution conditional on survival**. The
thesis survives; the overclaim does not.

**D5 (prior measurement).** The dose is now measured on the **compactor itself** via randomized-order
pairwise choice fitted with Bradley-Terry. Local Qwen3-8B logprobs are demoted to a robustness check and the
small-model contrast, because an 8B model's prior is not a 235B model's prior.

**D6 (PI directive 2 vs reviewer drift warning).** The reviewer asked to delete the multi-agent null-result
fallback as unfalsifiable drift. CLAUDE.md makes it a standing PI directive, which overrides. Reconciled:
the fallback stays a *project* contingency, but a clean null is written up and submitted as a scoped boundary
result for *this* paper, the claim-selection criteria are preregistered and reported either way, and the
multi-agent direction would be a separate paper. The reviewer withdrew the objection.

**D8 (infrastructure, cross-model code review).** GPT-5.6-Sol xhigh reviewed the measurement code
before any confirmatory spend and found real bugs that could have manufactured the predicted result:
(i) the coder let regex coverage veto a blind judge's RETAINED, so levels with richer format
coverage would be scored as retained more often; (ii) over-budget rewrites were prefix-truncated,
which censors by position, applies only to rewriting operators, and destroyed line structure in the
carried state; (iii) O6 pins were requested of the model rather than enforced; (iv) snapshots logged
raw generation length instead of carried-state length, so capacity matching would have targeted the
wrong number. All fixed; see commit c9f741d.

**D9 (frames).** The first frame generator produced only 9/39 usable manipulations. Rewriting the
prompt to describe *the system the fact is about* (rather than Sam's generic role) and drawing 14
drafts per family raised this to 26/35. Draft selection happens on elicitation Half A and the
reported shift comes from the independent Half B, so selecting the strongest draft cannot inflate
the result.

**D10 (the strong compactor barely compresses at normal budgets).** The dev sweep shows
`qwen3-235b` retains 97.5-100% of seeded items at k=10 under B=300 and B=600 word budgets. The
prespecified empirical adequacy condition (O1 retention at least 10 pp below the O7 access ceiling
and inside [0.10, 0.90]) is met **only at B=150**, which was therefore selected. This is itself a
reportable result and directly answers the *Faithful, Not Corrective* counter-evidence: the effect
has a compression regime, and we state what it is rather than quietly tuning until something appears.

**D11 (loss is deletion, not corruption).** Of 16,200 coded dev cases, 10,981 are RETAINED, 4,892
DROPPED and only **7** CHANGED. For this compactor at this regime the *selection* channel does
essentially all the work and the *rewriting* channel almost none. That makes the round-1 reframe from
"memory converges to the prior" to "prior-shaped selective survival" not just a correctness fix but
the empirically right description, and it means the C5 replacement-direction claim has almost no
events to test -- which will be reported as a scoped null rather than hidden.

**D12 (amendment A4: endpoint changed on dev data).** Binary retention at k=10 discards eight ninths
of each E-SHIFT trajectory; its dev minimum detectable effect is 37.8 pp. The survival fraction over
all nine checkpoints gives 15.9 pp at identical cost and is the quantity the claim is about. The
endpoint was changed on dev data **before any confirmatory E-SHIFT trajectory was run**, binary@k=10
is kept as a secondary endpoint, and the operative SESOI is frozen at X=15.9 pp. Power at the
original 8 pp target is 0.32; reaching 0.80 would need roughly 60 eligible families, which is a
follow-up rather than something to search for after seeing the data.

**D7 (rigour).** Fact families split dev F01-F12 / confirmatory F13-F40 (preferences P01-P06 / P07-P20).
All operating-point choices are made on dev families only and frozen into `FROZEN_PROTOCOL.md` with a commit
hash before any confirmatory family is touched. "go/no-go" renamed **claim-selection criteria**, since the
paper is submitted under either outcome.

## Bedrock spend
$2.49 of $140 (see COST_LOG.md). Projected total ~$40.

## Key measured numbers so far
- **Coder validation**: strict per-level regex recognition 0.973-0.993 (spread 0.020); every
  unrecognised variant is routed to the blind judges rather than mis-coded. The coder therefore
  cannot itself produce a retention-vs-surprise gradient.
- **Prior (P1, compactor-side pairwise Bradley-Terry)**: split-half Spearman mean 0.948, 97% of
  families >= 0.7; within-family log-odds range mean 5.12.
- **P1 vs local Qwen3-8B logprobs**: Spearman 0.55 only. Measuring the dose on the compactor rather
  than transferring it from the small model was therefore load-bearing, not cosmetic.
- **Designed level order is wrong often**: the designed L1 is the measured modal level in only
  19 of 36 five-level families, which is why the analysis uses measured surprise as a continuous
  variable rather than the designed rank.
- **E-SHIFT manipulation works**: 26/35 families eligible (r=0.74) at a >=0.5 log-odds threshold on
  elicitation Half A; achieved shift on the INDEPENDENT Half B is +2.63 log-odds on average, and
  26/26 are in the predicted direction. 18 of the eligible families are confirmatory, 8 are dev.
- **Protocol v2**: asking for 80% of the word cap and enforcing the cap cut hard trims from 8.2 to
  1.2 per 21-step trajectory. Trimming drops trailing lines, which censors by position and applies
  only to the rewriting operators, so leaving it high would have risked manufacturing both the
  gradient and the operator interaction.

## Next step
Confirmatory runs -> coding -> analysis -> figures -> /auto-review-loop -> /paper-writing.
