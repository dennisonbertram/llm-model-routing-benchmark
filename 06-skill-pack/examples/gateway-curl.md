# Example: Gateway Curl Session

Live verified (capstone; L4; 2026-06-21/22). Complete curl session against the
adaptive routing gateway showing cheap route, strong route, forced model, and cost ledger.

Back to [index](../index.md).

---

## Setup

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd model-routing/degrees/01-llm-model-routing/03-pocs/L-capstone-adaptive-routing-gateway/source
python3 gateway_server.py 8137 &
```

Expected:
```
adaptive routing gateway on :8137
```

---

## Curl 1: easy QA — routes cheap

```bash
curl -s -X POST localhost:8137/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"auto","messages":[{"role":"user","content":"What is the capital of France?"}]}'
```

Live response (2026-06-22):
```json
{
  "id": "amr-gw",
  "object": "chat.completion",
  "model": "gpt-4o-mini",
  "choices": [{"index": 0, "message": {"role": "assistant", "content": "Paris."}, "finish_reason": "stop"}],
  "usage": {"estimated_usd": 4e-06},
  "x_routing_decision": "classifier(p_cheap=0.97,thr=0.6)"
}
```

`p_cheap=0.97` — classifier very confident cheap is sufficient. Correct answer, $4e-06.

---

## Curl 2: hard math — routes strong

```bash
curl -s -X POST localhost:8137/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"auto","messages":[{"role":"user","content":"How many ways can you arrange the letters in BALLOON?"}]}'
```

Live response (2026-06-22):
```json
{
  "id": "amr-gw",
  "object": "chat.completion",
  "model": "gpt-4.1",
  "choices": [{"index": 0, "message": {"role": "assistant", "content": "1260"}, "finish_reason": "stop"}],
  "usage": {"estimated_usd": 6.8e-05},
  "x_routing_decision": "classifier(p_cheap=0.38,thr=0.6)"
}
```

`p_cheap=0.38` — classifier not confident cheap will handle this; routes to strong.
Answer "1260" is correct (7! / (2! × 2!) for duplicate L and O). Cost: $6.8e-05.

Note: The strong model costs 17x more per request than cheap for this query, but the
routing decision is correct — cheap gpt-4o-mini gets this combinatorics problem wrong.

---

## Curl 3: forced model (drop-in client pattern)

```bash
curl -s -X POST localhost:8137/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"Say hello briefly."}]}'
```

Live response (2026-06-22):
```json
{
  "id": "amr-gw",
  "model": "gpt-4o-mini",
  "choices": [{"message": {"content": "Hello!"}}],
  "x_routing_decision": "forced"
}
```

When `model` is a specific model ID (not "auto"), routing is bypassed. Existing clients
that pass a concrete model ID continue to work transparently through the gateway.

---

## Cost ledger (gateway-ledger.jsonl)

```bash
cat gateway-ledger.jsonl
```

Live captured (2026-06-22):
```json
{"ts": "2026-06-22T03:57:57Z", "decision": "classifier(p_cheap=0.97,thr=0.6)", "served_model": "gpt-4o-mini", "usd": 4e-06, "latency_ms": 1094, "fallback_from": null, "escalated": false, "total_spent": 4e-06}
{"ts": "2026-06-22T03:57:59Z", "decision": "classifier(p_cheap=0.38,thr=0.6)", "served_model": "gpt-4.1", "usd": 6.8e-05, "latency_ms": 1214, "fallback_from": null, "escalated": false, "total_spent": 7.2e-05}
{"decision": "forced", "served_model": "gpt-4o-mini", "usd": 3e-06}
```

---

## Stop the gateway

```bash
kill %1
```

---

## openai-python SDK override (L3c)

Live verified (L3c; 10/10 tests pass).

```python
import openai
client = openai.OpenAI(
    base_url="http://127.0.0.1:8137/v1",
    api_key="not-needed"   # gateway doesn't validate this field
)
resp = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "What is the capital of France?"}]
)
print(resp.model)       # "gpt-4o-mini" — actually-served model
print(resp.choices[0].message.content)   # "Paris."
```

The `base_url` override is the only change needed. All other client code is unchanged.
