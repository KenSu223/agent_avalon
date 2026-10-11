"""Live capture of the prompts the memory LIBRARIES actually send (they call the proxy directly, bypassing infra.llm and
its cache, so capture.py cannot verify them offline).

Each library adapter, in the environment the experiments used, ingests the first 3 sessions of framework-study user 0
and answers one context query. Every request it makes passes through the budget proxy, which logs it (as received and
as translated for Bedrock) to ~/llm_infra/state/requests/. The Qwen requests inside each probe's time window are
copied to prompts/captured/<library>.jsonl, and the distinct system prompts / tool schemas to <library>_distinct.json.
Run only when no other Qwen traffic goes through the proxy (otherwise the time windows would mix). Cost: cents.
These captures are not byte-reproducible (library ids, timestamps), so check_prompts.py does not compare them.
"""
import glob, hashlib, json, subprocess, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "prompts/captured"
LOG = Path("/home/ubuntu/llm_infra/state/requests")
ENV = "/home/ubuntu/llm_infra/{}/bin/python"
PROBES = [("mem0", "fw-env"), ("mem0_v1", "mem0v1-env"), ("langmem", "fw-env"), ("llamaindex_facts", "fw-env"),
          ("llamaindex_facts_default", "fw-env"), ("nemori", "nemori-env")]
CODE = """
import sys
sys.path.insert(0, "{src}")
import frameworks as FW
from sessions import make_users, load_distractors, build_history, ITEMS
hist = build_history(make_users(43)[0], load_distractors(), n_distract=12, seed=0)
ad = FW.ADAPTERS["{name}"]("qwen.qwen3-235b-a22b-2507-v1:0", temperature=0.0)
for s in hist[:3]:
    ad.ingest(s["messages"])
iid = make_users(43)[0][0][0]
print("CONTEXT:", (ad.context(ITEMS[iid]["question"]) or "")[:300])
"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {}
    for name, env in PROBES:
        t0 = time.time()
        r = subprocess.run([ENV.format(env), "-c", CODE.format(src=ROOT / "framework_study/src", name=name)],
                           capture_output=True, text=True, cwd=ROOT / "framework_study/src", timeout=1800)
        time.sleep(2)
        t1 = time.time()
        reqs = []
        for f in sorted(LOG.glob("requests_*.jsonl")):
            for l in open(f):
                d = json.loads(l)
                if t0 <= d["ts"] <= t1 and str(d.get("model", "")).startswith("qwen."):
                    reqs.append(d)
        with open(OUT / f"{name}.jsonl", "w") as fh:
            for d in reqs:
                fh.write(json.dumps(d, ensure_ascii=False) + "\n")
        distinct = {}
        for d in reqs:
            req = d["openai_request"]
            sysmsg = "\n".join(m.get("content") if isinstance(m.get("content"), str) else json.dumps(m.get("content"))
                               for m in req.get("messages", []) if m.get("role") in ("system", "developer"))
            key = hashlib.sha256((sysmsg + json.dumps(req.get("tools"), sort_keys=True) + json.dumps(req.get("response_format"), sort_keys=True)).encode()).hexdigest()[:12]
            distinct.setdefault(key, dict(system=sysmsg, tools=req.get("tools"), response_format=req.get("response_format"),
                                          first_user_message=next((m.get("content") for m in req.get("messages", []) if m.get("role") == "user"), None),
                                          n_requests=0))["n_requests"] += 1
        (OUT / f"{name}_distinct.json").write_text(json.dumps(distinct, indent=1, ensure_ascii=False))
        summary[name] = dict(requests=len(reqs), distinct_prompts=len(distinct), returncode=r.returncode, stderr_tail=r.stderr[-300:])
        print(f"{name:26s} rc={r.returncode} requests={len(reqs)} distinct={len(distinct)}  {r.stdout.strip()[:120]}")
    (OUT / "SUMMARY.json").write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
