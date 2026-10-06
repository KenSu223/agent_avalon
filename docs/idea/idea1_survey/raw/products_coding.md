# Production assistants and coding agents: memory and context compaction

Survey date: 2026-10-06. Scope: how each system writes, updates, forgets and retrieves memory, and above all whether an LLM repeatedly reads and rewrites its own summary or memory, which the drift-toward-prior hypothesis depends on. Security, attack and defense content is out of scope and left out on purpose.

Source checkouts (shallow clones under `scratchpad/survey/repos/`):

| Repo | Commit | Commit date | License |
|---|---|---|---|
| openai/codex | 822e58cc3d66 | 2026-10-06 | Apache-2.0 |
| google-gemini/gemini-cli | fb972b2f87fe (v0.64.0-nightly.20260929) | 2026-10-02 | Apache-2.0 |
| OpenHands/software-agent-sdk (openhands-sdk 1.53.0) | 6f8c38d00e04 | 2026-10-06 | MIT |
| All-Hands-AI/OpenHands (now mostly frontend/app; condenser moved to the SDK) | 81e83760a196 | 2026-10-06 | MIT |
| Aider-AI/aider (0.86.3.dev) | 5dc9490bb35f | 2026-05-22 | Apache-2.0 |
| cline/cline (VS Code ext 4.1.22 + `sdk/`) | dec80dadfa4f | 2026-10-06 | Apache-2.0 |
| openai/openai-agents-python (0.23.1) | d7e52c375021 | 2026-10-05 | MIT |

Claude Code is closed source (LICENSE.md: "© Anthropic PBC. All rights reserved"). For it I used the official docs plus the strings inside the locally installed binary (`~/.local/share/claude/versions/2.1.259`). Anything taken from the binary is labeled "binary v2.1.259".

---

### 1. Claude Code: context compaction (auto-compact and `/compact`)
- **Type:** coding agent (product, closed source)
- **Checked:** 2026-10-06, docs at code.claude.com plus binary v2.1.259. License: proprietary.
- **Sources:**
  - https://code.claude.com/docs/en/context-window#what-survives-compaction
  - https://code.claude.com/docs/en/how-claude-code-works#when-context-fills-up
  - https://code.claude.com/docs/en/model-config#default-auto-compact-thresholds
  - https://code.claude.com/docs/en/commands (`/compact`, `/autocompact`)
  - https://code.claude.com/docs/en/checkpointing (rewind "Summarize from here / up to here")
  - Compaction prompt strings in binary v2.1.259
- **WRITE:** An LLM summarizes the whole conversation. Docs: "Compaction replaces the conversation with a structured summary." The summary "keeps: your requests and intent, key technical concepts, files examined or modified with important code snippets, errors and how they were fixed, pending tasks, and current work. It replaces the verbatim conversation: full tool outputs and intermediate reasoning are gone." Since v2.1.198 the summarization call inherits the session's extended-thinking setting.
- **UPDATE:** The rewrite is in place. The whole message history is replaced by one summary message, which begins "This session is being continued from a previous conversation that ran out of context. The summary below covers the earlier portion of the conversation." (binary). After that, Claude Code re-injects from disk: CLAUDE.md, auto memory, the plan file, a fresh git status, up to 5 recently modified files (each ≤5k tokens), and invoked skill bodies (≤5k per skill, ≤25k in total). Context that hooks added earlier is summarized along with everything else.
- **FORGET / EXPIRE:** Tool results are cleared first ("It clears older tool outputs first, then summarizes the conversation if needed"). Anything the summarizer leaves out is gone. Docs warn that "detailed instructions from early in the conversation may be lost."
- **RETRIEVE:** The summary sits in the context window (full-context). Files are re-read from disk and are not drawn from the summary.
- **COMPACTION TRIGGER:**
  - Auto: "Claude Code compacts when the conversation reaches the model's context limit." Exceptions: about 967K tokens on native-1M models, and the 200K boundary on 200K-window models.
  - Users can set the trigger point with `/autocompact <100k..1M>`, the `autoCompactWindow` setting, or `CLAUDE_CODE_AUTO_COMPACT_WINDOW`.
  - Manual: `/compact [focus instructions]`, or a "Compact Instructions" section in CLAUDE.md.
  - Partial: `/rewind` → "Summarize from here" or "Summarize up to here". The binary carries a separate prompt for this: "RECENT portion of the conversation … The earlier messages are being kept intact and do NOT need to be summarized."
  - Thrashing guard: auto-compaction stops after a few attempts if the context refills immediately.
  - PreCompact hooks exist.
- **ITERATED REWRITE CHAIN?:** YES (by construction; the mechanics are not spelled out in the docs). After the first compaction the history is [summary + new turns], and the next compaction summarizes "the conversation so far", so the earlier summary becomes summarizer input. The generic prompt has no special handling for a previous summary: the phrases "previous summary" and "prior summary" do not occur in the binary. Anchors that partly counter drift:
  - The prompt asks for section "6. All user messages: List ALL user messages that are not tool results."
  - It asks for verbatim quotes in "Optional Next Step": "This should be verbatim to ensure there's no drift in task interpretation." (binary)
  - CLAUDE.md and memory are re-read from disk, not regenerated.
- **WHICH CHANNEL:** Transformation (full rewrite into a 9-section summary) plus rule-based selection (tool outputs cleared first; up to 5 recent files re-read).
- **DEFAULT PROMPTS:** Not published as a file. Binary v2.1.259 contains "Your task is to create a detailed summary of the conversation so far, paying close attention to the user's explicit requests and your previous actions." It asks for `<analysis>` and then `<summary>` with these sections: 1 Primary Request and Intent, 2 Key Technical Concepts, 3 Files and Code Sections, 4 Errors and fixes, 5 Problem Solving, 6 All user messages, 7 Pending Tasks, 8 Current Work, 9 Optional Next Step. Users cannot replace it, only extend it with `/compact <instructions>` or the "Compact Instructions" section in CLAUDE.md.
- **RUNNABLE FOR EXPERIMENTS:** Closed source. It can be pointed at a gateway with `ANTHROPIC_BASE_URL`, but a non-Claude backend is unsupported (UNVERIFIED that it works). For controlled replication, the Anthropic API compaction (section 2) is the cleaner instrument.
- **MULTI-AGENT:** Subagents have their own context window. Only their final summary returns to the parent, which is itself an LLM summary step.
- **UNCERTAIN:**
  - The exact auto-compact fraction for 200K models. The docs say "at the context limit"; GitHub issues report ~78–85% and say `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` is ignored. UNVERIFIED.
  - Whether summarization uses a smaller model: UNVERIFIED. The docs only say thinking settings are inherited.

### 1b. Claude Code: CLAUDE.md, auto memory, and "dream" consolidation
- **Type:** coding agent memory (product)
- **Checked:** 2026-10-06, https://code.claude.com/docs/en/memory plus binary v2.1.259
- **Sources:**
  - https://code.claude.com/docs/en/memory (sections "Auto memory", "Instructions seem lost after /compact")
  - Binary v2.1.259: "# Dream: Memory Consolidation" prompt string, `autoDreamEnabled`
  - Third-party reports on Auto Dream (claudefa.st, mindstudio.ai, implicator.ai), which are NOT primary sources
- **WRITE:**
  - CLAUDE.md is written by the user. Claude edits it only when asked ("add this to CLAUDE.md"); `/init` generates a starter file.
  - Auto memory (on by default in local sessions) is written by Claude during the session with ordinary file tools. Each memory is a topic file with a frontmatter `type` (user, feedback, project or reference) under `~/.claude/projects/<project>/memory/`, plus a `MEMORY.md` index with one line per memory.
  - What gets saved: "Claude skips anything it can derive from the codebase … It also skips anything your CLAUDE.md files already say." It also "decides what's worth remembering based on whether the information would be useful in a future conversation."
  - Claude Code stamps a `modified` ISO timestamp into the frontmatter on every write (v2.1.214+).
- **UPDATE:** In-place file edits by the model, with no fixed op set. For `MEMORY.md` the harness enforces size: near the 200-line / 25KB limit it "reminds Claude to shorten it: keep one line per entry, move detail into topic files, and merge or drop stale entries". Over the limit it returns an error telling Claude to rewrite the index.
- **FORGET / EXPIRE:**
  - The LLM decides what to merge or drop, and the user can edit or delete files.
  - Memory files are exempt from transcript retention cleanup.
  - Only the first 200 lines / 25KB of `MEMORY.md` load at startup, so content past that point is effectively forgotten.
- **RETRIEVE:** The `MEMORY.md` index is always in context. Topic files are read on demand with file tools. CLAUDE.md is loaded in full (up to 4 MiB) and is re-injected from disk after compaction.
- **COMPACTION TRIGGER:**
  - Ongoing in-session writes.
  - Size reminders when `MEMORY.md` nears its limit.
  - "Dream" consolidation. The binary holds a 4-phase prompt: "You are performing a dream — a reflective pass over your memory files. Synthesize what you've learned recently into durable, well-organized memories …". Its phases are Orient, Gather recent signal ("Existing memories that drifted — facts that contradict something you see in the codebase now"), Consolidate ("Merging new signal into existing topic files rather than creating near-duplicates", "Converting relative dates … to absolute dates", "Deleting contradicted facts"), and Prune and index.
  - The dream feature is NOT in the official docs (neither `/dream` nor autoDream appears in code.claude.com/docs). Third-party sources describe an automatic run "after roughly 24 hours and at least five sessions" plus a manual `/dream`: UNVERIFIED.
- **ITERATED REWRITE CHAIN?:** YES across sessions. The model re-reads its existing memory files and the index ("Skim existing topic files so you improve them rather than creating duplicates") and rewrites or merges them. The dream pass explicitly consolidates the existing memory with new signal. CLAUDE.md is a NO, since it is human-authored and not auto-rewritten.
- **WHICH CHANNEL:** Both. Transformation (merge or rewrite topic files, shorten the index) and selection (prune stale entries, delete contradicted facts).
- **DEFAULT PROMPTS:** In the binary only, so they cannot be replaced. Users can steer with CLAUDE.md, turn auto memory off (`autoMemoryEnabled`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`), or move it (`autoMemoryDirectory`).
- **RUNNABLE FOR EXPERIMENTS:** Closed source, with the same caveats as section 1.
- **MULTI-AGENT:** The main auto memory is not loaded into subagents, except forks. Subagents can have their own separate memory directory. Memory is shared across worktrees of one repo and is machine-local.
- **UNCERTAIN:** Dream trigger conditions and default-on status (binary shows gating by `autoDreamEnabled` and a "minHours" re-arm); the exact auto-memory system prompt section was not extracted.

### 2. Anthropic API context management (compaction, context editing, memory tool, Managed Agents "Dreams")
- **Type:** API features (platform)
- **Checked:** 2026-10-06, platform.claude.com docs
- **Sources:**
  - https://platform.claude.com/docs/en/build-with-claude/compaction
  - …/compaction-on-demand
  - …/compaction-threshold
  - …/context-editing
  - https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool
  - https://platform.claude.com/docs/en/managed-agents/dreams
- **WRITE:**
  - *Compaction*: a server-side LLM summary, returned as a readable-text `compaction` block with a signature.
  - *Memory tool* (`memory_20250818`): client-side files under `/memories` with commands view, create, str_replace, insert, delete and rename. The API auto-injects: "IMPORTANT: ALWAYS VIEW YOUR MEMORY DIRECTORY BEFORE DOING ANYTHING ELSE. … ASSUME INTERRUPTION: Your context window might be reset at any moment, so you risk losing any progress that is not recorded in your memory directory."
  - *Dreams* (Managed Agents, research preview, beta `dreaming-2026-04-21`): an async job that reads one memory store plus 1–100 session transcripts and writes a NEW memory store.
- **UPDATE:**
  - Compaction replaces the summarized messages.
  - The memory tool edits in place via str_replace/insert, or overwrites via create.
  - Dreams produce "a new, reorganized memory store: duplicates merged, stale or contradicted entries replaced with the latest value, and new insights surfaced. The input store is never modified."
- **FORGET / EXPIRE:**
  - Context editing `clear_tool_uses_20250919` is rule-based: default trigger 100k input tokens, keep the last 3 tool uses, cleared results replaced by a placeholder. `clear_thinking_20251015` handles thinking blocks.
  - Memory tool: the LLM uses delete. Docs suggest the app "periodically delete memory files that haven't been accessed in a long time."
  - Dreams: an LLM merges, dedups and replaces.
- **RETRIEVE:** Compaction keeps the summary in context. The memory tool is on-demand file reads (agentic retrieval).
- **COMPACTION TRIGGER:**
  - Threshold compaction (`compact_20260112`, beta `compact-2026-01-12`): default trigger `{"type":"input_tokens","value":150000}`, minimum 50,000.
  - On-demand compaction (beta `compact-2026-09-04`): the app sends `"compaction":{"type":"summarize"}` whenever it chooses.
  - Dreams: an explicit API call.
- **ITERATED REWRITE CHAIN?:** YES, and it is documented explicitly. On-demand "Compact again": "To compact a conversation that already starts with a block, send `compaction` again. The new block summarizes the old summary and everything after it. From then on, send only the newest block." Threshold mode: "A long-running conversation might result in multiple compactions." Dreams form a chain if the output store is fed back as the next dream's input; each dream's output is a fresh full rewrite, but versions are retained.
- **WHICH CHANNEL:** Compaction is transformation. Context editing is rule-based selection. Memory tool and Dreams do both.
- **DEFAULT PROMPTS:** Threshold default prompt (quoted in docs): "You have written a partial transcript for the initial task above. Please write a summary of the transcript. The purpose of this summary is to provide continuity so you can continue to make progress towards solving the task in a future context, where the raw history above may not be accessible and will be replaced with this summary. Write down anything that would be helpful, including the state, next steps, learnings etc. You must wrap your summary in a <summary></summary> block." `instructions` (up to 16,384 chars for on-demand) "replaces that prompt entirely". The on-demand default prompt is not published. Dreams take `instructions`.
- **RUNNABLE FOR EXPERIMENTS:** Claude models only, with no local models. Even so, this is the best-documented instrument for iterated compaction: summaries are readable text, the prompt is replaceable, and both the trigger and the "compact again" chain are under the caller's control.
- **MULTI-AGENT:** Managed Agents memory stores can be shared across agents/sessions (docs not studied in detail).
- **UNCERTAIN:** The on-demand default prompt text.

### 3. OpenAI Codex CLI: context compaction (local and remote)
- **Type:** coding agent (open source)
- **Checked:** 2026-10-06, commit 822e58cc3d66, Apache-2.0
- **Sources** (paths under `codex-rs/`):
  - `prompts/templates/compact/prompt.md`, `prompts/templates/compact/summary_prefix.md`
  - `core/src/compact.rs` (L63, L121–126, L372–386, L422, L591, L601)
  - `core/src/compact_remote_v2.rs` (L73, L545), `core/src/compact_remote_v2_attempt.rs`
  - `core/src/session/turn.rs` (L1440–1520)
  - `core/src/session/context_window.rs`
  - `protocol/src/openai_models.rs` (L527–538)
  - Docs: https://developers.openai.com/codex/config-reference (`model_auto_compact_token_limit`, `compact_prompt`, `experimental_compact_prompt_file`)
- **WRITE:**
  - *Local path* (non-OpenAI providers, `RemoteCompactionSupport::Unsupported`): the compaction prompt is appended as a user turn to the full history. The model's reply becomes the summary text, which is stored as a user message prefixed with SUMMARY_PREFIX: "Another language model started to solve this problem and produced a summary of its thinking process. … Here is the summary produced by the other language model…"
  - *Remote path* (OpenAI provider, `RemoteCompactionSupport::V2`): the history plus a `CompactionTrigger` item go to the Responses API. It returns exactly one opaque `Compaction{encrypted_content}` item.
- **UPDATE:** History is replaced with [re-injected initial context] + [verbatim recent user messages] + [new summary]:
  - Local keeps the most recent real user messages up to `COMPACT_USER_MESSAGE_MAX_TOKENS = 20_000`.
  - Remote keeps user/developer messages up to `RETAINED_MESSAGE_TOKEN_BUDGET = 64_000`.
  - Previous summary messages are explicitly excluded from the verbatim retention (`if is_summary_message(&message) { return None; }`, compact.rs L591), so only the newest summary survives.
- **FORGET / EXPIRE:** Everything not in the summary or the retained user-message budget is dropped (assistant turns, tool calls and outputs). If compaction itself overflows, the oldest items are removed first ("removing oldest history item").
- **RETRIEVE:** Full context.
- **COMPACTION TRIGGER:**
  - Auto when active tokens ≥ `auto_compact_token_limit`, which defaults to 90% of the model context window (`(context_window * 9) / 10`) or `model_auto_compact_token_limit` if lower.
  - A scope option `body_after_prefix` counts only growth after the carried prefix.
  - Optional post-turn compaction at `model_post_turn_compact_threshold_percent`.
  - Also triggered on a model downshift to a smaller window (`CompactionReason::ModelDownshift`).
  - Manual `/compact`. PreCompact/PostCompact hooks.
  - A "TokenBudget" feature mode skips summarization and starts a fresh window (compact_token_budget.rs).
- **ITERATED REWRITE CHAIN?:** YES. On the local path the summarizer input is the full current history, which contains the previous summary (as a user message) plus all later turns. The new summary replaces the old one, and the prompt does not tell the model a previous summary exists. On the remote path the previous `Compaction` item is part of the input and is not retained, so the chain is also iterated, but encrypted and unobservable. The code prints a user-facing warning after each local compaction: "Heads up: Long threads and multiple compactions can cause the model to be less accurate. Start a new thread when possible to keep threads small and targeted." (compact.rs L422)
- **WHICH CHANNEL:** Transformation (summary) plus rule-based selection (keep recent raw user messages within the token budget).
- **DEFAULT PROMPTS:** `prompts/templates/compact/prompt.md`: "You are performing a CONTEXT CHECKPOINT COMPACTION. Create a handoff summary for another LLM that will resume the task. Include: Current progress and key decisions made; Important context, constraints, or user preferences; What remains to be done (clear next steps); Any critical data, examples, or references needed to continue. Be concise, structured, and focused on helping the next LLM seamlessly continue the work." It can be replaced with config `compact_prompt` (inline) or `experimental_compact_prompt_file`. The remote prompt is server-side and unknown.
- **RUNNABLE FOR EXPERIMENTS:** Yes. Open source, with built-in `ollama` and `lmstudio` providers, and any OpenAI-compatible provider via config. Non-OpenAI providers take the local, readable-text compaction path with a replaceable prompt.
- **MULTI-AGENT:** Sub-agent sessions are excluded from the memory pipeline. The guardian/reviewer sub-session disables auto-compact (`guardian/review.rs:166`).
- **UNCERTAIN:** What the server-side (remote) compactor does internally (encrypted).

### 3b. OpenAI Codex CLI: Memories (two-phase extraction and consolidation)
- **Type:** coding agent cross-session memory (open source)
- **Checked:** 2026-10-06, commit 822e58cc3d66, Apache-2.0. Feature flag `memories`, stage Stable, `default_enabled: false` (`features/src/lib.rs` ~L1231).
- **Sources:**
  - `codex-rs/memories/README.md`
  - `codex-rs/memories/write/templates/memories/{stage_one_system.md, stage_one_input.md, consolidation.md, consolidation_v2.md}`
  - `codex-rs/ext/memories/templates/memories/read_path.md`
  - `codex-rs/config/src/types.rs` (L55–60, L325–390)
  - Docs: https://developers.openai.com/codex/memories
- **WRITE:**
  - *Phase 1* (per-rollout LLM extraction, run in parallel): produces `raw_memory`, `rollout_summary` and `rollout_slug` for recent, idle rollouts. Defaults: age ≤10 days, idle ≥6h, ≤2 rollouts per startup, skipped when rate-limit headroom is <25%. Results are stored in the state DB.
  - *Phase 2*: syncs the selected stage-1 outputs into `~/.codex/memories/{raw_memories.md, rollout_summaries/}` and computes a git diff against the last successful baseline (`phase2_workspace_diff.md`). It then spawns a consolidation sub-agent that edits `MEMORY.md`, `memory_summary.md` and `skills/`.
- **UPDATE:** In-place incremental rewrite by an agent. The prompt has INIT and INCREMENTAL UPDATE modes. INCREMENTAL: "Read existing `MEMORY.md` and … existing `memory_summary.md` first for continuity" (L783), then "Integrate new signal into existing artifacts by: updating existing knowledge with better/newer evidence; updating stale or contradicting guidance; … doing light clustering and merging …; freely restructuring `memory_summary.md`…". The v2 variant rewrites only `memory_summary.md` (<10,000 bytes).
- **FORGET / EXPIRE:**
  - Rule-based selection: stage-1 memories unused for >`max_unused_days` (30) drop out of Phase-2 input; at most 256 raw memories are kept, ranked by `usage_count` then recency. Stale `rollout_summaries/` files are pruned.
  - LLM-propagated deletion: "deleted `rollout_summaries/*.md` … = forgetting / stale-cleanup queue … surgically delete or rewrite only the unsupported memory".
  - v2 adds: "do not restore corrected or deleted claims from older summaries."
- **RETRIEVE:** `memory_summary.md` is injected into the developer prompt at session start. The agent greps `MEMORY.md`, then opens rollout summaries or skills on demand (`read_path.md`: "Skim the MEMORY_SUMMARY … Search MEMORY.md using those keywords…"). Usage citations feed back into `usage_count`.
- **COMPACTION TRIGGER:** A background job at root-session startup, when the session is non-ephemeral, the feature is on, the session is not a sub-agent, and the state DB is available. Phase 2 runs only if the git workspace is dirty, under a global lock.
- **ITERATED REWRITE CHAIN?:** YES. Each Phase 2 run reads the previous `MEMORY.md` and `memory_summary.md` that an LLM wrote and produces a new version; this repeats at every startup that brings new rollouts. Phase 1 summaries are per rollout and not iterated. The prompt explicitly guards against abstraction drift (consolidation.md):
  - L364: "Do not rewrite concrete wording into more abstract synonyms when the original wording fits. Bad: `the user prefers evidence-backed debugging` Better: `when debugging, the user asked / corrected: "…" -> …`"
  - L367: "If several sources say nearly the same thing, merge by keeping one of the original phrasings … rather than inventing a new umbrella sentence."
  - L372: "Keep original wording by default."
  - L815: "Minimize churn in incremental mode."
  - Elsewhere: "Preserve epistemic status when consolidating."
  - v2: "Overly broad or rigid rules inferred from past tasks can therefore mislead future agents."
  - The baseline is versioned with git (`~/.codex/memories/.git`).
- **WHICH CHANNEL:** Both. Transformation (cluster, merge, rewrite) and selection (usage/recency-ranked input selection, deletion propagation).
- **DEFAULT PROMPTS:** The template files listed above (consolidation.md is 880 lines; stage_one_system.md is 569). They are compiled in (`include_str!`). Changing the text requires editing source, but `extract_model` and `consolidation_model` are configurable.
- **RUNNABLE FOR EXPERIMENTS:** Yes, with source access and local providers. It is a ready-made production "consolidation loop" whose chain length grows by one per qualifying startup. A near-identical port exists in openai-agents-python (`src/agents/sandbox/memory/prompts/memory_consolidation_prompt.md`, same "Do not rewrite concrete wording…" rule at L348, MIT).
- **MULTI-AGENT:** Private per user (`~/.codex`). Sub-agent sessions are excluded as inputs.
- **UNCERTAIN:** Whether v1 or v2 is the shipping default for the desktop app; `MemoryVersion::V1` is the code default.

### 4. OpenAI Responses API compaction and the OpenAI Agents SDK sessions
- **Type:** API feature plus library
- **Checked:** 2026-10-06. Docs at https://developers.openai.com/api/docs/guides/compaction; openai-agents-python d7e52c37 (MIT)
- **Sources:**
  - OpenAI compaction guide (server-side `context_management` and standalone `/responses/compact`)
  - `openai-agents-python/src/agents/memory/openai_responses_compaction_session.py` (L36, L46–69, L91–170, L449)
- **WRITE:** The server produces an "encrypted compaction item [that] carries forward key prior state and reasoning … It is opaque and not intended to be human-interpretable."
- **UPDATE:** Replace. Server-side mode: "after appending output items … you can drop items that came before the most recent compaction item". Standalone `/responses/compact` returns "a new compacted context window" that "can also include retained items from the previous window".
- **FORGET / EXPIRE:** Server-decided, and opaque.
- **RETRIEVE:** Full context (compaction item plus retained items).
- **COMPACTION TRIGGER:**
  - Server-side: `context_management=[{"type":"compaction","compact_threshold":N}]`; the server compacts mid-stream when rendered tokens cross N (docs example uses 200,000).
  - Agents SDK `OpenAIResponsesCompactionSession`: after each turn, by default when ≥10 candidate items exist (`DEFAULT_COMPACTION_THRESHOLD = 10`). User messages and existing compaction items are excluded from the candidate count. A custom `should_trigger_compaction` hook can replace the rule.
- **ITERATED REWRITE CHAIN?:** YES (inferred). The latest compaction item is part of the next compaction's input, and the newest item supersedes it. The content is encrypted, so drift cannot be observed directly. The docs do not state the "summary-of-summary" behavior verbatim.
- **WHICH CHANNEL:** Transformation (opaque) plus selection (retained items).
- **DEFAULT PROMPTS:** Server-side and unpublished. Not replaceable.
- **RUNNABLE FOR EXPERIMENTS:** OpenAI models only (the SDK validates `gpt-*` / `o*` model names). It is opaque and of little use for measuring content drift, but it could be used for behavioral probes.
- **MULTI-AGENT:** N/A.
- **UNCERTAIN:** The server prompt; whether a later compaction decrypts and re-summarizes the earlier item or carries some of it forward.

### 5. Gemini CLI: chat compression (plus memory files and auto memory)
- **Type:** coding agent (open source)
- **Checked:** 2026-10-02 commit fb972b2f87fe (v0.64.0-nightly), Apache-2.0
- **Sources** (paths under `packages/core/src/`):
  - `context/chatCompressionService.ts` (L45, L269, L282–312, L480–721; anchor at L591; probe at L632)
  - `prompts/snippets.ts` (`getCompressionPrompt`, L898–990), plus `prompts/snippets.legacy.ts` for older models
  - `core/client.ts` L703 (auto call), L1210 (`tryCompressChat`)
  - Experimental pipeline: `context/initializer.ts`, `context/utils/snapshotGenerator.ts` (L182+), `context/processors/rollingSummaryProcessor.ts`
  - Memory: `services/memoryService.ts` (L56–57), `agents/skill-extraction-agent.ts` (L60–91)
  - Docs: `docs/cli/settings.md` (`model.compressionThreshold`), `docs/cli/auto-memory.md`
- **WRITE:**
  - Compression: an LLM writes a structured XML `<state_snapshot>` with fields overall_goal, active_constraints, key_knowledge, artifact_trail, file_system_state, recent_actions and task_state. Before this, big tool outputs in old turns are truncated to a 50k-token function-response budget.
  - Memory: the agent edits `GEMINI.md`, the private project `MEMORY.md` or the global memory file directly with edit/write tools. "There is no `save_memory` tool."
  - Auto Memory (experimental, off by default): a background agent mines idle sessions (≥10 user messages, idle ≥3h) and writes unified-diff `.patch` proposals to an inbox. "Nothing is applied automatically; the user must approve each patch."
- **UPDATE:** Compression replaces the oldest ~70% of history (split at a user-turn boundary, `COMPRESSION_PRESERVE_THRESHOLD = 0.3` kept verbatim) with [snapshot as user msg, "Got it. Thanks for the additional context!"] followed by the recent 30%. The result is rejected if the new token count exceeds the old one.
- **FORGET / EXPIRE:** Whatever is left out of the snapshot. After one failed summarization attempt, later automatic attempts only truncate. Memory files are edited by the LLM or the user, and Auto Memory patches go through human review.
- **RETRIEVE:** Full context. Memory files are always loaded (global, project, private index); sibling memory files are read on demand.
- **COMPACTION TRIGGER:** Auto before each turn when the last prompt token count ≥ `model.compressionThreshold` × model token limit, default **0.5**. Manual `/compress` (forced). PreCompress hook.
- **ITERATED REWRITE CHAIN?:** YES, and handled explicitly. The previous snapshot lies in the history being compressed. The code detects it and switches instruction: "A previous <state_snapshot> exists in the history. You MUST integrate all still-relevant information from that snapshot into the new one, updating it with the more recent events. Do not lose established constraints or critical knowledge." A second self-verification call follows: "Critically evaluate the <state_snapshot> you just generated. Did you omit any specific technical details, file paths, tool results, or user constraints …? … generate a FINAL, improved <state_snapshot>. Otherwise, repeat the exact same <state_snapshot> again."
  - The experimental context pipeline (`contextManagement.enabled`, default false) uses a different design. A "Master State" JSON is updated by **delta patch ops** (`new_facts`, `new_constraints`, `new_tasks`, `resolved_task_ids`, `obsolete_fact_indices`, `obsolete_constraint_indices`, `chronological_summary`). It is not regenerated wholesale, and a pressure warning tells the LLM to "aggressively prune" when the state exceeds 80% of 4000 tokens.
  - That pipeline also has a `RollingSummaryProcessor` ("drastically shorten … Return ONLY the compressed summary").
- **WHICH CHANNEL:** Default compression is transformation (full rewrite plus a self-verification rewrite). The experimental pipeline combines selection ops (obsolete indices) with append-only additions. Auto Memory proposes diffs and a human selects.
- **DEFAULT PROMPTS:** `prompts/snippets.ts::getCompressionPrompt`: "This snapshot is CRITICAL, as it will become the agent's *only* memory of the past. The agent will resume its work based solely on this snapshot. All crucial details, plans, errors, and user directives MUST be preserved. … Be incredibly dense with information." Not configurable through settings (hardcoded; changing it requires editing code). Compression uses model aliases `chat-compression-*` that mirror the active model.
- **RUNNABLE FOR EXPERIMENTS:** Open source, but Gemini API / Vertex only. There is no native OpenAI-compatible backend (forks may exist; UNVERIFIED). The code is easy to port, and the anchor-plus-probe design is a natural ablation arm.
- **MULTI-AGENT:** Subagents (`agents/local-executor.ts`) have their own ChatCompressionService instance.
- **UNCERTAIN:** Whether the legacy-model compression prompt differs materially (not compared).

### 6. ChatGPT memory (saved memories, reference chat history, "improved memory")
- **Type:** product (closed)
- **Checked:** 2026-10-06. OpenAI Help Center "Memory in ChatGPT" (help.openai.com/en/articles/8590148-memory-faq, fetched through a reader proxy because the direct fetch returned 403).
- **Sources:** that article only. The OpenAI blog was not reachable (403).
- **WRITE:** "Saved memories are details that you explicitly ask ChatGPT to remember or that ChatGPT saves as useful context." Memory sources can include past chats, saved memories, custom instructions, Library files and connected apps.
- **UPDATE:**
  - "**Improved Memory continually updates a broader summary of relevant context.** Legacy saved memories use a more explicit list of individual memory items."
  - "Unlike an explicit saved memory, information derived from chat history can change as ChatGPT updates what is most useful to remember."
  - A user-visible "memory summary" can be corrected in place.
  - Saved-memory controls "can also include search, sorting, automatic prioritization, and version history."
- **FORGET / EXPIRE:** The user deletes items or entire chats. "Don't mention this again" suppresses an item without deleting it. Automatic prioritization exists, but its mechanism is not described. Turning off reference chat history deletes derived information within 30 days.
- **RETRIEVE:** "ChatGPT looks for relevant context when it is likely to improve a response." The mechanism is unpublished. "Sources" may be shown under a response.
- **COMPACTION TRIGGER:** Unpublished ("continually").
- **ITERATED REWRITE CHAIN?:** LIKELY YES / PARTIAL. "Improved memory" is described as a continually updated summary, which implies repeated rewriting of a summary. The implementation is UNVERIFIED. Legacy saved memories are discrete items (append, delete, user edit), so not an iterated summary.
- **WHICH CHANNEL:** Transformation (summary) plus selection (prioritization), both opaque.
- **DEFAULT PROMPTS:** Unpublished.
- **RUNNABLE FOR EXPERIMENTS:** No. Black-box probing only.
- **MULTI-AGENT:** Project-only memory scoping exists for some workspace plans.
- **UNCERTAIN:** Update cadence, whether the summary is regenerated from raw chats or from the previous summary, and how prioritization works.

### 7. Claude (claude.ai) memory and chat search
- **Type:** product (closed)
- **Checked:** 2026-10-06, support.claude.com/en/articles/11817273 (fetched through a reader proxy)
- **Sources:** that article, including its "Information for legacy memory users" section.
- **WRITE:**
  - Current: "Claude saves memory as a set of individual topics as you chat, rather than summarizing conversations after they end. … Claude saves on its own, and you can also tell Claude to 'remember this'."
  - Each project has its own memory space and project summary. Memory is shared between chat and Cowork tasks.
  - Sensitive topics are not stored by default.
- **UPDATE:** Topic-level updates during chat ("Mention that a deadline moved, and your next conversation already knows"). Users can edit or delete topics in Settings > Memory, or say "remember / change / forget" in a chat.
  - Legacy design (still documented): "Claude will automatically summarize your conversations and create a synthesis of key insights across your chat history … This synthesis is updated every 24 hours."
- **FORGET / EXPIRE:** User deletion; Claude's in-chat changes on request; org-level off deletes everything.
- **RETRIEVE:** Memory is loaded into new chats (mechanism unpublished). Past-chat search is RAG, shown as tool calls with citations.
- **COMPACTION TRIGGER:** Current: in-chat, per topic. Legacy: a daily (24h) re-synthesis.
- **ITERATED REWRITE CHAIN?:**
  - Legacy: YES, likely. A synthesis regenerated every 24h is a periodic rewrite, but whether it reads the previous synthesis or the raw chats is UNVERIFIED.
  - Current: PARTIAL. Topic entries are updated in place, so a single topic can be rewritten many times, but the whole store is not resummarized.
- **WHICH CHANNEL:** Transformation per topic, plus user-driven selection.
- **DEFAULT PROMPTS:** Unpublished.
- **RUNNABLE FOR EXPERIMENTS:** No.
- **MULTI-AGENT:** Shared between chat and Cowork; per-project scoping.
- **UNCERTAIN:** Internals of the topic updates (full topic rewrite or diff).

### 8. OpenHands (software-agent-sdk): LLMSummarizingCondenser
- **Type:** coding agent framework (open source)
- **Checked:** 2026-10-06, OpenHands/software-agent-sdk 6f8c38d00e04 (openhands-sdk 1.53.0), MIT
- **Sources** (paths under `openhands-sdk/openhands/sdk/`):
  - `context/condenser/README.md` (L8)
  - `context/condenser/llm_summarizing_condenser.py` (L64–84, L205–276, L278–353)
  - `context/condenser/prompts/summarizing_system.j2`, `summarizing_events.j2`
  - `event/condenser.py` (`CondensationSummaryEvent` L120)
  - `settings/model.py` (L160–309)
- **WRITE:** An LLM summary of the "forgotten" events, inserted as a `CondensationSummaryEvent` (user role) at `summary_offset`. The event log stays append-only: a `Condensation` tombstone records the forgotten IDs and the summary.
- **UPDATE:** Rolling. The head of the view (after `keep_first=2` protected events) up to the middle is forgotten and replaced by one summary; the tail stays verbatim.
- **FORGET / EXPIRE:** Rule-based and count/token driven. The view is cut to half of `max_size` events, or to half of `max_tokens`. A "hard context reset" summarizes the whole view on explicit requests or context-window errors.
- **RETRIEVE:** Full context.
- **COMPACTION TRIGGER:** View length > `max_size` (default 240 events), total tokens > `max_tokens` (default: the agent LLM's effective max input), or an explicit request from the user or agent. The condenser is enabled by default in settings.
- **ITERATED REWRITE CHAIN?:** YES, by design and documented. README: "events are summarized, and summaries are also summarized in future condensations, so important information stays in the context." System prompt: "You will be given a list of events … which will include previous summaries." The summary is placed at the start of the forgettable range, so the next condensation always re-summarizes it.
- **WHICH CHANNEL:** Transformation plus rule-based selection (which events).
- **DEFAULT PROMPTS:** `summarizing_system.j2`: "You are maintaining a context-aware state summary for an interactive agent." It tracks USER_CONTEXT, TASK_TRACKING ("PRESERVE TASK IDs"), COMPLETED, PENDING, CURRENT_STATE, CODE_STATE, TESTS, CHANGES, DEPS and VERSION_CONTROL_STATUS. "PRIORITIZE: … Keep all sections concise and relevant." The Jinja templates can be replaced by editing them or subclassing `_build_summary_messages`.
- **RUNNABLE FOR EXPERIMENTS:** Yes, and the best-suited of the open-source agents. It runs on LiteLLM, so any OpenAI-compatible or local model works, and it can use a separate condenser LLM. The append-only log keeps every forgotten raw event, which gives ground truth for measuring drift.
- **MULTI-AGENT:** Per-conversation.
- **UNCERTAIN:** None material.

### 9. Aider: ChatSummary (recursive chat-history summarization)
- **Type:** coding agent (open source)
- **Checked:** commit 5dc9490bb35f (2026-05-22, 0.86.3.dev), Apache-2.0
- **Sources:**
  - `aider/history.py` (L7–123)
  - `aider/prompts.py` (L46–61)
  - `aider/coders/base_coder.py` (L1002–1038)
  - `aider/main.py` (L949–951)
  - `aider/models.py` (L339, L358)
- **WRITE:** When `done_messages` (past exchanges) exceed the budget, a background thread summarizes the older head. The summary is a user message prefixed "I spoke to you previously about a number of things.\n", followed by an assistant "Ok.".
- **UPDATE:** The head is replaced by the summary and the tail (< max_tokens/2) is kept verbatim. If summary + tail still exceed the budget, the process recurses on (summary + tail) up to depth 3, then falls back to `summarize_all`.
- **FORGET / EXPIRE:** Implicit, through summarization. The prompt instructs recency-weighted loss.
- **RETRIEVE:** Full context. The repo map and files are re-sent separately.
- **COMPACTION TRIGGER:** Token count of the chat history > `max_chat_history_tokens` = min(max(max_input_tokens/16, 1024), 8192), or `--max-chat-history-tokens`. It is checked after every exchange, so in long sessions compaction fires very often.
- **ITERATED REWRITE CHAIN?:** YES, strongly. The previous summary message sits at the head of `done_messages` and is re-summarized each time the budget is exceeded, and within one call the recursion can re-summarize the fresh summary again (depth ≤3). By default the weak model (`[main_model.weak_model, main_model]`) does the summarizing.
- **WHICH CHANNEL:** Transformation.
- **DEFAULT PROMPTS:** `aider/prompts.py` `summarize`: "*Briefly* summarize this partial conversation about programming. **Include less detail about older parts and more detail about the most recent messages.** … The summary *MUST* include the function names, libraries, packages that are being discussed. … Phrase the summary with the USER in first person … Start the summary with 'I asked you...'." Replacing it requires a code edit.
- **RUNNABLE FOR EXPERIMENTS:** Yes, via LiteLLM (any OpenAI-compatible or local model). It is the cheapest high-iteration-count testbed: a small budget means many summary-of-summary passes, and the "less detail about older parts" instruction builds geometric decay of old content into the prompt.
- **MULTI-AGENT:** N/A.
- **UNCERTAIN:** None material.

### 10. Cline (VS Code extension and CLI on the Cline SDK): agentic compaction
- **Type:** coding agent (open source)
- **Checked:** 2026-10-06, commit dec80dadfa4f (VS Code ext 4.1.22), Apache-2.0
- **Sources:**
  - `sdk/packages/core/src/extensions/context/agentic-compaction.ts` (L69–150)
  - `.../compaction-shared.ts` (L13–27, L318, L669–703)
  - `.../compaction.ts` (L285–300)
  - `.../basic-compaction.ts`
  - `apps/vscode/src/sdk/cline-session-factory.ts` (L1122–1128)
  - `apps/vscode/src/shared/storage/state-keys.ts` (L277, `useAutoCondense` default true)
  - `apps/vscode/src/core/controller/slash/condense.ts`
- **WRITE:** The default "agentic" strategy calls the summarizer with the system line "Summarize the provided coding session into a concise continuation note with detailed next steps." The request uses fixed sections (Goal, State: Done/In Progress/Blocked, Highlights, Next, Files Read/Edited). Thinking is disabled for the summarizer, and output is capped (default 8192).
- **UPDATE:** Messages before the cut index are replaced by a summary message (with metadata); the last `DEFAULT_PRESERVE_RECENT_TOKENS = 20_000` stay verbatim. The file-operation lists are computed programmatically, not by the LLM.
- **FORGET / EXPIRE:** Content before the cut that is not in the summary. The "basic" strategy is deterministic (truncation plus a tool-activity summary, no LLM).
- **RETRIEVE:** Full context.
- **COMPACTION TRIGGER:** Transcript ≥ `COMPACTION_TRIGGER_RATIO = 0.9` of the usable input budget, which is itself 0.9 × context window when only the window is known. Target ratio 0.7; 0.5 for long conversations. Manual `/compact`, `/smol`, or the condense command (target 0.5).
- **ITERATED REWRITE CHAIN?:** YES, and explicit. `findLatestSummaryIndex` locates the previous summary; only messages after it are serialized as "Conversation", and the old summary is passed as "Previous summary:\n…" in the same request (compaction-shared.ts L696–697). The new summary replaces it. This is an incremental summarizer, S_t = f(S_{t-1}, new turns).
- **WHICH CHANNEL:** Transformation plus rule-based selection (recent-token preservation, programmatic file lists).
- **DEFAULT PROMPTS:** `buildSummaryRequest` in compaction-shared.ts (L669–703). Replaceable via a custom `compaction.compact` function, a separate summarizer provider config, or the `basic` strategy.
- **RUNNABLE FOR EXPERIMENTS:** Yes, with many providers including OpenAI-compatible, Ollama and LM Studio.
- **MULTI-AGENT:** Spawned agents are disabled in the VS Code session factory by default.
- **UNCERTAIN:** Older Cline releases (pre-SDK `summarize_task` / condense prompt) were not examined.
