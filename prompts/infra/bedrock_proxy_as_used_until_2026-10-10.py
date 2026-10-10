#!/usr/bin/env python3
"""Budget-enforcing Bedrock proxy.

The only process that holds the Bedrock API key. It exposes an
OpenAI-compatible endpoint on 127.0.0.1, forwards requests to the Bedrock
Converse API, prices each call from the official us-west-2 on-demand price
list, appends every call to a ledger, and refuses any request that could take
cumulative spend past the hard cap.

Endpoints
  POST /v1/chat/completions   OpenAI-style request; returns OpenAI-style response plus `cost_usd`
  GET  /v1/budget             {"spent_usd", "cap_usd", "remaining_usd", "calls", "by_model"}
  GET  /v1/models             priced models that may be used
"""
import json, os, threading, time, urllib.request, urllib.error, math, sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

HOME = os.path.expanduser("~")
KEY_FILE = os.path.join(HOME, ".config/bedrock/env")
STATE_DIR = os.path.join(HOME, "llm_infra/state")
LEDGER = os.path.join(STATE_DIR, "budget_ledger.jsonl")
STATUS = os.path.join(STATE_DIR, "budget_status.json")
REGION = "us-west-2"
PORT = int(os.environ.get("PROXY_PORT", "8787"))

ABSOLUTE_LIMIT = 150.0          # user's limit; never exceeded
HARD_CAP = min(float(os.environ.get("BUDGET_CAP_USD", "140")), 145.0)  # margin below the limit

# USD per 1M tokens (input, output), AWS Price List API, us-west-2 on-demand, fetched 2026-10-06.
# "profile": model is only callable through the US cross-region inference profile.
PRICES = {
    "qwen.qwen3-235b-a22b-2507-v1:0":        (0.22, 0.88, False),
    "qwen.qwen3-32b-v1:0":                   (0.15, 0.60, False),
    "qwen.qwen3-coder-30b-a3b-v1:0":         (0.15, 0.60, False),
    "openai.gpt-oss-120b-1:0":               (0.15, 0.60, False),
    "openai.gpt-oss-20b-1:0":                (0.07, 0.30, False),
    "google.gemma-3-27b-it":                 (0.23, 0.38, False),
    "google.gemma-3-12b-it":                 (0.09, 0.29, False),
    "meta.llama3-3-70b-instruct-v1:0":       (0.72, 0.72, True),
    "meta.llama3-1-70b-instruct-v1:0":       (0.72, 0.72, False),
    "meta.llama3-1-8b-instruct-v1:0":        (0.22, 0.22, False),
    "meta.llama4-maverick-17b-instruct-v1:0":(0.24, 0.97, True),
    "meta.llama4-scout-17b-instruct-v1:0":   (0.17, 0.66, True),
    "mistral.mistral-large-3-675b-instruct": (0.50, 1.50, False),
    "mistral.ministral-3-14b-instruct":      (0.20, 0.20, False),
    "mistral.ministral-3-8b-instruct":       (0.15, 0.15, False),
    "deepseek.v3.2":                         (0.62, 1.85, False),
    "zai.glm-4.7":                           (0.60, 2.20, False),
    "zai.glm-4.7-flash":                     (0.07, 0.40, False),
    "moonshotai.kimi-k2.5":                  (0.60, 3.00, False),
    "minimax.minimax-m2.5":                  (0.30, 1.20, False),
    "nvidia.nemotron-super-3-120b":          (0.15, 0.65, False),
    "nvidia.nemotron-nano-3-30b":            (0.06, 0.24, False),
}

lock = threading.Lock()
state = {"spent": 0.0, "reserved": 0.0, "calls": 0, "refused": 0, "by_model": {}}


def load_key():
    for line in open(KEY_FILE):
        line = line.strip()
        if "AWS_BEARER_TOKEN_BEDROCK=" in line:
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("key not found")


KEY = load_key()


def load_ledger():
    os.makedirs(STATE_DIR, exist_ok=True)
    if not os.path.exists(LEDGER):
        return
    for line in open(LEDGER):
        try:
            r = json.loads(line)
        except Exception:
            continue
        state["spent"] += r.get("cost", 0.0)
        state["calls"] += 1
        m = state["by_model"].setdefault(r["model"], {"calls": 0, "in": 0, "out": 0, "cost": 0.0})
        m["calls"] += 1; m["in"] += r.get("in", 0); m["out"] += r.get("out", 0); m["cost"] += r.get("cost", 0.0)


def write_status():
    s = {"spent_usd": round(state["spent"], 4), "cap_usd": HARD_CAP, "absolute_limit_usd": ABSOLUTE_LIMIT,
         "remaining_usd": round(HARD_CAP - state["spent"], 4), "in_flight_reserved_usd": round(state["reserved"], 4),
         "calls": state["calls"], "refused": state["refused"],
         "by_model": {k: {**v, "cost": round(v["cost"], 4)} for k, v in state["by_model"].items()},
         "updated": time.strftime("%Y-%m-%d %H:%M:%S")}
    tmp = STATUS + ".tmp"
    json.dump(s, open(tmp, "w"), indent=1)
    os.replace(tmp, STATUS)
    return s


def _text(c):
    if isinstance(c, list):
        return "".join(p.get("text", "") for p in c if isinstance(p, dict) and p.get("type", "text") == "text")
    return c or ""


def _append(msgs, role, blocks):
    blocks = [b for b in blocks if not ("text" in b and not b["text"].strip())]
    if not blocks:
        return
    if msgs and msgs[-1]["role"] == role:
        msgs[-1]["content"].extend(blocks)
    else:
        msgs.append({"role": role, "content": blocks})


def to_converse(req, model=""):
    """OpenAI chat request -> Bedrock Converse body. Supports tools / tool_calls / tool messages and
    response_format (as an instruction, since Converse has no JSON mode)."""
    system, msgs = [], []
    for m in req.get("messages", []):
        role = m.get("role")
        if role in ("system", "developer"):
            t = _text(m.get("content"))
            if t.strip():
                system.append({"text": t})
        elif role == "assistant":
            blocks = [{"text": _text(m.get("content"))}]
            for tc in m.get("tool_calls") or []:
                fn = tc.get("function", {})
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except Exception:
                    args = {"_raw": fn.get("arguments")}
                blocks.append({"toolUse": {"toolUseId": tc.get("id") or f"call_{len(blocks)}", "name": fn.get("name"), "input": args}})
            _append(msgs, "assistant", blocks)
        elif role in ("tool", "function"):
            _append(msgs, "user", [{"toolResult": {"toolUseId": m.get("tool_call_id") or m.get("name", "call"),
                                                   "content": [{"text": _text(m.get("content")) or "(empty)"}]}}])
        else:
            _append(msgs, "user", [{"text": _text(m.get("content"))}])
    if msgs and msgs[0]["role"] == "assistant":
        msgs.insert(0, {"role": "user", "content": [{"text": "(continue)"}]})
    rf = req.get("response_format") or {}
    if rf.get("type") in ("json_object", "json_schema"):
        instr = "Respond only with a single valid JSON object and nothing else (no code fences)."
        if rf.get("type") == "json_schema":
            instr += " It must follow this JSON schema: " + json.dumps((rf.get("json_schema") or {}).get("schema", {}))
        system.append({"text": instr})
    cfg = {"maxTokens": int(req.get("max_tokens") or req.get("max_completion_tokens") or 2048)}
    if req.get("temperature") is not None:
        cfg["temperature"] = float(req["temperature"])
    if req.get("top_p") is not None:
        cfg["topP"] = float(req["top_p"])
    if req.get("stop"):
        cfg["stopSequences"] = req["stop"] if isinstance(req["stop"], list) else [req["stop"]]
    body = {"messages": msgs, "inferenceConfig": cfg}
    if system:
        body["system"] = system
    tools = req.get("tools") or [{"type": "function", "function": f} for f in (req.get("functions") or [])]
    if tools:
        specs = [{"toolSpec": {"name": t["function"]["name"], "description": t["function"].get("description") or t["function"]["name"],
                               "inputSchema": {"json": t["function"].get("parameters") or {"type": "object", "properties": {}}}}}
                 for t in tools if t.get("type", "function") == "function"]
        tc = {"tools": specs}
        ch = req.get("tool_choice")
        if ch == "required":
            tc["toolChoice"] = {"any": {}}
        elif isinstance(ch, dict) and ch.get("function", {}).get("name"):
            tc["toolChoice"] = {"tool": {"name": ch["function"]["name"]}}
        body["toolConfig"] = tc
    elif any("toolUse" in b or "toolResult" in b for mm in msgs for b in mm["content"]):
        names = {b["toolUse"]["name"] for mm in msgs for b in mm["content"] if "toolUse" in b}
        body["toolConfig"] = {"tools": [{"toolSpec": {"name": n, "description": n, "inputSchema": {"json": {"type": "object"}}}} for n in names]}
    extra = {}
    if req.get("reasoning_effort") and model.startswith("openai.gpt-oss"):
        extra["reasoning_effort"] = req["reasoning_effort"]
    if extra:
        body["additionalModelRequestFields"] = extra
    return body, cfg["maxTokens"]


def call_bedrock(model, body):
    pin, pout, profile = PRICES[model]
    mid = ("us." + model) if profile else model
    url = f"https://bedrock-runtime.{REGION}.amazonaws.com/model/{urllib.request.quote(mid, safe='')}/converse"
    r = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                               headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=600) as resp:
        return json.loads(resp.read())


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path.startswith("/v1/budget"):
            with lock:
                return self.send(200, write_status())
        if self.path.startswith("/v1/models"):
            return self.send(200, {"data": [{"id": k, "usd_per_M_in": v[0], "usd_per_M_out": v[1]} for k, v in PRICES.items()]})
        self.send(404, {"error": "not found"})

    def do_POST(self):
        if not self.path.startswith("/v1/chat/completions"):
            return self.send(404, {"error": "not found"})
        try:
            req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        except Exception as e:
            return self.send(400, {"error": f"bad json: {e}"})
        model = req.get("model")
        if model not in PRICES:
            return self.send(400, {"error": {"type": "model_not_allowed", "message": f"{model} has no verified price; allowed: {sorted(PRICES)}"}})
        body, max_out = to_converse(req, model)
        pin, pout, _ = PRICES[model]
        chars = len(json.dumps(body))
        est = (chars / 2.5 + 50) * pin / 1e6 + max_out * pout / 1e6  # conservative upper bound
        with lock:
            if state["spent"] + state["reserved"] + est > HARD_CAP:
                state["refused"] += 1
                write_status()
                return self.send(402, {"error": {"type": "budget_exceeded",
                    "message": f"BUDGET_EXCEEDED: spent ${state['spent']:.2f} + in-flight ${state['reserved']:.2f} + this call (<= ${est:.4f}) would pass the hard cap ${HARD_CAP:.2f}. No further Bedrock calls are possible."}})
            state["reserved"] += est
        try:
            out = call_bedrock(model, body)
        except urllib.error.HTTPError as e:
            with lock:
                state["reserved"] -= est
            msg = e.read().decode(errors="replace")[:2000]
            return self.send(e.code if e.code in (400, 403, 404, 429, 500, 503) else 502, {"error": {"type": "bedrock_error", "status": e.code, "message": msg}})
        except Exception as e:
            with lock:
                state["reserved"] -= est
            return self.send(502, {"error": {"type": "proxy_error", "message": repr(e)[:2000]}})
        u = out.get("usage", {})
        tin, tout = int(u.get("inputTokens", 0)), int(u.get("outputTokens", 0))
        cost = tin * pin / 1e6 + tout * pout / 1e6
        text, reasoning, tool_calls = "", "", []
        for c in out.get("output", {}).get("message", {}).get("content", []):
            if "text" in c:
                text += c["text"]
            elif "reasoningContent" in c:
                reasoning += c["reasoningContent"].get("reasoningText", {}).get("text", "")
            elif "toolUse" in c:
                tu = c["toolUse"]
                tool_calls.append({"id": tu.get("toolUseId"), "type": "function",
                                   "function": {"name": tu.get("name"), "arguments": json.dumps(tu.get("input", {}))}})
        if (req.get("response_format") or {}).get("type") in ("json_object", "json_schema"):
            t = text.strip()
            if t.startswith("```"):
                t = t.split("\n", 1)[1] if "\n" in t else t
                t = t.rsplit("```", 1)[0]
            text = t.strip()
        with lock:
            state["reserved"] -= est
            state["spent"] += cost
            state["calls"] += 1
            m = state["by_model"].setdefault(model, {"calls": 0, "in": 0, "out": 0, "cost": 0.0})
            m["calls"] += 1; m["in"] += tin; m["out"] += tout; m["cost"] += cost
            with open(LEDGER, "a") as f:
                f.write(json.dumps({"ts": time.time(), "model": model, "in": tin, "out": tout, "cost": cost, "cum": state["spent"]}) + "\n")
            if state["calls"] % 25 == 0 or state["spent"] > HARD_CAP * 0.9:
                write_status()
            spent = state["spent"]
        stop = out.get("stopReason")
        finish = "tool_calls" if tool_calls else ("length" if stop == "max_tokens" else "stop")
        msg = {"role": "assistant", "content": text if (text or not tool_calls) else None}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        if reasoning:
            msg["reasoning_content"] = reasoning
        usage = {"prompt_tokens": tin, "completion_tokens": tout, "total_tokens": tin + tout}
        rid = f"bedrock-{int(time.time()*1000)}"
        if req.get("stream"):
            delta = {"role": "assistant", "content": msg["content"] or ""}
            if tool_calls:
                delta["tool_calls"] = [dict(tc, index=i) for i, tc in enumerate(tool_calls)]
            chunks = [{"id": rid, "object": "chat.completion.chunk", "created": int(time.time()), "model": model,
                       "choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
                      {"id": rid, "object": "chat.completion.chunk", "created": int(time.time()), "model": model,
                       "choices": [{"index": 0, "delta": {}, "finish_reason": finish}], "usage": usage}]
            body_b = "".join("data: " + json.dumps(c) + "\n\n" for c in chunks) + "data: [DONE]\n\n"
            b = body_b.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return
        self.send(200, {
            "id": rid, "object": "chat.completion", "created": int(time.time()), "model": model,
            "choices": [{"index": 0, "finish_reason": finish, "message": msg}],
            "usage": usage, "cost_usd": cost, "budget_spent_usd": spent, "budget_cap_usd": HARD_CAP})


if __name__ == "__main__":
    load_ledger()
    write_status()
    print(f"bedrock proxy on 127.0.0.1:{PORT}; spent so far ${state['spent']:.4f}; hard cap ${HARD_CAP}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
