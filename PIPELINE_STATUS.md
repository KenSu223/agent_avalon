# PIPELINE_STATUS

Unattended ARIS run. Started 2026-10-06. Branch `memory-prior-paper`.
Settings: effort balanced, assurance conference-ready, AUTO_PROCEED true, human checkpoint false, venue ACL.

## Stage ledger

| Stage | Status | Notes |
|---|---|---|
| /research-refine | **done** | 5 rounds w/ GPT-5.6-Sol xhigh. 6.4 -> 8.6 -> 9.1 -> 8.9 -> **9.5 READY**. Output: `refine-logs/FINAL_PROPOSAL.md` |
| /experiment-plan | in progress | |
| /experiment-bridge (pilot) | pending | |
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

**D7 (rigour).** Fact families split dev F01-F12 / confirmatory F13-F40 (preferences P01-P06 / P07-P20).
All operating-point choices are made on dev families only and frozen into `FROZEN_PROTOCOL.md` with a commit
hash before any confirmatory family is touched. "go/no-go" renamed **claim-selection criteria**, since the
paper is submitted under either outcome.

## Bedrock spend
$0.0001 of $140 (nothing spent yet; the refine stage used the PI's ChatGPT plan via Codex, not Bedrock).

## Next step
/experiment-plan, building on docs/idea/idea1_pilot/PILOT_PLAN.md and refine-logs/FINAL_PROPOSAL.md
