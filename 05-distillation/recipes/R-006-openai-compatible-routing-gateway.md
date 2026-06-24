# R-006: OpenAI-Compatible Routing Gateway (+ base_url Override)

**Category**: recipe
**Evidence tier**: Live verified (POCs L3c, L4, L-capstone)
**Source POCs**: L3c-openai-compatible-gateway-integration, L4-routing-gateway-runtime, L-capstone-adaptive-routing-gateway

## Live verified

A routing gateway that exposes an OpenAI-compatible `/v1/chat/completions` endpoint. Existing
clients connect via a one-line `base_url` override and receive a standard OpenAI response object.

Live verified 10/10 behavioral tests (L3c). Three curl-based live routing decisions (L4).
Capstone gateway curled live with real routing decisions (L-capstone).

Example routing decisions (L3c live run):

| Prompt                    | Requested model | Served model  | USD       | Latency  |
|---------------------------|-----------------|---------------|-----------|----------|
| "What is the capital of France?" | `auto` | `gpt-4o-mini` | $6.30e-06 | 1010 ms |
| "arrange BALLOON" (combinatorics) | `auto` | `gpt-4.1`   | $0.002686 | 3042 ms |
| "Say hello briefly."      | `gpt-4o-mini`   | `gpt-4o-mini` | $3.10e-06 | 957 ms  |

## Client usage — one-line base_url override

**openai-python SDK:**
```python
import openai
client = openai.OpenAI(
    base_url="http://127.0.0.1:8770/v1",
    api_key="not-needed",            # gateway holds real keys server-side
)
resp = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "What is the capital of France?"}],
)
print(resp.model)    # "gpt-4o-mini" (the actually-served model, never "auto")
print(resp.choices[0].message.content)
```

**Vercel AI SDK (TypeScript):**
```typescript
import { createOpenAI } from "@ai-sdk/openai";
const router = createOpenAI({ baseURL: "http://127.0.0.1:8770/v1", apiKey: "x" });
const { text } = await generateText({ model: router("auto"), prompt: "What is 2+2?" });
```

**LangChain (Python):**
```python
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="auto", base_url="http://127.0.0.1:8770/v1", api_key="x")
```

**Raw HTTP (curl / any HTTP client):**
```bash
curl -s http://127.0.0.1:8770/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer x" \
  -d '{"model":"auto","messages":[{"role":"user","content":"What is 2+2?"}]}'
```

## Response contract (live-captured, L3c)

```json
{
  "id":      "chatcmpl-f2a9...",
  "object":  "chat.completion",
  "created": 1750563177,
  "model":   "gpt-4o-mini",
  "choices": [
    {
      "index": 0,
      "message": {"role": "assistant", "content": "The capital of France is Paris."},
      "finish_reason": "stop"
    }
  ],
  "usage": {"prompt_tokens": 14, "completion_tokens": 7, "total_tokens": 21},
  "x_routing": {
    "routed_model": "gpt-4o-mini",
    "latency_ms":   767,
    "usd":          6.3e-06
  }
}
```

Key contracts:
- `model` is the **actually-served** model — never `"auto"`. Clients always see the real backend.
- `usage` contains real upstream token counts.
- `x_routing` is a non-standard extension field; standard clients silently ignore it.
- Forced model requests (`model != "auto"`) are honored without applying any routing logic.

## Minimal gateway implementation (stdlib only)

```python
"""Minimal OpenAI-compatible routing gateway — stdlib http.server, no extra packages."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from providers import chat

CHEAP  = "gpt-4o-mini"
STRONG = "gpt-4.1"

STRONG_KEYWORDS = {
    "combinatorics", "permutations", "arrangements", "probability",
    "integral", "recursion", "prove", "induction", "how many ways",
}

def heuristic_route(messages: list[dict]) -> tuple[str, str]:
    """Returns (model_id, decision_reason)."""
    text = " ".join(m.get("content", "") for m in messages).lower()
    for kw in STRONG_KEYWORDS:
        if kw in text:
            return STRONG, f"keyword:{kw}"
    if len(text.split()) > 120:
        return STRONG, "long_prompt"
    return CHEAP, "default_cheap"


class RoutingHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404); return

        length = int(self.headers.get("Content-Length", 0))
        body   = json.loads(self.rfile.read(length))

        messages    = body.get("messages", [])
        forced_model = body.get("model", "auto")
        max_tokens   = body.get("max_tokens", 512)

        if forced_model == "auto":
            model, decision = heuristic_route(messages)
        else:
            model, decision = forced_model, "forced"

        result = chat(model, messages, max_tokens=max_tokens)

        response = {
            "id":      f"chatcmpl-{id(result):x}",
            "object":  "chat.completion",
            "model":   model,
            "choices": [{
                "index":  0,
                "message": {"role": "assistant", "content": result.text},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens":     result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "total_tokens":      result.prompt_tokens + result.completion_tokens,
            },
            "x_routing": {
                "decision":     decision,
                "routed_model": model,
                "usd":          result.usd,
                "latency_ms":   result.latency_ms,
            },
        }

        payload = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args): pass   # suppress request log noise


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8770
    HTTPServer(("127.0.0.1", port), RoutingHandler).serve_forever()
```

## Swapping in a classifier router

To use the logistic classifier (R-001) instead of keyword heuristics, replace
`heuristic_route` with `classifier_route`:

```python
# At startup, load the trained model
import numpy as np
w, b = load_logistic_weights("router_weights.json")
embed_cache = {}

def classifier_route(messages: list[dict]) -> tuple[str, str]:
    text  = messages[-1].get("content", "")
    if text not in embed_cache:
        (vec,), _ = embed([text])
        v = np.array(vec, dtype=np.float64)
        v /= np.linalg.norm(v) + 1e-12
        embed_cache[text] = v
    p = float(sigmoid(embed_cache[text] @ w + b))
    model = CHEAP if p >= 0.80 else STRONG
    return model, f"classifier:p_cheap={p:.3f}"
```

Live verified (capstone): "capital of France" → p_cheap=0.97 → gpt-4o-mini;
"arrange BALLOON" → p_cheap=0.38 → gpt-4.1 → "1260" (correct). (L-capstone)

## Gotchas (live-discovered, L3c, L4)

- The gateway starts and serves `/v1/health` even without API credentials. The 502 error
  only appears when a real upstream call is attempted. Health-check liveness and
  credential-validity are independent concerns — test them separately. (L4)
- OpenAI-python's `base_url` override worked out of the box with no other changes —
  confirmed in this workspace with the real openai package. (L3c)
- Per-request JSONL cost ledger (`cost-ledger.jsonl`) enables offline budget audit. Never
  log the raw API key value; log only token counts, USD, decision, and model. (L4, L5)

## Evidence

- L3c-openai-compatible-gateway-integration/README.md — 10/10 live tests, SDK override confirmed
- L4-routing-gateway-runtime/README.md — 3 live curl requests, ledger format
- L-capstone-adaptive-routing-gateway/README.md — classifier gateway, budget guard, fallback
- results-digest.md lines 27–29 — live gateway behavior
