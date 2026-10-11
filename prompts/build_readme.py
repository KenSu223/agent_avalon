"""Generate prompts/README.md from prompts/registry.json and prompts/library/MANIFEST.json.   python prompts/build_readme.py"""
import json
from pathlib import Path
P = Path(__file__).resolve().parent
reg = json.load(open(P / "registry.json"))
man = json.load(open(P / "library/MANIFEST.json"))

HEAD = """# Prompt archive

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
"""


def table_templates(rs):
    lines = ["| id | source | file |", "|---|---|---|"]
    for r in rs:
        lines.append(f"| `{r['id']}` | {r['source']}{(' — ' + r['note']) if r.get('note') else ''} | [{r['file']}]({r['file']}) |")
    return "\n".join(lines)


def table_exemplars(rs):
    lines = ["| id | used for | model | parameters | verified | file |", "|---|---|---|---|---|---|"]
    for r in rs:
        prm = ", ".join(f"{k}={v}" for k, v in r.get("params", {}).items())
        lines.append(f"| `{r['id']}` | {r['used_for']} | {r.get('model', '')} | {prm} | {'✅' if r['verified'] else '❌'} | [{r['file']}]({r['file']}) |")
    return "\n".join(lines)


def main():
    out = [HEAD]
    tmpl = [r for r in reg if r["kind"] == "template"]
    ex = [r for r in reg if r["kind"] == "exemplar"]
    out.append(f"## Summary\n{len(tmpl)} templates; {len(ex)} exemplars, {sum(r['verified'] for r in ex)} verified byte-identical against the response cache.\n")
    stages = []
    for r in tmpl + ex:
        if r["stage"] not in stages:
            stages.append(r["stage"])
    for st in stages:
        out.append(f"## {st}")
        t = [r for r in tmpl if r["stage"] == st]
        e = [r for r in ex if r["stage"] == st]
        if t:
            out.append("**Templates**\n\n" + table_templates(t) + "\n")
        if e:
            out.append("**Verified exemplars**\n\n" + table_exemplars(e) + "\n")
    out.append("## Library-internal prompts (default prompts of the libraries)")
    out.append("| package | environment | licence | archived files |\n|---|---|---|---|")
    for pkg, m in man.items():
        out.append(f"| {pkg} | {m['environment']} | {m['license']} | " + ", ".join(f"[{f['file']}](library/{pkg}/{f['archived_as']})" for f in m["files"]) + " |")
    cap = P / "captured/SUMMARY.json"
    if cap.exists():
        out.append("\n## Library prompts as actually sent (live capture)")
        out.append("Each library ran on the first 3 sessions of framework-study user 0 plus one query; every request it sent was recorded inside the "
                   "process (httpx / httpx2 transport) by `capture_library_live.py`. Prompts that only fire under conditions not reached in 3 sessions "
                   "(e.g. LlamaIndex fact condensation beyond max_facts) are covered by the archived source files above.\n")
        out.append("| library | requests | distinct system prompts / tool schemas | files |\n|---|---|---|---|")
        for k, v in json.load(open(cap)).items():
            out.append(f"| {k} | {v['requests']} | {v['distinct_prompts']} | [captured/{k}.jsonl](captured/{k}.jsonl), [captured/{k}_distinct.json](captured/{k}_distinct.json) |")
    out.append("\nProduct compaction prompts are verbatim copies of the upstream sources in `framework_study/prompts/` "
               "(Codex @822e58c, OpenHands @6f8c38d, Aider @5dc9490, Gemini CLI @fb972b2; Anthropic API documented default); "
               "the framing each adapter adds is in `templates/fw_compactor_*.json`.\n")
    (P / "README.md").write_text("\n".join(out))
    print("README.md written:", len(tmpl), "templates,", len(ex), "exemplars")


if __name__ == "__main__":
    main()
