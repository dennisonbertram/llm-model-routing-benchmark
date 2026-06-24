# L3c — OpenAI-Compatible Routing Gateway Integration

**Evidence: Live verified (2026-06-22).** Status: Complete with live evidence.

## What this proves

A routing decision layer can be exposed behind an **OpenAI-compatible wire interface** so that
existing clients — the `openai` Python SDK, raw `urllib` calls, LangChain, Vercel AI SDK — connect
to it without modification, using only a `base_url` override. The client sends `{model:"auto", ...}`.
The gateway routes to a real upstream model and returns a standard OpenAI `chat.completion` object.
This is the **deployment integration seam** for any model router in this degree.

## Live verified results

| Test | Requested model | Model actually served | USD | Latency |
|---|---|---|---|---|
| cheap route (factual) | `auto` | `gpt-4o-mini` | $6.30e-06 | 1010 ms |
| strong route (combinatorics) | `auto` | `gpt-4.1` | $0.002686 | 3042 ms |
| explicit passthrough | `gpt-4.1-nano` | `gpt-4.1-nano` | $3.10e-06 | 957 ms |

openai Python SDK (`base_url` override): **used, all pass** — `model=gpt-4o-mini content='The capital of France is Paris.'`

10/10 behavioral tests pass (4 offline heuristic + 6 live wire).

## Response shape (actual captured output)

For `{model:"auto", messages:[{role:"user", content:"What is the capital of France?"}]}`:

```json
{
  "id": "chatcmpl-f2a9...",
  "object": "chat.completion",
  "created": 1750563177,
  "model": "gpt-4o-mini",
  "choices": [{"index": 0, "message": {"role": "assistant", "content": "The capital of France is Paris."}, "finish_reason": "stop"}],
  "usage": {"prompt_tokens": 14, "completion_tokens": 7, "total_tokens": 21},
  "x_routing": {"routed_model": "gpt-4o-mini", "latency_ms": 767, "usd": 6.3e-06}
}
```

Key contract:
- `model` is the **actually-served** model (never `"auto"`) — clients see the real backend.
- `usage` contains real token counts from the upstream provider.
- `x_routing` is a non-standard extension field; standard clients ignore it.

## How to use it: one-line base_url override

**openai-python:**
```python
import openai
client = openai.OpenAI(base_url="http://127.0.0.1:8770/v1", api_key="not-needed")
resp = client.chat.completions.create(model="auto", messages=[...])
```

**Vercel AI SDK (TypeScript):**
```typescript
import { createOpenAI } from "@ai-sdk/openai";
const router = createOpenAI({ baseURL: "http://127.0.0.1:8770/v1", apiKey: "x" });
const { text } = await generateText({ model: router("auto"), prompt: "..." });
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

## Architecture

```
Client (openai SDK / curl / AI SDK)
    |
    | POST /v1/chat/completions  {model:"auto", messages:[...]}
    v
Gateway (gateway.py — stdlib http.server, no extra packages)
    |
    | heuristic_route(messages) -> "gpt-4o-mini" or "gpt-4.1"
    |   keywords: "combinatorics","permutation","prove","induction" -> strong
    |   keywords: "def ","write a python","what is the capital" -> cheap
    |   fallback: short prompt -> cheap, long prompt (>80 words) -> strong
    v
Harness providers.chat(routed_model, messages)  [real API call]
    |
    v
OpenAI API (upstream, real credentials on server side)
    |
    v
Gateway wraps result in OpenAI chat.completion shape
    |
    v
Client receives standard response — sees actual model served
```

## Routing strategy (no oracle leakage)

The heuristic uses **only the prompt text** as features:
- Strong-signal keywords (math reasoning, combinatorics, proof, induction) → escalate
- Cheap-signal keywords (short coding tasks, factual lookup) → stay cheap
- Length: prompts > 80 words default to strong
- Tie / neither: default to cheap

This is a keyword heuristic — it is simple and interpretable, showing that even a trivial
router can route correctly on well-typed prompts. A classifier or embedding-kNN router
(L2/L2b) would generalize further.

## What the explicit passthrough proves

When a client sends `model:"gpt-4.1-nano"` (not `"auto"`), the gateway honours the explicit
choice and routes there without applying the heuristic. This is the standard proxy behavior
expected by clients that want model pinning for specific calls.

## Surprising live finding

The `openai` Python package was importable in this workspace and the `base_url` override worked
exactly as documented — `client = openai.OpenAI(base_url="http://127.0.0.1:8770/v1", api_key="x")`
made a real call through the gateway with zero code changes on the client side. This confirms
the wire-compat claim is not theoretical: a real SDK client exercised the full path.

## Run it

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd source && python3 test_l3c.py      # GREEN: 10 live behavioral tests pass
python3 run_l3c.py                    # full integration run, writes l3c_evidence.json
```

RED (recorded in `red-output.txt`): with API keys unset, the gateway starts but upstream calls
fail with HTTP 502 (Bad Gateway wrapping ProviderError: Missing env var OPENAI_API_KEY).
Offline heuristic routing tests (4/10) still pass without keys.
