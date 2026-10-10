"""Run protocols.py for each (bench, system) as soon as its results_v2 file is complete (Step 2.3 helper)."""
import subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).parent
ROOT = HERE.parent
V2 = ROOT / "benchmark_audit/results_v2"
PY = "/home/ubuntu/llm_infra/fw-env/bin/python"
SYS = ["raw_rag", "mem0", "mem0_v1", "langmem", "llamaindex_facts_default", "gemini_cli", "neutral_roll", "openhands",
       "langchain_summary", "aider", "anthropic_api", "codex"]
JOBS = [("locomo", s) for s in SYS] + [("mab_ruler", s) for s in SYS if s != "langmem"]


def running(bench, system):
    out = subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True).stdout
    return any(f"rescore.py {system} {bench}" in l for l in out.splitlines())


done = {j for j in JOBS if (HERE / "results" / f"protocols_{j[0]}_{j[1]}.jsonl").exists()}
while len(done) < len(JOBS):
    for b, s in JOBS:
        if (b, s) in done:
            continue
        f = V2 / f"rescore_{b}_{s}.jsonl"
        if f.exists() and f.stat().st_size > 0 and not running(b, s):
            with open(HERE / "logs" / f"protocols_{b}_{s}.log", "w") as log:
                subprocess.run([PY, str(HERE / "protocols.py"), b, s], stdout=log, stderr=subprocess.STDOUT, cwd=HERE)
            print(time.strftime("%H:%M:%S"), b, s, open(HERE / "logs" / f"protocols_{b}_{s}.log").read().strip().splitlines()[-1], flush=True)
            done.add((b, s))
    if not (ROOT / "benchmark_audit/logs_v2/all.log").exists() or "ALL DONE" not in open(ROOT / "benchmark_audit/logs_v2/all.log").read():
        time.sleep(30)
    elif len(done) < len(JOBS):
        missing = [j for j in JOBS if j not in done and not (V2 / f"rescore_{j[0]}_{j[1]}.jsonl").exists()]
        if missing and all(not running(b, s) for b, s in missing):
            print("rescore finished but missing:", missing, flush=True)
            break
print("protocol runner finished", flush=True)
