# G-001: Reasoning models return empty content under a small token budget

**Category**: gotcha
**Severity**: critical
**Evidence tier**: Live verified
**Source POC**: L0-smoke-and-harness

## What

Live verified. `gpt-5-mini` (and o-series reasoning models generally) returned `''` (empty string) when called with `max_completion_tokens=16`. The reasoning budget consumed all available tokens before any visible content was written. The chat response was HTTP 200 with an empty text field — not an error.

## Why it matters

A router that probes a reasoning model with a tight `max_tokens` to save cost will receive a blank answer and misclassify the item as a model failure. The real cause is budget starvation. This is the number-one "why is my gpt-5 call blank" gotcha.

## Root cause

Reasoning models spend tokens internally on a chain-of-thought trace before emitting visible content. Under OpenAI's API, the `max_completion_tokens` cap is shared between reasoning tokens and output tokens. If the budget is smaller than the reasoning trace, the visible content slot is zero — the model silently omits the answer.

## Fix

Set a `REASONING_FLOOR` of at least 2048 tokens for any call to a reasoning model (gpt-5, o-series, gpt-5-mini, or any model ID containing "o1", "o3", "o4", "gpt-5"). The harness enforces this as:

```python
REASONING_FLOOR = 2048

def _safe_max_tokens(model: str, requested: int) -> int:
    if is_reasoning_model(model):
        return max(requested, REASONING_FLOOR)
    return requested
```

Never use `max_tokens` / `max_completion_tokens` < 512 with a reasoning model. For routing benchmarks that probe many models, distinguish reasoning vs. completion models and apply the floor before each call.

## Regression note

Add a smoke test: call the reasoning model with a token budget well below `REASONING_FLOOR` and assert that the harness's safety floor raised it. Assert `len(response.text) > 0`. This fires if the floor is ever removed.

## Evidence

- Source: `03-pocs/L0-smoke-and-harness/surprises.md`, item 4: "Reasoning models return empty content under a tight budget. `gpt-5-mini` with `max_completion_tokens=16` returned `''` (the budget was consumed by hidden reasoning). Fixed with `REASONING_FLOOR=2048` in the harness." (Live verified)
- Source: results-digest.md, Gotchas item 1: "Reasoning models (gpt-5/o-series, grok-4.x) return EMPTY text under a small token budget — floor it (REASONING_FLOOR=2048)." (Live verified)
