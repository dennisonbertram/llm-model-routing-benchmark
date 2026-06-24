# G-003: grok-4.x hides reasoning tokens, bills them, and uses a 1/1e10 ticks-to-USD scale

**Category**: gotcha
**Severity**: high
**Evidence tier**: Live verified
**Source POC**: L0-smoke-and-harness

## What

Live verified on `grok-4.3` (xAI API). Three separate traps:

1. **Hidden reasoning tokens**: `completion_tokens` reported as 1 when `total_tokens` was 232. The reasoning trace (231 tokens) is consumed and billed but not counted in `completion_tokens`. A harness computing cost as `completion_tokens × out_price` severely underestimates spend.

2. **Correct billing formula**: Use `(total_tokens − prompt_tokens)` as billed completion tokens, not the raw `completion_tokens` field.

3. **Ticks-to-USD scale is 1/1e10, not 1/1e9**: xAI returns `cost_in_usd_ticks` in the usage object. The conversion is `ticks / 1e10 = USD`. An initial assumption of `1e9` produced costs 10× too high. Even the corrected formula diverges ~1.5× from uniform `tokens × price` due to cached-token discounts — trust the provider's native field for grok's true spend.

## Why it matters

Cost-accuracy ledgers that mix grok with OpenAI models and use a uniform `tokens × price` formula will undercount grok's true cost by 10× or more. A Pareto frontier built on wrong cost numbers will make grok appear cheaper than it is and may route too aggressively to it.

## Root cause

xAI's reasoning model (`grok-4.3`) spends reasoning tokens by default (it reasons before every response). The `completion_tokens` field reports only the visible output tokens, excluding the reasoning trace. This is different from OpenAI's o-series, which surfaces `completion_tokens_details.reasoning_tokens`. xAI uses a separate `cost_in_usd_ticks` field in the usage object with a 1/1e10 scale.

## Fix

In the pricing module, add a grok-specific cost extraction path:

```python
def extract_cost(model: str, usage: dict) -> float:
    if model.startswith("grok"):
        # Use provider-native ticks if available; fall back to billed tokens
        ticks = usage.get("cost_in_usd_ticks")
        if ticks is not None:
            return ticks / 1e10
        # Fallback: bill (total - prompt) at out_price rate
        billed_ct = usage["total_tokens"] - usage["prompt_tokens"]
        return usd_for(model, usage["prompt_tokens"], billed_ct)
    # Standard path for OpenAI / Anthropic
    return usd_for(model, usage["prompt_tokens"], usage["completion_tokens"])
```

Always record both the `native_cost_usd` (from ticks) and the uniform formula cost in evidence files so comparisons are reproducible.

## Regression note

Add a unit test that computes cost for a synthetic grok usage object with `cost_in_usd_ticks=1000000` and asserts the result is `0.0001` USD (not `0.001`). Fires if the scale constant is changed.

## Evidence

- Source: `03-pocs/L0-smoke-and-harness/surprises.md`, item 5: "A trivial call reported `completion_tokens=1` with `total_tokens=232`. Uniform `tokens × price` undercounts unless you bill `total − prompt`; even then it diverges ~1.5× from xAI's native `cost_in_usd_ticks / 1e10`. We compute cost uniformly for cross-model fairness but record grok's native ticks for transparency. (The ticks scale is `1e10` per USD per xAI's cost-tracking docs — NOT `1e9`, which we initially assumed and corrected.)" (Live verified)
- Source: results-digest.md, Gotchas item 3: "grok-4.x hides reasoning tokens from `completion_tokens` but bills them (bill total−prompt); ticks→USD is `/1e10` (NOT 1e9); native cost still diverges ~1.5× from token×price (cached tokens) — trust the provider field for grok." (Live verified)
- Source: model-routing-spec.md, Wire-format notes: "xAI returns `cost_in_usd_ticks` (ticks → USD; verify the conversion live and record it)." (Live verified)
