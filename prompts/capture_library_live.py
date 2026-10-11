"""Live capture of the prompts the memory LIBRARIES actually send (they call the proxy through their own OpenAI clients,
bypassing infra.llm and its cache, so capture.py cannot verify them offline).

Each library adapter, in the environment the experiments used, ingests the first 3 sessions of framework-study user 0
and answers one context query. Inside the probe process, the HTTPTransport / AsyncHTTPTransport of httpx and of httpx2 (used by openai 3.x) are wrapped so that every
request body sent to the proxy (port 8787) is written to prompts/captured/<library>.jsonl: exactly what the library
sent, isolated from any other traffic. Distinct system prompts / tool schemas / response formats go to
<library>_distinct.json. The proxy additionally logs everything to ~/llm_infra/state/requests/. Cost: cents.
These captures are not byte-reproducible (library ids, timestamps), so check_prompts.py does not compare them.
"""
import hashlib, json, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "prompts/captured"
LOG = Path("/home/ubuntu/llm_infra/state/requests")
ENV = "/home/ubuntu/llm_infra/{}/bin/python"
PROBES = [("mem0", "fw-env"), ("mem0_v1", "mem0v1-env"), ("langmem", "fw-env"), ("llamaindex_facts", "fw-env"),
          ("llamaindex_facts_default", "fw-env"), ("nemori", "nemori-env")]
CODE = """
import sys, json, httpx
LOGF = open({log!r}, "w")
def _log(request):
    try:
        if "8787" in str(request.url):
            LOGF.write(json.dumps({{"url": str(request.url), "body": json.loads(request.content or b"{{}}")}}) + "\\n"); LOGF.flush()
    except Exception as e:
        LOGF.write(json.dumps({{"capture_error": repr(e)}}) + "\\n")
# transport level: every httpx client (whatever wrapper class the openai version uses) goes through these
_h, _ah = httpx.HTTPTransport.handle_request, httpx.AsyncHTTPTransport.handle_async_request
def handle(self, request):
    _log(request); return _h(self, request)
async def ahandle(self, request):
    _log(request); return await _ah(self, request)
httpx.HTTPTransport.handle_request, httpx.AsyncHTTPTransport.handle_async_request = handle, ahandle
try:   # openai 3.x (mem0v1-env, nemori-env) uses the httpx2 fork
    import httpx2
    _h2, _ah2 = httpx2.HTTPTransport.handle_request, httpx2.AsyncHTTPTransport.handle_async_request
    def handle2(self, request):
        _log(request); return _h2(self, request)
    async def ahandle2(self, request):
        _log(request); return await _ah2(self, request)
    httpx2.HTTPTransport.handle_request, httpx2.AsyncHTTPTransport.handle_async_request = handle2, ahandle2
except ImportError:
    pass
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
        log = OUT / f"{name}.jsonl"
        r = subprocess.run([ENV.format(env), "-c", CODE.format(src=ROOT / "framework_study/src", name=name, log=str(log))],
                           capture_output=True, text=True, cwd=ROOT / "framework_study/src", timeout=1800)
        reqs = [json.loads(l) for l in open(log)] if log.exists() else []
        errs = [d for d in reqs if "capture_error" in d]
        reqs = [d["body"] for d in reqs if "body" in d]
        distinct = {}
        for req in reqs:
            sysmsg = "\n".join(m.get("content") if isinstance(m.get("content"), str) else json.dumps(m.get("content"))
                               for m in req.get("messages", []) if m.get("role") in ("system", "developer"))
            key = hashlib.sha256((sysmsg + json.dumps(req.get("tools"), sort_keys=True) + json.dumps(req.get("response_format"), sort_keys=True)).encode()).hexdigest()[:12]
            distinct.setdefault(key, dict(system=sysmsg, tools=req.get("tools"), response_format=req.get("response_format"),
                                          first_user_message=next((m.get("content") for m in req.get("messages", []) if m.get("role") == "user"), None),
                                          example_request=req, n_requests=0))["n_requests"] += 1
        (OUT / f"{name}_distinct.json").write_text(json.dumps(distinct, indent=1, ensure_ascii=False))
        summary[name] = dict(requests=len(reqs), distinct_prompts=len(distinct), capture_errors=len(errs), returncode=r.returncode, stderr_tail=r.stderr[-400:])
        print(f"{name:26s} rc={r.returncode} requests={len(reqs)} distinct={len(distinct)} errors={len(errs)}  {r.stdout.strip()[:100]}")
    (OUT / "SUMMARY.json").write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
