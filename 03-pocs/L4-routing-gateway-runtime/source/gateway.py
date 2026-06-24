"""L4 — Routing Gateway Runtime

A real local HTTP server that exposes POST /v1/chat/completions.

Accepts:
  {"model": "auto" | "<model_id>", "messages": [...], "max_tokens": N}

When model="auto", applies a heuristic router (prompt length + keyword signals):
- Hard math keywords (combinatorics, probability, integral, ...): route to strong (gpt-4.1)
- Short prompts (<= 40 tokens) with no complexity signals: route to cheap (gpt-4o-mini)
- Default: cheap

Returns OpenAI-shaped JSON (id, object, choices, usage, model).
Appends one JSON line to cost-ledger.jsonl on every request.

Ledger line schema:
  {ts, decision, chosen_model, prompt_tokens, completion_tokens, usd, latency_ms}

Run:
  python3 gateway.py [--port 8765]

This file is entirely self-contained; it imports the harness providers module for real API calls.
"""
import argparse
import json
import os
import sys
import time
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
HARNESS = os.path.join(HERE, "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

from providers import chat, ProviderError  # noqa: E402
from config import CHEAP_DEFAULT, STRONG_DEFAULT  # noqa: E402

LEDGER_PATH = os.path.join(HERE, "cost-ledger.jsonl")
_ledger_lock = threading.Lock()

# Signals that push routing toward the strong model.
STRONG_KEYWORDS = {
    "combinatorics", "probability", "integral", "calculus", "matrix", "eigenvalue",
    "recursion", "recurrence", "induction", "proof", "theorem", "derive", "differentiate",
    "how many ways", "permutation", "combination", "binomial", "modular arithmetic",
    "remainder", "gcd", "lcm", "prime factorization", "number theory",
    "solve for", "inequality", "limit", "convergence", "series expansion",
}


def heuristic_route(prompt_text: str) -> tuple[str, str]:
    """Return (chosen_model_id, decision_reason).

    Rules (in order of priority):
    1. Any hard-math keyword present -> strong
    2. Prompt length > 120 words -> strong (complex multi-step tasks are usually longer)
    3. Default -> cheap
    """
    lower = prompt_text.lower()
    word_count = len(prompt_text.split())

    for kw in STRONG_KEYWORDS:
        if kw in lower:
            return STRONG_DEFAULT, f"keyword:{kw}"

    if word_count > 120:
        return STRONG_DEFAULT, "long_prompt"

    return CHEAP_DEFAULT, "default_cheap"


def _append_ledger(entry: dict):
    line = json.dumps(entry)
    with _ledger_lock:
        with open(LEDGER_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")


class GatewayHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # silence default access log to stderr
        pass

    def do_GET(self):
        if self.path == "/v1/health":
            self._send_json(200, {"status": "ok", "ledger": LEDGER_PATH})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self._send_json(404, {"error": "only /v1/chat/completions is supported"})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            req = json.loads(body.decode("utf-8"))
        except Exception as e:
            self._send_json(400, {"error": f"bad JSON: {e}"})
            return

        messages = req.get("messages", [])
        model_req = req.get("model", "auto")
        max_tokens = req.get("max_tokens", 512)

        # Routing decision
        if model_req == "auto":
            prompt_text = " ".join(m.get("content", "") for m in messages)
            chosen_model, decision = heuristic_route(prompt_text)
        else:
            chosen_model = model_req
            decision = "forced"

        # Live model call
        t0 = time.time()
        try:
            result = chat(chosen_model, messages, max_tokens=max_tokens)
        except ProviderError as e:
            self._send_json(502, {"error": str(e)})
            return
        latency_ms = int((time.time() - t0) * 1000)

        # Persist ledger entry
        ledger_entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "decision": decision,
            "chosen_model": chosen_model,
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
            "usd": round(result["usd"], 8),
            "latency_ms": latency_ms,
        }
        _append_ledger(ledger_entry)

        # Build OpenAI-shaped response
        response = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": chosen_model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": result["text"]},
                    "finish_reason": result.get("finish_reason", "stop"),
                }
            ],
            "usage": {
                "prompt_tokens": result["prompt_tokens"],
                "completion_tokens": result["completion_tokens"],
                "total_tokens": result["total_tokens"],
            },
            # Extended metadata (non-standard, for routing transparency)
            "x_routing": {
                "decision": decision,
                "chosen_model": chosen_model,
                "usd": round(result["usd"], 8),
                "latency_ms": latency_ms,
            },
        }
        self._send_json(200, response)

    def _send_json(self, code: int, obj: dict):
        body = json.dumps(obj, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    ap = argparse.ArgumentParser(description="Model Routing Gateway — OpenAI-compatible local server")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()

    server = HTTPServer(("127.0.0.1", args.port), GatewayHandler)
    print(f"Gateway listening on http://127.0.0.1:{args.port}", flush=True)
    print(f"Ledger: {LEDGER_PATH}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
