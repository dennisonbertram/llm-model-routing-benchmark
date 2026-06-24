# Evidence

Evidence tier: Live verified (2026-06-21).

## Live calls made

All calls were made on 2026-06-21 from this workspace against the real OpenAI API.
No cached responses were used — each failure mode required a fresh live call to trigger.

### FM1 — Invalid model slug
- Model attempted: `gpt-9000-doesnt-exist` (POST to https://api.openai.com/v1/chat/completions)
- Real response: HTTP 404, body: `{"error": {"message": "The model gpt-9000-doesnt-exist does not exist or you do not have access to it.", "type": "invalid_request_error"}}`
- Fallback model: `gpt-4o-mini` — succeeded, latency 444ms, cost $0.00000375

### FM2 — Sub-millisecond timeout
- Model: `gpt-4o-mini`, timeout=0.001s
- Real error: `<urlopen error timed out>` (Python urllib TimeoutError before TCP handshake)
- Retry: same model, timeout=30s — succeeded, latency 641ms, cost $0.00000375

### FM3 — Over-limit max_tokens
- Model: `gpt-4o-mini`, max_tokens=999999
- Real response: HTTP 400, body: `{"error": {"message": "max_tokens is too large: 999999. This model supports at most 16384 completion tokens, whereas you provided 999999.", "type": "invalid_request_error", "param": "max_tokens", "code": "invalid_value"}}`
- Fallback: max_tokens=64 — succeeded, cost $0.00000375

### FM4 — Cost-budget guard
- Budget: $0.000015
- 4 tasks submitted (b1–b4) against `[gpt-4o-mini, gpt-4.1]`
- b1: gpt-4o-mini accepted, cost $0.00000405
- b2: gpt-4o-mini accepted, cost $0.00000375
- b3: gpt-4o-mini accepted, cost $0.00000360; running total $0.00001140
- b4: remaining budget $0.00000360 < gpt-4o-mini cost ($0.00000375) — downgraded; remaining < gpt-4.1 cost ($0.00005000) — downgraded; refused with `no_model_fits_budget`
- Guard outcome: 3 accepted, 1 refused; total spent $0.00001140 < budget $0.000015

### FM5 — Verifier escalation
- Model: `gpt-4o-mini`, prompt: "What is 17 * 23? Reply with just the number, nothing else."
- Answer: "391" (correct; gold=391)
- Escalation not triggered (cheap model was sufficient)
- Verifier logic unit-tested against `verify_numeric` function (pure Python regex)

## Test suite
- 9 behavioral tests in `source/test_l5.py`
- All 9 pass with live credentials (see `source/green-output.txt`)
- 5 fail without credentials with `ProviderError: Missing env var OPENAI_API_KEY` (see `source/red-output.txt`)

## Key-safety check
- The `test_observability_log_schema` test imports `run_l5`, triggers a log entry, and asserts
  that no `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `XAI_API_KEY` value appears in any log line.
  The test passed live on 2026-06-21 — confirmed key-safe.

## Cost of live runs
All failure-mode calls are tiny (≤128 tokens). Total cost of this POC across all live runs:
approximately $0.00003 (less than a cent). Provider: OpenAI only.
