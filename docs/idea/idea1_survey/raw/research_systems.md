# Research agents with memory / experience accumulation: memory lifecycle survey

Checked 2026-10-06. Repos cloned (depth 1) under `scratchpad/survey/repos/` (Memory-R1, AgeMem, Memory-Collapse-Eval are under `repos/_research/`). Papers were downloaded to `scratchpad/survey/papers/` and searched as text.
Scope: write / update / forget / retrieve. The focus is whether an LLM repeatedly reads and rewrites its own stored memory (an iterated rewrite chain, so content can drift toward the model prior) and whether an LLM decides deletion. Security topics are out of scope and not covered.

Legend for ITERATED REWRITE CHAIN:
- YES: memory text v(n+1) = LLM(v(n), new evidence), over many steps.
- PARTIAL: old memory text conditions new text, but old text is not replaced, or the chain stays inside one episode, or only some entries are rewritten.
- NO: memory is append-only, or it is regenerated from raw evidence and never from earlier memory text.

---

### Generative Agents (Park et al., UIST 2023, arXiv 2304.03442)
- Type: research system (multi-agent social simulation, "Smallville")
- Checked: 2026-10-06, `joonspk-research/generative_agents` @ fe05a71 (last commit 2023-08-11), Apache-2.0
- Sources:
  - Paper §4.1 (retrieval), §4.2 (reflection). Read from the PDF text.
  - `reverie/backend_server/persona/cognitive_modules/reflect.py` L21-35 (focal points), L38-55 (insights), L99-155 (run_reflect, trigger)
  - `cognitive_modules/retrieve.py` L132-267
  - `cognitive_modules/plan.py` L408-458 (`revise_identity`), L484-485
  - `cognitive_modules/perceive.py` L178-179
  - `memory_structures/scratch.py` L60-63
  - `memory_structures/associative_memory.py` (add_event/add_thought/add_chat)
  - `persona/prompt_template/v3_ChatGPT/{insight_and_evidence_v1, generate_focal_pt_v1, poignancy_event_v1}.txt`
- WRITE:
  - Every perceived event or chat is appended to the associative memory ("memory stream") as a node: an LLM-generated (s,p,o) triple, an embedding, and an LLM-rated importance (1-10). Prompt: "On the scale of 1 to 10, where 1 is purely mundane ... and 10 is extremely poignant ..., rate the likely poignancy...".
  - Reflections, post-conversation "planning thoughts" and "memos" are also appended as `thought` nodes, each with evidence pointers (node ids).
- UPDATE:
  - The memory stream is append-only. Nodes are never edited except for `last_accessed`, which retrieval sets (retrieve.py L267).
  - One exception is a true in-place rewrite. At each "New day", `revise_identity` asks the LLM to produce a new `scratch.currently` (the persona's status line) from the previous `currently` plus two LLM notes summarizing retrieved memories: "Given the above, write {name}'s status for {date} that reflects {name}'s thoughts at the end of {prev date}... Follow this format: Status: <new status>" (plan.py L435-448). The old value is overwritten.
- FORGET / EXPIRE: none. Each node gets `expiration = created + 30 days` (reflect.py L124), but no code reads it for filtering or deletion (grep shows it is only stored and serialized). Forgetting is soft only, through recency decay in retrieval scoring. Rule-based.
- RETRIEVE:
  - Score = recency + importance + relevance, each min-max normalized.
  - Paper: decay 0.995 per sandbox game hour since last retrieval; "all αs are set to 1".
  - Code differs: recency = 0.99^rank over nodes sorted by `last_accessed` (retrieve.py L145), weights `gw = [0.5, 3, 2]` (L244). Relevance is embedding cosine to a focal point. Top-30 per focal point (`n_count=30`).
- COMPACTION TRIGGER:
  - Reflection runs when the accumulated importance of newly perceived events exceeds 150. `importance_trigger_max=150`; the counter is decremented per event in perceive.py L178. The paper says this is "roughly two or three times a day".
  - `revise_identity` runs once per simulated day.
  - Planning thought and memo run at the end of each conversation.
- ITERATED REWRITE CHAIN?: PARTIAL.
  - (a) Reflections are new nodes, never rewritten. But focal points and reflection inputs come from `seq_event + seq_thought`, so reflections are built on earlier reflections. The paper describes these as "trees of reflections ... non-leaf nodes represent thoughts that become more abstract and higher-level". This is abstraction stacking, not overwriting; the original observations stay in the stream.
  - (b) `scratch.currently` is a genuine daily rewrite chain: currently(t+1) = LLM(currently(t), notes). It is a single short identity/status string that conditions planning, so drift there persists.
- WHICH CHANNEL: transformation (reflections stack abstractions; `currently` is rewritten). Selection is only implicit, through retrieval scoring (LLM-rated importance affects what is retrieved, never what is deleted).
- DEFAULT PROMPTS: `reverie/backend_server/persona/prompt_template/v2|v3_ChatGPT/*.txt` (file-based, replaceable). `revise_identity` prompts are hard-coded in plan.py L415-441. Reflection prompt: "What !<INPUT 1>! high-level insights can you infer from the above statements? (example format: insight (because of 1, 5, 3))". Focal points: "Given only the information above, what are !<INPUT 1>! most salient high-level questions we can answer about the subjects grounded in the statements?"
- RUNNABLE FOR EXPERIMENTS: Open source, but uses the legacy `openai` (<1.0) SDK with gpt-3.5-turbo / gpt-4 / text-davinci and OpenAI embeddings (gpt_structure.py). A local model can be pointed to via `openai.api_base`, but the prompts rely on fragile output parsing and the full simulation is heavy. The reflection and `revise_identity` logic is small and easy to extract.
- MULTI-AGENT: Each persona has a private memory stream. Information spreads only through perceived events and conversations, which each agent stores in its own stream. There is no shared store.
- UNCERTAIN: Whether the released simulation logs show drift in `currently` over many days is unverified (not inspected).

### MemoryBank / SiliconFriend (Zhong et al., AAAI 2024, arXiv 2305.10250)
- Type: research system (long-term companion chatbot memory)
- Checked: 2026-10-06, `zhongwanjun/MemoryBank-SiliconFriend` @ cf61c41 (2023-05-24), MIT
- Sources:
  - Paper §2.1-2.3 (PDF text)
  - `memory_bank/summarize_memory.py` L67-147
  - `memory_bank/memory_retrieval/forget_memory.py` L20-36, L63-71, L83-148, L353
  - `utils/memory_utils.py` L63-70
  - `SiliconFriend-ChatGLM-BELLE/cli_demo.py` L176-180
  - `utils/prompt_utils.py` L116-123
- WRITE:
  - Raw dialogue turns (query/response) are stored per user and date in a JSON file. These are verbatim, not LLM-extracted.
  - Daily event summary and daily personality analysis are produced by an LLM (gpt-3.5-turbo). Each is written once per date: generated only if missing (`his_flag` / `person_flag`, L128-137).
- UPDATE:
  - Global `overall_history` and `overall_personality` are regenerated each time summarization runs, as LLM(all daily summaries). The previous global summary is not an input ("Please provide a highly concise summary of the following event...", L80; "Please provide a highly concise and general summary of the user's personality and the most appropriate response strategy...", L91).
  - Daily summaries are not updated after their dialogues are forgotten.
- FORGET / EXPIRE:
  - Ebbinghaus-style stochastic forgetting by rule. At load time, each dialogue turn is kept with probability R = exp(-t/S) and otherwise popped from the JSON (L115-128). t = days since last recall; S = memory strength, initialized to 1 and incremented by 1 on retrieval, with t reset (L63-71; paper: "We increase S by 1 and reset t to 0").
  - A day's summary is removed only when all of that day's turns are gone (L129-131).
  - Code bug: `math.exp(-t / 5*S)` parses as exp(-(t/5)*S), so higher strength forgets faster, the opposite of the paper.
  - Who decides: rule plus RNG. No LLM.
- RETRIEVE: Dense retrieval (LangChain FAISS, top-k=6) over turns and daily summaries. The global summary and global personality are always injected into the prompt.
- COMPACTION TRIGGER: User-triggered at session start ("Would you like to summarize your memory?", cli_demo L178-180) or by a GUI button. Forgetting runs when the memory index is (re)built.
- ITERATED REWRITE CHAIN?: NO. The hierarchy is raw → daily summary (written once) → global summary (recomputed from the daily summaries each time, never from the previous global summary). The chain depth is fixed at 2, and the global summary is re-derived rather than rewritten from itself.
- WHICH CHANNEL: transformation (summaries) plus rule-based selection (stochastic forgetting). The LLM does not select.
- DEFAULT PROMPTS: Hard-coded strings in `memory_bank/summarize_memory.py` (CN and EN). Replaceable by editing.
- RUNNABLE FOR EXPERIMENTS: Open source but dated (legacy openai SDK, old LangChain). The summarizer can be redirected via `openai.api_base`. ChatGLM/BELLE local chat models are supported.
- MULTI-AGENT: N/A. Memory is per user.
- UNCERTAIN: Whether the paper's reported experiments used the buggy exponent is unverified.

### Reflexion (Shinn et al., NeurIPS 2023, arXiv 2303.11366)
- Type: research system (verbal RL by self-reflection across retries of the same task)
- Checked: 2026-10-06, `noahshinn/reflexion` @ 218cf0e (2025-01-13), MIT
- Sources:
  - `alfworld_runs/generate_reflections.py` L12-47 (WebShop identical: `webshop_runs/generate_reflections.py`)
  - `alfworld_runs/alfworld_trial.py` L48
  - `hotpotqa_runs/agents.py` L23-30, L105-118
  - `hotpotqa_runs/prompts.py` L21, L113-124
  - `programming_runs/reflexion.py` L57-81
- WRITE: After a failed trial, the LLM writes one reflection (plan) from the trajectory. ALFWorld prompt: "You were unsuccessful in completing the task. Do not summarize your environment, but rather think about the strategy and path you took... Devise a concise, new plan of action that accounts for your mistake..." HotpotQA: "In a few sentences, Diagnose a possible reason for failure and devise a new, concise, high level plan that aims to mitigate the same failure."
- UPDATE: Append-only per-task list (`env['memory'] += [reflection]`). HotpotQA strategy `LAST_ATTEMPT_AND_REFLEXION` replaces the list with only the newest reflection (agents.py L116-118).
- FORGET / EXPIRE: Capacity eviction by rule. Only the last 3 reflections are shown, both to the actor (`memory[-3:]`) and to the reflection generator (paper: Ω "usually set to 1-3"). No LLM deletion.
- RETRIEVE: Full context. The last ≤3 reflections for the same task are prepended.
- COMPACTION TRIGGER: End of every failed trial.
- ITERATED REWRITE CHAIN?: PARTIAL. In ALFWorld/WebShop the reflection prompt includes "Plans from past attempts: Trial #i: ...", so reflection n is conditioned on reflections n-3..n-1. Old ones are not overwritten, though, and memory is per task (it resets for new tasks), so chains are short (≤ ~10 trials).
- WHICH CHANNEL: transformation (new reflection conditioned on old). Selection is a rule-based sliding window.
- DEFAULT PROMPTS: `alfworld_runs/generate_reflections.py` (inline) plus `reflexion_few_shot_examples.txt`; `hotpotqa_runs/prompts.py`; `programming_runs/generators/*`. Replaceable.
- RUNNABLE FOR EXPERIMENTS: Open source. ALFWorld uses text-davinci-003 (completion) via legacy openai, so it needs porting to a chat or OpenAI-compatible endpoint.
- MULTI-AGENT: N/A.
- UNCERTAIN: none material.

### ExpeL (Zhao et al., AAAI 2024, arXiv 2308.10144)
- Type: research system (cross-task insight extraction + trajectory recall)
- Checked: 2026-10-06, `LeapLabTHU/ExpeL` @ e41ec9a (2024-12-20), Apache-2.0
- Sources:
  - Paper §"Insights extraction" and Fig. 2 (PDF text)
  - `prompts/templates/human.py` L21-66
  - `agent/expel.py` L202-243 (critique prompt builder), L330-400 (extraction loop), L666-742 (`parse_rules`, `update_rules`)
  - `configs/agent/expel.yaml`
- WRITE:
  - Training phase: Reflexion-style retries (`max_reflection_depth: 3`) collect success/failure trajectories.
  - Then the LLM (paper default gpt-4-0613 for insights) iterates over (success, fail) pairs of the same task, and over chunks of `success_critique_num: 8` successes. Each call sees the current insight list and outputs operations.
- UPDATE: Merge with ops. Paper names: ADD / EDIT / UPVOTE / DOWNVOTE. Code names: ADD / EDIT / AGREE / REMOVE. Prompt: "AGREE (if the existing rule is strongly relevant for the task), REMOVE (if one existing rule is contradictory or similar/duplicated to other existing rules), EDIT (if any existing rule is not general enough or can be enhanced, rewrite and improve it), ADD (add new rules that are very different from existing rules...)... Do at most 4 operations and each existing rule can only get a maximum of 1 operation." EDIT replaces the rule text in place with LLM output (expel.py L735-737).
- FORGET / EXPIRE:
  - Vote counter: ADD sets count=2; AGREE +1; EDIT +1; REMOVE -1 (-3 when the list is full, `max_num_rules: 20`). Rules with count ≤0 are dropped (L728-741).
  - When full, the prompt adds: "Focus on REMOVE rules first, and stop ADD rule unless the new rule is VERY insightful..."
  - Who decides: the LLM votes and a rule threshold executes. This is LLM-driven selection.
- RETRIEVE:
  - All insights (sorted by count) go into the eval prompt in full.
  - Successful trajectories are retrieved as few-shots by embedding similarity (`fewshot_strategy: task_similarity`, all-mpnet-base-v2, kNN).
- COMPACTION TRIGGER: Offline, sequentially, after the experience-gathering phase (one pass over pairs and chunks). Not during evaluation.
- ITERATED REWRITE CHAIN?: YES (moderate). Over dozens to hundreds of sequential calls, the LLM reads the full current rule list and may EDIT any rule, so a rule's text can be rewritten repeatedly (each EDIT also raises its count, which protects it). Raw trajectories stay in the experience pool, separate from the insights.
- WHICH CHANNEL: both. Transformation (EDIT, ADD) and selection (REMOVE votes leading to deletion).
- DEFAULT PROMPTS: `prompts/templates/human.py` (`FORMAT_RULES_OPERATION_TEMPLATE`, `CRITIQUE_SUMMARY_SUFFIX`, compare/all_success templates) plus per-benchmark system prompts in `prompts/{hotpotQA,alfworld,webshop,fever}.py`. Replaceable.
- RUNNABLE FOR EXPERIMENTS: Open source. LangChain `ChatOpenAI` (models/llm.py), so it can target an OpenAI-compatible base URL with a config change. Hydra configs.
- MULTI-AGENT: N/A.
- UNCERTAIN: The average number of EDITs per surviving rule in the released logs was not measured.

### Dynamic Cheatsheet (Suzgun et al., 2025, arXiv 2504.07952)
- Type: research system (test-time learning with an evolving text memory)
- Checked: 2026-10-06, `suzgunmirac/dynamic-cheatsheet` @ 5cfe3c3 (2026-03-12), MIT
- Sources:
  - Paper §2.1.2 (PDF text: "Mi+1 = Cur(Mi, xi, ỹi) ... Cur does not have access to ground-truth labels; so, it has to assess the correctness and efficiency of the solutions by itself")
  - `prompts/curator_prompt_for_dc_cumulative.txt`, `prompts/curator_prompt_for_dc_retrieval_synthesis.txt`
  - `dynamic_cheatsheet/language_model.py` L386-455 (Cumulative), L503-545 (RetrievalSynthesis)
  - `dynamic_cheatsheet/utils/extractor.py` L62-80
  - `run_benchmark.py` L170-187
- WRITE: After each query, the generator answers; then the curator LLM gets (previous cheatsheet, question, model answer) and emits a complete new cheatsheet in a `<cheatsheet>` block.
- UPDATE:
  - Full in-place rewrite of the whole memory every step.
  - Prompt: "Before updating the cheatsheet, however, you should first assess the correctness of the provided solution..."; "Rather than deleting old content and writing new content each time, consider ways to maintain table content and synthesize information from multiple solutions"; "N.B. Keep in mind that once the cheatsheet is updated, any previous content not directly included will be lost and cannot be retrieved. Therefore, make sure to explicitly copy any (or all) relevant information from the previous cheatsheet..."; "The cheatsheet can be as long as circa 2000-2500 words."
  - Entries carry an LLM-maintained "** Count:" usage counter.
  - If parsing fails, the old cheatsheet is kept (extractor.py).
- FORGET / EXPIRE: Implicit LLM deletion. Anything the curator does not copy forward is lost. The RS prompt says: "Discard redundant, trivial, or highly problem-specific details that do not generalize well." The word budget creates capacity pressure. Who decides: the LLM.
- RETRIEVE:
  - DC-Cu: the whole cheatsheet goes into the generator prompt.
  - DC-RS: embedding retrieval of the top-k similar past (input, output) pairs; the curator then synthesizes a query-specific cheatsheet from (previous cheatsheet + retrieved pairs + next input) before generation.
- COMPACTION TRIGGER: Every query (Cumulative: after answering; RS: before answering).
- ITERATED REWRITE CHAIN?: YES (canonical). v(n+1) = LLM(v(n), x_n, ŷ_n) for every test item, without ground truth. The model self-judges correctness, so its own errors and priors can enter and be re-copied. No raw-episode store backs the cheatsheet in DC-Cu.
- WHICH CHANNEL: both. Transformation (rewrite and synthesis) and selection (omission = deletion), entangled in one call.
- DEFAULT PROMPTS: `prompts/curator_prompt_for_dc_cumulative.txt`, `prompts/curator_prompt_for_dc_retrieval_synthesis.txt`, `prompts/generator_prompt.txt`. Passed by path (`--cheatsheet_prompt_path`), so fully replaceable.
- RUNNABLE FOR EXPERIMENTS: Yes. `text_generation/UnifiedLLMClient` supports OpenAI-compatible `base_url` (together, deepseek, ollama mapped to the OpenAI client, language_model.py L18-40). A cheatsheet can be seeded via `--initialize_cheatsheet_path`. This is the best minimal testbed for a pure rewrite chain.
- MULTI-AGENT: N/A.
- UNCERTAIN: none material.

### Agent Workflow Memory (AWM) (Wang et al., 2024, arXiv 2409.07429)
- Type: research system (induces reusable web-navigation workflows)
- Checked: 2026-10-06, `zorazrw/agent-workflow-memory` @ 8c0ff8c (2025-12-22), Apache-2.0
- Sources:
  - Paper §2.3 (WebFetch of arXiv HTML: online "M^t + {w^t} → M^{t+1}"; success judged by an LM evaluator, Pan et al. 2024)
  - `webarena/pipeline.py` L18-40
  - `webarena/induce_prompt.py` L86-160
  - `webarena/prompt/instruction.txt`
  - `mind2web/pipeline.py` (`online()`), `mind2web/online_induction.py`, `mind2web/prompt/instruction_action.txt`
- WRITE: After each test task (WebArena) or each `induce_steps` batch (Mind2Web), an LLM induces workflows from past trajectories. Prompt: "extract the common workflows... find the repetitive subset of actions across multiple tasks... Do not generate similar or overlapping workflows... Represent the non-fixed elements... with descriptive variable names."
- UPDATE:
  - The paper describes append (M + W → M').
  - The code regenerates the whole workflow file from scratch: `induce_prompt.py` collects all autoeval-successful result dirs, randomly samples `num_samples=1` trajectory per intent template, calls the LLM (temperature 1.0), and opens the output file with `'w'`, overwriting it.
  - The LLM never sees the previous workflows. This is re-induction from raw evidence, not an edit of memory.
- FORGET / EXPIRE: No explicit deletion. Old workflows vanish implicitly if the re-induction (with random per-template sampling) does not reproduce them. Who decides: the LLM, implicitly, through what it regenerates.
- RETRIEVE: Full text of the website's workflow file is injected into the agent prompt. `mind2web/workflow/retrieve.py` provides an optional FAISS retrieval variant.
- COMPACTION TRIGGER: After every task (WebArena online) or every N examples (Mind2Web `--induce_steps`). The offline variant induces once from training data.
- ITERATED REWRITE CHAIN?: NO in the official code: each version = LLM(sample of raw successful trajectories), with no conditioning on the previous workflow text. There is regeneration churn, though: the same experience pool can yield different memories at each step (sampling + temperature 1.0). Earlier wrong judgments persist because autoeval labels gate the pool. The Memory-Collapse paper still reports AWM degrading on WebShop ("collapse-by-accretion", its §H.1.2).
- WHICH CHANNEL: transformation (abstraction of trajectories). Selection is implicit through regeneration plus LLM-judge filtering of which trajectories enter the pool.
- DEFAULT PROMPTS: `webarena/prompt/{instruction.txt, one_shot.txt}`, `mind2web/prompt/{instruction_action.txt, instruction_abstract.txt, one_shot_*.txt}`. Passed by path, so replaceable.
- RUNNABLE FOR EXPERIMENTS: Open source. Uses `openai.OpenAI()`, which honors `OPENAI_BASE_URL`, but argparse restricts `--model` choices (gpt-3.5/gpt-4/gpt-4o) and needs a one-line edit. WebArena requires the Docker environment.
- MULTI-AGENT: N/A.
- UNCERTAIN: Code/paper discrepancy, observed in the code (unverified whether the paper's experiments used the overwrite path): (a) WebArena code overwrites rather than appends; (b) `mind2web/online_induction.py` reads all result files with no success filter, while the paper says only LM-judged successes are used.

### ReasoningBank (Ouyang et al., ICLR 2026, arXiv 2509.25140)
- Type: research system (reasoning-strategy memory from successes and failures)
- Checked: 2026-10-06, `google-research/reasoning-bank` @ ed80611 (2026-05-18), Apache-2.0
- Sources:
  - Paper App. A.1-A.2 (WebFetch of arXiv HTML)
  - `WebArena/induce_memory.py` (main)
  - `WebArena/prompts/memory_instruction.py` L15-61 (`SUCCESSFUL_SI`, `FAILED_SI`), L63+ (`PARALLEL_SI` for MaTTS)
  - `WebArena/memory_management.py` L138-214
- WRITE: After each task, the trajectory gets an LLM-as-judge success/failure label (or GT reward). The LLM then extracts at most 3 memory items (Title / Description / Content), using a different prompt for successes and failures. Examples: "You must first think why the trajectory is successful, and then summarize the insights... Prefer concrete, actionable procedures over abstract principles. Do not embed specific product names, queries, or literal string contents from the task." / "...reflect and think why the trajectory failed, and then summarize what lessons you have learned...". Temperature 1.0.
- UPDATE: Append-only JSONL (`open(output_path, 'a')`). Paper: "a simple addition operation"; "We deliberately keep the memory usage pipeline simple, avoiding additional complexity in retrieval or consolidation". No merge, dedup or edit.
- FORGET / EXPIRE: none.
- RETRIEVE: Embedding similarity of the current query to past queries (gemini-embedding-001 or Qwen3-Embedding-8B, instruction-aware). Default top-k=1 past experience; its memory items are injected.
- COMPACTION TRIGGER: none (extraction per task only). MaTTS (parallel/sequential scaling) extracts from multiple trajectories of one query via self-contrast (`PARALLEL_SI`, "at most 5 memory items").
- ITERATED REWRITE CHAIN?: NO. Each item is written once from one trajectory and never re-read by the extractor. Indirect coupling exists: retrieved memories influence future trajectories, which then produce new items (a behavioral loop, not a text-rewrite loop).
- WHICH CHANNEL: transformation (single-pass abstraction) only. No selection.
- DEFAULT PROMPTS: `WebArena/prompts/memory_instruction.py` (Python constants). Replaceable. The file also has AWM baseline prompts.
- RUNNABLE FOR EXPERIMENTS: Open source. Clients for GPT, Gemini and Claude-on-Vertex (`utils/clients.py`); embeddings require Vertex AI or the local Qwen3-Embedding-8B. Adding an OpenAI-compatible local client needs a small edit. A SWE-Bench variant is also included.
- MULTI-AGENT: N/A.
- UNCERTAIN: The SWE-Bench memory pipeline was not inspected.

### Memory-R1 (Yan et al., 2025, arXiv 2508.19828; ACL 2026)
- Type: research system (RL-trained memory manager + answer agent)
- Checked: 2026-10-06, `yansikuan/memory-r1` @ 9c413a2 (2025-09-10), Apache-2.0. The repo contains only README, LICENSE and figures: "Status: Code coming soon". No weights were found on Hugging Face (searched "memory-r1", "Memory-R1").
- Sources: arXiv HTML v4 (WebFetch); paper App. C.1 prompt; repo README
- WRITE: An LLM (GPT-4o-mini) extracts facts from each dialogue turn. The Memory Manager (a fine-tuned LLaMA-3.1-8B / Qwen-2.5 3B-14B) receives the new facts plus similarity-retrieved old memories and emits one operation per fact.
- UPDATE: Learned policy over ADD / UPDATE / DELETE / NOOP, mem0-style. UPDATE rewrites a memory entry: "keep the same ID and preserve old_memory"; "keep the version with more detail". Example: "Likes cheese pizza" + "Loves cheese pizza" consolidated into one entry.
- FORGET / EXPIRE: LLM-issued DELETE. Prompt: "If the retrieved facts contain information that contradicts the memory, delete it." The policy is RL-trained (PPO/GRPO) with reward = exact match of the downstream Answer Agent's answer (152 LoCoMo training QA pairs). Who decides: a learned LLM policy.
- RETRIEVE: RAG retrieves 60 candidate memories per question. The Answer Agent then performs "memory distillation" (an LLM filter) before answering.
- COMPACTION TRIGGER: Every dialogue turn (online).
- ITERATED REWRITE CHAIN?: PARTIAL to YES at entry level. An entry can be UPDATEd many times across sessions, each time from its prior text plus a new fact. RL rewards QA accuracy, not fidelity of the entry text.
- WHICH CHANNEL: both. Transformation (UPDATE) and learned selection (DELETE/NOOP).
- DEFAULT PROMPTS: Appendix C.1 of the paper only. Not in a repo.
- RUNNABLE FOR EXPERIMENTS: Not currently. No code and no weights. Reproduction would require reimplementation on VERL. The LoCoMo data is CC BY-NC 4.0.
- MULTI-AGENT: Two agents (manager, answerer) over one shared memory bank.
- UNCERTAIN: The release status after 2025-09-10 was checked only via GitHub repo contents on 2026-10-06 (still placeholder).

### MEM1 (Zhou et al., 2025, arXiv 2506.15841)
- Type: research system (RL-trained constant-memory agent; memory = internal state)
- Checked: 2026-10-06, `MIT-MI/MEM1` @ 2609aef (2026-01-03), MIT. Weights: `Mem-Lab/Qwen2.5-7B-RL-RAG-Q2-EM-Release` on HF; the HF card declares no license (UNVERIFIED terms; base Qwen2.5-7B is Apache-2.0).
- Sources:
  - README
  - `Mem1/gen_data/data_process/qa_search_train_merge_multi.py` L43-58 (prompt)
  - `Mem1/inference/data_pipelines.py` L110-150
  - `Mem1/train/verl/utils/reward_score/qa_em.py`
- WRITE / UPDATE: Each turn the model emits `<think>` containing the updated internal state, then a search or answer. Prompt: "Perform reasoning and update a cumulative, concise summary within <think> ... </think>. This acts as persistent memory and must include all essential information from previous <think> and <information> tags." All previous context is then deleted (`cur_obs = ""`), so the next turn sees only the prompt, the latest state and the new observation.
- FORGET / EXPIRE: Implicit. Whatever the model does not carry into the new `<think>` is gone. Learned (PPO, exact-match outcome reward via `qa_em.py`). Who decides: the learned policy.
- RETRIEVE: The state is always in context. External search is an environment action, not memory.
- COMPACTION TRIGGER: Every turn.
- ITERATED REWRITE CHAIN?: YES, within an episode: state(t+1) = π(state(t), obs(t)) for up to ~16+ objectives and turns. Not across episodes (no persistent cross-task memory). RL pressure keeps answer-relevant content.
- WHICH CHANNEL: both, entangled (rewrite = selection).
- DEFAULT PROMPTS: Prompt templates in `Mem1/gen_data/data_process/*.py` (baked into the training data, so changing them shifts off-policy from the trained weights).
- RUNNABLE FOR EXPERIMENTS: Yes. vLLM serving plus `inference/generate_rollout.py --use_mem1`. Weights are on HF.
- MULTI-AGENT: N/A.
- UNCERTAIN: The HF weights' license; the paper's exact reward shaping beyond EM was not read.

### MemAgent (H. Yu et al., 2025, arXiv 2507.02259)
- Type: research system (RL-trained overwrite memory for long-context reading)
- Checked: 2026-10-06, `BytedTsinghua-SIA/MemAgent` @ ef4219b (2026-05-12), Apache-2.0. Weights `BytedTsinghua-SIA/RL-MemoryAgent-7B` and `-14B` on HF, license apache-2.0 (HF card), base Qwen2.5-Instruct.
- Sources:
  - README L45-46 (RLVR, extended DAPO "Multi-conv RL")
  - `recurrent/impls/memory.py` L114-140
  - `quickstart.py` L23-110
- WRITE / UPDATE: The document is read chunk by chunk; per chunk, the memory is fully overwritten. Prompt: "Please read the provided section carefully and update the memory with the new information that helps to answer the problem. Be sure to retain all relevant details from the previous memory while adding any new, useful information." Fixed memory budget (`RECURRENT_MAX_NEW = 1024` tokens).
- FORGET / EXPIRE: Implicit, by omission under the token cap. Learned (verifiable-reward RL on final answer, strict `\boxed{}` EM verifier). Who decides: the learned policy.
- RETRIEVE: Memory is always in context; the final answer comes from memory only (`TEMPLATE_FINAL_BOXED`).
- COMPACTION TRIGGER: Every chunk (e.g., every ~5K tokens of input).
- ITERATED REWRITE CHAIN?: YES, within one task: hundreds of sequential overwrites for 1M+ token inputs. Not across tasks.
- WHICH CHANNEL: both, entangled.
- DEFAULT PROMPTS: `TEMPLATE` / `TEMPLATE_FINAL_BOXED` in `recurrent/impls/memory.py` and `quickstart.py`.
- RUNNABLE FOR EXPERIMENTS: Yes. `quickstart.py` talks to any OpenAI-compatible server (vLLM). Weights are Apache-2.0. A good controlled testbed for "untrained vs RL-trained rewriter" drift on a long rewrite chain.
- MULTI-AGENT: N/A.
- UNCERTAIN: none material.

### AgeMem (Yu et al., 2026, arXiv 2601.01885; ACL 2026)
- Type: research system (RL-trained unified LTM + STM management via tools)
- Checked: 2026-10-06, `y1y5/AgeMem` @ 98f563f (2026-04-24). No LICENSE file in the repo and none in the GitHub API; `pyproject.toml` (Trinity-RFT fork) declares the Apache classifier (UNVERIFIED for AgeMem additions). No trained weights found on HF (searched "AgeMem").
- Sources:
  - arXiv HTML v1 §3.2-3.5 and App. A.1 (WebFetch)
  - README
  - `AgeMem_code_agentscope/agent.py` L245-530
  - `AgeMem_code_agentscope/prompts.py`
  - `trinity/common/workflows/memory_context/{utils.py L60-140, memory_store.py}`
- WRITE: The agent policy calls `Add_memory(content, metadata)`. The content is written by the policy LLM itself.
- UPDATE: `Update_memory(memory_id, content)` replaces an entry's content with policy-written text (after a `Retrieve_memory` to get the ID). Short-term memory has `Summary_context(span)`, where an LLM summary replaces messages in the context ("compress the given conversation span into a concise summary that preserves all important information..."), and `Filter_context`.
- FORGET / EXPIRE: `Delete_memory(memory_id)`, chosen by the RL-trained policy. The reward includes memory-management terms (fraction of stored entries judged high-quality, "meaningful update or delete operations") plus task reward from an LLM judge. Who decides: the learned policy plus an LLM-judge reward.
- RETRIEVE: Embedding cosine top-k over the vector store via the `Retrieve_memory` tool.
- COMPACTION TRIGGER: Whenever the policy calls the tools. Training is a 3-stage curriculum within one trajectory: casual interaction → distractors → QA; LTM persists across stages and context is reset.
- ITERATED REWRITE CHAIN?: PARTIAL. Entries may be UPDATEd repeatedly, and `Summary_context("all")` can summarize earlier summaries. Both happen within a training or eval episode; cross-episode persistence is not described.
- WHICH CHANNEL: both. Transformation (Update, Summary) and learned selection (Delete, Filter).
- DEFAULT PROMPTS: Tool schemas in `trinity/common/workflows/memory_context/utils.py`; summary/filter prompts in `AgeMem_code_agentscope/prompts.py`.
- RUNNABLE FOR EXPERIMENTS: Training code available (Trinity-RFT, Qwen2.5-7B / Qwen3-4B). No released checkpoints, so one must train. The standalone AgentScope example uses a separate chat client (default `qwen-max`) for summarization.
- MULTI-AGENT: N/A.
- UNCERTAIN: License; whether `Summary_context` at training time uses the policy model or a separate model.

### "Useful Memories Become Faulty When Continuously Updated by LLMs" (Zhang, Lin, Wu, Sun, Li, Li, Peng; arXiv 2605.12978 v1 2026-05-13, v2 2026-08-29; UIUC / Tsinghua IIIS)
- Type: empirical study + benchmark harness (Memory-Collapse-Eval)
- Checked: 2026-10-06
  - Paper v1 and v2 HTML were downloaded and text-searched.
  - Code: `DylanZSZ/Memory-Collapse-Eval` @ adf347f (2026-08-15). Code is MIT (`LICENSE`); data is CC BY 4.0 (`LICENSE-DATA`); paper is CC BY 4.0. Vendored AgentGym fork is MIT.
- Sources:
  - Paper §3-6, Table 5, App. B (prompts), D (failure modes), L.2/L.6/L.7
  - `agentmem/controller/methods.py` (DC L262-475, DC-GT L340-412, AWM L536-600, ACE L607-1080, Agent KB L1083+)
  - `arc/solver/prompts/macro_action_prompt.py`
  - `arc/memory/providers/strategy_buffer/prompts/extract_strategy_prompt.py` L22-290
  - `docs/propworld.md`
  - `agentmem/VENDORED.md`
  - `README.md` L245-280
- WHAT IS STUDIED (consolidation operators):
  - (1) Existing lesson-style consolidators, re-implemented "faithfully": CLIN, AWM, Dynamic Cheatsheet (incl. DC-GT variant that is told "the verified correct answer is GIVEN to you as ground truth — do NOT re-judge"), ACE (generator / reflector / curator + embedding-similarity merge at threshold 0.75, prompt "Merge them into ONE bulletpoint..."). The repo has 14 methods behind one interface: ACE, AWM, A-MEM, Agent KB, DC, ExpeL, LangMem, Letta, mem0, ProPlay, ReasoningBank, SimpleMem, Synapse, self-managed. Controls: raw-trajectory ("verbatim"/episodic-only) and no-memory.
  - (2) Update regimes: Static-All (one pass over the whole pool), Static-Group (per task type, concatenated), Stream (batch-by-batch).
  - (3) ARC-AGI Stream with explicit macro-actions over an Episodic buffer and an Abstract (strategy) store: Keep/Retain, Remove/Delete, Strategy extraction/Consolidate. The extraction step outputs the FULL replacement strategy buffer as JSON entries of kind retain (`from_existing`), new (`from_functions`), or merge (both). Prompt: "Output the FULL replacement strategy buffer: every strategy you include will be kept; every existing entry you omit will be discarded... Merge redundant / near-duplicate entries into a single cleaner description... Drop entries that are no longer representative (simply omit them from your output)." Control loops: Force (consolidate every round, no episodic carryover), Auto (model chooses), Episodic Management Only (retain/delete only, abstraction off).
- KEY FINDINGS relevant here:
  - Utility rises, then falls, sometimes below no-memory.
  - GPT-5.4 solves a set of ARC-AGI problems at 100% with no memory. After streamed consolidation from their ground-truth solutions, accuracy drops to 54%, i.e., it now fails on about 46% of them (§1 and Fig. 2: "100% → 54%"). The abstract's "fails on 54%" contradicts the body; the body figure is 54% accuracy.
  - Table 5 (ARC-AGI Stream, GPT-5.4, bsz 1, forced, step 400), in the paper's own words: "in-place rewriting is the most damaging single component, while pruning (delete without rewrite) actually helps".

    | Condition | Accuracy |
    |---|---|
    | Default (in-place rewriting) | 43.2 |
    | Append-only, prior store visible | 50.0 |
    | Add + delete, no in-place edit | 64.0 |
    | Append-only, prior store hidden | 70.0 |
    | Raw trajectories | 76.6 |

  - App. D.2 "Concrete-vocabulary erosion": 50 consecutive rewrites of one task's memory by GPT-5-mini. Round 1 contains "max size"; by round 50 the entry reads "a derived per-object numeric attribute", which no longer says which attribute to maximize. Other named modes: vacuous abstraction, foreign-family injection, phantom strategies from failed attempts, single-strategy collapse.
  - L.7: GEPA prompt optimization recovers only part of the loss. The selected prompt tells the solver to "Treat any provided strategy only as a tentative hint, not a correct rule."
  - The paper does not use the phrase "drift toward the model's prior". It frames the problem as segmentation errors, overgeneralization/interference and overfitting, and cites schema-vs-prior-knowledge CLS theory.
- PropWorld:
  - Not mentioned in v1 or v2 paper text (searched).
  - It exists in the code release as a synthetic streaming crafting world (`agentmem/envs/propworld/`, `docs/propworld.md`). All tokens are meaningless nonces and the eval split is CFQ/MCD-style (novel value combinations). The ground-truth rule legend is fully known, so memory can be scored against what it should have learned. An oracle given the legend scores ≈1.0, so "all difficulty is in the memory".
  - Base-1: 64 independent look-up facts, 768-episode stream. Base-2: 3-stage compositional world, 108 tool facts.
  - Design notes (`agentmem/tmp/propworld_frameworks_adversarial_2026-07-01.md`) report that decodable signals were solved zero-shot by the no-memory agent (leak 0.91), so the authors switched to opaque nonces (leak 0.03). In other words, PropWorld is deliberately built to remove prior knowledge. `agentmem/tmp/PLAN_2026-07-01.md` L156 leaves open whether failures hold with semantic values.
  - PropWorld code is released (MIT). Raw run artifacts are NOT in the public clone: `agentmem/outputs/` is absent; README L258-264 says they live in the private `memory-abstraction-collapse/toy-memory-example` @ 3036e87, which returns 404. This contradicts `agentmem/VENDORED.md`, which lists 468 run dirs. Full reruns need vLLM with Qwen3.6-27B.
- WRITE / UPDATE / FORGET / RETRIEVE: Vary by method. The harness exposes `init_state / curate / inject / memory_text` per method, so memory snapshots are saved at each checkpoint (released under `results/*/memory/`).
- ITERATED REWRITE CHAIN?: YES. That is what the study is about: Stream mode with DC/ACE/ARC strategy-buffer replace-mode is an explicit chain, and they isolate it.
- WHICH CHANNEL: Both, and they separate them experimentally: rewriting (transformation) vs pruning (selection) vs conditioning on the prior store.
- DEFAULT PROMPTS: In repo: `agentmem/controller/methods.py`, `arc/solver/prompts/*.py`, `arc/memory/providers/*/prompts/*.py`, `bench/memory/*.py`. Paper App. B.1-B.7 reproduces the ARC prompts.
- RUNNABLE FOR EXPERIMENTS:
  - Yes, the most directly reusable harness found. Backbones: OpenAI, Anthropic, local OpenAI-compatible, vLLM, HF. CPU stub demo via `make demo`.
  - `python results/verify_numbers.py` recomputes 675 published numbers offline.
  - Environments: ALFWorld, ScienceWorld, WebShop, AppWorld (AgentGym fork), PropWorld, ARC-AGI.
  - Repository is ~1.6 GB (results/ ~1 GB). Sparse checkout is documented.
- MULTI-AGENT: N/A. An "OpenCode" autonomous-agent memory-management arm appears in L.6.
- UNCERTAIN:
  - Whether PropWorld results appear in any paper version or a companion paper.
  - Which backbone(s) produced the PropWorld numbers beyond the Qwen3.6-27B mention in docs.
  - The WebFetch summary misreported model names; all model and number claims above come from my own text search of v2.

---

## Summary table

| System | Update type | Iterated rewrite chain? | Who decides deletion | Code / prompts available | License |
|---|---|---|---|---|---|
| Generative Agents | Append-only stream + stacked reflections; daily in-place rewrite of `currently` | PARTIAL (reflection trees; `currently` is a true daily chain) | Nobody (`expiration` stored but unused); recency decay only | Yes / yes (txt templates) | Apache-2.0 |
| MemoryBank | Raw turns + write-once daily summaries; global summary recomputed from the dailies | NO (fixed depth 2) | Rule + RNG (Ebbinghaus; exponent bug) | Yes / yes (inline) | MIT |
| Reflexion | Append per-task reflections, window of 3 | PARTIAL (new reflection sees the last 3; per task) | Rule (sliding window) | Yes / yes | MIT |
| ExpeL | Ops: ADD / EDIT / AGREE(UPVOTE) / REMOVE(DOWNVOTE) over a rule list | YES (sequential EDITs, offline) | LLM votes, rule threshold (count ≤ 0) | Yes / yes | Apache-2.0 |
| Dynamic Cheatsheet | Full rewrite of the whole cheatsheet per query, no ground truth | YES (canonical) | LLM (omission) | Yes / yes (prompt files) | MIT |
| AWM | Re-induction from raw successful trajectories, file overwritten (paper says append) | NO (but regeneration churn) | LLM implicitly + LLM-judge pool filter | Yes / yes | Apache-2.0 |
| ReasoningBank | Append-only items (≤3 per trajectory) | NO | Nobody | Yes / yes | Apache-2.0 |
| Memory-R1 | Learned ADD / UPDATE / DELETE / NOOP | PARTIAL-YES (entry UPDATEs) | Learned LLM policy (RL, QA EM) | No (placeholder repo) / paper App. C.1 only; no weights | Apache-2.0 (empty repo) |
| MEM1 | Learned overwrite of internal state each turn | YES (within episode) | Learned (omission) | Yes / yes; weights on HF | MIT code; HF weights no license tag |
| MemAgent | Learned overwrite of 1K-token memory per chunk | YES (within task) | Learned (omission) | Yes / yes; weights on HF | Apache-2.0 (code + weights) |
| AgeMem | Learned tools: Add / Update / Delete + Summary / Filter context | PARTIAL (within episode) | Learned policy + LLM-judge reward | Training code yes; no weights | No LICENSE file (pyproject: Apache) |
| Faulty-memories study (Memory-Collapse-Eval) | Studies stream rewrite vs append vs prune; ARC retain / new / merge full-buffer replace | YES (object of study) | Varies; ablated | Yes (14 methods, 6 envs); PropWorld code yes, raw runs private | MIT code; CC BY 4.0 data |
