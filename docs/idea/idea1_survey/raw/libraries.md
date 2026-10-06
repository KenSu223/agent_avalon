# Memory libraries / infrastructure: lifecycle survey (write / update / forget / retrieve)

Surveyor scope: open-source memory libraries. Checked 2026-10-06. All repos were shallow-cloned to
`scratchpad/survey/repos/` and read directly. Paper claims were checked against the arXiv PDFs (converted to text in
`scratchpad/survey/papers/{memgpt,amem,mem0,zep}.txt`). Paths below are relative to each repo root. "UNVERIFIED" marks
anything I could not confirm in code or the primary paper.

Main point for the drift hypothesis: in each system, the question is whether an LLM reads its own earlier memory text and
writes a replacement. The places where it does (rolling summaries, entity/community summaries, fused memories, rewritten
neighbour context) are the transformation channel. The places where an LLM decides keep/delete/invalidate are the
selection channel.

---

### MemGPT / Letta

- Type: library / agent harness (current: Letta Code, TypeScript; historical: Letta V1 Python server = MemGPT lineage)
- Checked: 2026-10-06.
  - `letta-ai/letta` `main` @5bcdd17 (2026-09-10) is now only a landing page. Its `AGENTS.md` says the V1 server lives on the
    `archive` branch "for historical reference only" and must not be used for "benchmarks, evaluations, experiments, or
    academic research" or "comparisons with other agent or memory systems".
  - Current implementation: `letta-ai/letta-code` @4b028fa (2026-10-05), v0.34.4, Apache-2.0.
  - Historical: `letta-ai/letta` branch `archive` @56ba9c2 (2026-08-13), v0.16.8, Apache-2.0. I read it only to document the
    history.
- Sources:
  - Paper: Packer et al. 2023, arXiv 2310.08560, Sec. 2.2 (Queue Manager) and 2.3 (Function executor)
  - letta-code: `src/backend/local/compaction.ts` (L22-45 constants; L61-109 prompts; L259-261 the prior summary is fed back in;
    L483-501 how the summary message is packaged)
  - letta-code: `src/backend/dev/provider-turn-executor.ts` L241-272 (compaction threshold)
  - letta-code: `src/agent/subagents/builtin/reflection-v2.md` (background reflection prompt)
  - letta-code: `src/agent/subagents/builtin/memory-v2.md`
  - letta-code: `src/cli/helpers/memory-reminder.ts` L51-56 (default reflection trigger)
  - letta-code: `src/agent/prompts/letta.md` (agent system prompt on memory)
  - letta-code: `src/skills/builtin/self-configuration/references/compaction-prompt-patterns.md`
  - archive: `letta/functions/function_sets/base.py` L246-310 and L488-530 (memory tools)
  - archive: `letta/prompts/summarizer_prompt.py`, `letta/prompts/gpt_summarize.py`
  - archive: `letta/constants.py` L82-83 and L412-420
  - archive: `letta/prompts/system_prompts/sleeptime_v2.py`
  - archive: `letta/groups/sleeptime_multi_agent_v3.py` L135-140
- WRITE:
  - Message history ("recall memory") is stored raw and automatically. letta.md: "cannot be mutated".
  - In-context memory ("memory blocks") is free text that the agent LLM edits itself through tool calls. There is no separate
    extraction model.
  - In letta-code, blocks and external memory are projected to a git-backed filesystem (MemFS). The agent edits them with the
    generic Edit/Write/Bash tools and commits.
  - Historical MemGPT/V1 used the functions `core_memory_append`, `core_memory_replace`, `memory_insert`, `memory_replace`,
    `memory_rethink` and `archival_memory_insert`. Archival memory = passages written by the LLM into a vector DB.
  - Granularity: free-text block or file (core), passage (archival), message (recall).
- UPDATE: in-place rewrite by the LLM. There are two paths.
  - (a) Surgical string edits: `core_memory_replace`/`memory_replace` (str-replace) and the Edit tool.
  - (b) Whole-block rewrite: `memory_rethink`/`rethink_memory`.
    - Docstring: "completely rewrite the contents of a memory block ... (e.g. when you want to condense or reorganize the
      memory blocks)".
    - `rethink_memory`: "new_memory should contain all current information from the block that is not outdated or
      inconsistent, integrating any new information".
  - Background reflection in letta-code (reflection-v2.md):
    - Updates are made with Edit.
    - Guard rails:
      - "Identity preservation ... Never rewrite them wholesale" (L100)
      - "Contradiction resolution: ... fix the stale entry at the source. Do not append the new version alongside the old."
        (L102)
    - Re-runs over old transcripts are explicit: "Slices marked `mode: "replay"` were already reflected before and are
      intentionally included for another pass" (L56).
- FORGET / EXPIRE:
  - The LLM decides.
    - Old: `core_memory_replace` docstring says "To delete memories, use an empty string for new_content".
    - Reflection subagent: "Delete (don't archive) content the user asked to forget ... or junk", or move content to
      `ARCHIVE.md` (L104).
    - Moving a file out of root removes it from context ("tier" change).
  - Recall (message history) is never deleted. Context eviction is rule-based: a token threshold triggers it, and an LLM
    writes the summary.
  - No time decay or TTL.
  - Git history keeps every prior version of MemFS.
- RETRIEVE:
  - Core blocks are always in context (full-context).
  - Deferred memory files: the agent picks them by name/description and reads them.
  - Recall: message search through the `recall` subagent / `/search`. Historical: `conversation_search`, plus embedding
    search for `archival_memory_search`.
- COMPACTION TRIGGER:
  - MemGPT paper Sec. 2.2:
    - At the "warning token count ... (e.g. 70% of the context window)" a "memory pressure" system message invites the LLM to
      save information.
    - At the "flush token count (e.g. 100%)" the manager "evicts a specific count of messages (e.g. 50% of the context
      window), generates a new recursive summary using the existing recursive summary and evicted messages".
  - Archive: `SUMMARIZATION_TRIGGER_MULTIPLIER = 0.9`.
  - letta-code:
    - Compaction runs on context overflow / pressure (threshold = window minus a reserve of at most 20%) or on manual
      `/compact`.
    - Default mode `sliding_window` with `LOCAL_DEFAULT_SLIDING_WINDOW_PERCENTAGE = 0.3`. Modes: `all`, `sliding_window`,
      `self_compact_*`.
  - Background reflection:
    - Default trigger `"compaction-event"`: reflection runs after each compaction. Alternatives: `step-count` or `off`.
    - Sleep-time agents in V1 ran every N turns (`sleeptime_agent_frequency`).
- ITERATED REWRITE CHAIN?: YES, at two levels.
  - (1) The conversation summary is recursive by design.
    - Paper: "new recursive summary using the existing recursive summary".
    - letta-code prompt: "If there is a previous summary being evicted, please extract a concise version of the critical info
      from it" (compaction.ts L66/L89).
    - The previous summary is re-inserted into the transcript that gets summarized (L259-261).
    - Word caps: 300 (sliding) / 500 (all).
    - Letta's own tuning doc admits the effect: "If prior long-term goals drift over repeated compactions, require the
      summarizer to incorporate any existing summary" (compaction-prompt-patterns.md L115).
  - (2) Memory blocks/files are re-read and edited by the agent and by the reflection subagent after every compaction.
    `memory_rethink` regenerates a whole block from the old block plus new context.
- WHICH CHANNEL:
  - Transformation: recursive summary, block rethink/edit.
  - Selection: LLM deletes or archives lines/files; rule-based eviction of messages from context.
- DEFAULT PROMPTS:
  - letta-code `src/backend/local/compaction.ts`: `LOCAL_ALL_COMPACTION_PROMPT`, `LOCAL_SLIDING_WINDOW_COMPACTION_PROMPT`.
    Server equivalents are in archive `letta/prompts/summarizer_prompt.py` (`ALL_PROMPT`, `SLIDING_PROMPT`,
    `SELF_SLIDING_PROMPT`, `SELF_ALL_PROMPT`).
  - Reflection: `src/agent/subagents/builtin/reflection-v2.md`.
  - Old V1 summarizer: `letta/prompts/gpt_summarize.py` ("Summarize what happened in the conversation from the perspective of
    the AI ... less than 100 words").
  - Replaceable: yes.
    - `compaction_settings.prompt`/`model`/`mode`/`clip_chars` per agent (script `update-compaction-prompt.ts`).
    - The reflection prompt is a markdown subagent definition that can be overridden.
- RUNNABLE FOR EXPERIMENTS:
  - letta-code is open source (Apache-2.0) and has a local backend. BYOK providers include "OpenAI-compatible API", Ollama and
    LM Studio (`src/providers/byok-providers.ts` L149, L279).
  - The compaction function is a self-contained TS module, easy to isolate for repeated-compaction experiments.
  - Caveat: the repo itself forbids using the archived Python V1 for research or benchmarks. Results on V1 must be labelled
    historical.
- MULTI-AGENT:
  - Each agent has its own MemFS. "Shared memory" repos can be attached to several agents (git-pushed after each turn).
  - Agents can call other agents (including themselves) as subagents.
  - Historical V1: memory blocks can be attached to multiple agents; sleep-time agent groups edit the primary agent's blocks.
- UNCERTAIN:
  - Exact Letta Cloud server-side compaction code (closed). I verified only the local backend and the archived server.
  - Whether Cloud uses the same default prompts: UNVERIFIED (README says bundled prompts become "Cloud-managed").

### Mem0 (open-source `mem0ai` Python library; also legacy v1.x and the graph variant Mem0g)

- Type: library (+ hosted platform)
- Checked: 2026-10-06.
  - `mem0ai/mem0` main @c93420c (2026-10-05), package v2.2.1, Apache-2.0.
  - Legacy algorithm: tag `v1.0.11` (last 1.x), cloned separately.
  - Paper: Chhikara et al. 2025, arXiv 2504.19413.
- Sources:
  - Current:
    - `mem0/memory/main.py` L881-1100 (`_add_to_vector_store`, "=== V3 PHASED BATCH PIPELINE ===" L918)
    - `mem0/configs/prompts.py` L468+ (`ADDITIVE_EXTRACTION_PROMPT`), L1016+ (`generate_additive_extraction_prompt`)
    - `docs/migration/oss-v2-to-v3.mdx`
    - `docs/changelog/sdk.mdx` L373-396 (v2.0.0, 2026-04-14)
    - `docs/platform/features/dream.mdx`
  - Legacy: v1.0.11
    - `mem0/memory/main.py` L520-670
    - `mem0/configs/prompts.py` L175+ (`DEFAULT_UPDATE_MEMORY_PROMPT`)
    - `mem0/graphs/utils.py` L57+ (`DELETE_RELATIONS_SYSTEM_PROMPT`)
    - `mem0/memory/graph_memory.py` L383-420
  - Paper Sec. 2.1 (extraction/update), 2.2 (Mem0g)
- WRITE:
  - `add()` with `infer=True` (default) makes one LLM call, `ADDITIVE_EXTRACTION_PROMPT`: "Your sole operation is ADD:
    identify every piece of memorable information" (L472). Also "When in doubt, extract." (L578).
  - Inputs: the new messages, the last 10 messages of the session (SQLite), and top-10 similar existing memories "ONLY for
    deduplication and linking".
  - Output: contextually rich fact sentences with `linked_memory_ids`. Exact duplicates are dropped by MD5 hash. spaCy
    entities are linked in an `{collection}_entities` store.
  - `infer=False` stores raw messages.
  - Granularity: fact sentence.
- UPDATE:
  - Current OSS (v2.0.0+): append-only. The changelog says "Replaced 2-LLM-call pipeline with additive extraction ... no more
    UPDATE/DELETE events", "Memories accumulate; nothing is overwritten".
    - `custom_update_memory_prompt` is deprecated. `DEFAULT_UPDATE_MEMORY_PROMPT` still sits in `prompts.py` but nothing in
      `main.py` calls it (verified by grep).
    - Manual `update(memory_id, data)` exists.
  - Legacy v1.x (the paper's algorithm): merge with ops ADD / UPDATE / DELETE / NONE(NOOP).
    - Each extracted fact is compared by an LLM against the top-5 similar memories per fact.
    - Prompt: "If the retrieved facts contain information that is already present in the memory but the information is totally
      different, then you have to update it ... keep the fact which has the most information".
    - On UPDATE the LLM writes the new text for an existing ID (old text is kept in the history table).
  - Platform "Dream" (closed, not OSS):
    - "Supersede" marks an older fact superseded.
    - "Merge" folds a duplicate into a canonical memory. Example in the doc: the richer statement is stored and the barer one
      marked merged.
    - "Synthesis" adds pattern memories every 7 days (Pro). Doc: "Nothing Dream does is destructive".
- FORGET / EXPIRE:
  - Current OSS: no LLM deletion. Only explicit `delete()`/`delete_all()`, plus an optional per-memory `expiration_date`
    (TTL-like; expired memories are filtered from search/get unless `show_expired`).
  - Legacy v1: the LLM decides DELETE ("If the retrieved facts contain information that contradicts the information present
    in the memory, then you have to delete it", prompts.py L263 @v1.0.11). This was a hard delete from the vector store,
    logged in history.
  - Legacy Mem0g: an LLM "update resolver" (`DELETE_RELATIONS_SYSTEM_PROMPT`) picks contradictory/outdated relations to
    delete, implemented as a soft-delete ("mark relationship as invalid instead of removing it", graph_memory.py L420).
    - Paper Sec. 2.2: "marking them as invalid rather than physically removing them".
- RETRIEVE:
  - Current: hybrid score = semantic + BM25 (lemmatized) + entity boost (+ temporal boosts per changelog). Default
    `top_k=20`, `threshold=0.1`, optional reranker.
  - Legacy: vector similarity (+ graph traversal for Mem0g).
- COMPACTION TRIGGER:
  - OSS: none; extraction runs on each `add()` call.
  - Paper: "an asynchronous summary generation module that periodically refreshes the conversation summary" S used as
    extraction context (Sec. 2.1).
    - In current OSS the `## Summary` slot exists in the prompt builder, but `main.py` never passes a summary.
    - In v1.0.11 extraction uses only the parsed messages. The summary refresher is therefore NOT in OSS; presumably
      platform-only (UNVERIFIED).
  - Platform Dream Synthesis: weekly per user with at least 20 memories.
- ITERATED REWRITE CHAIN?:
  - Current OSS: NO. Existing memory texts are shown to the LLM only for dedup/linking, and are never rewritten.
  - Legacy v1: PARTIAL. UPDATE has the LLM read an old fact and emit a replacement under the same ID, so a single memory can
    be rewritten repeatedly across sessions. Each pass is local (one fact plus up to ~5 neighbours), not a global rewrite.
  - Paper's summary S: likely YES (periodic refresh of a summary), but the code is not public. UNVERIFIED.
- WHICH CHANNEL:
  - Current OSS: selection only, at write time (what to extract / dedup skip). No deletion channel.
  - Legacy v1: transformation (UPDATE text) plus selection (LLM DELETE).
  - Mem0g: selection by invalidation.
- DEFAULT PROMPTS:
  - `mem0/configs/prompts.py`: `ADDITIVE_EXTRACTION_PROMPT`, `AGENT_CONTEXT_SUFFIX`, `PROCEDURAL_MEMORY_SYSTEM_PROMPT`.
  - Legacy: `FACT_RETRIEVAL_PROMPT`, `USER_MEMORY_EXTRACTION_PROMPT`, `DEFAULT_UPDATE_MEMORY_PROMPT`; graph prompts in
    `mem0/graphs/utils.py`.
  - Replaceable:
    - Current: only `custom_instructions` (appended as "## Custom Instructions", "highest priority"). Full system-prompt
      replacement needs monkeypatching the module constant.
    - Legacy: `custom_fact_extraction_prompt` and `custom_update_memory_prompt` fully replaced the prompts.
- RUNNABLE FOR EXPERIMENTS:
  - Open source; 24 LLM providers including Ollama, vLLM, LM Studio, LiteLLM; Qdrant/Chroma/FAISS etc.
  - To study the UPDATE/DELETE chain, pin `mem0ai==1.0.11`. v2+ removed it, and also removed graph memory from OSS ("Graph
    memory moved to Platform").
- MULTI-AGENT:
  - Memories are scoped by `user_id` / `agent_id` / `run_id`.
  - Agent-scoped adds append `AGENT_CONTEXT_SUFFIX`.
  - Sharing is done by querying the same scope; there is no cross-agent merge logic.
- UNCERTAIN:
  - Platform v3 internals (Dream supersede/merge implementation, summary refresher): closed, documented only.
  - Exact temporal boost formula: not checked.

### LangMem (LangChain) + LangGraph long-term memory store

- Type: library (LangMem = memory-management functions; LangGraph `BaseStore` = storage substrate)
- Checked: 2026-10-06.
  - `langchain-ai/langmem` @48e3c11 (2026-10-02), v0.0.30, MIT.
  - `langchain-ai/langgraph` @2d94208 (2026-10-05), MIT.
  - Dependency `hinthornw/trustcall` @8c7312b, MIT (implements the patch/remove ops).
- Sources:
  - `src/langmem/knowledge/extraction.py`:
    - L185-207 `_MEMORY_INSTRUCTIONS`
    - L217-300 `MemoryManager`
    - L832-880 `MemoryStoreManager`
    - L1006-1060 retrieval of existing memories
    - L2092 factory
  - `src/langmem/knowledge/tools.py` L25-40 (`manage_memory` tool)
  - `src/langmem/short_term/summarization.py` L23-45 (running summary prompts)
  - `src/langmem/reflection.py` L273-330 (`ReflectionExecutor`, debounced)
  - `src/langmem/prompts/optimization.py` (prompt optimizers)
  - `docs/docs/concepts/conceptual_guide.md`
  - trustcall `trustcall/_base.py` L1195-1310 (`RemoveDoc`, `PatchDoc`) and L653-760 (`_ExtractUpdates`)
  - langgraph `libs/checkpoint/langgraph/store/base/__init__.py` L545-570 (`TTLConfig`), L756-946 (API)
- WRITE: two modes.
  - (a) Hot path: the agent calls `manage_memory` (create/update/delete), "Proactively call this tool when you ... Identify
    that an existing MEMORY is incorrect or outdated."
  - (b) Background: `create_memory_store_manager` searches the store for related memories (default `query_limit=5`). It then
    asks the LLM (trustcall extractor) to insert new `Memory(content=str)` docs and/or patch existing ones.
  - Profiles (a single schema doc per user) are also supported.
  - Granularity: free-text memory doc or structured profile.
- UPDATE: in-place rewrite by the LLM.
  - Existing docs are shown in `<existing>` and the LLM emits `PatchDoc` JSON-Patch ops. For a `content: str` memory this is a
    `replace /content` with new LLM-written text.
  - Default instructions explicitly ask for consolidation: "Consolidate and compress redundant memories to maintain
    information-density; strengthen based on reliability and recency; maximize SNR" and "Remove incorrect or redundant
    memories" (extraction.py L196-197). Also "What generalizations can you make?"
  - Multi-step refinement: with `max_steps>1` a `Done` tool lets the LLM keep patching ("continue to refine existing
    memories").
- FORGET / EXPIRE:
  - LLM-judged `RemoveDoc` (trustcall) leads to `store.delete` (hard delete).
    - `create_memory_manager` / `create_memory_store_manager` default `enable_deletes=False`.
    - `manage_memory` tool default allows delete.
  - LangGraph store has rule-based TTL (`TTLConfig`: `default_ttl` minutes, `refresh_on_read=True`,
    `sweep_interval_minutes`).
  - No importance decay in code. The conceptual guide talks about "strength" based on recency/frequency, but I found no such
    scoring in `langmem/knowledge` (grep).
- RETRIEVE:
  - `BaseStore.search(namespace, query=...)`: embedding similarity if the store has an index; filter by namespace/metadata.
  - Manager pre-retrieval:
    - Default: "dilated windows" over recent messages.
    - Alternative: an LLM query generator when `query_model` is set.
- COMPACTION TRIGGER:
  - Background manager runs when invoked. Typically through `ReflectionExecutor.submit(..., after_seconds=N)`, debounced per
    thread_id (a new submit cancels the pending one), i.e. after conversation inactivity.
  - Short-term `SummarizationNode`/`summarize_messages`: token threshold (`max_tokens_before_summary`).
- ITERATED REWRITE CHAIN?: YES.
  - (1) Running conversation summary: `DEFAULT_EXISTING_SUMMARY_PROMPT`, "This is summary of the conversation so far:
    {existing_summary} Extend this summary by taking into account the new messages above" (summarization.py L31-37). The
    summary is rewritten every time the threshold is crossed.
  - (2) Collection memories and profiles are re-read and patched on every background run. A profile doc is rewritten each
    session.
  - (3) Prompt optimizers (`gradient`/`metaprompt`/`prompt_memory`) rewrite the system prompt from trajectories.
- WHICH CHANNEL:
  - Transformation: patch/consolidate, running summary, prompt rewriting.
  - Selection: `RemoveDoc` when enabled; TTL by rule.
- DEFAULT PROMPTS:
  - `src/langmem/knowledge/extraction.py` `_MEMORY_INSTRUCTIONS`
  - `src/langmem/short_term/summarization.py` `DEFAULT_INITIAL_SUMMARY_PROMPT` / `DEFAULT_EXISTING_SUMMARY_PROMPT` /
    `DEFAULT_FINAL_SUMMARY_PROMPT`
  - trustcall `PatchDoc` field descriptions (these also steer behaviour)
  - Replaceable: yes. `instructions=`, `schemas=`, summary prompt args, `actions_permitted`, `enable_inserts/updates/deletes`.
- RUNNABLE FOR EXPERIMENTS:
  - Fully open source.
  - Models come through LangChain `init_chat_model`, so any OpenAI-compatible endpoint, Ollama or vLLM works (LLM must
    support tool calling).
  - `InMemoryStore` with an embedding index gives a self-contained setup. Very convenient for controlled iterated-rewrite
    experiments: the profile mode is a clean single-document chain.
- MULTI-AGENT:
  - Namespaces (default `("memories", "{langgraph_user_id}")`). Agents share memory by sharing a namespace; no conflict
    handling beyond the LLM patching.
- UNCERTAIN:
  - LangGraph Platform-hosted store features (managed TTL sweeps, semantic index config) are only partly checked.

### A-MEM (Agentic Memory, Xu et al. 2025)

- Type: research system + small library
- Checked: 2026-10-06.
  - `agiresearch/A-mem` @ceffb86 (2025-12-12), MIT
  - `WujiangXu/A-mem-sys` @f303dfc (2025-11-06), MIT (library variant; adds SGLang/OpenRouter backends and memory_id-tagged
    neighbours)
  - Paper reproduction repo `WujiangXu/AgenticMemory` @0c8039f (2026-03-05), MIT
  - Paper arXiv 2502.12110 (NeurIPS 2025 per repo; venue UNVERIFIED)
- Sources:
  - `agentic_memory/memory_system.py` in agiresearch/A-mem:
    - L93-124 init (`evo_threshold=100`)
    - L127-158 `_evolution_system_prompt`
    - L159-200 `analyze_content`
    - L233-286 `add_note` / `consolidate_memories`
    - L590-727 `process_memory`
  - `agentic_memory/retrievers.py` (ChromaDB, `all-MiniLM-L6-v2`)
  - Reproduction: `memory_layer.py` L672-801 (same prompt)
  - Paper Sec. 3.1-3.4, Eq. 7
- WRITE:
  - Every `add_note(content)` stores the raw content verbatim.
  - An LLM generates metadata: "keywords", one-sentence "context", "tags" (`analyze_content`).
  - Granularity: one note per interaction/turn.
- UPDATE: in-place rewrite of metadata of other notes ("memory evolution").
  - For each new note, the k nearest neighbours are retrieved and the LLM decides `should_evolve`. Actions:
    - `strengthen`: add links, re-tag the new note.
    - `update_neighbor`: write `new_context_neighborhood` and `new_tags_neighborhood` for each neighbour.
  - Prompt: "If choose to update_neighbor, you can update the context and tags of these memories based on the understanding of
    these memories. If the context and the tags are not updated, the new context and tags should be the same as the original
    ones."
  - Paper Eq. 7: "m_j* ← LLM(m_n ∥ M_near \ m_j ∥ m_j ∥ P_s3) ... The evolved memory m_j* then replaces the original memory
    m_j" (Sec. 3.3).
  - The raw `content` field is never rewritten. Only context/tags (and links) change.
  - `evolution_history` exists as a field but is never appended to, so old context versions are lost.
- FORGET / EXPIRE:
  - None automatic. `delete(memory_id)` is an API call only.
  - `retrieval_count` / `last_accessed` fields are stored but never incremented or used (grep).
  - No LLM delete op.
- RETRIEVE:
  - ChromaDB embedding search over content (+ metadata).
  - `search_agentic` also returns linked neighbours (graph expansion via `links`).
- COMPACTION TRIGGER:
  - Evolution runs synchronously on every `add_note`.
  - `consolidate_memories()` runs every `evo_threshold` (=100) evolutions. It only rebuilds the Chroma index from the
    in-memory dict and makes no LLM call.
    - Side effect: neighbour context/tag rewrites reach the vector index metadata only at that point (UNVERIFIED whether this
      affects retrieval scoring, since embeddings are on `content`).
- ITERATED REWRITE CHAIN?: PARTIAL.
  - A popular note's `context` and `tags` are regenerated by the LLM each time a new note lands nearby. Each pass reads the
    previous LLM-written context, so the context field forms a chain that can drift with no record.
  - The verbatim `content` is protected, so drift is confined to the retrieval-facing metadata (and thus what gets surfaced
    in some search paths).
- WHICH CHANNEL:
  - Transformation (neighbour context/tags rewrite).
  - Weak selection (link creation decides adjacency). No deletion channel.
- DEFAULT PROMPTS:
  - `agentic_memory/memory_system.py` (`analyze_content` prompt string, `self._evolution_system_prompt`).
  - Replaceable: not via a config parameter; the attribute can be overwritten after construction, or fork.
- RUNNABLE FOR EXPERIMENTS:
  - Yes, small and readable (~1.1k LOC).
  - Backends: `openai` and `ollama` (A-mem); plus `sglang` and `openrouter` (A-mem-sys).
  - The controller has no `base_url` parameter (grep). A local OpenAI-compatible server would need the `OPENAI_BASE_URL`
    env var (standard OpenAI SDK behaviour; untested here) or the `ollama` backend.
  - Embeddings are local (sentence-transformers).
  - Good minimal testbed for "LLM rewrites neighbour summaries repeatedly".
- MULTI-AGENT: N/A (single memory store).
- UNCERTAIN:
  - The index-mapping code in `update_neighbor` maps by list position (`noteslist[memorytmp_idx]`). Whether it always
    targets the intended neighbours was not tested at runtime; possible bug.

### Zep / Graphiti (temporal knowledge graph)

- Type: library (Graphiti, open source) + product (Zep Cloud, closed)
- Checked: 2026-10-06. `getzep/graphiti` @2a85bbb (2026-10-05), graphiti-core v0.30.2, Apache-2.0. Paper: Rasmussen et al.
  2025, arXiv 2501.13956.
- Sources:
  - `graphiti_core/prompts/`:
    - `extract_nodes.py` L509-540 (`extract_summaries_batch`) and the episode-summary system prompt below it
    - `summarize_nodes.py` (`summarize_context`, `summarize_pair`)
    - `snippets.py` (`summary_instructions`)
    - `dedupe_edges.py` L43+ (`resolve_edge`)
    - `summarize_sagas.py` L43-56
  - `graphiti_core/utils/maintenance/node_operations.py` L836-1005 (summary gating)
  - `graphiti_core/utils/maintenance/edge_operations.py` L538-573 (`resolve_edge_contradictions`), L693-840 (dedupe,
    expiry)
  - `graphiti_core/utils/maintenance/community_operations.py` L341-356
  - `graphiti_core/graphiti.py` L1043 (`add_episode`), L1219-1226, L520-560 (saga summary)
  - `graphiti_core/utils/text_utils.py` L26 (`MAX_SUMMARY_CHARS = 1000`)
  - Paper Sec. 2.1-2.3, 3.1-3.2
- WRITE:
  - `add_episode()` stores the raw episode (message or text: episodic node, kept verbatim).
  - LLM extraction of entity nodes and fact edges (triples with a natural-language `fact`).
  - LLM entity resolution / dedup against existing nodes.
  - LLM timestamp extraction (`valid_at`/`invalid_at`).
  - Granularity: episode, entity, fact-edge.
- UPDATE: invalidate with timestamps (bi-temporal) for facts, plus in-place LLM rewrite of summaries.
  - Edges:
    - `resolve_edge` prompt returns `duplicate_facts` and `contradicted_facts`.
    - Duplicates do not rewrite the fact. The episode uuid is appended to the existing edge.
    - Contradicted edges get `invalid_at = new.valid_at`, `expired_at = now`. This is a rule applied to the LLM's
      contradiction labels.
    - Paper: "invalidates the affected edges by setting their t_invalid to the t_valid of the invalidating edge ... Graphiti
      consistently prioritizes new information" (Sec. 2.2.3).
  - Entity summaries:
    - "For each entity, combine relevant information from the MESSAGES with any existing summary content" (extract_nodes.py
      L532).
    - Async-worker variant: "Use ONLY facts explicitly stated in EPISODES and durable facts already present in
      EXISTING_SUMMARY ... Current state over superseded state".
  - Community summaries: `summarize_pair(entity.summary, community.summary)`, "Synthesize the information from the following
    two summaries into a single information-dense summary".
  - Saga summaries: "Merge any new facts from MESSAGES" into `EXISTING_KNOWLEDGE`.
- FORGET / EXPIRE:
  - Facts are never physically deleted by the pipeline. They are expired/invalidated; the LLM selects which ones (selection
    channel), and the rule sets timestamps.
  - Hard deletion only through explicit API (`remove_episode`, node/edge deletes).
  - No decay/TTL.
- RETRIEVE:
  - Hybrid: cosine similarity, BM25 full-text, BFS graph traversal.
  - Rerankers: RRF, MMR, `node_distance`, `episode_mentions`, cross-encoder (`search/search_config.py`; paper Sec. 3.1-3.2).
  - Results expose `valid_at`/`invalid_at` for temporal filtering.
- COMPACTION TRIGGER: a length threshold on entity summaries.
  - By default (`skip_fact_appending=False`) new edge facts are appended raw, with no LLM call, while
    `len(summary + facts) <= 2 * MAX_SUMMARY_CHARS` (2000 chars) (node_operations.py L880).
  - Above that, the LLM rewrites (old summary + episode messages) to under 1000 chars, then `truncate_at_sentence`.
  - With `skip_fact_appending=True` (the async-worker style) the LLM rewrites on every episode.
  - Communities: only when `add_episode(update_communities=True)` (default False). The dynamic label-propagation step
    re-summarizes the community.
    - Paper: "communities gradually diverge from those that would be generated by a complete label propagation run.
      Therefore, periodic community refreshes remain necessary" (Sec. 2.3).
  - Sagas: on explicit summarize call.
- ITERATED REWRITE CHAIN?: YES, for summaries; NO for facts.
  - Entity summary: a classic compaction loop. Append raw until 2x the cap, then the LLM compresses the previous LLM-written
    summary plus new messages back under the cap, then append again. A frequently mentioned entity goes through many
    compressions.
  - Community summaries: `summarize_pair` recursively folds each new member's summary into the running community summary
    (when enabled).
  - Fact edges are immutable text, with LLM-judged invalidation.
- WHICH CHANNEL:
  - Transformation: entity, community and saga summaries.
  - Selection: LLM contradiction/duplicate judgments lead to invalidation and dedup. Deterministic timestamp rules decide
    direction ("prioritizes new information").
- DEFAULT PROMPTS:
  - `graphiti_core/prompts/*.py`, exposed via `prompt_library`. The worker variant is mirrored in a Go file not in this repo.
  - Replaceable:
    - Supported hook: `custom_extraction_instructions` (appended to extraction prompts) and custom `entity_types`/
      `edge_types`.
    - Full replacement needs monkeypatching `prompt_library` or forking.
    - `should_summarize_node` filter can turn summarization off per node.
- RUNNABLE FOR EXPERIMENTS:
  - Yes. Clients: `OpenAIGenericClient` (any OpenAI-compatible endpoint, e.g. Ollama/vLLM; requires structured-output
    capable models), Anthropic, Gemini, Groq, Azure.
  - Graph DB: Neo4j/FalkorDB/Kuzu/Neptune.
  - The entity-summary loop is easy to isolate: one entity, many episodes.
- MULTI-AGENT:
  - `group_id` partitions graphs. Multiple agents writing the same `group_id` share one graph; conflicts are resolved by the
    same invalidation logic.
- UNCERTAIN:
  - Zep Cloud's async summary worker (Go, `src/lib/graphsummary/processor.go`) is referenced in a comment but closed.
  - Whether Cloud uses fact-appending or always-LLM summaries: UNVERIFIED.

### MemOS (MemTensor)

- Type: library + service ("memory operating system")
- Checked: 2026-10-06. `MemTensor/MemOS` @a7367d0 (2026-09-22), MemoryOS v2.0.33, Apache-2.0.
- Sources:
  - `src/memos/templates/mem_reader_prompts.py`:
    - L1+ `SIMPLE_STRUCT_MEM_READER_PROMPT`
    - L940+ `SIMPLE_STRUCT_ADD_BEFORE_SEARCH_PROMPT`
    - L966+ `MEMORY_MERGE_PROMPT_EN`
  - `src/memos/templates/tree_reorganize_prompts.py`:
    - L1 `REORGANIZE_PROMPT`
    - L194 `REDUNDANCY_MERGE_PROMPT`
    - L197 `MEMORY_RELATION_DETECTOR_PROMPT`
    - L211 `MEMORY_RELATION_RESOLVER_PROMPT`
  - `src/memos/templates/mem_feedback_prompts.py` L319+ (`UPDATE_FORMER_MEMORIES`)
  - `src/memos/memories/textual/tree_text_memory/organize/`:
    - `manager.py` L55-90, L523-548
    - `handler.py` L76-190
    - `reorganizer.py` L151-210, L314-345, L550-590
  - `src/memos/mem_reader/multi_modal_struct.py` L542-612
  - `src/memos/mem_feedback/feedback.py` L295-330
  - `src/memos/memories/textual/item.py` L109-111
  - `src/memos/configs/memory.py` L175
  - `src/memos/api/config.py` L1256
  - `src/memos/dream/README.md`
- WRITE:
  - `add()` sends conversation chunks to the mem_reader LLM: "extract memories from the perspective of user ... Prioritize
    completeness and fidelity over conciseness."
  - Output: key/value/tags/summary items typed `LongTermMemory` / `UserMemory` / `WorkingMemory`, stored as nodes in a graph
    DB (Neo4j/Polar etc.) with embeddings.
  - Granularity: memory item (fact/episode paragraph).
- UPDATE: several paths; the defaults matter.
  - (a) Write-time LLM merge (`MEMORY_MERGE_PROMPT_EN`: "merge them into an integrated memory") is currently disabled.
    `_get_maybe_merged_memory` is marked "TODO: delete this function" and returns the item unchanged; `_merge_memories_with_llm`
    is never called. The `merged_from` → `status="archived"` plumbing remains.
  - (b) Reorganizer (`reorganize=False` by default; env `MOS_ENABLE_REORGANIZE`, default "false"). When on, each added node
    goes to LLM relation detection (`contradictory`/`redundant`/`independent`) against top-k neighbours. Then
    `MEMORY_RELATION_RESOLVER_PROMPT`: "produce a single, coherent, and comprehensive statement ... If the contradiction is
    fundamental and cannot be logically resolved, output <answer>No</answer>."
    - The fused node replaces both. Originals are set `status="archived"` with `MERGED_TO` edges.
    - On "No", the older node is deleted outright (`_hard_update` → `delete_node`, by `updated_at`).
  - (c) Feedback API (`POST /feedback`): LLM ADD / UPDATE / NONE.
    - Prompt: UPDATE "only modifying the relevant error segments in the existing memory paragraphs while keeping other text
      completely unchanged".
    - The old version is archived and linked via `covered_history`.
- FORGET / EXPIRE:
  - Rule-based capacity eviction: when a type reaches 80% of its cap, `remove_oldest_memory(keep_latest=limit)`.
    - Defaults: WorkingMemory 20, LongTermMemory 1500, UserMemory 480, RawFileMemory 1500.
    - Evicts by age, not importance.
  - LLM-driven: only in the reorganizer (fusion → archive; unresolvable conflict → delete older).
  - Status lifecycle field: `activated | resolving | archived | deleted`.
- RETRIEVE:
  - Graph + vector recall, optional BM25/full-text (`EnhancedBM25`), reranker, optional internet retrievers.
  - Scheduler prompts can LLM-filter/rerank working memory (`mem_scheduler_prompts.py`).
- COMPACTION TRIGGER: when reorganize is on:
  - Conflict/redundancy resolution on every add (queue consumer).
  - `optimize_structure` (k-means clustering, then `REORGANIZE_PROMPT` "Summarize all child memory items into one memory
    item") every 100 s and after new nodes.
  - Optional Dream plugin (off by default, beta): threshold on pending memories → LLM "insights" + diary.
- ITERATED REWRITE CHAIN?: PARTIAL, and off by default.
  - With reorganize on, a fused memory can itself be fused again with the next contradicting/redundant item: a chain of LLM
    rewrites of the same fact.
  - Cluster parent summaries are built from child summaries and sub-parent summaries (hierarchical summary-of-summaries).
  - With defaults (reorganize off, merge disabled): NO. Items are append-only, with age-based eviction.
- WHICH CHANNEL:
  - Default: selection by rule (FIFO capacity eviction).
  - Reorganize on: transformation (fusion, cluster summaries) plus LLM selection (archive/delete in conflicts).
  - Feedback: transformation of targeted items.
- DEFAULT PROMPTS: `src/memos/templates/*.py` (EN + ZH variants).
  - Replaceable: partly. Some readers take custom prompts/tags (`CUSTOM_TAGS_INSTRUCTION`); others are module constants
    (monkeypatch/fork). UNVERIFIED for each one.
- RUNNABLE FOR EXPERIMENTS:
  - Open source. LLM backends: openai (`api_base` configurable, `configs/llm.py` L39), ollama, vLLM, HF.
  - Heavy deployment: graph DB + vector DB + optional Redis/MySQL scheduler. Isolating `NodeHandler.resolve` for a
    repeated-fusion experiment is feasible.
- MULTI-AGENT:
  - MemCubes per user/agent. `multi_mem_cube` routes across cubes; cubes can be shared/registered to multiple users.
- UNCERTAIN:
  - MemOS paper (arXiv 2507.03724) lifecycle claims were not checked against the paper.
  - `add_before_search` (LLM keep/drop vs existing) is defined in `multi_mem_cube/single_cube.py` L563 but I found no caller
    in `src/`. Whether it runs in any default path: UNVERIFIED.

### Cognee (brief; second of the "MemOS and/or Cognee" slot)

- Type: library + service
- Checked: 2026-10-06. `topoteretes/cognee` @b32d8af (2026-10-01), v1.6.2, Apache-2.0.
- Sources:
  - `cognee/skill.md`
  - `cognee/api/v1/improve/improve.py`
  - `cognee/modules/improve/registry.py` L27-37 (`DEFAULT_STAGES`), `stages.py` L228-300
  - `cognee/modules/session_distillation/distill.py`
  - Prompts in `cognee/infrastructure/llm/prompts/`:
    - `session_distillation_curator_system.txt`
    - `session_distillation_writer_system.txt`
    - `consolidate_entity_details.txt`
    - `generate_graph_prompt.txt`
  - `cognee/modules/user_preferences/update.py`
  - `cognee/memify_pipelines/consolidate_entity_descriptions.py`
- WRITE:
  - `remember()` = `add()` (raw ingest) + `cognify()` (chunk, LLM knowledge-graph extraction, summaries) + `improve()`.
  - Granularity: chunk, entity/edge, summary, distilled "lesson".
- UPDATE:
  - Mostly additive. Session distillation:
    - Curator proposes "durable lessons" ("MERGE: combine turns and candidates that express the same underlying learning
      into ONE lesson").
    - Writer accepts/rejects against "SIMILAR EXISTING LESSONS" ("already_known" → reject). Existing lessons are not
      rewritten.
  - Preference text refresh is "Deterministic, no LLM call".
  - Opt-in memify pipeline `consolidate_entity_descriptions` rewrites entity descriptions from the old description plus
    neighbour descriptions. Prompt: "Use synonym words where possible in order to change the wording but keep the meaning"
    (`consolidate_entity_details.txt` L3), an explicit paraphrase instruction on a re-runnable pass.
- FORGET / EXPIRE:
  - `forget()` = explicit delete.
  - Preference `prefers` edges decay by turn counter (computed on read) and are pruned by rule.
  - Feedback weights adjust edge weights.
  - No LLM-judged deletion found.
- RETRIEVE:
  - `recall()` routes rule-based (no LLM) to graph/vector/chunk/summary/temporal/Cypher search types.
  - Session memory is included as a source.
- COMPACTION TRIGGER:
  - `improve()` stages: feedback weights, session QA persistence, agent traces, distill sessions, user preferences, truth
    subspace, triplet enrichment, global context index.
  - Runs after `remember()` (`self_improvement=True` by default per skill.md) or on explicit call, with a debounce
    (`auto_improve_debounce.py`).
  - Entity-description consolidation runs only when explicitly invoked.
- ITERATED REWRITE CHAIN?:
  - NO in the default path (accept/reject plus additive lessons).
  - YES if `consolidate_entity_descriptions` is run repeatedly: an LLM re-describes entities from its own previous
    description, with a paraphrase instruction.
- WHICH CHANNEL:
  - Default: selection (LLM accept/reject of lessons; rule-based decay/prune).
  - Opt-in: transformation (entity description rewrite).
- DEFAULT PROMPTS: `cognee/infrastructure/llm/prompts/*.txt`.
  - Replaceable: `cognify(custom_prompt=...)` for graph extraction (`cognify.py` L122). For the improve/memify stages,
    replace the prompt files or pass custom tasks (UNVERIFIED for every stage).
- RUNNABLE FOR EXPERIMENTS: open source; LiteLLM-style providers including Ollama/OpenAI-compatible (UNVERIFIED in detail).
- MULTI-AGENT: datasets + `node_set` scoping, per-user permissions; sessions bridged into a shared graph.
- UNCERTAIN:
  - On re-extraction of an existing entity in `cognify`, node IDs are deterministic (`generate_node_id`). Whether the
    description is overwritten or merged: UNVERIFIED.
