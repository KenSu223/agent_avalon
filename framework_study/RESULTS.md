# Does agent memory regress to the prior? An empirical study on 11 memory systems

2026-10-06. Everything here is reproducible from `framework_study/` (stimuli, code, raw results).

**Bedrock spend for this phase:** about $17.7, all through the budget proxy. Cumulative spend is $38.47 against a hard cap of $140.

## 1. Data: counter-schema minimal pairs (Bartlett-style)

### Items
`stimuli/items.jsonl` has 44 hand-written minimal pairs:

| Type | Count | Example |
|---|---|---|
| Counter-schema rules | 30 | "big files upload faster/more slowly than small ones" |
| Order-inverted procedures | 6 | — |
| User formatting preferences | 8 | Both levels are real instructions; neither is a null preference |

How the items are built:
- Each item is mentioned **in passing** while Sam asks Atlas for help with something unrelated.
- The two versions differ only in the swapped words. Neither version carries "actually" or a reason clause.
- Items whose incongruent version describes a bad practice are tagged `normative`.

### Validation

**V1, prior strength**, measured with 20 forced-choice samples:

| Model | Schema strength |
|---|---|
| Qwen3-235B | P(congruent) ≥ 0.9 for 43/44 items; P06 = 0.80 |
| gpt-oss-120b | Agrees, with two model-specific exceptions |
| Llama-3.3-70B | Agrees, with three weaker schemas (0.4–0.5) |

**V2, comprehension.** The model hears the item and is asked about it right away.
- Comprehension is near-perfect.
- One item fails on all three models: S08, "back up after the upgrade". The model rewrites it as the normative version, so S08 is excluded.
- During development two more items were removed:
  - S02, "delete the old key first", was explicitly "corrected" by the model.
  - S06 had a schema direction that depends on the model.

**V3, Bartlett positive control** (`results/v3_coded.jsonl`). Setup: 30 note sets × 8 items, 6 generations, Qwen3-235B at T=1.

| Condition | I → C (regularisation) | C → I | Difference, 95% CI |
|---|---|---|---|
| Narrative, serial retelling | 0% | 0% | — (loss is deletion only) |
| Narrative, compress to gist and expand | **4%** | 0% | +4.2 pp [+0.9, +7.9] |
| Explicit list, serial retelling | **5%** | 0% | +5.0 pp [+0.9, +9.7] |

Distortion is strictly one-directional, toward the schema. The stimuli can elicit Bartlett-style rationalisation, but a strong model does it rarely. Judges agree 0.908 of the time.

## 2. Framework study

### Design
43 simulated users per system.
- Each user receives 8 items, counterbalanced C/I, so each item appears about 4× as C and 4× as I.
- Each user has 4 seeding sessions (2 items each), followed by 12 unrelated distractor sessions. The distractors are freshly generated and topic-scrubbed.
- Memory is updated after every session.
- Memory is measured at k = 0, 2, 4, 8 and 12 distractor sessions.
- Every system is driven by Qwen3-235B-A22B (T=0).

### Measures
**Memory state.** Two judges from other model families (gpt-oss-120b, gemma-3-27b) read the full memory dump. Each item is labelled RETAINED, DROPPED or FLIPPED. Only labels the two judges agree on are counted. Agreement is 0.983 over 20,640 judgments.

**Belief.** The agent answers a forced-choice question from the system's own retrieved context.

### Systems
**Libraries, using their own code:**
- mem0ai 2.2.1, append-only, with `[extras,nlp]`, telemetry off, and `get_all` uncapped. Its default `top_k=20` truncated the first run; that run is kept as `capped20_*` and not used.
- mem0ai 1.0.11, with LLM UPDATE/DELETE.
- langmem 0.0.30 `create_memory_manager`, with inserts, updates and deletes.
- llama-index-core 0.14.25 `FactExtractionMemoryBlock`. **max_facts = 12**; the default is 50.
- langchain 1.4.3 `SummarizationMiddleware`, on its prompt path.

**Products, using verbatim prompts and message framing at pinned commits:**
- Codex local compaction (822e58c)
- OpenHands LLMSummarizingCondenser (6f8c38d)
- Aider ChatSummary (5dc9490)
- Gemini CLI compression (fb972b2)
- Anthropic API documented default compaction prompt

**Reference conditions:**
- A neutral rewrite.
- The raw transcript, which serves as the ceiling.

### Results at k = 12
Bootstrap CIs are over users. `results/summary_*.txt` holds every checkpoint and the per-item-type subsets.

| System | Retained C | Retained I | Flip asym. I−C | Belief kept C | Belief kept I | Belief gap C−I [95% CI] |
|---|---|---|---|---|---|---|
| raw transcript (ceiling) | 1.00 | 1.00 | 0.000 | 1.00 | 0.99 | +0.01 [+0.00, +0.02] |
| mem0 1.0.11 (local UPDATE) | 0.91 | 0.94 | 0.000 | 0.99 | 0.95 | +0.04 [+0.01, +0.08] |
| mem0 2.2.1 (append-only) | 0.77 | 0.73 | 0.000 | 0.99 | 0.72 | +0.27 [+0.21, +0.34] |
| neutral rewrite | 0.73 | 0.73 | 0.000 | 0.98 | 0.74 | +0.24 [+0.12, +0.37] |
| Gemini CLI | 0.45 | 0.54 | 0.000 | 0.96 | 0.58 | +0.38 [+0.24, +0.51] |
| LlamaIndex facts | 0.45 | 0.47 | +0.006 | 0.98 | 0.52 | +0.46 [+0.33, +0.59] |
| LangMem | 0.52 | 0.45 | 0.000 | 0.99 | 0.45 | +0.54 [+0.39, +0.68] |
| LangChain summarization | 0.13 | 0.15 | 0.000 | 0.95 | 0.17 | +0.78 [+0.68, +0.88] |
| OpenHands condenser | 0.15 | 0.15 | 0.000 | 0.98 | 0.17 | +0.80 [+0.70, +0.89] |
| Anthropic API compaction | 0.08 | 0.11 | 0.000 | 0.98 | 0.15 | +0.84 [+0.75, +0.91] |
| Codex compaction | 0.06 | 0.07 | 0.000 | 0.96 | 0.12 | +0.84 [+0.75, +0.92] |
| Aider ChatSummary | 0.00 | 0.00 | 0.000 | 0.97 | 0.01 | +0.96 [+0.93, +0.99] |

### Mechanism
`results/decompose.txt` breaks belief down by memory state, pooled over k ≥ 2:

| Memory state | Belief kept, C | Belief kept, I |
|---|---|---|
| Item retained | ≈1.00 | ≈1.00 |
| Item dropped | 0.91–0.98 (the prior supplies the right answer) | 0.02–0.12 (the agent falls back to the schema) |

98–100% of all I-belief losses come from deletion, not from rewriting.

## 3. What this says

1. **Memory text does not regress to the prior.** Across all 11 systems:
   - Retention is the same for schema-congruent and counter-schema items. Every retention-gap CI contains 0 except Gemini CLI, where counter-schema descriptive items are kept *better*: −13.8 pp [−23.3, −3.3], a von Restorff-like salience effect.
   - Rewriting toward the schema ("flips") is essentially absent in production pipelines (≤1%). It appears only in the gist-reconstruction positive control.
2. **The agent's knowledge does regress to the prior.**
   - Deletion is prior-blind, but reconstruction from the prior is not. Losing a congruent fact costs nothing; losing a counter-schema fact makes the agent answer the default.
   - The belief gap therefore scales with each system's deletion rate. It runs from +0.04 for Mem0 1.0.11 to +0.96 for Aider.
   - This is "memory converges to the prior" at the level of what the agent believes, not of what memory stores.
3. **What drives deletion is the scope of rewriting, not whether rewriting happens.**
   - Mem0 1.0.11 rewrites, but only memories similar to the new input. Unrelated items are never touched, so it is the most stable system.
   - Whole-memory rewrites lose most items within a few sessions: LangChain, Codex, OpenHands, Anthropic, Aider, and the condense step in LlamaIndex.
   - Mem0 2.2.1 loses items only at extraction time (k = 0); after that its retention is flat.

Short version: memory forgets symmetrically, and the prior forgets selectively.

## 4. Caveats
- **One compactor model.** Everything uses Qwen3-235B; V3 shows that a strong model rarely rewrites. Weaker or smaller compactors may flip more, and this has not been tested yet.
- **Forced compaction.** Compaction runs after every session, which simulates long horizons. Real products trigger on token thresholds.
- **Non-default LlamaIndex setting.** `max_facts` is 12 rather than 50.
- **Product replicas are partial.** They reproduce each product's prompt and message framing. They do not reproduce the rest of the harness: tool outputs, re-injected files, or Aider's verbatim tail.
- **Belief is forced choice.** No abstention was allowed.
- **No human validation.** Two LLM judges stand in, with agreement 0.983. FLIPPED is counted only when both judges agree, which is conservative; one judge (Gemma) occasionally "regularised" items itself.
- **Narrow distractors.** Distractor sessions are unrelated chats, so nothing competes with or contradicts the items.
