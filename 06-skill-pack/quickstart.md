# Quickstart — LLM Model Routing

Live verified. Five commands to load credentials, start the adaptive routing gateway,
and get a routed response. Every number below is from the committed capstone evidence.

Back to [index](index.md).

---

## Prerequisites

- Python 3.9+, stdlib + numpy only (no pip installs needed for the harness)
- `OPENAI_API_KEY` set (required for chat + embeddings)
- `ANTHROPIC_API_KEY` set (optional; used by the ensemble pool)
- Credentials file: `.agent-university/secrets.local.env` (gitignored)

Check presence without printing the value:

```bash
[ -n "$OPENAI_API_KEY" ] && echo SET || echo UNSET
```

---

## Step 1 — Load credentials

```bash
set -a; . .agent-university/secrets.local.env; set +a
```

---

## Step 2 — Run the baseline (optional, confirms harness works)

Live verified. Runs the 45-task suite through gpt-4o-mini and gpt-4.1, prints the
baseline table, and writes `l0_summary.json`.

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/L0-smoke-and-harness/source
python3 run_l0.py
```

Expected output (live-measured, 2026-06-21):

```
always-cheap  gpt-4o-mini  acc=0.844  $0.00166
always-strong gpt-4.1      acc=0.978  $0.02148  (12.9x cheap)
ORACLE ceil                acc=0.978  $0.00214  (only 6/45 need strong)
```

---

## Step 3 — Start the adaptive routing gateway

Live verified. The capstone gateway runs `gateway_server.py` on localhost port 8137.
It uses a logistic classifier (threshold=0.6 at runtime) trained on embedding features to
route requests to gpt-4o-mini (cheap) or gpt-4.1 (strong). Every request is appended
to `gateway-ledger.jsonl`.

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/L-capstone-adaptive-routing-gateway/source
python3 gateway_server.py 8137 &
```

Expected:

```
adaptive routing gateway on :8137
```

---

## Step 4 — Send a request and inspect routing

Live verified. Two representative requests from the committed green-output.txt:

**Easy QA (routes cheap):**

```bash
curl -s -X POST localhost:8137/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"auto","messages":[{"role":"user","content":"What is the capital of France?"}]}'
```

Expected response fields (live-measured, 2026-06-22):

```json
{
  "model": "gpt-4o-mini",
  "choices": [{"message": {"content": "Paris."}}],
  "x_routing_decision": "classifier(p_cheap=0.97,thr=0.6)"
}
```

`p_cheap=0.97` — classifier is very confident the cheap model is sufficient.
USD: ~$4e-06.

**Hard math (routes strong):**

```bash
curl -s -X POST localhost:8137/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"auto","messages":[{"role":"user","content":"How many ways can you arrange the letters in BALLOON?"}]}'
```

Expected response fields (live-measured, 2026-06-22):

```json
{
  "model": "gpt-4.1",
  "choices": [{"message": {"content": "1260"}}],
  "x_routing_decision": "classifier(p_cheap=0.38,thr=0.6)"
}
```

`p_cheap=0.38` — classifier is not confident cheap will handle this; routes to strong.
Answer "1260" is correct (7! / (2! × 2!) for duplicate L and O).

---

## Step 5 — Read the cost ledger

Live verified. Every request appends one JSON line:

```bash
cat gateway-ledger.jsonl
```

```json
{"ts": "2026-06-22T03:57:57Z", "decision": "classifier(p_cheap=0.97,thr=0.6)", "served_model": "gpt-4o-mini", "usd": 4e-06, "latency_ms": 1094, "fallback_from": null, "escalated": false, "total_spent": 4e-06}
{"ts": "2026-06-22T03:57:59Z", "decision": "classifier(p_cheap=0.38,thr=0.6)", "served_model": "gpt-4.1", "usd": 6.8e-05, "latency_ms": 1214, "fallback_from": null, "escalated": false, "total_spent": 7.2e-05}
```

---

## Benchmark the gateway (optional)

Live verified. Run the 5-fold CV benchmark over 45 tasks and see the full Pareto sweep:

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/L-capstone-adaptive-routing-gateway/source
python3 run_capstone.py
```

Headline from committed evidence (2026-06-21):

```
adaptive(thr=0.8): acc=0.978  $0.00257  pct_cheap=71%
  = 8.4x cheaper than always-strong ($0.02148)
  = 1.20x the unrealizable oracle cost ($0.00214)
```

---

## Stop the gateway

```bash
kill %1
```

---

## What to do next

- Trace the router strategies: [curriculum.md](curriculum.md)
- Understand the negatives (ensembles didn't win): [lessons/L-ensemble-strategies.md](lessons/L-ensemble-strategies.md)
- Build your own logistic classifier: [recipes/R-002-logistic-classifier-router.md](recipes/R-002-logistic-classifier-router.md)
- Pre-deploy checklist: [live-service-checklist.md](live-service-checklist.md)
