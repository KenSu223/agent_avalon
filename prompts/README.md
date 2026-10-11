# Prompt archive

Every prompt used to produce the results of this project is archived here, verbatim, so that the paper can publish
all prompts and every number can be reproduced. **This directory is generated; do not edit by hand.** Rebuild with
`python prompts/capture.py && python prompts/export_library.py && python prompts/build_readme.py` (fw-env python), and
verify with `python prompts/check_prompts.py`, which rebuilds everything into a temp dir and fails on any difference.

## What is here
| Part | Content | How it is guaranteed to be what was actually sent |
|---|---|---|
| `templates/` | One file per prompt template, taken from the code objects themselves (constants are imported; inline message builders are called with `{placeholder}` arguments; product adapters are run with placeholder turns). | Generated from the code that ran the experiments; `check_prompts.py` fails if the code and the archive drift apart. |
| `exemplars/` | Fully rendered real requests (messages + decoding parameters) for every call site, including 3-step replays of every product compaction chain on user 0 for both compactor models. | Each exemplar is rebuilt exactly as the experiment built it and looked up **offline** in the response cache (`infra.llm.cache_lookup`, keyed by a SHA-256 of the full payload). `verified_in_cache: true` means the request is byte-identical to one the experiment sent. |
| `library/` | Prompt-bearing source files of the memory libraries run with their default prompts, copied from the exact installed versions, with licences and `MANIFEST.json` (sha256). `prompts_extracted.txt` lists the prompt strings for reading. | Copied from the environments the experiments used. |
| `infra/` | The budget proxy that translates OpenAI-format requests to the Bedrock Converse API (as used until 2026-10-10, and the current version). | Source copies. |
| live logs (not in git) | `logs/requests/` (every `infra.llm` call since 2026-10-10, incl. cache hits) and `~/llm_infra/state/requests/` (every request reaching Bedrock through the proxy, incl. library-internal calls, as received and as translated). | Written at call time. |

## Request transformations outside the prompt text (needed for exact reproduction)
- **Bedrock (via the proxy):** `system`/`developer` messages become the Converse `system` field; consecutive same-role
  messages are merged; if the first message is from the assistant, a user message `(continue)` is prepended.
  `response_format` of type `json_object` / `json_schema` (used by some libraries) is turned into an extra system
  instruction: `Respond only with a single valid JSON object and nothing else (no code fences).` plus, for
  `json_schema`, ` It must follow this JSON schema: <schema>`. OpenAI tool definitions become Converse `toolConfig`
  (missing descriptions default to the tool name). `reasoning_effort` is forwarded only for `openai.gpt-oss-*`.
- **Local model (vLLM, Qwen3-8B):** `chat_template_kwargs = {"enable_thinking": false}` and `seed = sample_idx`.
- Decoding parameters (temperature, max_tokens, sample_idx, reasoning_effort) are part of every exemplar's `payload`.

## Data that is inserted into prompts
- C/I items: `framework_study/stimuli/items.jsonl` (built by `build_items.py`; written by Claude, an LLM, and to be
  spot-checked by humans). Distractor sessions: `framework_study/stimuli/distractors.json` (generated, then screened).
  The complete session sequence for one user is in `exemplars/fw_user0_history.json`.
- Benchmarks (LongMemEval, LoCoMo, MemoryAgentBench, PrefEval) are inserted with the formats shown in the
  `rescore_*_format` templates; LoCoMo and PrefEval are CC BY-NC 4.0 and are not redistributed here.

## Not part of the paper
The earlier ARIS pipeline in `src/` (2026-10-06, iterated-learning chains) is superseded and not used for any reported
result; its prompts remain available in git history.

## Summary
46 templates; 124 exemplars, 124 verified byte-identical against the response cache.

## closed-book audit
**Templates**

| id | source | file |
|---|---|---|
| `cb_natural_system` | benchmark_audit/closed_book.py NAT_SYS | [templates/cb_natural_system.txt](templates/cb_natural_system.txt) |
| `cb_forced_system` | benchmark_audit/closed_book.py FORCED_SYS (also method draw F0) | [templates/cb_forced_system.txt](templates/cb_forced_system.txt) |

**Verified exemplars**

| id | used for | model | parameters | verified | file |
|---|---|---|---|---|---|
| `cb_longmemeval_natural_qwen` | closed-book natural answer, LongMemEval (FINDINGS §8) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=150 | ✅ | [exemplars/cb_longmemeval_natural_qwen.json](exemplars/cb_longmemeval_natural_qwen.json) |
| `cb_longmemeval_forced_qwen` | closed-book forced answer, LongMemEval (FINDINGS §8) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=150 | ✅ | [exemplars/cb_longmemeval_forced_qwen.json](exemplars/cb_longmemeval_forced_qwen.json) |
| `cb_locomo_natural_qwen` | closed-book natural answer, LoCoMo (FINDINGS §8) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=150 | ✅ | [exemplars/cb_locomo_natural_qwen.json](exemplars/cb_locomo_natural_qwen.json) |
| `cb_locomo_forced_qwen` | closed-book forced answer, LoCoMo (FINDINGS §8) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=150 | ✅ | [exemplars/cb_locomo_forced_qwen.json](exemplars/cb_locomo_forced_qwen.json) |
| `cb_memoryagentbench_natural_qwen` | closed-book natural answer, MemoryAgentBench (FINDINGS §8) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=150 | ✅ | [exemplars/cb_memoryagentbench_natural_qwen.json](exemplars/cb_memoryagentbench_natural_qwen.json) |
| `cb_memoryagentbench_forced_qwen` | closed-book forced answer, MemoryAgentBench (FINDINGS §8) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=150 | ✅ | [exemplars/cb_memoryagentbench_forced_qwen.json](exemplars/cb_memoryagentbench_forced_qwen.json) |
| `cb_prefeval_qwen` | PrefEval memoryless answer (FINDINGS §8) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=600 | ✅ | [exemplars/cb_prefeval_qwen.json](exemplars/cb_prefeval_qwen.json) |
| `cb_longmemeval_natural_llama` | closed-book natural answer, LongMemEval (FINDINGS §8) | meta.llama3-3-70b-instruct-v1:0 | temperature=0.0, max_tokens=150 | ✅ | [exemplars/cb_longmemeval_natural_llama.json](exemplars/cb_longmemeval_natural_llama.json) |
| `cb_longmemeval_forced_llama` | closed-book forced answer, LongMemEval (FINDINGS §8) | meta.llama3-3-70b-instruct-v1:0 | temperature=0.0, max_tokens=150 | ✅ | [exemplars/cb_longmemeval_forced_llama.json](exemplars/cb_longmemeval_forced_llama.json) |
| `cb_locomo_natural_llama` | closed-book natural answer, LoCoMo (FINDINGS §8) | meta.llama3-3-70b-instruct-v1:0 | temperature=0.0, max_tokens=150 | ✅ | [exemplars/cb_locomo_natural_llama.json](exemplars/cb_locomo_natural_llama.json) |
| `cb_locomo_forced_llama` | closed-book forced answer, LoCoMo (FINDINGS §8) | meta.llama3-3-70b-instruct-v1:0 | temperature=0.0, max_tokens=150 | ✅ | [exemplars/cb_locomo_forced_llama.json](exemplars/cb_locomo_forced_llama.json) |
| `cb_memoryagentbench_natural_llama` | closed-book natural answer, MemoryAgentBench (FINDINGS §8) | meta.llama3-3-70b-instruct-v1:0 | temperature=0.0, max_tokens=150 | ✅ | [exemplars/cb_memoryagentbench_natural_llama.json](exemplars/cb_memoryagentbench_natural_llama.json) |
| `cb_memoryagentbench_forced_llama` | closed-book forced answer, MemoryAgentBench (FINDINGS §8) | meta.llama3-3-70b-instruct-v1:0 | temperature=0.0, max_tokens=150 | ✅ | [exemplars/cb_memoryagentbench_forced_llama.json](exemplars/cb_memoryagentbench_forced_llama.json) |
| `cb_prefeval_llama` | PrefEval memoryless answer (FINDINGS §8) | meta.llama3-3-70b-instruct-v1:0 | temperature=0.0, max_tokens=600 | ✅ | [exemplars/cb_prefeval_llama.json](exemplars/cb_prefeval_llama.json) |

## judging
**Templates**

| id | source | file |
|---|---|---|
| `judge_lme_single-session-user` | benchmark_audit/official/lme_prompts.py (verbatim LongMemEval evaluate_qa.py, MIT) — single-session-assistant and multi-session use the single-session-user template | [templates/judge_lme_single-session-user.txt](templates/judge_lme_single-session-user.txt) |
| `judge_lme_temporal-reasoning` | benchmark_audit/official/lme_prompts.py (verbatim LongMemEval evaluate_qa.py, MIT) — single-session-assistant and multi-session use the single-session-user template | [templates/judge_lme_temporal-reasoning.txt](templates/judge_lme_temporal-reasoning.txt) |
| `judge_lme_knowledge-update` | benchmark_audit/official/lme_prompts.py (verbatim LongMemEval evaluate_qa.py, MIT) — single-session-assistant and multi-session use the single-session-user template | [templates/judge_lme_knowledge-update.txt](templates/judge_lme_knowledge-update.txt) |
| `judge_lme_single-session-preference` | benchmark_audit/official/lme_prompts.py (verbatim LongMemEval evaluate_qa.py, MIT) — single-session-assistant and multi-session use the single-session-user template | [templates/judge_lme_single-session-preference.txt](templates/judge_lme_single-session-preference.txt) |
| `judge_lme_abstention` | benchmark_audit/official/lme_prompts.py — LoCoMo cat 5 uses explanation = 'The conversation does not contain this information.' | [templates/judge_lme_abstention.txt](templates/judge_lme_abstention.txt) |
| `judge_prefeval_violation` | benchmark_audit/official/prefeval_check_violation.txt (verbatim PrefEval) | [templates/judge_prefeval_violation.txt](templates/judge_prefeval_violation.txt) |
| `judge_prefeval_helpful` | benchmark_audit/official/prefeval_check_helpful.txt (verbatim PrefEval) | [templates/judge_prefeval_helpful.txt](templates/judge_prefeval_helpful.txt) |
| `judge_prefeval_system` | closed_book.py main (system message of the PrefEval judge calls) | [templates/judge_prefeval_system.txt](templates/judge_prefeval_system.txt) |
| `pcme_abstention_judge` | method/abstention_judge.py PROMPT (METHOD §10.4) | [templates/pcme_abstention_judge.txt](templates/pcme_abstention_judge.txt) |
| `fw_memory_state_judge` | v3_reproduction.py JUDGE_PROMPT (memory-state coding; also probe.py) | [templates/fw_memory_state_judge.txt](templates/fw_memory_state_judge.txt) |

**Verified exemplars**

| id | used for | model | parameters | verified | file |
|---|---|---|---|---|---|
| `judge_lme_closed_book` | LongMemEval official judge (closed-book run) | openai.gpt-oss-120b-1:0 | temperature=0.0, max_tokens=600, reasoning_effort=low | ✅ | [exemplars/judge_lme_closed_book.json](exemplars/judge_lme_closed_book.json) |
| `judge_locomo_closed_book` | LoCoMo judge = LongMemEval generic prompt (closed-book run) | openai.gpt-oss-120b-1:0 | temperature=0.0, max_tokens=600, reasoning_effort=low | ✅ | [exemplars/judge_locomo_closed_book.json](exemplars/judge_locomo_closed_book.json) |
| `judge_locomo_cat5_closed_book` | LoCoMo category 5 (unanswerable) judge | openai.gpt-oss-120b-1:0 | temperature=0.0, max_tokens=600, reasoning_effort=low | ✅ | [exemplars/judge_locomo_cat5_closed_book.json](exemplars/judge_locomo_cat5_closed_book.json) |
| `judge_prefeval_violation` | PrefEval official violation check | openai.gpt-oss-120b-1:0 | temperature=0.0, max_tokens=800, reasoning_effort=low | ✅ | [exemplars/judge_prefeval_violation.json](exemplars/judge_prefeval_violation.json) |
| `judge_prefeval_helpful` | PrefEval official helpful check | openai.gpt-oss-120b-1:0 | temperature=0.0, max_tokens=800, reasoning_effort=low | ✅ | [exemplars/judge_prefeval_helpful.json](exemplars/judge_prefeval_helpful.json) |
| `judge_locomo_rescore` | LoCoMo judge in re-scoring | openai.gpt-oss-120b-1:0 | temperature=0.0, max_tokens=600, reasoning_effort=low | ✅ | [exemplars/judge_locomo_rescore.json](exemplars/judge_locomo_rescore.json) |
| `pcme_abstention_judge` | abstention classification (validation sample + all answers) | openai.gpt-oss-120b-1:0 | temperature=0.0, max_tokens=400, reasoning_effort=low | ✅ | [exemplars/pcme_abstention_judge.json](exemplars/pcme_abstention_judge.json) |
| `fw_probe_judge_gptoss` | memory-state coding of a framework dump | openai.gpt-oss-120b-1:0 | temperature=0.0, max_tokens=600, reasoning_effort=low | ✅ | [exemplars/fw_probe_judge_gptoss.json](exemplars/fw_probe_judge_gptoss.json) |
| `fw_probe_judge_gemma` | memory-state coding of a framework dump | google.gemma-3-27b-it | temperature=0.0, max_tokens=12 | ✅ | [exemplars/fw_probe_judge_gemma.json](exemplars/fw_probe_judge_gemma.json) |

## benchmark re-scoring
**Templates**

| id | source | file |
|---|---|---|
| `rescore_answer_system_piA` | benchmark_audit/rescore.py ANSWER_SYS (native protocol pi_A) | [templates/rescore_answer_system_piA.txt](templates/rescore_answer_system_piA.txt) |
| `rescore_locomo_turn_format` | benchmark_audit/rescore.py locomo_episodes (speaker_a -> role user, speaker_b -> role assistant; one ingest per session) | [templates/rescore_locomo_turn_format.txt](templates/rescore_locomo_turn_format.txt) |
| `rescore_mab_chunk_format` | benchmark_audit/rescore.py mab_ruler_episodes (one ingest per chunk) | [templates/rescore_mab_chunk_format.json](templates/rescore_mab_chunk_format.json) |
| `rescore_threshold_context_format` | benchmark_audit/threshold_compaction.py ThresholdCompaction.dump (systems '<adapter>@thr64k'; T = 64,000 estimated tokens = chars/4) — full_history = the turns only, one '{role}: {content}' line each, no header | [templates/rescore_threshold_context_format.txt](templates/rescore_threshold_context_format.txt) |

**Verified exemplars**

| id | used for | model | parameters | verified | file |
|---|---|---|---|---|---|
| `rescore_answer_piA_locomo_codex` | native-protocol answer from a system's context (§11, Step 2) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=120 | ✅ | [exemplars/rescore_answer_piA_locomo_codex.json](exemplars/rescore_answer_piA_locomo_codex.json) |
| `rescore_answer_piA_codex_thr64k` | native-protocol answer, threshold robustness check (METHOD §10.6) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=120 | ✅ | [exemplars/rescore_answer_piA_codex_thr64k.json](exemplars/rescore_answer_piA_codex_thr64k.json) |
| `rescore_answer_piA_full_history` | native-protocol answer, threshold robustness check (METHOD §10.6) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=120 | ✅ | [exemplars/rescore_answer_piA_full_history.json](exemplars/rescore_answer_piA_full_history.json) |

## PCME method (Steps 1-2)
**Templates**

| id | source | file |
|---|---|---|
| `pcme_answer_system_piF` | method/common.py ANSWER_SYS_F (forced protocol pi_F) | [templates/pcme_answer_system_piF.txt](templates/pcme_answer_system_piF.txt) |
| `pcme_prior_F1_system` | method/common.py F1_SYS (closed-book draw F1) | [templates/pcme_prior_F1_system.txt](templates/pcme_prior_F1_system.txt) |
| `pcme_prior_F2_user` | method/common.py F2_USER (closed-book draw F2, no system prompt) | [templates/pcme_prior_F2_user.txt](templates/pcme_prior_F2_user.txt) |
| `pcme_followup_user` | method/reask.py FOLLOW (compliance follow-up, pi_F+R) | [templates/pcme_followup_user.txt](templates/pcme_followup_user.txt) |

**Verified exemplars**

| id | used for | model | parameters | verified | file |
|---|---|---|---|---|---|
| `pcme_prior_longmemeval_F1_T0` | closed-book prior draw (E1.1, METHOD §2.1) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=150, sample_idx=0 | ✅ | [exemplars/pcme_prior_longmemeval_F1_T0.json](exemplars/pcme_prior_longmemeval_F1_T0.json) |
| `pcme_prior_longmemeval_F2_T0` | closed-book prior draw (E1.1, METHOD §2.1) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=150, sample_idx=0 | ✅ | [exemplars/pcme_prior_longmemeval_F2_T0.json](exemplars/pcme_prior_longmemeval_F2_T0.json) |
| `pcme_prior_longmemeval_F0_T1_s1` | closed-book prior draw (E1.1, METHOD §2.1) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=1.0, max_tokens=150, sample_idx=1 | ✅ | [exemplars/pcme_prior_longmemeval_F0_T1_s1.json](exemplars/pcme_prior_longmemeval_F0_T1_s1.json) |
| `pcme_prior_longmemeval_F0_T1_s2` | closed-book prior draw (E1.1, METHOD §2.1) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=1.0, max_tokens=150, sample_idx=2 | ✅ | [exemplars/pcme_prior_longmemeval_F0_T1_s2.json](exemplars/pcme_prior_longmemeval_F0_T1_s2.json) |
| `pcme_prior_longmemeval_F0_T1_s3` | closed-book prior draw (E1.1, METHOD §2.1) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=1.0, max_tokens=150, sample_idx=3 | ✅ | [exemplars/pcme_prior_longmemeval_F0_T1_s3.json](exemplars/pcme_prior_longmemeval_F0_T1_s3.json) |
| `pcme_prior_locomo_F1_T0` | closed-book prior draw (E1.1, METHOD §2.1) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=150, sample_idx=0 | ✅ | [exemplars/pcme_prior_locomo_F1_T0.json](exemplars/pcme_prior_locomo_F1_T0.json) |
| `pcme_prior_locomo_F2_T0` | closed-book prior draw (E1.1, METHOD §2.1) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=150, sample_idx=0 | ✅ | [exemplars/pcme_prior_locomo_F2_T0.json](exemplars/pcme_prior_locomo_F2_T0.json) |
| `pcme_prior_locomo_F0_T1_s1` | closed-book prior draw (E1.1, METHOD §2.1) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=1.0, max_tokens=150, sample_idx=1 | ✅ | [exemplars/pcme_prior_locomo_F0_T1_s1.json](exemplars/pcme_prior_locomo_F0_T1_s1.json) |
| `pcme_prior_locomo_F0_T1_s2` | closed-book prior draw (E1.1, METHOD §2.1) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=1.0, max_tokens=150, sample_idx=2 | ✅ | [exemplars/pcme_prior_locomo_F0_T1_s2.json](exemplars/pcme_prior_locomo_F0_T1_s2.json) |
| `pcme_prior_locomo_F0_T1_s3` | closed-book prior draw (E1.1, METHOD §2.1) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=1.0, max_tokens=150, sample_idx=3 | ✅ | [exemplars/pcme_prior_locomo_F0_T1_s3.json](exemplars/pcme_prior_locomo_F0_T1_s3.json) |
| `pcme_prior_memoryagentbench_F1_T0` | closed-book prior draw (E1.1, METHOD §2.1) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=150, sample_idx=0 | ✅ | [exemplars/pcme_prior_memoryagentbench_F1_T0.json](exemplars/pcme_prior_memoryagentbench_F1_T0.json) |
| `pcme_prior_memoryagentbench_F2_T0` | closed-book prior draw (E1.1, METHOD §2.1) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=150, sample_idx=0 | ✅ | [exemplars/pcme_prior_memoryagentbench_F2_T0.json](exemplars/pcme_prior_memoryagentbench_F2_T0.json) |
| `pcme_prior_memoryagentbench_F0_T1_s1` | closed-book prior draw (E1.1, METHOD §2.1) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=1.0, max_tokens=150, sample_idx=1 | ✅ | [exemplars/pcme_prior_memoryagentbench_F0_T1_s1.json](exemplars/pcme_prior_memoryagentbench_F0_T1_s1.json) |
| `pcme_prior_memoryagentbench_F0_T1_s2` | closed-book prior draw (E1.1, METHOD §2.1) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=1.0, max_tokens=150, sample_idx=2 | ✅ | [exemplars/pcme_prior_memoryagentbench_F0_T1_s2.json](exemplars/pcme_prior_memoryagentbench_F0_T1_s2.json) |
| `pcme_prior_memoryagentbench_F0_T1_s3` | closed-book prior draw (E1.1, METHOD §2.1) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=1.0, max_tokens=150, sample_idx=3 | ✅ | [exemplars/pcme_prior_memoryagentbench_F0_T1_s3.json](exemplars/pcme_prior_memoryagentbench_F0_T1_s3.json) |
| `pcme_prior_eval_longmemeval_E_T1_s1` | eval-prompt prior draw g' (remedy a, METHOD v1.1/v1.2) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=1.0, max_tokens=120, sample_idx=1 | ✅ | [exemplars/pcme_prior_eval_longmemeval_E_T1_s1.json](exemplars/pcme_prior_eval_longmemeval_E_T1_s1.json) |
| `pcme_prior_eval_locomo_E_T1_s1` | eval-prompt prior draw g' (remedy a, METHOD v1.1/v1.2) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=1.0, max_tokens=120, sample_idx=1 | ✅ | [exemplars/pcme_prior_eval_locomo_E_T1_s1.json](exemplars/pcme_prior_eval_locomo_E_T1_s1.json) |
| `pcme_prior_eval_memoryagentbench_E_T1_s1` | eval-prompt prior draw g' (remedy a, METHOD v1.1/v1.2) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=1.0, max_tokens=120, sample_idx=1 | ✅ | [exemplars/pcme_prior_eval_memoryagentbench_E_T1_s1.json](exemplars/pcme_prior_eval_memoryagentbench_E_T1_s1.json) |
| `pcme_refsys_empty_locomo` | reference system under pi_F (E1.2, METHOD §6) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=120 | ✅ | [exemplars/pcme_refsys_empty_locomo.json](exemplars/pcme_refsys_empty_locomo.json) |
| `pcme_refsys_empty_memoryagentbench` | reference system under pi_F (E1.2, METHOD §6) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=120 | ✅ | [exemplars/pcme_refsys_empty_memoryagentbench.json](exemplars/pcme_refsys_empty_memoryagentbench.json) |
| `pcme_followup_refsys_empty` | compliance follow-up (remedy b, METHOD v1.1) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=120, sample_idx=100 | ✅ | [exemplars/pcme_followup_refsys_empty.json](exemplars/pcme_followup_refsys_empty.json) |
| `pcme_refsys_oracle_locomo` | reference system under pi_F (E1.2, METHOD §6) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=120 | ✅ | [exemplars/pcme_refsys_oracle_locomo.json](exemplars/pcme_refsys_oracle_locomo.json) |
| `pcme_refsys_oracle_memoryagentbench` | reference system under pi_F (E1.2, METHOD §6) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=120 | ✅ | [exemplars/pcme_refsys_oracle_memoryagentbench.json](exemplars/pcme_refsys_oracle_memoryagentbench.json) |
| `pcme_refsys_bm25_ev_locomo` | reference system under pi_F (E1.2, METHOD §6) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=120 | ✅ | [exemplars/pcme_refsys_bm25_ev_locomo.json](exemplars/pcme_refsys_bm25_ev_locomo.json) |
| `pcme_refsys_bm25_ev_memoryagentbench` | reference system under pi_F (E1.2, METHOD §6) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=120 | ✅ | [exemplars/pcme_refsys_bm25_ev_memoryagentbench.json](exemplars/pcme_refsys_bm25_ev_memoryagentbench.json) |
| `pcme_refsys_bm25_noev_locomo` | reference system under pi_F (E1.2, METHOD §6) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=120 | ✅ | [exemplars/pcme_refsys_bm25_noev_locomo.json](exemplars/pcme_refsys_bm25_noev_locomo.json) |
| `pcme_refsys_bm25_noev_memoryagentbench` | reference system under pi_F (E1.2, METHOD §6) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=120 | ✅ | [exemplars/pcme_refsys_bm25_noev_memoryagentbench.json](exemplars/pcme_refsys_bm25_noev_memoryagentbench.json) |
| `pcme_protocol_piF_locomo_codex` | Step 2 forced-protocol answer | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=120 | ✅ | [exemplars/pcme_protocol_piF_locomo_codex.json](exemplars/pcme_protocol_piF_locomo_codex.json) |
| `pcme_protocol_piFR_locomo_codex` | Step 2 pi_F+R follow-up | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=120, sample_idx=100 | ✅ | [exemplars/pcme_protocol_piFR_locomo_codex.json](exemplars/pcme_protocol_piFR_locomo_codex.json) |

## stimuli
**Templates**

| id | source | file |
|---|---|---|
| `fw_user_turn_rule` | framework_study/stimuli/build_items.py user_turn (rule / procedure) | [templates/fw_user_turn_rule.txt](templates/fw_user_turn_rule.txt) |
| `fw_user_turn_preference` | build_items.py user_turn (preference; preceded by a filler question in sessions) | [templates/fw_user_turn_preference.txt](templates/fw_user_turn_preference.txt) |
| `fw_seed_session` | framework_study/src/sessions.py build_history / item_exchange — preference items: user = '{filler question} {user_turn}', assistant = '{filler answer} Got it.' | [templates/fw_seed_session.json](templates/fw_seed_session.json) |
| `fw_distractor_generation` | framework_study/src/make_distractors.py PROMPT (Qwen3-235B, T=0.8) | [templates/fw_distractor_generation.txt](templates/fw_distractor_generation.txt) |

**Verified exemplars**

| id | used for | model | parameters | verified | file |
|---|---|---|---|---|---|
| `fw_distractor_generation` | distractor sessions (stimuli/distractors.json) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.8, max_tokens=500, sample_idx=0 | ✅ | [exemplars/fw_distractor_generation.json](exemplars/fw_distractor_generation.json) |
| `fw_user0_history` | the full session sequence ingested by every framework for user 0 |  |  | ✅ | [exemplars/fw_user0_history.json](exemplars/fw_user0_history.json) |

## validation + probe
**Templates**

| id | source | file |
|---|---|---|
| `fw_world_system` | framework_study/src/validate.py WORLD | [templates/fw_world_system.txt](templates/fw_world_system.txt) |
| `fw_forced_choice_question` | validate.py ask (order 0; order 1 swaps the options) | [templates/fw_forced_choice_question.txt](templates/fw_forced_choice_question.txt) |

## validation
**Templates**

| id | source | file |
|---|---|---|
| `fw_v1_prefix_rule` | validate.py v1 (rule / procedure items) | [templates/fw_v1_prefix_rule.txt](templates/fw_v1_prefix_rule.txt) |
| `fw_v1_prefix_preference` | validate.py v1 (preference items) | [templates/fw_v1_prefix_preference.txt](templates/fw_v1_prefix_preference.txt) |

**Verified exemplars**

| id | used for | model | parameters | verified | file |
|---|---|---|---|---|---|
| `fw_v1_qwen` | V1 prior strength (20 draws per item) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=1.0, sample_idx=0, max_tokens=12 | ✅ | [exemplars/fw_v1_qwen.json](exemplars/fw_v1_qwen.json) |
| `fw_v2_qwen` | V2 comprehension | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=12 | ✅ | [exemplars/fw_v2_qwen.json](exemplars/fw_v2_qwen.json) |
| `fw_v1_llama` | V1 prior strength (20 draws per item) | meta.llama3-3-70b-instruct-v1:0 | temperature=1.0, sample_idx=0, max_tokens=12 | ✅ | [exemplars/fw_v1_llama.json](exemplars/fw_v1_llama.json) |
| `fw_v2_llama` | V2 comprehension | meta.llama3-3-70b-instruct-v1:0 | temperature=0.0, max_tokens=12 | ✅ | [exemplars/fw_v2_llama.json](exemplars/fw_v2_llama.json) |
| `fw_v1_gptoss` | V1 prior strength (20 draws per item) | openai.gpt-oss-120b-1:0 | temperature=1.0, sample_idx=0, max_tokens=600, reasoning_effort=low | ✅ | [exemplars/fw_v1_gptoss.json](exemplars/fw_v1_gptoss.json) |
| `fw_v2_gptoss` | V2 comprehension | openai.gpt-oss-120b-1:0 | temperature=0.0, max_tokens=600, reasoning_effort=low | ✅ | [exemplars/fw_v2_gptoss.json](exemplars/fw_v2_gptoss.json) |

## validation (V3 Bartlett positive control)
**Templates**

| id | source | file |
|---|---|---|
| `fw_v3_system` | framework_study/src/v3_reproduction.py SYSTEM | [templates/fw_v3_system.txt](templates/fw_v3_system.txt) |

## validation (V3)
**Templates**

| id | source | file |
|---|---|---|
| `fw_v3_first_notes` | v3_reproduction.py first_notes() (B = 100 words) | [templates/fw_v3_first_notes.json](templates/fw_v3_first_notes.json) |
| `fw_v3_retell` | v3_reproduction.py retell() (B = 100 words) | [templates/fw_v3_retell.json](templates/fw_v3_retell.json) |
| `fw_v3_gist` | v3_reproduction.py gist() (B = 100 words) | [templates/fw_v3_gist.json](templates/fw_v3_gist.json) |
| `fw_v3_expand` | v3_reproduction.py expand() (B = 100 words) | [templates/fw_v3_expand.json](templates/fw_v3_expand.json) |

**Verified exemplars**

| id | used for | model | parameters | verified | file |
|---|---|---|---|---|---|
| `fw_v3_first_notes` | V3 generation 0 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=1.0, max_tokens=400, sample_idx=0 | ✅ | [exemplars/fw_v3_first_notes.json](exemplars/fw_v3_first_notes.json) |

## probe
**Templates**

| id | source | file |
|---|---|---|
| `fw_probe_qa_system` | framework_study/src/probe.py QA_SYSTEM (belief probe) | [templates/fw_probe_qa_system.txt](templates/fw_probe_qa_system.txt) |

**Verified exemplars**

| id | used for | model | parameters | verified | file |
|---|---|---|---|---|---|
| `fw_probe_belief` | belief probe (forced choice from the framework's context) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=12 | ✅ | [exemplars/fw_probe_belief.json](exemplars/fw_probe_belief.json) |

## framework compaction
**Templates**

| id | source | file |
|---|---|---|
| `fw_compactor_codex` | framework_study/src/frameworks.py Codex.ingest (verbatim product prompt + framing) | [templates/fw_compactor_codex.json](templates/fw_compactor_codex.json) |
| `fw_compactor_openhands` | framework_study/src/frameworks.py OpenHands.ingest (verbatim product prompt + framing) | [templates/fw_compactor_openhands.json](templates/fw_compactor_openhands.json) |
| `fw_compactor_aider` | framework_study/src/frameworks.py Aider.ingest (verbatim product prompt + framing) | [templates/fw_compactor_aider.json](templates/fw_compactor_aider.json) |
| `fw_compactor_gemini_cli` | framework_study/src/frameworks.py GeminiCLI.ingest (verbatim product prompt + framing) | [templates/fw_compactor_gemini_cli.json](templates/fw_compactor_gemini_cli.json) |
| `fw_compactor_anthropic_api` | framework_study/src/frameworks.py AnthropicAPI.ingest (verbatim product prompt + framing) | [templates/fw_compactor_anthropic_api.json](templates/fw_compactor_anthropic_api.json) |
| `fw_compactor_langchain_summary` | framework_study/src/frameworks.py LangChainSummary.ingest (verbatim product prompt + framing) | [templates/fw_compactor_langchain_summary.json](templates/fw_compactor_langchain_summary.json) |
| `fw_compactor_neutral_roll` | framework_study/src/frameworks.py NeutralRoll.ingest (verbatim product prompt + framing) | [templates/fw_compactor_neutral_roll.json](templates/fw_compactor_neutral_roll.json) |

**Verified exemplars**

| id | used for | model | parameters | verified | file |
|---|---|---|---|---|---|
| `fw_replay_codex_qwen235b_call0` | user 0, session 1 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_codex_qwen235b_call0.json](exemplars/fw_replay_codex_qwen235b_call0.json) |
| `fw_replay_codex_qwen235b_call1` | user 0, session 2 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_codex_qwen235b_call1.json](exemplars/fw_replay_codex_qwen235b_call1.json) |
| `fw_replay_codex_qwen235b_call2` | user 0, session 3 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_codex_qwen235b_call2.json](exemplars/fw_replay_codex_qwen235b_call2.json) |
| `fw_replay_codex_qwen8b_local_call0` | user 0, session 1 | local:qwen3-8b | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_codex_qwen8b_local_call0.json](exemplars/fw_replay_codex_qwen8b_local_call0.json) |
| `fw_replay_codex_qwen8b_local_call1` | user 0, session 2 | local:qwen3-8b | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_codex_qwen8b_local_call1.json](exemplars/fw_replay_codex_qwen8b_local_call1.json) |
| `fw_replay_codex_qwen8b_local_call2` | user 0, session 3 | local:qwen3-8b | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_codex_qwen8b_local_call2.json](exemplars/fw_replay_codex_qwen8b_local_call2.json) |
| `fw_replay_openhands_qwen235b_call0` | user 0, session 1 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_openhands_qwen235b_call0.json](exemplars/fw_replay_openhands_qwen235b_call0.json) |
| `fw_replay_openhands_qwen235b_call1` | user 0, session 2 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_openhands_qwen235b_call1.json](exemplars/fw_replay_openhands_qwen235b_call1.json) |
| `fw_replay_openhands_qwen235b_call2` | user 0, session 3 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_openhands_qwen235b_call2.json](exemplars/fw_replay_openhands_qwen235b_call2.json) |
| `fw_replay_openhands_qwen8b_local_call0` | user 0, session 1 | local:qwen3-8b | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_openhands_qwen8b_local_call0.json](exemplars/fw_replay_openhands_qwen8b_local_call0.json) |
| `fw_replay_openhands_qwen8b_local_call1` | user 0, session 2 | local:qwen3-8b | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_openhands_qwen8b_local_call1.json](exemplars/fw_replay_openhands_qwen8b_local_call1.json) |
| `fw_replay_openhands_qwen8b_local_call2` | user 0, session 3 | local:qwen3-8b | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_openhands_qwen8b_local_call2.json](exemplars/fw_replay_openhands_qwen8b_local_call2.json) |
| `fw_replay_aider_qwen235b_call0` | user 0, session 1 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_aider_qwen235b_call0.json](exemplars/fw_replay_aider_qwen235b_call0.json) |
| `fw_replay_aider_qwen235b_call1` | user 0, session 2 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_aider_qwen235b_call1.json](exemplars/fw_replay_aider_qwen235b_call1.json) |
| `fw_replay_aider_qwen235b_call2` | user 0, session 3 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_aider_qwen235b_call2.json](exemplars/fw_replay_aider_qwen235b_call2.json) |
| `fw_replay_aider_qwen8b_local_call0` | user 0, session 1 | local:qwen3-8b | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_aider_qwen8b_local_call0.json](exemplars/fw_replay_aider_qwen8b_local_call0.json) |
| `fw_replay_aider_qwen8b_local_call1` | user 0, session 2 | local:qwen3-8b | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_aider_qwen8b_local_call1.json](exemplars/fw_replay_aider_qwen8b_local_call1.json) |
| `fw_replay_aider_qwen8b_local_call2` | user 0, session 3 | local:qwen3-8b | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_aider_qwen8b_local_call2.json](exemplars/fw_replay_aider_qwen8b_local_call2.json) |
| `fw_replay_gemini_cli_qwen235b_call0` | user 0, session 1 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=4096 | ✅ | [exemplars/fw_replay_gemini_cli_qwen235b_call0.json](exemplars/fw_replay_gemini_cli_qwen235b_call0.json) |
| `fw_replay_gemini_cli_qwen235b_call1` | user 0, session 2 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=4096 | ✅ | [exemplars/fw_replay_gemini_cli_qwen235b_call1.json](exemplars/fw_replay_gemini_cli_qwen235b_call1.json) |
| `fw_replay_gemini_cli_qwen235b_call2` | user 0, session 3 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=4096 | ✅ | [exemplars/fw_replay_gemini_cli_qwen235b_call2.json](exemplars/fw_replay_gemini_cli_qwen235b_call2.json) |
| `fw_replay_gemini_cli_qwen8b_local_call0` | user 0, session 1 | local:qwen3-8b | temperature=0.0, max_tokens=4096 | ✅ | [exemplars/fw_replay_gemini_cli_qwen8b_local_call0.json](exemplars/fw_replay_gemini_cli_qwen8b_local_call0.json) |
| `fw_replay_gemini_cli_qwen8b_local_call1` | user 0, session 2 | local:qwen3-8b | temperature=0.0, max_tokens=4096 | ✅ | [exemplars/fw_replay_gemini_cli_qwen8b_local_call1.json](exemplars/fw_replay_gemini_cli_qwen8b_local_call1.json) |
| `fw_replay_gemini_cli_qwen8b_local_call2` | user 0, session 3 | local:qwen3-8b | temperature=0.0, max_tokens=4096 | ✅ | [exemplars/fw_replay_gemini_cli_qwen8b_local_call2.json](exemplars/fw_replay_gemini_cli_qwen8b_local_call2.json) |
| `fw_replay_anthropic_api_qwen235b_call0` | user 0, session 1 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_anthropic_api_qwen235b_call0.json](exemplars/fw_replay_anthropic_api_qwen235b_call0.json) |
| `fw_replay_anthropic_api_qwen235b_call1` | user 0, session 2 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_anthropic_api_qwen235b_call1.json](exemplars/fw_replay_anthropic_api_qwen235b_call1.json) |
| `fw_replay_anthropic_api_qwen235b_call2` | user 0, session 3 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_anthropic_api_qwen235b_call2.json](exemplars/fw_replay_anthropic_api_qwen235b_call2.json) |
| `fw_replay_anthropic_api_qwen8b_local_call0` | user 0, session 1 | local:qwen3-8b | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_anthropic_api_qwen8b_local_call0.json](exemplars/fw_replay_anthropic_api_qwen8b_local_call0.json) |
| `fw_replay_anthropic_api_qwen8b_local_call1` | user 0, session 2 | local:qwen3-8b | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_anthropic_api_qwen8b_local_call1.json](exemplars/fw_replay_anthropic_api_qwen8b_local_call1.json) |
| `fw_replay_anthropic_api_qwen8b_local_call2` | user 0, session 3 | local:qwen3-8b | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_anthropic_api_qwen8b_local_call2.json](exemplars/fw_replay_anthropic_api_qwen8b_local_call2.json) |
| `fw_replay_langchain_summary_qwen235b_call0` | user 0, session 1 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_langchain_summary_qwen235b_call0.json](exemplars/fw_replay_langchain_summary_qwen235b_call0.json) |
| `fw_replay_langchain_summary_qwen235b_call1` | user 0, session 2 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_langchain_summary_qwen235b_call1.json](exemplars/fw_replay_langchain_summary_qwen235b_call1.json) |
| `fw_replay_langchain_summary_qwen235b_call2` | user 0, session 3 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_langchain_summary_qwen235b_call2.json](exemplars/fw_replay_langchain_summary_qwen235b_call2.json) |
| `fw_replay_langchain_summary_qwen8b_local_call0` | user 0, session 1 | local:qwen3-8b | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_langchain_summary_qwen8b_local_call0.json](exemplars/fw_replay_langchain_summary_qwen8b_local_call0.json) |
| `fw_replay_langchain_summary_qwen8b_local_call1` | user 0, session 2 | local:qwen3-8b | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_langchain_summary_qwen8b_local_call1.json](exemplars/fw_replay_langchain_summary_qwen8b_local_call1.json) |
| `fw_replay_langchain_summary_qwen8b_local_call2` | user 0, session 3 | local:qwen3-8b | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_langchain_summary_qwen8b_local_call2.json](exemplars/fw_replay_langchain_summary_qwen8b_local_call2.json) |
| `fw_replay_neutral_roll_qwen235b_call0` | user 0, session 1 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_neutral_roll_qwen235b_call0.json](exemplars/fw_replay_neutral_roll_qwen235b_call0.json) |
| `fw_replay_neutral_roll_qwen235b_call1` | user 0, session 2 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_neutral_roll_qwen235b_call1.json](exemplars/fw_replay_neutral_roll_qwen235b_call1.json) |
| `fw_replay_neutral_roll_qwen235b_call2` | user 0, session 3 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_neutral_roll_qwen235b_call2.json](exemplars/fw_replay_neutral_roll_qwen235b_call2.json) |
| `fw_replay_neutral_roll_qwen8b_local_call0` | user 0, session 1 | local:qwen3-8b | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_neutral_roll_qwen8b_local_call0.json](exemplars/fw_replay_neutral_roll_qwen8b_local_call0.json) |
| `fw_replay_neutral_roll_qwen8b_local_call1` | user 0, session 2 | local:qwen3-8b | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_neutral_roll_qwen8b_local_call1.json](exemplars/fw_replay_neutral_roll_qwen8b_local_call1.json) |
| `fw_replay_neutral_roll_qwen8b_local_call2` | user 0, session 3 | local:qwen3-8b | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/fw_replay_neutral_roll_qwen8b_local_call2.json](exemplars/fw_replay_neutral_roll_qwen8b_local_call2.json) |

## framework compaction (library default)
**Templates**

| id | source | file |
|---|---|---|
| `lib_langchain_default_summary_prompt` | langchain 1.4.3 langchain/agents/middleware/summarization.py DEFAULT_SUMMARY_PROMPT | [templates/lib_langchain_default_summary_prompt.txt](templates/lib_langchain_default_summary_prompt.txt) |

## dataset gates (step 3)
**Templates**

| id | source | file |
|---|---|---|
| `v2_update_dialogue` | framework_study/src/validate_v2.py item_turns (knowledge updates: initial value, then the update, then the question) | [templates/v2_update_dialogue.json](templates/v2_update_dialogue.json) |
| `v2_preference_filler` | framework_study/src/validate_v2.py PREF_FILLER (as in validate.v2) | [templates/v2_preference_filler.json](templates/v2_preference_filler.json) |
| `distractor_leak_check` | framework_study/src/make_distractors_v2.py LEAK_PROMPT (layer 2 of the leak check) | [templates/distractor_leak_check.txt](templates/distractor_leak_check.txt) |

**Verified exemplars**

| id | used for | model | parameters | verified | file |
|---|---|---|---|---|---|
| `v1_expanded_qwen3-235b-a22b-2507` | V1 prior strength on the expanded set (20 draws per item) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=1.0, sample_idx=0, max_tokens=12 | ✅ | [exemplars/v1_expanded_qwen3-235b-a22b-2507.json](exemplars/v1_expanded_qwen3-235b-a22b-2507.json) |
| `v1_expanded_llama3-3-70b-instruct` | V1 prior strength on the expanded set (20 draws per item) | meta.llama3-3-70b-instruct-v1:0 | temperature=1.0, sample_idx=0, max_tokens=12 | ✅ | [exemplars/v1_expanded_llama3-3-70b-instruct.json](exemplars/v1_expanded_llama3-3-70b-instruct.json) |
| `v1_expanded_gpt-oss-120b-1:0` | V1 prior strength on the expanded set (20 draws per item) | openai.gpt-oss-120b-1:0 | temperature=1.0, sample_idx=0, max_tokens=600, reasoning_effort=low | ✅ | [exemplars/v1_expanded_gpt-oss-120b-1:0.json](exemplars/v1_expanded_gpt-oss-120b-1:0.json) |
| `v1_expanded_deepseek-v3-2` | V1 prior strength on the expanded set (20 draws per item) | deepseek.v3.2 | temperature=1.0, sample_idx=0, max_tokens=12 | ✅ | [exemplars/v1_expanded_deepseek-v3-2.json](exemplars/v1_expanded_deepseek-v3-2.json) |
| `v2_expanded_rule` | V2 comprehension, rule item | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=12 | ✅ | [exemplars/v2_expanded_rule.json](exemplars/v2_expanded_rule.json) |
| `v2_expanded_preference` | V2 comprehension, preference item | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=12 | ✅ | [exemplars/v2_expanded_preference.json](exemplars/v2_expanded_preference.json) |
| `v2_expanded_update` | V2 comprehension, update item | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=12 | ✅ | [exemplars/v2_expanded_update.json](exemplars/v2_expanded_update.json) |
| `v2_expanded_neutral` | V2 comprehension, neutral item | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=12 | ✅ | [exemplars/v2_expanded_neutral.json](exemplars/v2_expanded_neutral.json) |
| `v3_expanded_first_notes` | V3 positive control on the expanded set, generation 0 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=1.0, max_tokens=400, sample_idx=0 | ✅ | [exemplars/v3_expanded_first_notes.json](exemplars/v3_expanded_first_notes.json) |
| `distractor_generation_v2` | new distractor sessions (same generator and prompt as round 1) | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.8, max_tokens=500, sample_idx=0 | ✅ | [exemplars/distractor_generation_v2.json](exemplars/distractor_generation_v2.json) |
| `distractor_leak_check` | layer-2 leak check of one flagged (distractor, item) pair | openai.gpt-oss-120b-1:0 | temperature=0.0, max_tokens=400, reasoning_effort=low | ✅ | [exemplars/distractor_leak_check.json](exemplars/distractor_leak_check.json) |

## framework study, step 4 (Llama-3.3-70B and Qwen3-235B on the expanded items)
**Templates**

| id | source | file |
|---|---|---|
| `s4_update_initial_exchange` | framework_study/src/sessions_v2.py initial_exchange (initial value of an update item, placed in seeding session 1) | [templates/s4_update_initial_exchange.json](templates/s4_update_initial_exchange.json) |

**Verified exemplars**

| id | used for | model | parameters | verified | file |
|---|---|---|---|---|---|
| `s4_replay_codex_llama_call0` | step-4 user 0, session 1 | meta.llama3-3-70b-instruct-v1:0 | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/s4_replay_codex_llama_call0.json](exemplars/s4_replay_codex_llama_call0.json) |
| `s4_replay_codex_llama_call1` | step-4 user 0, session 2 | meta.llama3-3-70b-instruct-v1:0 | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/s4_replay_codex_llama_call1.json](exemplars/s4_replay_codex_llama_call1.json) |
| `s4_probe_belief_llama` | belief probe by the family's own answer model | meta.llama3-3-70b-instruct-v1:0 | temperature=0.0, max_tokens=12 | ✅ | [exemplars/s4_probe_belief_llama.json](exemplars/s4_probe_belief_llama.json) |
| `s4_replay_codex_qwen_call0` | step-4 user 0, session 1 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/s4_replay_codex_qwen_call0.json](exemplars/s4_replay_codex_qwen_call0.json) |
| `s4_replay_codex_qwen_call1` | step-4 user 0, session 2 | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=2048 | ✅ | [exemplars/s4_replay_codex_qwen_call1.json](exemplars/s4_replay_codex_qwen_call1.json) |
| `s4_probe_belief_qwen` | belief probe by the family's own answer model | qwen.qwen3-235b-a22b-2507-v1:0 | temperature=0.0, max_tokens=12 | ✅ | [exemplars/s4_probe_belief_qwen.json](exemplars/s4_probe_belief_qwen.json) |

## Library-internal prompts (default prompts of the libraries)
| package | environment | licence | archived files |
|---|---|---|---|
| mem0ai-2.2.1 | fw-env | License-Expression: Apache-2.0 | [mem0/configs/prompts.py](library/mem0ai-2.2.1/mem0__configs__prompts.py), [mem0/memory/main.py](library/mem0ai-2.2.1/mem0__memory__main.py), [mem0/memory/utils.py](library/mem0ai-2.2.1/mem0__memory__utils.py) |
| mem0ai-1.0.11 | mem0v1-env | License-Expression: Apache-2.0 | [mem0/configs/prompts.py](library/mem0ai-1.0.11/mem0__configs__prompts.py), [mem0/memory/main.py](library/mem0ai-1.0.11/mem0__memory__main.py), [mem0/memory/utils.py](library/mem0ai-1.0.11/mem0__memory__utils.py) |
| langmem-0.0.30 | fw-env | License: MIT License | [langmem/knowledge/extraction.py](library/langmem-0.0.30/langmem__knowledge__extraction.py) |
| trustcall-0.0.39 | fw-env | License: MIT | [trustcall/_base.py](library/trustcall-0.0.39/trustcall___base.py) |
| llama-index-core-0.14.25 | fw-env | License-Expression: MIT | [llama_index/core/memory/memory_blocks/fact.py](library/llama-index-core-0.14.25/llama_index__core__memory__memory_blocks__fact.py) |
| langchain-1.4.3 | fw-env | License: MIT | [langchain/agents/middleware/summarization.py](library/langchain-1.4.3/langchain__agents__middleware__summarization.py) |
| nemori-0.2.0@d2a6dff | nemori-env | License: (see METADATA) | [nemori/llm/prompts.py](library/nemori-0.2.0@d2a6dff/nemori__llm__prompts.py), [nemori/llm/generators/segmenter.py](library/nemori-0.2.0@d2a6dff/nemori__llm__generators__segmenter.py), [nemori/llm/generators/episode.py](library/nemori-0.2.0@d2a6dff/nemori__llm__generators__episode.py), [nemori/llm/generators/semantic.py](library/nemori-0.2.0@d2a6dff/nemori__llm__generators__semantic.py), [nemori/llm/generators/merger.py](library/nemori-0.2.0@d2a6dff/nemori__llm__generators__merger.py) |

## Library prompts as actually sent (live capture)
Each library ran on the first 3 sessions of framework-study user 0 plus one query; every request it sent was recorded inside the process (httpx / httpx2 transport) by `capture_library_live.py`. Prompts that only fire under conditions not reached in 3 sessions (e.g. LlamaIndex fact condensation beyond max_facts) are covered by the archived source files above.

| library | requests | distinct system prompts / tool schemas | files |
|---|---|---|---|
| mem0 | 3 | 1 | [captured/mem0.jsonl](captured/mem0.jsonl), [captured/mem0_distinct.json](captured/mem0_distinct.json) |
| mem0_v1 | 6 | 2 | [captured/mem0_v1.jsonl](captured/mem0_v1.jsonl), [captured/mem0_v1_distinct.json](captured/mem0_v1_distinct.json) |
| langmem | 3 | 3 | [captured/langmem.jsonl](captured/langmem.jsonl), [captured/langmem_distinct.json](captured/langmem_distinct.json) |
| llamaindex_facts | 3 | 1 | [captured/llamaindex_facts.jsonl](captured/llamaindex_facts.jsonl), [captured/llamaindex_facts_distinct.json](captured/llamaindex_facts_distinct.json) |
| llamaindex_facts_default | 3 | 1 | [captured/llamaindex_facts_default.jsonl](captured/llamaindex_facts_default.jsonl), [captured/llamaindex_facts_default_distinct.json](captured/llamaindex_facts_default_distinct.json) |
| nemori | 10 | 3 | [captured/nemori.jsonl](captured/nemori.jsonl), [captured/nemori_distinct.json](captured/nemori_distinct.json) |

Product compaction prompts are verbatim copies of the upstream sources in `framework_study/prompts/` (Codex @822e58c, OpenHands @6f8c38d, Aider @5dc9490, Gemini CLI @fb972b2; Anthropic API documented default); the framing each adapter adds is in `templates/fw_compactor_*.json`.
