# Observability Playbook — LLM Model Routing

Live verified. Covers: routing-decision logging, cost ledger, budget tracking, and
what to monitor in a deployed gateway.

---

## 1. Every routing decision must be logged

**Live verified** (L4; L5; capstone)

Each request through the routing gateway emits one structured JSON line:

```json
{
  "ts": "2026-06-22T03:48:57Z",
  "event": "routed",
  "decision": "default_cheap",
  "chosen_model": "gpt-4o-mini",
  "prompt_tokens": 14,
  "completion_tokens": 7,
  "usd": 6.3e-06,
  "latency_ms": 763
}
```

From the capstone gateway-ledger.jsonl (live evidence):
- `auto` + "capital of France" → `p_cheap=0.97` → `gpt-4o-mini` → "Paris." — $6.3e-06
- `auto` + "arrange BALLOON" → `p_cheap=0.38` → `gpt-4.1` → "1260" (correct) — $1.1e-03

Required fields per log line:
- `ts` — ISO 8601 timestamp (UTC)
- `decision` — reason for routing choice (e.g., `classifier_cheap`, `classifier_strong`,
  `forced`, `budget_guard`, `fallback_from=gpt-9000`, `default_cheap`)
- `chosen_model` — the model actually used
- `prompt_tokens`, `completion_tokens` — from the response usage object
- `usd` — cost computed as `tokens × price` (uniform method)
- `latency_ms` — wall-clock time for the API call

Optional (add when available):
- `p_cheap` — classifier probability (for classifier-based routers)
- `fallback_from` — original model slug when a fallback fired
- `budget_spent`, `budget_remaining` — running totals for budget-guard sessions

---

## 2. Never log API key values

**Live verified** (L5)

The L5 test suite explicitly asserts that API key values do not appear in any log line.
Structured observability must be key-safe. The log captures routing decisions, errors,
tokens, USD, and latency — none of which requires the key value.

Check:
```python
def test_no_api_key_in_log(self):
    key = os.environ.get("OPENAI_API_KEY", "")
    if key:
        with open("routing-log.jsonl") as f:
            content = f.read()
        self.assertNotIn(key, content, "API key must not appear in log")
```

Run this test on every log rotation or before shipping log files to external storage.

---

## 3. The cost ledger is the financial audit trail

**Live verified** (L4; capstone)

The cost ledger (`cost-ledger.jsonl`, `gateway-ledger.jsonl`) is an append-only file
written after each request. It is the ground truth for:
- Total spend per session
- Distribution of cheap vs. strong routing
- Whether the budget guard is calibrated correctly
- Anomaly detection (spike in strong-model routing = shift in query difficulty)

Compute from the ledger:

```python
import json

with open("gateway-ledger.jsonl") as f:
    entries = [json.loads(line) for line in f]

total_usd = sum(e["usd"] for e in entries)
pct_cheap = sum(1 for e in entries if "mini" in e["chosen_model"]) / len(entries)
budget_guard_fires = sum(1 for e in entries if "budget_guard" in e.get("decision", ""))
```

The capstone live run showed: 71% of requests routed cheap, 2 budget-guard fires in a
6-request demo with $0.00025 cap.

---

## 4. Routing-decision observability in the HTTP response

**Live verified** (L3c; L4; capstone)

The gateway returns standard OpenAI-shaped JSON plus an `x_routing` extension field:

```json
{
  "id": "chatcmpl-8b95b3d5d5f6",
  "object": "chat.completion",
  "model": "gpt-4o-mini",
  "choices": [...],
  "usage": {"prompt_tokens": 14, "completion_tokens": 7, "total_tokens": 21},
  "x_routing": {
    "decision": "default_cheap",
    "chosen_model": "gpt-4o-mini",
    "usd": 6.3e-06,
    "latency_ms": 763
  }
}
```

The `x_routing` field is visible to clients that explicitly check it. Clients that only
read `choices[0].message.content` are unaffected. This enables:
- Debugging: a client can log which model was used for each request
- Testing: assert `x_routing.decision` matches expectation without parsing the full response
- Monitoring: parse `x_routing.usd` for per-request cost tracking in a caller-side ledger

---

## 5. Failure observability — what a fault looks like in the log

**Live verified** (L5)

Real error log lines from the L5 live run:

```json
{"ts": "23:49:37", "event": "fm1_invalid_slug", "model": "gpt-9000-doesnt-exist",
 "outcome": "failure", "error": "openai HTTP 404: model does not exist"}
{"ts": "23:49:38", "event": "fm1_fallback_success", "model": "gpt-4o-mini",
 "outcome": "success", "usd": 3.75e-06, "latency_ms": 444}

{"ts": "23:49:43", "event": "fm2_attempt", "attempt": "tiny-timeout",
 "outcome": "failure", "error": "openai network error ... timed out"}
{"ts": "23:49:43", "event": "fm2_attempt", "attempt": "normal-timeout",
 "outcome": "success", "tokens_prompt": 21, "tokens_completion": 1, "usd": 3.75e-06}

{"ts": "23:49:48", "event": "budget_guard", "task": "b4",
 "decision": "refused", "reason": "no_model_fits_budget", "remaining_usd": 3.6e-06}
```

Five fault types and their log signatures (all live-verified, L5):

| Fault | Log event | Recovery signal |
|---|---|---|
| Invalid model slug | `outcome=failure`, `error="HTTP 404"` | `fm1_fallback_success` |
| Network timeout | `outcome=failure`, `error="timed out"` | `fm2_attempt` with `attempt="normal-timeout"` |
| max_tokens over limit | `outcome=failure`, `error="HTTP 400"` | `fm3_fallback` with corrected params |
| Budget guard fires | `event=budget_guard`, `decision=downgraded/refused` | No recovery — request refused or downgraded |
| Verifier no-escalate | `event=fm5_verify`, `decision=no_escalate` | Normal routing continues |

Alert thresholds to set in production:
- `fallback_from != null` rate > 2% of requests → investigate model slug or provider status
- `budget_guard.reason=refused` rate > 0 → investigate budget calibration
- `latency_ms > 5000` rate > 5% → investigate provider latency or retry storms
- `outcome=failure` without a subsequent success → investigate provider availability

---

## 6. Health check endpoint — separate from credential validity

**Live verified** (L4; L5)

The gateway's `/v1/health` endpoint returns `{"status": "ok"}` even when credentials
are not loaded. This is intentional: the liveness check (is the process running?) is
a different concern from credential validity (can it make API calls?).

Do NOT use `/v1/health` as evidence that the gateway can route requests. Use a
separate readiness probe that makes a real cheap-model call and checks for a valid
response. The L5 test suite splits these:

```python
def test_01_health(self):
    # Passes even without credentials
    resp = self.client.get("/v1/health")
    self.assertEqual(resp["status"], "ok")

def test_02_auto_simple_routes_cheap(self):
    # Fails without credentials (HTTP 502); passes with them
    resp = self.client.post("/v1/chat/completions", ...)
    self.assertIn("gpt-4o-mini", resp["x_routing"]["chosen_model"])
```

---

## Evidence

- L4 README.md: "Three curl requests, three real backend calls, three ledger entries." + full ledger format. (Live verified)
- L5 README.md: structured log JSON from live run; all 5 failure modes and their log signatures. (Live verified)
- Capstone README.md: "every request appended to `gateway-ledger.jsonl` (decision, model, tokens, USD, latency)." (Live verified)
- L5 README.md: "Structured observability is key-safe: the log captures all routing decisions, errors, tokens, USD, and latency without ever logging an API key value (verified by the test suite)." (Live verified)
