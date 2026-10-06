# Per-system record (one block per system)

### <System name>
- Type: library / research system / product / coding agent / multi-agent framework
- Checked: <date>, version/commit, license
- Sources: URLs (paper section, docs page, source file paths with line refs)
- WRITE: what triggers a write; raw text vs LLM extraction; granularity (turn, fact, note, summary block)
- UPDATE: append-only / in-place rewrite (LLM reads old memory, writes new version) / merge with ops (list exact ops) / invalidate with timestamps / learned policy
- FORGET / EXPIRE: mechanism (time decay, LLM-judged importance, LLM DELETE op, TTL, capacity eviction, none); who decides (LLM / rule / learned)
- RETRIEVE: mechanism (embedding, BM25, graph, recency/importance weighting, full-context)
- COMPACTION TRIGGER: when consolidation runs (token threshold, session end, background job, every N turns, explicit tool call)
- ITERATED REWRITE CHAIN?: YES / PARTIAL / NO — does an LLM repeatedly read its own previous memory text and produce a new version (so content can drift over repeated passes)? Explain.
- WHICH CHANNEL: transformation (rewriting content) and/or selection (LLM decides keep/delete) and/or neither
- DEFAULT PROMPTS: where the consolidation/extraction prompts live (file path or URL), and whether they can be replaced
- RUNNABLE FOR EXPERIMENTS: open source? works with local models via OpenAI-compatible API? notes
- MULTI-AGENT: shared vs private memory; how sharing works (only if relevant)
- UNCERTAIN: anything you could not verify
