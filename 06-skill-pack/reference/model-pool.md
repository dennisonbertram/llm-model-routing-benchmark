# Reference: Model Pool

Live verified (L0; spec; 2026-06-21). The live-verified model pool used throughout this
degree, with pricing, provider notes, and per-provider gotchas.

Back to [index](../index.md).

---

## Pool configuration (from harness/config.py)

Live verified. These constants are the canonical model pool for this degree.

```python
CHEAP_DEFAULT  = "gpt-4o-mini"       # baseline cheap
STRONG_DEFAULT = "gpt-4.1"           # baseline strong
MID_DEFAULT    = "gpt-4o"            # mid-tier (used as MoA aggregator)
JUDGE_MODEL    = "gpt-4.1"           # LLM judge for open-ended grading
EMBED_MODEL    = "text-embedding-3-small"  # 1536-d; used for all routing embeddings
ENSEMBLE_CHEAP = [
    "gpt-4o-mini",
    "gpt-4.1-mini",
    "claude-haiku-4-5-20251001",
]
```

---

## Verified live models

Live verified (L0; 2026-06-21). These models responded to real API calls with measured
tokens, latency, and cost.

| Model | Provider | Role | Live smoke |
|-------|----------|------|------------|
| gpt-4o-mini | OpenAI | cheap | L0 baseline: acc=0.844, $0.00166/45 tasks |
| gpt-4.1 | OpenAI | strong | L0 baseline: acc=0.978, $0.02148/45 tasks |
| gpt-4o | OpenAI | mid / aggregator | Used in MoA (X1) |
| gpt-4.1-mini | OpenAI | cheap ensemble | Used in MoA (X1) |
| gpt-4.1-nano | OpenAI | cheap | Solves all 18 coding tasks — coding saturates it |
| gpt-5-mini | OpenAI | reasoning | Smoke tested; REASONING_FLOOR=2048 required |
| text-embedding-3-small | OpenAI | embeddings | $3e-05 for 45 prompts (1536-d) |
| claude-haiku-4-5-20251001 | Anthropic | cheap ensemble | Used in MoA (X1) |
| grok-4.3 | xAI | chat | Live in L0 smoke; see gotchas below |

---

## Pricing (from harness/pricing.py; reconciled 2026-06-21)

Research supported (official provider pricing pages). Use `harness/pricing.py` for current values.

| Model | Input ($/1M tokens) | Output ($/1M tokens) |
|-------|--------------------|-----------------------|
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4.1 | $2.00 | $8.00 |
| gpt-4o | $2.50 | $10.00 |
| gpt-4.1-mini | $0.40 | $1.60 |
| gpt-4.1-nano | $0.10 | $0.40 |
| text-embedding-3-small | $0.02/1M tokens | — |

Note: Provider pricing changes. Always check the official pricing page and update
`harness/pricing.py` before running a new benchmark.

---

## Provider wire-format differences

Live verified (L0; spec).

### OpenAI (gpt-4o-mini, gpt-4.1, gpt-4o, etc.)

```
POST https://api.openai.com/v1/chat/completions
Authorization: Bearer $OPENAI_API_KEY
```

- Standard models: `max_tokens` param; `temperature` supported.
- Reasoning models (gpt-5, o-series): use `max_completion_tokens` (not `max_tokens`);
  reject custom `temperature`. Apply `REASONING_FLOOR=2048`.
- Cost: NOT returned in response. Compute `Σ tokens × unit_price` from `harness/pricing.py`.

### Anthropic (claude-haiku-4-5-20251001, etc.)

```
POST https://api.anthropic.com/v1/messages
x-api-key: $ANTHROPIC_API_KEY
anthropic-version: 2023-06-01
```

- Requires `max_tokens` in every request.
- Content is in `content[0].text` (not `choices[0].message.content`).
- Cost: NOT returned. Compute from token counts + price table.

### xAI (grok-4.3)

```
POST https://api.x.ai/v1/chat/completions   (OpenAI-compatible endpoint)
Authorization: Bearer $XAI_API_KEY
```

- `grok-4.3` always spends reasoning tokens by default.
- `completion_tokens` in the response HIDES reasoning tokens, but they ARE billed.
- True billed cost: bill on `total_tokens - prompt_tokens` (not just `completion_tokens`).
- Provider returns `cost_in_usd_ticks`; ticks → USD = `ticks / 1e10`. Even this diverges
  ~1.5x from token × price due to cached tokens. Trust the provider's native field.
- REASONING_FLOOR=2048 applies here too.

---

## Per-model gotchas

Live verified (L0; 2026-06-21).

| Model | Gotcha |
|-------|--------|
| gpt-5-mini, o-series | Empty content with HTTP 200 under small token budget (hidden reasoning). Use REASONING_FLOOR=2048. Gotcha: [`../05-distillation/gotchas/G-001-reasoning-model-empty-content-small-budget.md`](../05-distillation/gotchas/G-001-reasoning-model-empty-content-small-budget.md) |
| gpt-5, o-series | `temperature` param rejected (HTTP 400). Use `max_completion_tokens`. |
| grok-4.3 | Reasoning tokens hidden from `completion_tokens` but billed. Ticks → USD is `/1e10`. Diverges ~1.5x from token × price. |
| gpt-4.1-nano | Solves ALL 18 coding tasks — canonical coding problems are memorized and not routing-discriminative. |
| gpt-4o-mini | Overconfident on hard math: returns confidence=0.9 for wrong answers. Self-confidence gating fails. (L3a) |

---

## What cheap-model accuracy is NOT monotonic means

Live verified (L0). gpt-4o-mini sometimes fails items that gpt-4.1-nano solves.
A router cannot assume "cheaper model = strictly worse per item." Build the labelset
empirically for your specific cheap+strong pair, not by assumption.
