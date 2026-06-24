# Lesson: OpenAI-Compatible Gateway Deployment

Live verified (L3c; L4; L5; capstone; 2026-06-21/22). Running a model router as a
live HTTP service that any OpenAI SDK client can call without modification.

Back to [index](../index.md).

---

## What it is

An OpenAI-compatible gateway exposes `POST /v1/chat/completions` with the same wire
format as the OpenAI API. Clients pass `{model: "auto", messages: [...]}`. The gateway
routes internally to the cheapest sufficient model, makes the real upstream call, and
returns a standard `chat.completion` object whose `model` field reports the actually-served
model.

---

## Live evidence

### L3c: base_url override (10/10 live tests)

Live verified. From `03-pocs/L3c-openai-compatible-gateway-integration/README.md`.

One-line SDK override:
```python
import openai
client = openai.OpenAI(base_url="http://127.0.0.1:8770/v1", api_key="not-needed")
resp = client.chat.completions.create(model="auto", messages=[...])
```

Measured live:
- `auto` + factual: routed to gpt-4o-mini, $6.30e-06, 1010 ms
- `auto` + combinatorics: routed to gpt-4.1, $0.002686, 3042 ms
- explicit passthrough `gpt-4.1-nano`: honored, $3.10e-06, 957 ms

### L4: HTTP gateway runtime (3 live curls)

Live verified. From `03-pocs/L4-routing-gateway-runtime/README.md`.

| request | routed to | decision | USD |
|---------|-----------|----------|-----|
| "What is the capital of France?" | gpt-4o-mini | default_cheap | $0.0000063 |
| "... combinatorics?" | gpt-4.1 | keyword:combinatorics | $0.001078 |
| forced gpt-4o-mini | gpt-4o-mini | forced | $0.0000029 |

Cost ledger entry (real captured output):
```json
{"ts": "2026-06-22T03:48:57Z", "decision": "default_cheap", "chosen_model": "gpt-4o-mini",
 "prompt_tokens": 14, "completion_tokens": 7, "usd": 6.3e-06, "latency_ms": 763}
```

### L5: 5 live failure modes recovered

Live verified. From `03-pocs/L5-failure-modes-and-observability/README.md`.

| Failure | Trigger | Recovery |
|---------|---------|----------|
| Invalid slug | `gpt-9000-doesnt-exist` | HTTP 404 from OpenAI → fallback to gpt-4o-mini |
| Sub-ms timeout | `timeout=0.001s` | Network timeout → retry with 30s timeout |
| max_tokens overlimit | `max_tokens=999999` | HTTP 400 from OpenAI → fallback with max_tokens=64 |
| Budget guard | $0.000015 cap, 4 calls | 3 accepted; 4th refused (no_model_fits_budget) |
| Verifier no-escalate | gpt-4o-mini correct answer | No escalation triggered (correct behavior) |

---

## Wire format contract

Live verified (L3c; L4; capstone).

The gateway MUST return:
- `model` = the actually-served model (never `"auto"`)
- `choices[0].message.content` = non-null text
- `usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens`
- Any extension fields (e.g., `x_routing_decision`, `x_routing`) in named non-standard fields

Standard clients ignore extension fields. The `model` field is the only routing-visible
field that standard clients read.

---

## Deployment pattern (from capstone)

Live verified.

```
python3 gateway_server.py 8137 &   # start on port 8137
curl ... localhost:8137/v1/chat/completions   # any client
# inspect cost ledger:
cat gateway-ledger.jsonl
kill %1   # stop
```

The ledger format (live-captured):
```json
{"ts": "2026-06-22T03:57:57Z", "decision": "classifier(p_cheap=0.97,thr=0.6)",
 "served_model": "gpt-4o-mini", "usd": 4e-06, "latency_ms": 1094,
 "fallback_from": null, "escalated": false, "total_spent": 4e-06}
```

---

## Observability requirements

Live verified (L5).

Every request must log: `ts`, `event`, `model`, `outcome`, `error` (if any), `tokens_prompt`,
`tokens_completion`, `usd`, `latency_ms`, `decision`, `budget_usd`, `spent_total`.

No API key value in any log line. Verify with a test that scans log output for the known key prefix.

---

## When to use a gateway deployment

- You want to swap in routing for an existing client that already calls OpenAI.
- You need a centralized cost ledger for a multi-client application.
- You want to apply budget guards, fallback chains, or routing policies server-side.

## When NOT to use

- Client-side routing is acceptable (you control all callers) — saves the network hop.
- The gateway itself becomes a latency bottleneck (no async handling in the stdlib http.server).

---

## Recipe

[recipes/R-004-adaptive-gateway.md](../recipes/R-004-adaptive-gateway.md)

## Troubleshooting

- [troubleshooting/empty-response-reasoning-model.md](../troubleshooting/empty-response-reasoning-model.md)

## POC sources

- `../03-pocs/L3c-openai-compatible-gateway-integration/`
- `../03-pocs/L4-routing-gateway-runtime/`
- `../03-pocs/L5-failure-modes-and-observability/`
- `../03-pocs/L-capstone-adaptive-routing-gateway/`
