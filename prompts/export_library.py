"""Archive the prompts that live inside the memory libraries we ran with their DEFAULT prompts.

The files are copied verbatim from the exact installed versions (the environments the experiments used), with the
package licence and a manifest (version, source path, sha256). Prompt constants are additionally extracted to
library/<pkg>/prompts_extracted.txt for reading convenience.
  mem0ai 2.2.1 (fw-env)         Mem0, append-only            framework study + re-scoring
  mem0ai 1.0.11 (mem0v1-env)    Mem0 with UPDATE/DELETE      framework study + re-scoring
  langmem 0.0.30 + trustcall 0.0.39 (fw-env)                 framework study + re-scoring (LoCoMo)
  llama-index-core 0.14.25 (fw-env) FactExtractionMemoryBlock framework study + re-scoring
  langchain 1.4.3 (fw-env)      SummarizationMiddleware DEFAULT_SUMMARY_PROMPT (used through our adapter)
  nemori 0.2.0 = github nemori-ai/nemori @d2a6dff (nemori-env)  framework study
Run: python prompts/export_library.py
"""
import ast, hashlib, json, os, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("PROMPTS_OUT", ROOT / "prompts")) / "library"
ENV = Path("/home/ubuntu/llm_infra")
SP = {e: next((ENV / e / "lib").glob("python3*/site-packages")) for e in ("fw-env", "mem0v1-env", "nemori-env")}
FILES = {
    "mem0ai-2.2.1": ("fw-env", "mem0ai-2.2.1.dist-info", ["mem0/configs/prompts.py", "mem0/memory/main.py", "mem0/memory/utils.py"]),
    "mem0ai-1.0.11": ("mem0v1-env", "mem0ai-1.0.11.dist-info", ["mem0/configs/prompts.py", "mem0/memory/main.py", "mem0/memory/utils.py"]),
    "langmem-0.0.30": ("fw-env", "langmem-0.0.30.dist-info", ["langmem/knowledge/extraction.py"]),
    "trustcall-0.0.39": ("fw-env", "trustcall-0.0.39.dist-info", ["trustcall/_base.py"]),
    "llama-index-core-0.14.25": ("fw-env", "llama_index_core-0.14.25.dist-info", ["llama_index/core/memory/memory_blocks/fact.py"]),
    "langchain-1.4.3": ("fw-env", "langchain-1.4.3.dist-info", ["langchain/agents/middleware/summarization.py"]),
    "nemori-0.2.0@d2a6dff": ("nemori-env", "nemori-0.2.0.dist-info", ["nemori/llm/prompts.py", "nemori/llm/generators/segmenter.py",
                                                                      "nemori/llm/generators/episode.py", "nemori/llm/generators/semantic.py",
                                                                      "nemori/llm/generators/merger.py"]),
}


def extract_strings(src):
    """Prompt-like strings: named *PROMPT*/*INSTRUCTION* string constants, any string literal or f-string longer than
    200 characters (wherever it appears, e.g. inside PromptTemplate(...) calls), with its line number."""
    out, seen = [], set()
    tree = ast.parse(src)
    parent_name = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            for sub in ast.walk(node.value):
                parent_name[id(sub)] = names[0] if names else ""
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            text = node.value
        elif isinstance(node, ast.JoinedStr):
            text = ast.get_source_segment(src, node) or ""
        else:
            continue
        name = parent_name.get(id(node), "")
        if (len(text) > 200 or ("PROMPT" in name.upper() or "INSTRUCTION" in name.upper()) and len(text) > 40) and (node.lineno, text[:50]) not in seen:
            seen.add((node.lineno, text[:50]))
            out.append((name or "(literal)", node.lineno, text))
    return sorted(out, key=lambda t: t[1])


def main():
    manifest = {}
    for pkg, (env, dist, files) in FILES.items():
        d = OUT / pkg
        d.mkdir(parents=True, exist_ok=True)
        lic = [p for p in (SP[env] / dist).glob("**/*") if p.is_file() and p.name.upper().startswith(("LICENSE", "LICENCE", "COPYING"))]
        meta = (SP[env] / dist / "METADATA").read_text(errors="replace")
        lic_line = next((l for l in meta.splitlines() if l.startswith(("License:", "License-Expression:"))), "License: (see METADATA)")
        for p in lic:
            shutil.copy(p, d / p.name)
        ext_lines = []
        entries = []
        for rel in files:
            src = SP[env] / rel
            dst = d / rel.replace("/", "__")
            shutil.copy(src, dst)
            text = src.read_text()
            entries.append(dict(file=rel, archived_as=dst.name, sha256=hashlib.sha256(text.encode()).hexdigest()))
            for name, line, s in extract_strings(text):
                ext_lines.append(f"===== {rel}:{line}  {name} =====\n{s}\n")
        (d / "prompts_extracted.txt").write_text("\n".join(ext_lines))
        manifest[pkg] = dict(environment=env, license=lic_line, license_files=[p.name for p in lic], files=entries)
        print(f"{pkg:28s} {len(files)} files, {len(ext_lines)} prompt strings extracted, {lic_line}")
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
