# Project: Agent memory compaction regresses to the pretraining prior

## Pipeline Status

```yaml
stage: idle          # idle | refine | planning | pilot | experiments | review | paper | done
idea: "LLM-driven agent memory compaction is iterated learning: memory drifts to the compactor's prior, so surprising content is forgotten and plausible / unsurprising content is kept"
contract: "docs/idea/idea1_memory_converges_to_prior.md"
current_branch: "memory-prior-paper"
baseline: ""
training_status: idle
language: en
active_tasks: []
next: "Run /research-refine on docs/idea/idea1_memory_converges_to_prior.md"
last_updated: ""
```

## What this project is

- The source of truth for the idea is `docs/idea/idea1_memory_converges_to_prior.md` (v3). Supporting material:
  - `docs/idea/idea1_pilot/PILOT_PLAN.md` and `docs/idea/idea1_pilot/stimuli/`: a ready pilot design and stimuli.
  - `docs/idea/idea1_survey/`: a survey of compaction mechanisms in 30+ systems, plus dataset licences and paper method details.
  - `docs/idea/idea1_novelty_check_2026-09-29.md`: the novelty check.
- **Scope: agent memory and continual learning only.** How agents write, consolidate, forget and use memory over long horizons, and whether they can keep learning beyond pretraining through memory.
  - No security framing anywhere: no attacks, poisoning, adversaries, backdoors or "defenses".
  - Call mitigations "memory design".
- Target venue: **ACL 2027** (ARR, long paper, 8 pages, anonymous submission). Primary track: special theme *Homogenization and knowledge collapse in LLMs*.

## Directives from the PI (these override the idea doc where they conflict)

1. **The pilot must use a strong model**, so that a null result cannot be blamed on a small or weak compactor.
   - Use a large hosted model as the pilot's main compactor. A good default is `qwen.qwen3-235b-a22b-2507-v1:0`.
   - Spot-check a second strong family, for example `meta.llama3-3-70b-instruct-v1:0`, `deepseek.v3.2` or `mistral.mistral-large-3-675b-instruct`.
   - The local Qwen3-8B is for the weak/small-model contrast and for logprob-based priors, not the main pilot compactor.
2. **If the pilot shows no core effect, keep the thesis and change the angle.** Keep the iterated-learning thesis: an LLM that manages the memory lifecycle makes memory look more and more like that LLM's prior, so surprising facts are forgotten and plausible falsehoods or unsurprising facts are kept.
   - First rule out weak-model or no-bottleneck explanations (strong model, tighter length budget, longer chains).
   - Then look for another entry point. The designated fallback is **multi-agent shared memory** with a **wisdom-of-crowds collapse** framing (Lorenz et al. 2011 effects: diversity loss, range reduction, confidence), using the same iterated-learning claim. The idea doc §11.1 says "single-agent only"; that is overridden, and multi-agent is the planned fallback.
   - Do not abandon the thesis because of one null pilot. Do report every result honestly, including nulls.
3. **Headline claim**: surprising facts are forgotten; plausible / unsurprising content is kept.
   - A *plausible falsehood vs. surprising truth* contrast is allowed as a truth-blind control: the compactor never sees ground truth, so it should keep plausible content regardless of truth.
   - Falsehoods must be non-adversarial, such as an honest mistake by the user or a colleague. Never frame them as injected or attacker content.
4. **Nothing that needs humans can happen during this run.** That rules out human κ annotation, IRB studies, Prolific ratings and emailing authors.
   - Never fabricate human data.
   - Replace human validation of the judge with agreement between two independent LLM judges from different model families, and report it.
   - Save the stratified 150-item human-validation sample to `human_validation/` for later.
   - State the limitation in the paper.
5. **Data licences**:
   - Do not redistribute ClashEval: the authors have not been asked yet.
   - Avoid CC BY-NC data (PrefEval, LoCoMo).
   - Prefer our own stimuli and MIT, Apache or CC BY datasets (CounterFact, MemoryAgentBench FactConsolidation, CompInt-style probes, IFEval-style checks).
6. Do not read or use anything in the parent repository `../agent_avalon/`. It holds unrelated projects. Everything this project needs is in this worktree.

## Run settings

- ARIS: `effort: balanced`, `assurance: conference-ready`, `AUTO_PROCEED: true`, `human checkpoint: false`, `AUTO_WRITE: true`, `venue: ACL`, `gpu: local`.
- Reviewer: Codex MCP (`mcp__codex__codex`, gpt-5.6-sol). It is configured for this worktree and uses the PI's ChatGPT plan, not the Bedrock budget.
- **Do not run `/idea-discovery`.** The idea is fixed. Order:
  1. `/research-refine` on the idea doc;
  2. `/experiment-plan` (start from the existing PILOT_PLAN);
  3. `/experiment-bridge`: pilot first, then the go/no-go per PILOT_PLAN §5 together with PI directive 2, then the full experiments;
  4. `/auto-review-loop`;
  5. `/paper-writing — venue: ACL` (assurance: conference-ready).
- Keep `PIPELINE_STATUS.md` (top level) up to date after every stage and every major experiment: what ran, key numbers, Bedrock spend so far, and the next step.
- When the final paper PDF exists and the conference-ready audits have run, write `PIPELINE_DONE` (one line: path to the PDF).
- Commit to the local branch `memory-prior-paper` at stage boundaries. **Never push.** Never modify files outside this worktree.

## Compute and budget (hard rules)

**Local GPU**: 1× NVIDIA A10G (24 GB). A vLLM server runs **Qwen3-8B** at `http://127.0.0.1:8001/v1`.
- Use model id `local:qwen3-8b` in `infra/llm.py`.
- It is free, supports logprobs (`score_continuations`), and runs in non-thinking mode.
- Status and restart: `/home/ubuntu/llm_infra/vllmctl.sh status|start`.
- The GPU is fully used by this server. Do not load other models on it.

**Bedrock**: the only access is the budget proxy at `http://127.0.0.1:8787/v1`, which is OpenAI-compatible.
- Use `infra/llm.py`: `chat`, `batch_chat`, `budget`, `estimate_cost`. It caches every response on disk.
- **Hard cap: $140 total** (the PI's absolute limit is $150). The proxy refuses calls past the cap with HTTP 402 and `infra.llm.BudgetExceeded`.
- Never try to obtain the credential or call Bedrock directly; a guard hook blocks it. Never touch the proxy.
- Current spend: `curl -s 127.0.0.1:8787/v1/budget`.
- If the proxy is down: `/home/ubuntu/llm_infra/proxyctl.sh start`.
- **Budget plan**: pilot ≤ $25; full experiments ≤ $90; keep ≥ $15 in reserve for review-driven additions.
  - Before every batch over $2, run `estimate_cost` and append a line to `COST_LOG.md`: date, purpose, model, number of calls, estimated cost, cumulative spend.
  - If the plan would exceed the budget, scale down: fewer seeds or temperatures, fewer cells, more local-model calls. Do not drop the core design.
- Choose the cheapest model that is good enough for each role, and justify the choice in `COST_LOG.md`.
- Bedrock models do not return logprobs. For hosted compactors, measure priors by sampling (PILOT_PLAN §4 method b) and default-behaviour rates (method c). Use the local model for the logprob method (a).
- For `openai.gpt-oss-*` models, pass `reasoning_effort="low"` (reasoning tokens are billed as output).
- Use `temperature=0` for probes and judges. Use `max_tokens` close to what is needed.

**Priced models** (USD per 1M tokens, input / output; full list from `GET 127.0.0.1:8787/v1/models`):

| Role suggestion | Model id | In | Out |
|---|---|---|---|
| strong compactor (pilot main) | qwen.qwen3-235b-a22b-2507-v1:0 | 0.22 | 0.88 |
| strong 2nd family | meta.llama3-3-70b-instruct-v1:0 | 0.72 | 0.72 |
| strong 2nd family | deepseek.v3.2 | 0.62 | 1.85 |
| strong 2nd family | mistral.mistral-large-3-675b-instruct | 0.50 | 1.50 |
| mid / cheap families | google.gemma-3-27b-it | 0.23 | 0.38 |
| mid / cheap families | meta.llama4-maverick-17b-instruct-v1:0 | 0.24 | 0.97 |
| mid / cheap families | qwen.qwen3-32b-v1:0 | 0.15 | 0.60 |
| judge (different family from the compactor) | openai.gpt-oss-120b-1:0 | 0.15 | 0.60 |
| cheap judge / helper | google.gemma-3-12b-it | 0.09 | 0.29 |
| cheap judge / helper | mistral.ministral-3-14b-instruct | 0.20 | 0.20 |
| small / free | local:qwen3-8b | 0 | 0 |

## Writing

- English for all paper artifacts.
- Report negative and null results.
- Every number in the paper must trace to a results file.
- Cite only verified papers. The related-work table in the idea doc §6 lists papers that were already checked.
