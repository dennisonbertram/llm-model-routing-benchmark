# G-002: gpt-5/o-series require `max_completion_tokens` and reject custom `temperature`

**Category**: gotcha
**Severity**: critical
**Evidence tier**: Live verified
**Source POC**: L0-smoke-and-harness

## What

Live verified. OpenAI's reasoning model family (gpt-5, gpt-5-mini, o1, o3, o4-mini, and any future o-series) uses a different wire format from the standard chat completions API:

1. The token-budget parameter is `max_completion_tokens`, not `max_tokens`.
2. Passing a custom `temperature` returns an HTTP 400 error: "temperature is not supported for this model."

A harness that uses the same parameter set for all models will fail on the first reasoning model it encounters.

## Why it matters

Router harnesses that probe multiple model families in the same suite will silently break when they add a reasoning model. The `max_tokens` parameter is silently ignored (or raises a 400) and a `temperature=0.0` call is rejected outright.

## Root cause

Reasoning models control determinism via internal sampling, not the `temperature` parameter. The API surface intentionally omits `temperature` to prevent callers from interfering with the reasoning process. The token budget uses `max_completion_tokens` so it's explicit that it covers both reasoning and output tokens.

## Fix

Branch on model family when building the API payload. In the shared harness:

```python
def _build_payload(model: str, messages: list, max_tokens: int, temperature: float) -> dict:
    if is_reasoning_model(model):
        return {
            "model": model,
            "messages": messages,
            "max_completion_tokens": max(max_tokens, REASONING_FLOOR),
            # temperature intentionally omitted
        }
    return {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
```

`is_reasoning_model(model)` should match on any model ID containing "gpt-5", "o1", "o3", "o4", or "o-preview". Maintain this list as OpenAI adds new reasoning variants.

## Regression note

Keep a unit test that verifies `_build_payload("gpt-5-mini", ...)` omits `temperature` and uses `max_completion_tokens`, while `_build_payload("gpt-4o-mini", ...)` includes both. Run on every harness change.

## Evidence

- Source: `03-pocs/L0-smoke-and-harness/` harness `providers.py` provider branching on model family (Live verified)
- Source: results-digest.md, Gotchas item 2: "gpt-5/o-series use `max_completion_tokens` + reject custom `temperature`." (Live verified)
- Source: model-routing-spec.md, Wire-format notes: "gpt-5 / o-series use `max_completion_tokens` (not `max_tokens`) and reject custom `temperature` — the harness must branch on model family." (Live verified)
