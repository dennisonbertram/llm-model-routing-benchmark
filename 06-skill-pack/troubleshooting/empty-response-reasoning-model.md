# Troubleshooting: Empty Response from Reasoning Model

Live verified (L0; 2026-06-21). gpt-5 / o-series / grok-4.x returns HTTP 200 with
blank content under a small token budget.

Back to [index](../index.md). See also: [`../05-distillation/gotchas/G-001-reasoning-model-empty-content-small-budget.md`](../05-distillation/gotchas/G-001-reasoning-model-empty-content-small-budget.md)

---

## Symptom

- HTTP 200 response with `choices[0].message.content = ""` or `None`.
- No error, no exception — just blank text.
- Only occurs with reasoning models (gpt-5, gpt-5-mini, o1, o3, o4, grok-4.x).

---

## Root cause

Live verified (L0). Reasoning models spend tokens internally on a chain-of-thought trace
before writing visible content. The `max_completion_tokens` cap is SHARED between reasoning
tokens and output tokens. If the budget is smaller than the reasoning trace, the visible
content slot is zero.

Concrete example from L0: `gpt-5-mini` with `max_completion_tokens=16` returned `''`.
The 16-token budget was consumed entirely by hidden reasoning; no visible content was written.

---

## Fix

Apply `REASONING_FLOOR=2048` for any call to a reasoning model:

```python
REASONING_FLOOR = 2048

def safe_max_tokens(model: str, requested: int) -> int:
    reasoning_ids = ("o1", "o3", "o4", "gpt-5", "grok")
    if any(s in model for s in reasoning_ids):
        return max(requested, REASONING_FLOOR)
    return requested
```

Use `max_completion_tokens` (not `max_tokens`) for gpt-5 / o-series:

```python
if is_reasoning_model(model):
    payload["max_completion_tokens"] = safe_max_tokens(model, requested)
    # Do NOT pass temperature — these models reject it
else:
    payload["max_tokens"] = requested
    payload["temperature"] = temperature
```

---

## Additional grok-4.x wrinkle

Live verified (L0). grok-4.3 hides reasoning tokens from `completion_tokens` but bills them.
- `completion_tokens` in the response is only the visible output, not reasoning.
- The provider returns `cost_in_usd_ticks`; ticks → USD = `ticks / 1e10`.
- Even this diverges ~1.5x from `token × price` due to cached tokens.
- Trust the provider's native cost field for grok. See [reference/model-pool.md](../reference/model-pool.md).

---

## Regression test

```python
def test_reasoning_floor_applied():
    """Confirm the harness floor raises small budgets for reasoning models."""
    from config import REASONING_FLOOR
    assert safe_max_tokens("gpt-5-mini", 16) >= REASONING_FLOOR
    assert safe_max_tokens("o4-mini", 100) >= REASONING_FLOOR
    assert safe_max_tokens("gpt-4o-mini", 16) == 16  # non-reasoning: unchanged
```

---

## Source

`03-pocs/L0-smoke-and-harness/surprises.md`, item 4.
`05-distillation/gotchas/G-001-reasoning-model-empty-content-small-budget.md`
