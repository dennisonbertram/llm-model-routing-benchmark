# Troubleshooting: grok-4.x Cost Accounting Diverges

Live verified (L0; 2026-06-21). grok-4.x hides reasoning tokens and bills differently
from uniform tokens × price.

Back to [index](../index.md).

---

## Symptom

- `usd = completion_tokens × output_price + prompt_tokens × input_price` gives a value
  that is substantially lower than what the provider actually charged.
- Live measured: cost via `completion_tokens × price` diverges ~1.5x from the native cost.

---

## Root cause

Live verified (L0). grok-4.3 always reasons by default. The reasoning tokens:
1. Are NOT included in the `completion_tokens` field of the response.
2. ARE billed by xAI as output tokens.
3. The provider returns `cost_in_usd_ticks` in the usage field.

So the true billed completion tokens = `total_tokens - prompt_tokens` (not just `completion_tokens`).

Even using `total_tokens - prompt_tokens`, cost still diverges ~1.5x from `token × price`
because xAI bills cached prompt tokens at a discounted rate that is not reflected in the
standard token counts.

---

## Fix

Trust the provider's native cost field for grok:

```python
def cost_for_grok(response: dict) -> float:
    """
    Extract cost from xAI's native field.
    Ticks → USD = ticks / 1e10 (live-verified conversion).
    """
    usage = response.get("usage", {})
    ticks = usage.get("cost_in_usd_ticks")
    if ticks is not None:
        return ticks / 1e10
    # Fallback: use total_tokens - prompt_tokens as billed completion tokens
    total = usage.get("total_tokens", 0)
    prompt = usage.get("prompt_tokens", 0)
    billed_completion = total - prompt
    # Use output price for billed_completion
    return prompt * INPUT_PRICE + billed_completion * OUTPUT_PRICE
```

In the harness, `chat()` returns `native_cost_usd` for providers that supply it.
Use `result["native_cost_usd"]` for grok, not `result["usd"]` (which is the uniform
tokens × price estimate).

---

## Live evidence

From `03-pocs/L0-smoke-and-harness/surprises.md` and `results-digest.md` Gotcha #3:

> "grok-4.x hides reasoning tokens from `completion_tokens` but bills them (bill
> total−prompt); ticks→USD is `/1e10` (NOT 1e9); native cost still diverges ~1.5×
> from token×price (cached tokens) — trust the provider field for grok."

---

## Regression note

If you add grok to a cost benchmark, add an assertion:

```python
# native_cost should be positive and within 3x of the token estimate
assert result["native_cost_usd"] > 0
token_estimate = (result["prompt_tokens"] * INPUT_PRICE +
                  result["completion_tokens"] * OUTPUT_PRICE)
assert result["native_cost_usd"] < token_estimate * 5, \
    f"native_cost {result['native_cost_usd']} seems implausible vs token estimate {token_estimate}"
```

---

## Source

`03-pocs/L0-smoke-and-harness/surprises.md`
`.context/results-digest.md` Gotcha #3
