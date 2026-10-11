"""Memory-framework adapters. Every adapter implements

    ingest(session_messages)   # called once per session, in order
    dump() -> str              # everything the memory currently stores, as text
    context(question) -> str   # what the framework would put in the prompt for this question

Two kinds:
  * LIBRARY adapters run the framework's own code (Mem0, LangMem, LlamaIndex FactExtractionMemoryBlock,
    LangChain SummarizationMiddleware prompt path).
  * PRODUCT adapters replicate a product's compaction loop with its VERBATIM prompt and message framing
    (Codex, OpenHands, Aider, Gemini CLI, Anthropic API documented default). Compaction is forced after
    every session to simulate a long-running context; the prompt text is unchanged.

All LLM traffic goes through the budget proxy (Bedrock) or the local vLLM server; embeddings through the
local CPU embedding server.
"""
import json, os, re, sys, uuid, asyncio, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from infra.llm import chat

PROXY = "http://127.0.0.1:8787/v1"
EMBED = "http://127.0.0.1:8002/v1"
PROMPTS = ROOT / "framework_study/prompts"


def _render(messages):
    return "\n\n".join(f"{'Sam' if m['role'] == 'user' else 'Atlas'}: {m['content']}" for m in messages)


class Base:
    name = "base"

    def __init__(self, model, temperature=0.0):
        self.model, self.temperature = model, temperature

    def llm(self, messages, max_tokens=2048):
        return chat(self.model, messages, temperature=self.temperature, max_tokens=max_tokens)["text"]

    def context(self, question):
        return self.dump()


# ------------------------------------------------------------------ product replicas (verbatim prompts)

class Codex(Base):
    """codex-rs local compaction path @822e58cc3d66: history = [prior summary as a user message with SUMMARY_PREFIX]
    + new turns + compact prompt as the final user turn; the reply replaces the history."""
    name = "codex"

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.prompt = (PROMPTS / "codex_compact_prompt.md").read_text()
        self.prefix = (PROMPTS / "codex_summary_prefix.md").read_text().rstrip()
        self.summary = ""

    def ingest(self, msgs):
        hist = ([{"role": "user", "content": f"{self.prefix}\n{self.summary}"}] if self.summary else []) + msgs
        self.summary = self.llm(hist + [{"role": "user", "content": self.prompt}]).strip()

    def dump(self):
        return self.summary


class OpenHands(Base):
    """openhands-sdk LLMSummarizingCondenser @6f8c38d00e04: system = summarizing_system.j2, user = events
    (previous summary is one of the events) rendered with summarizing_events.j2."""
    name = "openhands"

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.system = (PROMPTS / "openhands_summarizing_system.j2").read_text()
        self.summary = ""

    def ingest(self, msgs):
        events = []
        if self.summary:
            events.append(f"CondensationSummaryEvent(summary={self.summary!r})")
        for m in msgs:
            src = "user" if m["role"] == "user" else "agent"
            events.append(f"MessageEvent(source={src!r}, content={m['content']!r})")
        body = "".join(f"\n<EVENT>\n{e}\n</EVENT>\n" for e in events) + "\nNow summarize the events using the rules above."
        self.summary = self.llm([{"role": "system", "content": self.system}, {"role": "user", "content": body}]).strip()

    def dump(self):
        return self.summary


class Aider(Base):
    """aider ChatSummary.summarize_all @5dc9490bb35f: '# USER' / '# ASSISTANT' transcript under the `summarize`
    system prompt; the result, prefixed with summary_prefix, becomes the head user message next time."""
    name = "aider"
    SUMMARIZE = None

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        src = (PROMPTS / "aider_prompts.py").read_text()
        ns = {}
        exec(src, ns)
        self.prompt, self.prefix = ns["summarize"], ns["summary_prefix"]
        self.head = None

    def ingest(self, msgs):
        msgs = ([self.head] if self.head else []) + msgs
        content = ""
        for m in msgs:
            content += f"# {m['role'].upper()}\n{m['content']}"
            if not content.endswith("\n"):
                content += "\n"
        out = self.llm([{"role": "system", "content": self.prompt}, {"role": "user", "content": content}]).strip()
        self.head = {"role": "user", "content": self.prefix + out}

    def dump(self):
        return self.head["content"] if self.head else ""


class GeminiCLI(Base):
    """gemini-cli chatCompressionService @fb972b2f87fe: system = getCompressionPrompt(); contents = history
    (previous snapshot included) + 'First, reason in your scratchpad. Then, generate the <state_snapshot>.'"""
    name = "gemini_cli"

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        ts = (PROMPTS / "gemini_snippets.ts").read_text()
        body = ts[ts.index("export function getCompressionPrompt"):]
        tpl = body[body.index("return `") + len("return `"):body.index("`.trim();")]
        self.system = tpl.replace("${planPreservation}", "").replace("\\`", "`").strip()
        self.snapshot = ""

    def ingest(self, msgs):
        hist = ([{"role": "user", "content": self.snapshot}, {"role": "assistant", "content": "Got it. Thanks for the additional context!"}]
                if self.snapshot else []) + msgs
        out = self.llm([{"role": "system", "content": self.system}] + hist +
                       [{"role": "user", "content": "First, reason in your scratchpad. Then, generate the <state_snapshot>."}], max_tokens=4096)
        m = re.search(r"<state_snapshot>.*?</state_snapshot>", out, re.S)
        self.snapshot = (m.group(0) if m else out).strip()

    def dump(self):
        return self.snapshot


class AnthropicAPI(Base):
    """Anthropic API compaction, documented threshold default prompt (platform docs, 2026-10-06), appended as a
    user turn after the history; the previous compaction block is part of the history."""
    name = "anthropic_api"
    PROMPT = ("You have written a partial transcript for the initial task above. Please write a summary of the transcript. "
              "The purpose of this summary is to provide continuity so you can continue to make progress towards solving the task "
              "in a future context, where the raw history above may not be accessible and will be replaced with this summary. "
              "Write down anything that would be helpful, including the state, next steps, learnings etc. "
              "You must wrap your summary in a <summary></summary> block.")

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.summary = ""

    def ingest(self, msgs):
        hist = ([{"role": "user", "content": f"<summary>{self.summary}</summary>"}] if self.summary else []) + msgs
        out = self.llm(hist + [{"role": "user", "content": self.PROMPT}])
        m = re.search(r"<summary>(.*?)</summary>", out, re.S)
        self.summary = (m.group(1) if m else out).strip()

    def dump(self):
        return self.summary


class LangChainSummary(Base):
    """langchain 1.4.3 SummarizationMiddleware._create_summary prompt path: DEFAULT_SUMMARY_PROMPT over the
    messages to summarise; the previous summary message ('Here is a summary of the conversation to date:')
    is among those messages next time."""
    name = "langchain_summary"

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        from langchain.agents.middleware import summarization as S
        self.S = S
        self.prompt = S.DEFAULT_SUMMARY_PROMPT
        self.summary_msg = None

    def ingest(self, msgs):
        from langchain_core.messages import HumanMessage, AIMessage
        from langchain_core.messages.utils import get_buffer_string
        lc = ([HumanMessage(content=self.summary_msg)] if self.summary_msg else []) + \
             [HumanMessage(content=m["content"]) if m["role"] == "user" else AIMessage(content=m["content"]) for m in msgs]
        text = self.prompt.format(messages=get_buffer_string(lc)).rstrip()
        out = self.llm([{"role": "user", "content": text}]).strip()
        self.summary_msg = f"Here is a summary of the conversation to date:\n\n{out}"

    def dump(self):
        return self.summary_msg or ""


class NeutralRoll(Base):
    """Our earlier neutral rewrite operator (O1), kept as a reference point."""
    name = "neutral_roll"
    SYSTEM = ("You are the memory manager for Atlas, an AI assistant that works with the same user across many sessions. "
              "After each session you rewrite Atlas's long-term memory notes. Future sessions will see only these notes, not the transcripts.")

    def __init__(self, *a, budget_words=None, **k):
        super().__init__(*a, **k)
        self.notes, self.budget = "", budget_words

    def ingest(self, msgs):
        lim = f" The notes must be at most {self.budget} words." if self.budget else ""
        self.notes = self.llm([{"role": "system", "content": self.SYSTEM},
                               {"role": "user", "content": f"CURRENT MEMORY NOTES:\n{self.notes or '(empty)'}\n\nTRANSCRIPT OF THE SESSION THAT JUST ENDED:\n{_render(msgs)}\n\nRewrite the memory notes so that they contain the information that will be useful in future sessions.{lim} Output only the new notes."}]).strip()

    def dump(self):
        return self.notes


class RawHistory(Base):
    """Ceiling: the full transcript, never compacted."""
    name = "raw_history"

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.msgs = []

    def ingest(self, msgs):
        self.msgs += msgs

    def dump(self):
        return _render(self.msgs)


# ------------------------------------------------------------------ libraries (their own code)

class Mem0(Base):
    """mem0ai (installed version) Memory.add / get_all / search with its default prompts."""
    name = "mem0"

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        os.environ["MEM0_TELEMETRY"] = "False"  # telemetry opens a shared local Qdrant under ~/.mem0 that cannot be used concurrently
        from mem0 import Memory
        d = tempfile.mkdtemp(prefix="mem0_")
        self.uid = "sam"
        cfg = {
            "llm": {"provider": "openai", "config": {"model": self.model, "openai_base_url": PROXY, "api_key": "proxy",
                                                       "temperature": self.temperature or 0.0, "max_tokens": 2000}},
            "embedder": {"provider": "openai", "config": {"model": "bge-small", "openai_base_url": EMBED, "api_key": "local",
                                                          "embedding_dims": 384}},
            "vector_store": {"provider": "qdrant", "config": {"collection_name": "m" + uuid.uuid4().hex[:8], "embedding_model_dims": 384,
                                                              "path": os.path.join(d, "qdrant"), "on_disk": False}},
            "history_db_path": os.path.join(d, "history.db"),
        }
        self.m = Memory.from_config(cfg)

    def ingest(self, msgs):
        self.m.add(msgs, user_id=self.uid)

    def _all(self):
        # mem0 2.x get_all defaults to top_k=20 and 1.x to limit=100: ask for everything explicitly
        try:
            r = self.m.get_all(filters={"user_id": self.uid}, top_k=100000)
        except Exception:
            r = self.m.get_all(user_id=self.uid, limit=100000)
        rows = r.get("results", r) if isinstance(r, dict) else r
        return [x.get("memory", "") for x in rows]

    def dump(self):
        return "\n".join(f"- {t}" for t in self._all())

    def context(self, question):
        try:
            r = self.m.search(question, user_id=self.uid, limit=8)
        except Exception:
            r = self.m.search(question, filters={"user_id": self.uid}, top_k=8)
        rows = r.get("results", r) if isinstance(r, dict) else r
        return "\n".join(f"- {x.get('memory', '')}" for x in rows)


class LangMem(Base):
    """langmem create_memory_manager (inserts + updates + deletes) over the running memory list."""
    name = "langmem"

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        from langchain_openai import ChatOpenAI
        from langmem import create_memory_manager
        llm = ChatOpenAI(model=self.model, base_url=PROXY, api_key="proxy", temperature=self.temperature or 0.0, max_tokens=2000)
        self.mgr = create_memory_manager(llm, enable_inserts=True, enable_updates=True, enable_deletes=True)
        self.mem = []  # list of (id, content)
        self.invoke_config = None  # library default (recursion_limit 25); LangMemRL overrides

    def ingest(self, msgs):
        existing = [(i, c) for i, c in self.mem]
        inputs = {"messages": msgs, "existing": existing}
        out = self.mgr.invoke(inputs, config=self.invoke_config) if self.invoke_config else self.mgr.invoke(inputs)
        new = []
        for x in out:
            content = getattr(x, "content", None)
            cid = getattr(x, "id", None)
            text = getattr(content, "content", None) if content is not None and not isinstance(content, str) else content
            if text is None and isinstance(content, dict):
                text = content.get("content")
            if text and "RemoveDoc" not in type(content).__name__:
                new.append((cid, str(text)))
        self.mem = new

    def dump(self):
        return "\n".join(f"- {c}" for _, c in self.mem)


class LangMemRL(LangMem):
    """LangMem with recursion_limit = 100 instead of the library default 25, which fails on long documents
    (GraphRecursionError on MemoryAgentBench). Supplementary, non-default configuration (PLAN item 5c)."""
    name = "langmem_rl100"

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.invoke_config = {"recursion_limit": 100}


class LlamaIndexFacts(Base):
    """llama-index-core FactExtractionMemoryBlock: extract facts from each session; when facts exceed max_facts the
    whole list is condensed (rewritten) by the LLM."""
    name = "llamaindex_facts"

    def __init__(self, *a, max_facts=12, **k):
        super().__init__(*a, **k)
        from llama_index.llms.openai_like import OpenAILike
        from llama_index.core.memory.memory_blocks.fact import FactExtractionMemoryBlock
        llm = OpenAILike(model=self.model, api_base=PROXY, api_key="proxy", is_chat_model=True,
                         temperature=self.temperature or 0.0, max_tokens=2000, context_window=32000)
        self.block = FactExtractionMemoryBlock(name="facts", llm=llm, max_facts=max_facts)

    def ingest(self, msgs):
        from llama_index.core.llms import ChatMessage
        cms = [ChatMessage(role=m["role"], content=m["content"]) for m in msgs]
        asyncio.run(self.block._aput(cms))

    def dump(self):
        return "\n".join(f"- {f}" for f in self.block.facts)


class RawRAG(Base):
    """Append-only store of raw turns; context = top-k turns by embedding similarity (local bge-small). Never rewrites."""
    name = "raw_rag"
    K = 20

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.turns, self.vecs = [], []

    def _embed(self, texts):
        import urllib.request
        out = []
        for i in range(0, len(texts), 64):
            req = urllib.request.Request(EMBED + "/embeddings", data=json.dumps({"model": "bge", "input": texts[i:i + 64]}).encode(),
                                         headers={"Content-Type": "application/json"})
            out += [d["embedding"] for d in json.loads(urllib.request.urlopen(req, timeout=300).read())["data"]]
        return out

    def ingest(self, msgs):
        new = [m["content"] for m in msgs if m["content"].strip()]
        self.turns += new
        self.vecs += self._embed(new)

    def dump(self):
        return "\n".join(self.turns)

    def context(self, question):
        if not self.turns:
            return ""
        q = self._embed([question])[0]
        sims = sorted(range(len(self.turns)), key=lambda i: -sum(a * b for a, b in zip(q, self.vecs[i])))[:self.K]
        return "\n".join(self.turns[i] for i in sorted(sims))


class LlamaIndexFactsDefault(LlamaIndexFacts):
    """FactExtractionMemoryBlock with the library default max_facts (50), used for benchmark re-scoring."""
    name = "llamaindex_facts_default"

    def __init__(self, *a, **k):
        super().__init__(*a, max_facts=50, **k)


class Nemori(Base):
    """nemori (github nemori-ai/nemori @d2a6dff, MIT) with its default config: episodic segmentation + semantic memory
    with Predict-Calibrate (enable_prediction_correction=True), i.e. a PRIOR-AWARE write policy that stores only what the
    model failed to predict. Postgres (docker, :5433) + Qdrant (docker, :6333); embeddings from the local bge server."""
    name = "nemori"

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        import asyncio
        os.environ.setdefault("DATABASE_URL", "postgresql://nemori:nemori@127.0.0.1:5433/nemori")
        os.environ["LLM_BASE_URL"] = PROXY
        os.environ["EMBEDDING_BASE_URL"] = EMBED
        os.environ.setdefault("LLM_API_KEY", "proxy")
        os.environ.setdefault("EMBEDDING_API_KEY", "local")
        from nemori import NemoriMemory, MemoryConfig
        self.loop = asyncio.new_event_loop()
        self.uid = "u" + uuid.uuid4().hex[:12]
        cfg = MemoryConfig(llm_model=self.model, embedding_model="bge-small", embedding_dimension=384,
                           qdrant_url="127.0.0.1", qdrant_port=6333, qdrant_collection_prefix="nem" + uuid.uuid4().hex[:8],
                           db_pool_min=1, db_pool_max=4, llm_timeout=300.0)
        self.mem = NemoriMemory(config=cfg)
        self.loop.run_until_complete(self.mem.__aenter__())

    def ingest(self, msgs):
        self.loop.run_until_complete(self.mem.add_messages(self.uid, [{"role": m["role"], "content": m["content"]} for m in msgs]))
        self.loop.run_until_complete(self.mem.flush(self.uid))

    def dump(self):
        sysm = self.mem._ensure_system()
        eps = self.loop.run_until_complete(sysm._episode_store.list_by_user(self.uid, sysm._agent_id, limit=100000))
        sem = self.loop.run_until_complete(sysm._semantic_store.list_by_user(self.uid, sysm._agent_id))
        return "\n".join([f"- [episode] {e.title}: {e.content}" for e in eps] + [f"- [semantic] {x.content}" for x in sem])

    def context(self, question):
        r = self.loop.run_until_complete(self.mem.search(self.uid, question))
        parts = []
        for e in r.get("episodes", []) or r.get("episodic", []) or []:
            parts.append(f"- [episode] {e.get('title', '')}: {e.get('content', '')}")
        for x in r.get("semantic", []) or r.get("semantic_memories", []) or []:
            parts.append(f"- [semantic] {x.get('content', '')}")
        return "\n".join(parts) if parts else json.dumps(r)[:4000]


class Mem0V1(Mem0):
    """Same adapter, run under mem0ai==1.0.11 (the last release with LLM-driven UPDATE/DELETE of existing memories)."""
    name = "mem0_v1"


ADAPTERS = {c.name: c for c in [Nemori, RawRAG, LlamaIndexFactsDefault, Mem0V1, LangMemRL, Codex, OpenHands, Aider, GeminiCLI, AnthropicAPI, LangChainSummary, NeutralRoll, RawHistory,
                                  Mem0, LangMem, LlamaIndexFacts]}
