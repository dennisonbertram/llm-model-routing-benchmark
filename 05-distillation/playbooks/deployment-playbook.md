# Deployment Playbook — LLM Model Routing Gateway

Live verified. Covers: starting the gateway, verifying routing, confirming the
budget guard, and graduated rollout approach.

---

## 1. Pre-deployment checklist

**Live verified** (L4; L5; capstone)

Before starting the gateway:

- [ ] Credentials loaded: `[ -n "$OPENAI_API_KEY" ] && echo SET || echo UNSET`
- [ ] Price table current: check `pricing.py` header for reconciliation date and URL
- [ ] Decision threshold set: confirm τ meets your accuracy/cost SLA from the CV benchmark
- [ ] Budget cap set: confirm the per-session USD cap from cost profiling on your workload
- [ ] Fallback chain configured: primary model + at least one fallback (gpt-4o-mini)
- [ ] Ledger path writable: the gateway writes `gateway-ledger.jsonl` to the current dir
- [ ] Observability log path: structured log file is not in a publicly accessible directory

---

## 2. Starting the gateway

**Live verified** (L4; capstone)

```bash
# Load credentials without printing them
set -a; . .agent-university/secrets.local.env; set +a

# Start the gateway (capstone implementation)
cd model-routing/degrees/01-llm-model-routing/03-pocs/L-capstone-adaptive-routing-gateway/source
python3 gateway_server.py 8137 &
GATEWAY_PID=$!

# Smoke test: health check
curl -s localhost:8137/v1/health
# Expected: {"status": "ok"}

# Smoke test: live routing (requires credentials)
curl -s -X POST localhost:8137/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"auto","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":8}'
# Expected: choices[0].message.content non-empty; x_routing.decision and x_routing.usd present
```

Check the ledger was written:
```bash
tail -1 gateway-ledger.jsonl
# Expected: {"ts":..., "decision":..., "chosen_model":..., "usd":...}
```

---

## 3. Verifying routing decisions

**Live verified** (capstone; L4)

The live behavior from the capstone run (2026-06-21):

| Prompt | p_cheap | Model chosen | Response |
|---|---|---|---|
| "capital of France" | 0.97 | gpt-4o-mini | "Paris." |
| "ways to arrange BALLOON" | 0.38 | gpt-4.1 | "1260" (correct) |
| `model:"gpt-4o-mini"` (forced) | — | gpt-4o-mini | honors forced model |

Verify routing logic is working:
1. Easy factual question → should route cheap (p_cheap > threshold)
2. Hard combinatorics/math question → should route strong (p_cheap < threshold)
3. Forced model bypass → `x_routing.decision` should be `"forced"`

Test the threshold is not collapsed:
```bash
# Should route cheap
curl -s -X POST localhost:8137/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"auto","messages":[{"role":"user","content":"What is the capital of Germany?"}],"max_tokens":16}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['x_routing']['decision'])"

# Should route strong (contains hard combinatorics keyword)
curl -s -X POST localhost:8137/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"auto","messages":[{"role":"user","content":"How many permutations of MISSISSIPPI are there?"}],"max_tokens":32}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['x_routing']['decision'], d['x_routing']['chosen_model'])"
```

---

## 4. Verifying the budget guard

**Live verified** (capstone; L5)

Set a deliberately low cap to verify the guard fires:

```bash
# Start capstone with a $0.00025 cap (fires after ~4–6 requests)
BUDGET_CAP=0.00025 python3 run_capstone.py
# Expected output includes: "decision=budget_guard(spent=0.0003>=cap)"
```

Check the ledger for guard events:
```bash
grep "budget_guard" gateway-ledger.jsonl | wc -l
# Should be > 0 if the cap was tight enough

# Or parse structured log:
python3 -c "
import json
entries = [json.loads(l) for l in open('gateway-ledger.jsonl')]
guards = [e for e in entries if 'budget_guard' in e.get('decision','')]
print(f'{len(guards)} budget-guard events out of {len(entries)} requests')
"
```

---

## 5. Verifying provider fallback

**Live verified** (L5; capstone)

Trigger the fallback by passing a bad strong model slug:

```bash
# Capstone handles bad slug → fallback to gpt-4o-mini
curl -s -X POST localhost:8137/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-9000-doesnt-exist","messages":[{"role":"user","content":"test"}],"max_tokens":8}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['x_routing'])"
# Expected: x_routing.fallback_from="gpt-9000-doesnt-exist", x_routing.chosen_model="gpt-4o-mini"
```

From the capstone live run: a bad strong slug fell back to gpt-4o-mini with
`fallback_from=yes` in the routing metadata.

---

## 6. Graduated rollout

**Research supported** (RouterBench methodology; deployment patterns from L3c; L4)

**Step 1 — Shadow mode.** Route all traffic to cheap (or strong) normally; additionally
route a fraction (5–10%) through the experimental router in parallel and log decisions
without serving them. Compare decisions off-band. Verify the new router agrees with the
expected model on well-known easy/hard items.

**Step 2 — Canary.** Route 5% of production traffic through the router. Monitor:
- Cost per request (should decrease vs always-strong baseline)
- Error rate (should not increase vs baseline)
- Budget guard fire rate (should be within expected range)
- User satisfaction proxy (e.g., downstream task success rate)

**Step 3 — Full rollout.** Once canary metrics are stable for 48 hours, route 100%.
Keep the always-strong path as the fallback for any routing failure.

**Step 4 — Threshold recalibration.** Every month (or after major model pool changes),
re-run the benchmark on a fresh sample of production queries to check if the Pareto
curve has shifted (model prices change, workload distributions change).

---

## 7. Stopping the gateway

```bash
kill $GATEWAY_PID
# Or if you lost the PID:
pkill -f "gateway_server.py"
```

Verify the ledger is intact:
```bash
python3 -c "
import json
entries = [json.loads(l) for l in open('gateway-ledger.jsonl')]
total = sum(e['usd'] for e in entries)
print(f'Total spend: \${total:.6f}, requests: {len(entries)}')
"
```

---

## Evidence

- Capstone README.md: live gateway behaviors including "capital of France" → cheap; "arrange BALLOON" → strong. (Live verified)
- Capstone README.md: "Budget guard ($0.00025 cap): reqs 5–6 forced cheap." (Live verified)
- Capstone README.md: "Provider fallback: a deliberately bad strong slug → fell back to gpt-4o-mini." (Live verified)
- L4 README.md: full curl examples and ledger format. (Live verified)
- L5 README.md: FM1 (invalid slug), FM2 (timeout), FM3 (max_tokens), FM4 (budget), FM5 (verify). All live. (Live verified)
