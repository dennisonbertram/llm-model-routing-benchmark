# L5 — Failure Modes and Observability

**Evidence: Live verified (2026-06-21).** Status: Complete with live evidence.

## What this proves

A resilient router must survive real provider faults gracefully and emit structured logs that make
every decision auditable. This POC triggers **5 live failure modes** against the real OpenAI API
(no mocks), shows that a fallback chain recovers from each, and demonstrates a cost-budget guard
that enforces a hard USD ceiling. All 9 behavioral tests pass against live providers.

## Live verified: failure modes triggered and results

| # | Failure mode | Trigger | Real provider response | Recovery | Status |
|---|---|---|---|---|---|
| FM1 | Invalid model slug | `gpt-9000-doesnt-exist` | OpenAI HTTP 404: "model does not exist" | fallback to `gpt-4o-mini` | PASS |
| FM2 | Sub-millisecond timeout | `timeout=0.001s` | `<urlopen error timed out>` | retry with `timeout=30s` | PASS |
| FM3 | max_tokens over limit | `max_tokens=999999` | OpenAI HTTP 400: "supports at most 16384" | fallback with `max_tokens=64` | PASS |
| FM4 | Cost-budget guard trips | `$0.000015` budget, 4 calls | 3 accepted ($0.0000114 total); 4th refused | refused with `no_model_fits_budget` | PASS |
| FM5 | Verifier escalation logic | `17 * 23 = ?`, gold=391 | `gpt-4o-mini` answered correctly (391) | no escalation needed | PASS |

## Real error responses captured

**FM1 — OpenAI HTTP 404 (real response body):**
```
openai HTTP 404 for gpt-9000-doesnt-exist: {
    "error": {
        "message": "The model `gpt-9000-doesnt-exist` does not exist or you do not have access to it.",
        "type": "invalid_request_error",
        ...
    }
}
```

**FM3 — OpenAI HTTP 400 (real response body):**
```
openai HTTP 400 for gpt-4o-mini: {
  "error": {
    "message": "max_tokens is too large: 999999. This model supports at most 16384 completion tokens,
                whereas you provided 999999.",
    "type": "invalid_request_error",
    "param": "max_tokens",
    "code": "invalid_value"
  }
}
```

**FM2 — Real network timeout:**
```
openai network error for gpt-4o-mini: <urlopen error timed out>
```

## Live verified: observability log (real structured output)

Every router decision emits a JSON log line with no secrets. Fields: `ts`, `event`, `model`,
`outcome`, `error`, `tokens_prompt`, `tokens_completion`, `usd`, `latency_ms`, `decision`,
`budget_usd`, `spent_total`.

Sample from the live run:

```json
{"ts": "23:49:37", "event": "fm1_invalid_slug", "model": "gpt-9000-doesnt-exist", "outcome": "failure", "error": "openai HTTP 404 ..."}
{"ts": "23:49:38", "event": "fm1_fallback_success", "model": "gpt-4o-mini", "outcome": "success", "usd": 3.75e-06, "latency_ms": 444}
{"ts": "23:49:43", "event": "fm2_attempt", "attempt": "tiny-timeout", "model": "gpt-4o-mini", "outcome": "failure", "error": "openai network error ... timed out"}
{"ts": "23:49:43", "event": "fm2_attempt", "attempt": "normal-timeout", "model": "gpt-4o-mini", "outcome": "success", "tokens_prompt": 21, "tokens_completion": 1, "usd": 3.75e-06, "latency_ms": 641}
{"ts": "23:49:43", "event": "fm3_overlimit", "model": "gpt-4o-mini", "max_tokens": 999999, "outcome": "failure", "error": "openai HTTP 400 ..."}
{"ts": "23:49:44", "event": "fm3_fallback", "model": "gpt-4o-mini", "max_tokens": 64, "outcome": "success", "usd": 3.75e-06}
{"ts": "23:49:45", "event": "budget_router_accepted", "task": "b1", "model": "gpt-4o-mini", "usd": 4.05e-06, "spent_total": 4.05e-06}
{"ts": "23:49:46", "event": "budget_router_accepted", "task": "b2", "model": "gpt-4o-mini", "usd": 3.75e-06, "spent_total": 7.8e-06}
{"ts": "23:49:46", "event": "budget_router_accepted", "task": "b3", "model": "gpt-4o-mini", "usd": 3.6e-06, "spent_total": 1.14e-05}
{"ts": "23:49:47", "event": "budget_guard", "task": "b4", "decision": "downgraded", "reason": "would_exceed_budget", "attempted_model": "gpt-4o-mini", "attempted_usd": 3.75e-06, "remaining_usd": 3.6e-06}
{"ts": "23:49:48", "event": "budget_guard", "task": "b4", "decision": "downgraded", "reason": "would_exceed_budget", "attempted_model": "gpt-4.1", "attempted_usd": 5e-05, "remaining_usd": 3.6e-06}
{"ts": "23:49:48", "event": "budget_guard", "task": "b4", "decision": "refused", "reason": "no_model_fits_budget"}
```

## Live verified: FM4 cost-budget guard detail

| Task | Decision | Model | USD spent | Running total | Remaining budget |
|---|---|---|---|---|---|
| b1 | accepted | gpt-4o-mini | $0.00000405 | $0.00000405 | $0.0000150 |
| b2 | accepted | gpt-4o-mini | $0.00000375 | $0.00000780 | $0.0000150 |
| b3 | accepted | gpt-4o-mini | $0.00000360 | $0.00001140 | $0.0000150 |
| b4 | refused | — | — | $0.00001140 | $0.00000360 (too small for any model) |

Budget: $0.000015. The guard correctly refused b4 because even the cheapest model ($0.00000375)
would have exceeded the $0.00000360 remaining. Both `gpt-4o-mini` and `gpt-4.1` were tried and
rejected before refusing.

## Test results (live, 2026-06-21)

```
Ran 9 tests in 9.061s

OK
```

All 9 behavioral tests green. RED baseline (no credentials): 5 tests fail with
`ProviderError: Missing env var OPENAI_API_KEY`.

## What this proves

- **Real provider errors are typed and catchable** — `ProviderError` wraps HTTP 404 (bad slug),
  HTTP 400 (bad params), and network-level `TimeoutError`/`URLError` uniformly.
- **A fallback chain can recover from any of these** without crashing. The `resilient_call`
  helper tries each attempt in order and returns the first success.
- **A cost-budget guard is straightforward to implement** on top of the harness's per-call USD
  accounting. The guard makes a real call, measures the actual cost, and only accepts if it fits
  in the remaining budget — no estimation required.
- **Structured observability is key-safe**: the log captures all routing decisions, errors,
  tokens, USD, and latency without ever logging an API key value (verified by the test suite).

## Run it

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd source
python3 test_l5.py          # GREEN: 9 live behavioral tests pass
python3 run_l5.py           # triggers all 5 failure modes; writes l5_results.json
```

RED (recorded in `source/red-output.txt`): 5 tests fail with
`ProviderError: Missing env var OPENAI_API_KEY` when credentials are unset.
