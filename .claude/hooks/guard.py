#!/usr/bin/env python3
"""PreToolUse guard for unattended runs in this worktree.

Blocks (exit 2) any tool call that would:
  - read or use the Bedrock credential, or call Bedrock without the budget proxy
  - modify or stop the budget proxy / its ledger
  - push to a remote
  - write or edit files outside this worktree (Write/Edit/NotebookEdit tools)
"""
import json, os, re, sys

WT = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
ALLOWED_WRITE_ROOTS = [WT, "/tmp", os.path.expanduser("~/.cache"), os.path.expanduser("~/.aris"),
                       os.path.expanduser("~/.claude/projects"), os.path.expanduser("~/.codex")]

BLOCK = [
    (r"\.config/bedrock", "the Bedrock credential file is off limits; use the proxy at 127.0.0.1:8787"),
    (r"AWS_BEARER_TOKEN", "the Bedrock credential is off limits; use the proxy at 127.0.0.1:8787"),
    (r"bedrock-runtime\.|bedrock\.[a-z0-9-]+\.amazonaws\.com", "call Bedrock only through the proxy at 127.0.0.1:8787 (infra/llm.py)"),
    (r"client\(\s*['\"]bedrock", "call Bedrock only through the proxy at 127.0.0.1:8787 (infra/llm.py)"),
    (r"llm_infra/(bedrock_proxy\.py|state)", "the budget proxy and its ledger must not be touched; read spend via GET 127.0.0.1:8787/v1/budget"),
    (r"proxyctl\.sh\s+stop", "do not stop the budget proxy"),
    (r"BUDGET_CAP_USD|PROXY_PORT", "do not change the budget proxy configuration"),
    (r"\bgit\s+push\b", "never push; commit locally only"),
]

d = json.load(sys.stdin)
tool = d.get("tool_name", "")
inp = d.get("tool_input", {}) or {}
blob = json.dumps(inp)

for pat, why in BLOCK:
    if re.search(pat, blob):
        print(f"BLOCKED by project guard: {why}", file=sys.stderr)
        sys.exit(2)

if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
    p = inp.get("file_path") or inp.get("notebook_path") or ""
    rp = os.path.realpath(p) if p else ""
    if rp and not any(rp == r or rp.startswith(r.rstrip("/") + "/") for r in ALLOWED_WRITE_ROOTS):
        print(f"BLOCKED by project guard: writes must stay inside the worktree {WT} (got {p})", file=sys.stderr)
        sys.exit(2)

sys.exit(0)
