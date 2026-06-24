"""L3c — OpenAI-compatible routing gateway.

Exposes a /v1/chat/completions endpoint whose wire shape is identical to the OpenAI REST API.
Clients that normally hit api.openai.com point their base_url at this server instead and send
{model:"auto", messages:[...]} — the gateway routes to a real backend model and returns an
OpenAI-shaped response with:
  - choices[0].message.content  — real answer
  - model                       — actually-served model (not "auto")
  - usage                       — real token counts

Routing strategy (heuristic, no oracle leakage):
  Use the prompt text to classify difficulty by:
    - length: long prompts are typically harder
    - math/reasoning keywords: imply hard reasoning task
    - code keywords: typically cheap-model saturated for short tasks
  Route to gpt-4o-mini (cheap) or gpt-4.1 (strong) accordingly.

Server uses stdlib http.server — no extra packages needed.
"""
import http.server
import json
import os
import sys
import time

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

import config  # noqa: E402
from providers import chat  # noqa: E402

CHEAP = config.CHEAP_DEFAULT   # gpt-4o-mini
STRONG = config.STRONG_DEFAULT  # gpt-4.1

# Keywords that indicate a hard reasoning/math task → escalate to strong model
STRONG_KEYWORDS = [
    "combinatorics", "probability", "integration", "derivative", "differential",
    "eigenvalue", "matrix inverse", "proof", "theorem", "how many ways",
    "in how many", "permutation", "combination", "optimize", "minimize", "maximize",
    "compound interest", "geometric series", "modular arithmetic",
    "prove that", "show that", "for all n", "induction",
]

# Keywords that strongly suggest cheap model is fine (coding / factual retrieval)
CHEAP_KEYWORDS = [
    "def ", "function", "implement", "write a python", "write python",
    "sort ", "reverse ", "fibonacci", "palindrome", "anagram",
    "what is the capital", "who wrote", "who invented", "what year",
]


def heuristic_route(messages: list) -> str:
    """Choose cheap or strong model from message content alone (no oracle features)."""
    text = " ".join(
        m.get("content", "") for m in messages if isinstance(m.get("content"), str)
    ).lower()

    # Strong signal for cheap: short coding/factual prompts
    cheap_hits = sum(1 for kw in CHEAP_KEYWORDS if kw in text)
    strong_hits = sum(1 for kw in STRONG_KEYWORDS if kw in text)

    # Length heuristic: very long prompts tend to be harder
    word_count = len(text.split())
    length_strong = word_count > 80

    if strong_hits > 0 and strong_hits >= cheap_hits:
        return STRONG
    if cheap_hits > 0:
        return CHEAP
    if length_strong:
        return STRONG
    return CHEAP  # default: cheap


def make_openai_response(routed_model: str, chat_result: dict, request_id: str) -> dict:
    """Wrap a harness chat() result into an OpenAI-shaped response object."""
    created = int(time.time())
    return {
        "id": f"chatcmpl-{request_id}",
        "object": "chat.completion",
        "created": created,
        "model": routed_model,  # actually-served model, not "auto"
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": chat_result["text"],
                },
                "logprobs": None,
                "finish_reason": chat_result.get("finish_reason", "stop"),
            }
        ],
        "usage": {
            "prompt_tokens": chat_result["prompt_tokens"],
            "completion_tokens": chat_result["completion_tokens"],
            "total_tokens": chat_result["total_tokens"],
        },
        # Non-standard extension: routing metadata (ignored by standard clients)
        "x_routing": {
            "routed_model": routed_model,
            "latency_ms": chat_result.get("latency_ms"),
            "usd": chat_result.get("usd"),
        },
    }


class GatewayHandler(http.server.BaseHTTPRequestHandler):
    """Handle POST /v1/chat/completions with OpenAI-compatible wire format."""

    def log_message(self, fmt, *args):
        # Suppress default Apache-style access log; we print our own routing log
        pass

    def do_POST(self):
        if self.path not in ("/v1/chat/completions", "/chat/completions"):
            self._error(404, "Not found")
            return

        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            self._error(400, "Empty body")
            return

        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError as e:
            self._error(400, f"Invalid JSON: {e}")
            return

        messages = body.get("messages", [])
        requested_model = body.get("model", "auto")
        max_tokens = body.get("max_tokens", 512)
        temperature = body.get("temperature", 0.0)

        # Route: if client says "auto" use heuristic; otherwise honour explicit model
        if requested_model == "auto":
            routed_model = heuristic_route(messages)
            route_reason = "heuristic"
        else:
            routed_model = requested_model
            route_reason = "passthrough"

        print(f"  [{route_reason}] {requested_model!r} -> {routed_model!r}  "
              f"msg_len={sum(len(m.get('content','')) for m in messages)}")

        try:
            result = chat(routed_model, messages, max_tokens=max_tokens, temperature=temperature)
        except Exception as e:
            self._error(502, f"Upstream error: {e}")
            return

        import hashlib
        req_id = hashlib.md5(json.dumps(messages, sort_keys=True).encode()).hexdigest()[:12]
        response = make_openai_response(routed_model, result, req_id)

        resp_bytes = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp_bytes)))
        self.end_headers()
        self.wfile.write(resp_bytes)

    def _error(self, code: int, msg: str):
        body = json.dumps({"error": {"message": msg, "type": "gateway_error"}}).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server(host="127.0.0.1", port=8765):
    server = http.server.HTTPServer((host, port), GatewayHandler)
    print(f"Gateway listening on http://{host}:{port}/v1/chat/completions")
    print(f"  cheap model : {CHEAP}")
    print(f"  strong model: {STRONG}")
    return server
