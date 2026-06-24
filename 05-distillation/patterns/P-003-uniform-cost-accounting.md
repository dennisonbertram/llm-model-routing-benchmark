# P-003: Uniform Cost Accounting Across Providers

**Category**: pattern
**Evidence tier**: Live verified (POCs L0, X5, capstone)
**Source POCs**: L0-smoke-and-harness, X5-router-benchmark-pareto, L-capstone-adaptive-routing-gateway

## Live verified

The measurement harness computes cost as `Σ tokens × unit_price` from a price table for all
OpenAI and Anthropic providers. This produces consistent, comparable costs across models and
providers. The benchmark results in this degree all use this method. (L0, X5)

Live-measured baseline costs (45 tasks):

| Model        | Cost (45 tasks) | Cost per task (avg) |
|--------------|-----------------|---------------------|
| gpt-4o-mini  | $0.00166        | ~$3.7e-05           |
| gpt-4.1      | $0.02148        | ~$4.8e-04           |

Cost ratio: 12.9× (L0). All router cost comparisons in the degree use this accounting
method, making cost numbers directly comparable across strategies.

## The pattern

**Use `tokens × price` uniformly.** OpenAI and Anthropic do NOT return USD cost in their
API responses. Compute cost server-side from the token counts in each response:

```python
# pricing.py — price table (USD per 1M tokens), sourced from official pricing pages
PRICES = {
    # model                input $/1M    output $/1M
    "gpt-4o-mini":         (0.15,        0.60),
    "gpt-4o":              (2.50,        10.00),
    "gpt-4.1":             (2.00,        8.00),
    "gpt-4.1-mini":        (0.40,        1.60),
    "gpt-4.1-nano":        (0.10,        0.40),
    "text-embedding-3-small": (0.02,     0.0),
    # add Anthropic models as needed
}

def usd_for(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Returns estimated USD for one call."""
    if model not in PRICES:
        raise ValueError(f"No price for model: {model}")
    inp_price, out_price = PRICES[model]
    return (prompt_tokens * inp_price + completion_tokens * out_price) / 1_000_000
```

## Provider-specific exceptions (live-discovered, L0)

**grok-4.x / xAI (live-discovered, L0 surprises):**

- grok-4.x hides reasoning tokens from `completion_tokens` but bills them
- Uniform `tokens × price` using `completion_tokens` undercounts the true cost
- Correct approach: bill `total_tokens − prompt_tokens` (billed_completion_tokens), which
  includes hidden reasoning tokens
- Even then, the result diverges ~1.5× from xAI's native `cost_in_usd_ticks` due to
  cached-token discounts in the native cost
- **Trust the provider's native cost field for grok** (`cost_in_usd_ticks / 1e10`)
- Note: ticks → USD conversion is `/1e10`, NOT `/1e9` (live-verified; off-by-10× if wrong)

**gpt-5 / o-series (live-discovered, L0):**

- Use `max_completion_tokens` not `max_tokens` for the token budget parameter
- Reject custom `temperature` — the harness must branch on model family
- Under a small token budget, return EMPTY text (budget consumed by hidden reasoning)
- Floor the budget at `REASONING_FLOOR = 2048` to avoid empty responses

**Anthropic:**

- `POST https://api.anthropic.com/v1/messages`, headers `x-api-key`,
  `anthropic-version: 2023-06-01`, requires `max_tokens`
- Content is at `content[0].text` (not `choices[0].message.content`)
- No native USD field; use `tokens × price` from the price table

## Embedding cost (live-measured, L2, X5)

text-embedding-3-small: $0.02 per 1M tokens.
Embedding 45 prompts (the full benchmark corpus): **$0.000030 total** (L2).
Embedding a single prompt at inference time: **~$6e-07** (L2b live confirmation).

Embedding cost is negligible relative to inference cost but should be tracked in the
cost ledger for full auditability.

## What the ledger should capture

Every routing decision should append to a JSONL ledger. Required fields (live format, L4):

```json
{
  "ts":                "2026-06-22T03:48:57Z",
  "decision":          "default_cheap",
  "chosen_model":      "gpt-4o-mini",
  "prompt_tokens":     14,
  "completion_tokens": 7,
  "usd":               6.3e-06,
  "latency_ms":        763
}
```

Never log the raw API key value. The ledger is the source of truth for cost audits and
budget guard enforcement.

## Why uniform accounting matters for routing comparisons

Without a consistent cost measure, Pareto comparisons are meaningless. If MoA costs were
reported using Anthropic's list price but the baseline used OpenAI's price, the cost ratios
would be wrong. The uniform `tokens × price` method applied consistently enables the
7.4× savings claim (logistic vs always-strong) to be directly comparable. (X5)

All benchmark numbers in this degree (results-digest.md) use this accounting. Reproduce
results using the same `pricing.py` price table to get matching numbers.

## Evidence

- L0-smoke-and-harness/README.md — baseline cost measurements, provider gotchas (grok, o-series)
- L0-smoke-and-harness/surprises.md — grok billing quirk, reasoning token floor
- L4-routing-gateway-runtime/README.md — ledger format, per-call USD tracking
- results-digest.md lines 8–9, gotchas 1–3 — provider-specific billing gotchas
