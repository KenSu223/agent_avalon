"""LLM client for all experiments in this project.

Two backends, both OpenAI-compatible:
  - Bedrock models via the local budget proxy at http://127.0.0.1:8787/v1
    (model ids such as "qwen.qwen3-235b-a22b-2507-v1:0"; see GET /v1/models for the priced list)
  - The local vLLM server at http://127.0.0.1:8001/v1 (model id "local:qwen3-8b"), free, with logprobs

Every response is cached on disk (SQLite) by a hash of the full request, so re-running an
analysis never pays twice. For temperature > 0, pass a distinct `sample_idx` per sample.

Usage:
    from infra.llm import chat, batch_chat, budget, score_continuations
    r = chat("qwen.qwen3-235b-a22b-2507-v1:0", [{"role": "user", "content": "hi"}], temperature=0, max_tokens=50)
    r["text"], r["usage"], r["cost_usd"]
"""
import hashlib, json, os, sqlite3, threading, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

PROXY = "http://127.0.0.1:8787/v1"
LOCAL = "http://127.0.0.1:8001/v1"
LOCAL_MODEL = "qwen3-8b"
CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache", "llm_cache.sqlite")

_local = threading.local()
_cache_lock = threading.Lock()


class BudgetExceeded(RuntimeError):
    """Raised when the proxy refuses a call because the hard spending cap would be passed."""


def _db():
    if not hasattr(_local, "db"):
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        db = sqlite3.connect(CACHE_PATH, timeout=60)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE IF NOT EXISTS c (k TEXT PRIMARY KEY, v TEXT)")
        _local.db = db
    return _local.db


def _post(url, payload, timeout=600):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _key(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def chat(model, messages, temperature=0.0, max_tokens=1024, top_p=None, sample_idx=0,
         reasoning_effort=None, use_cache=True, max_retries=10, **extra):
    """One chat completion. Returns {"text", "usage", "cost_usd", "model", "cached"}."""
    local = model.startswith("local:")
    payload = {"model": LOCAL_MODEL if local else model, "messages": messages,
               "temperature": temperature, "max_tokens": max_tokens}
    if top_p is not None:
        payload["top_p"] = top_p
    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort
    if local:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
        payload["seed"] = sample_idx
    payload.update(extra)
    k = _key({"p": payload, "s": sample_idx, "b": "local" if local else "bedrock"})
    if use_cache:
        row = _db().execute("SELECT v FROM c WHERE k=?", (k,)).fetchone()
        if row:
            out = json.loads(row[0]); out["cached"] = True
            return out
    url = (LOCAL if local else PROXY) + "/chat/completions"
    delay = 2.0
    for attempt in range(max_retries):
        try:
            d = _post(url, payload)
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            if e.code == 402:
                raise BudgetExceeded(body)
            if e.code in (400, 403, 404) and "throttl" not in body.lower():
                raise RuntimeError(f"HTTP {e.code}: {body[:1000]}")
            if attempt == max_retries - 1:
                raise RuntimeError(f"HTTP {e.code} after {max_retries} tries: {body[:500]}")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt == max_retries - 1:
                raise
        time.sleep(delay)
        delay = min(delay * 2, 120)
    msg = d["choices"][0]["message"]
    out = {"text": msg.get("content") or "", "usage": d.get("usage", {}),
           "cost_usd": d.get("cost_usd", 0.0), "model": model,
           "finish_reason": d["choices"][0].get("finish_reason"), "cached": False}
    if use_cache:
        with _cache_lock:
            _db().execute("INSERT OR REPLACE INTO c VALUES (?,?)", (k, json.dumps(out)))
            _db().commit()
    return out


def batch_chat(requests, workers=16, desc="", stop_on_budget=True):
    """Run many chat() calls in parallel. `requests` is a list of kwargs dicts for chat().
    Returns results in the same order (None for failures, with the error in result['error'])."""
    results = [None] * len(requests)
    done = 0
    t0 = time.time()
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(chat, **r): i for i, r in enumerate(requests)}
        for f in as_completed(futs):
            i = futs[f]
            try:
                results[i] = f.result()
            except BudgetExceeded:
                if stop_on_budget:
                    ex.shutdown(wait=False, cancel_futures=True)
                    raise
                results[i] = {"error": "budget_exceeded"}
            except Exception as e:
                results[i] = {"error": repr(e)[:500]}
            done += 1
            if desc and done % max(1, len(requests) // 20) == 0:
                print(f"[{desc}] {done}/{len(requests)} in {time.time()-t0:.0f}s", flush=True)
    return results


def budget():
    """Current Bedrock spend as reported by the proxy."""
    with urllib.request.urlopen(PROXY + "/budget", timeout=30) as r:
        return json.loads(r.read())


def price_table():
    with urllib.request.urlopen(PROXY + "/models", timeout=30) as r:
        return {m["id"]: (m["usd_per_M_in"], m["usd_per_M_out"]) for m in json.loads(r.read())["data"]}


def estimate_cost(model, n_calls, in_tokens_per_call, out_tokens_per_call):
    """Back-of-envelope cost in USD before launching a batch. Local models cost 0."""
    if model.startswith("local:"):
        return 0.0
    pin, pout = price_table()[model]
    return n_calls * (in_tokens_per_call * pin + out_tokens_per_call * pout) / 1e6


def score_continuations(prefix, continuations, use_cache=True):
    """Log-probability of each continuation given `prefix` under the local model (raw text, no chat template).
    Returns a list of {"logprob": sum, "n_tokens": n, "mean_logprob": avg}."""
    out = []
    for cont in continuations:
        k = _key({"score": prefix, "cont": cont, "m": LOCAL_MODEL})
        if use_cache:
            row = _db().execute("SELECT v FROM c WHERE k=?", (k,)).fetchone()
            if row:
                out.append(json.loads(row[0])); continue
        full = _post(LOCAL + "/completions", {"model": LOCAL_MODEL, "prompt": prefix + cont, "max_tokens": 1,
                                               "temperature": 0, "echo": True, "logprobs": 0})
        pre = _post(LOCAL.rsplit("/v1", 1)[0] + "/tokenize", {"model": LOCAL_MODEL, "prompt": prefix})
        n_pre = len(pre["tokens"])
        lps = full["choices"][0]["logprobs"]["token_logprobs"]
        cont_lps = [x for x in lps[n_pre:len(lps) - 1] if x is not None]
        r = {"logprob": float(sum(cont_lps)), "n_tokens": len(cont_lps),
             "mean_logprob": float(sum(cont_lps) / max(1, len(cont_lps)))}
        if use_cache:
            with _cache_lock:
                _db().execute("INSERT OR REPLACE INTO c VALUES (?,?)", (k, json.dumps(r)))
                _db().commit()
        out.append(r)
    return out
