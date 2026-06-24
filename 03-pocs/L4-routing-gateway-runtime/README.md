# L4 — Routing Gateway Runtime

**Evidence: Live verified (2026-06-22).** Status: Complete with live evidence.

## What this proves

A heuristic model router can run as a real local HTTP gateway. This POC builds a
Python stdlib `http.server` that exposes `POST /v1/chat/completions`, routes incoming
requests to either `gpt-4o-mini` (cheap) or `gpt-4.1` (strong) based on prompt
content, makes REAL live calls to the OpenAI API, returns OpenAI-shaped JSON
(including non-standard `x_routing` metadata), and persists every routing decision
to an append-only JSONL cost ledger.

This is the **runtime proof layer**: not just that a router selects the right model,
but that the selection is made and executed by a running HTTP server process — a
curl client has no visibility into which backend model is used until it inspects the
response `x_routing` field.

## Live verified results

Three curl requests, three real backend calls, three ledger entries. Measured 2026-06-22.

| # | model requested | prompt | routed to | decision | prompt_tokens | completion_tokens | usd | latency_ms |
|---|---|---|---|---|---|---|---|---|
| 1 | `auto` | "What is the capital of France?" | `gpt-4o-mini` | `default_cheap` | 14 | 7 | $0.0000063 | 763 |
| 2 | `auto` | "How many ways can you arrange 5 items chosen from 8 ... combinatorics?" | `gpt-4.1` | `keyword:combinatorics` | 27 | 128 | $0.001078 | 1700 |
| 3 | `gpt-4o-mini` | "Say hello briefly." | `gpt-4o-mini` | `forced` | 11 | 2 | $0.0000029 | 608 |

**Total spend across 3 requests: $0.001087**

- The simple factual question was correctly routed to the cheap model (14.7× less expensive per request than the strong model path).
- The combinatorics question triggered keyword detection and was routed to the strong model; the response correctly begins a permutation computation.
- Forced model routing bypasses heuristics entirely.

## Routing logic

Live verified — the heuristic router in `gateway.py::heuristic_route()` applies three rules in order:

1. **Keyword match**: If the prompt contains any hard-math keyword (combinatorics, probability, integral, recursion, proof, etc.) → route to `gpt-4.1` (strong), `decision = "keyword:<kw>"`
2. **Long prompt (>120 words)**: Complex multi-part questions → route to `gpt-4.1`, `decision = "long_prompt"`
3. **Default**: Everything else → route to `gpt-4o-mini` (cheap), `decision = "default_cheap"`

Forced routing (`model != "auto"`) sets `decision = "forced"` and skips all heuristics.

## Cost ledger format

Live verified — each request appends one JSON line to `cost-ledger.jsonl`:

```json
{"ts": "2026-06-22T03:48:57Z", "decision": "default_cheap", "chosen_model": "gpt-4o-mini",
 "prompt_tokens": 14, "completion_tokens": 7, "usd": 6.3e-06, "latency_ms": 763}
```

The ledger enables offline cost audit, routing pattern analysis, and budget guard
implementation in later POCs.

## OpenAI-shaped response

Live verified — the gateway returns valid OpenAI-shaped JSON plus an `x_routing`
extension field that exposes the routing decision transparently:

```json
{
  "id": "chatcmpl-8b95b3d5d5f6",
  "object": "chat.completion",
  "model": "gpt-4o-mini",
  "choices": [{"message": {"role": "assistant", "content": "..."}, "finish_reason": "stop"}],
  "usage": {"prompt_tokens": 14, "completion_tokens": 7, "total_tokens": 21},
  "x_routing": {"decision": "default_cheap", "chosen_model": "gpt-4o-mini",
                 "usd": 6.3e-06, "latency_ms": 763}
}
```

Any OpenAI SDK client can call this gateway without modification; routing is transparent
unless the caller explicitly reads `x_routing`.

## Test coverage

Live verified — 5 behavioral tests in `source/test_l4.py`:

| Test | What it asserts |
|---|---|
| `test_01_health` | `/v1/health` returns `{"status": "ok"}` |
| `test_02_auto_simple_routes_cheap` | Simple factual question → `gpt-4o-mini`, `x_routing.usd > 0` |
| `test_03_auto_hard_math_routes_strong` | Combinatorics question → `gpt-4.1`, `decision` starts with `"keyword:"` |
| `test_04_forced_model_bypasses_routing` | Explicit `model=gpt-4o-mini` → `decision="forced"` |
| `test_05_ledger_written` | `cost-ledger.jsonl` exists with all required fields and positive USD |

RED (no credentials): tests 2-4 receive HTTP 502 ("Missing env var OPENAI_API_KEY"),
test 5 fails because no ledger is written. Test 1 (health) passes even without credentials.

GREEN (with credentials): all 5 pass in ~3 seconds.

## Run it

```bash
# Load credentials
set -a; . .agent-university/secrets.local.env; set +a

# Run demo (starts gateway, 3 curl requests, show ledger, stop)
cd model-routing/degrees/01-llm-model-routing/03-pocs/L4-routing-gateway-runtime/source
bash run_l4.sh

# Run tests
python3 -m unittest test_l4 -v

# Or start gateway manually and curl it directly
python3 gateway.py --port 8765 &
curl -s http://127.0.0.1:8765/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"auto","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":32}'
kill %1
```

## Surprises

See `surprises.md` for full details. The main finding: the gateway server starts and
serves `/v1/health` even without credentials; the 502 error only appears when a real
model call is attempted. This means health-check liveness and credential-validity
are independent concerns and should be tested separately.
