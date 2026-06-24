# Lab: L4/L5 — HTTP Gateway + Failure Modes

Live verified (L3c; L4; L5; 2026-06-21/22). Run the gateway, curl it, observe failure recovery.

Back to [index](../index.md).

---

## Goal

Start the HTTP routing gateway, send real curl requests, inspect the routing decision and
cost ledger, then trigger each of the 5 live failure modes and confirm recovery.

---

## Commands: L3c integration

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd model-routing/degrees/01-llm-model-routing/03-pocs/L3c-openai-compatible-gateway-integration/source
python3 -m unittest test_l3c -v    # 10/10 live tests pass
```

---

## Commands: L4 gateway runtime

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/L4-routing-gateway-runtime/source

# Run the demo (starts gateway, 3 curls, prints ledger, stops)
bash run_l4.sh

# Or start manually and curl directly
python3 gateway.py --port 8765 &
curl -s http://127.0.0.1:8765/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"auto","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":32}'
kill %1
```

Expected live output (3 requests, 2026-06-22):
```
req1: gpt-4o-mini  default_cheap       $0.0000063   763ms
req2: gpt-4.1      keyword:combinatorics  $0.001078  1700ms
req3: gpt-4o-mini  forced               $0.0000029   608ms
```

---

## Commands: L5 failure modes

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/L5-failure-modes-and-observability/source

python3 test_l5.py          # 9/9 behavioral tests pass
python3 run_l5.py           # triggers all 5 failure modes; writes l5_results.json
```

Expected: all 5 failures trigger and recover:
- FM1: invalid slug → HTTP 404 → fallback to gpt-4o-mini
- FM2: sub-ms timeout → network timeout → retry with 30s → success
- FM3: max_tokens=999999 → HTTP 400 → fallback with max_tokens=64
- FM4: budget guard → 3 accepted, 4th refused (`no_model_fits_budget`)
- FM5: verifier sees correct answer → no escalation (correct behavior)

---

## What to observe

- The gateway returns HTTP 200 only when it has content. Bad requests return 4xx.
- `x_routing` or `x_routing_decision` carries the routing decision for debugging.
- `model` field in the response is always the actually-served model — never "auto".
- The cost ledger is append-only JSONL. It persists across requests in the same session.
- No API key value appears in structured log output (test for this explicitly).

---

## POC sources

- `../03-pocs/L3c-openai-compatible-gateway-integration/`
- `../03-pocs/L4-routing-gateway-runtime/`
- `../03-pocs/L5-failure-modes-and-observability/`
