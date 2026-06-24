# Pricing, Quotas, and Rate Limits

**Target**: Model Routing — 01-llm-model-routing
**Checked**: 2026-06-21 — live WebFetch of official provider docs pages (see source URLs per section)
**Evidence tier**: Research supported but not live verified (prices fetched from official docs pages; no live API calls made in this file)

> **Warning**: Model pricing changes frequently. Re-verify at the official pricing pages before
> any live POC run that depends on accurate cost numbers.

---

## Purpose for this degree

The shared harness (`harness/pricing.py`) uses the table below to compute
`usd_for(model, prompt_tokens, completion_tokens)` without making a live
price-API call on every request. OpenAI and Anthropic do NOT return a USD cost
in their chat-completion responses — the harness must calculate it from token
counts × the price table here. xAI Grok-4.3 DOES return `cost_in_usd_ticks` in
its usage object; the harness should use that directly (and cross-check against
the price table as a sanity guard).

---

## Model Price Table

All prices USD per 1 million tokens (MTok). "Cached input" is the per-MTok rate
when the provider's prompt-caching feature is active.

### OpenAI models

Source: https://developers.openai.com/api/docs/pricing (individual model pages)  
Checked: 2026-06-21

| Model | Input $/MTok | Cached input $/MTok | Output $/MTok | Context window | Status |
|---|---|---|---|---|---|
| `gpt-4.1-nano` | $0.10 | $0.025 | $0.40 | 1,047,576 | Active (snapshot 2025-04-14; OpenAI recommends gpt-5-nano for new work) |
| `gpt-4.1-mini` | $0.40 | $0.10 | $1.60 | 1,047,576 | Active (OpenAI recommends gpt-5-mini for new work) |
| `gpt-4o-mini` | $0.15 | $0.075 | $0.60 | 128,000 | Active (snapshot 2024-07-18) |
| `gpt-4o` | $2.50 | $1.25 | $10.00 | 128,000 | Active (snapshot 2024-11-20, listed as "current default") |
| `gpt-4.1` | $2.00 | $0.50 | $8.00 | 1,047,576 | Active (snapshot 2025-04-14, "smartest non-reasoning model") |
| `gpt-5-mini` | $0.25 | $0.025 | $2.00 | 400,000 | Active (OpenAI recommends gpt-5.4-mini for most new workloads) |
| `gpt-5` | $1.25 | $0.125 | $10.00 | 400,000 | Active (OpenAI describes it as "previous model" vs gpt-5.5) |
| `text-embedding-3-small` | $0.02 | — | — | — | Active (embeddings model; no output tokens, no cached pricing) |

**Notes:**
- As of 2026-06-21, OpenAI's current frontier line is `gpt-5.4` / `gpt-5.5`. The `gpt-4.1-*` and `gpt-5` / `gpt-5-mini` families are still available and priced but OpenAI's docs recommend newer models for most new production workloads. The spec-listed models were live-verified accessible from this workspace.
- `gpt-5` and `gpt-5-mini` (o-series reasoning family) require `max_completion_tokens` instead of `max_tokens` and do not accept custom `temperature`. The harness must branch on model family — see spec wire-format notes.
- `text-embedding-3-small` is billed only on input tokens (the text to embed); there is no output-token charge.
- Batch API: all OpenAI models listed above qualify for a 50% discount on both input and output tokens via the Batch API.
- Cached input: OpenAI prompt caching is implicit/automatic (no `cache_control` header needed) for prompts ≥ 1,024 tokens. Cache write fees are folded into the standard input price.

**Sources (individual model pages, all checked 2026-06-21):**
- gpt-4.1-nano: https://developers.openai.com/api/docs/models/gpt-4.1-nano
- gpt-4.1-mini: https://developers.openai.com/api/docs/models/gpt-4.1-mini
- gpt-4o-mini: https://developers.openai.com/api/docs/models/gpt-4o-mini
- gpt-4o: https://developers.openai.com/api/docs/models/gpt-4o
- gpt-4.1: https://developers.openai.com/api/docs/models/gpt-4.1
- gpt-5-mini: https://developers.openai.com/api/docs/models/gpt-5-mini
- gpt-5: https://developers.openai.com/api/docs/models/gpt-5
- text-embedding-3-small: https://developers.openai.com/api/docs/models/text-embedding-3-small

---

### Anthropic models

Source: https://platform.claude.com/docs/en/about-claude/pricing  
Checked: 2026-06-21

| Model | API ID | Input $/MTok | Cached input $/MTok (hit) | Output $/MTok | Context window |
|---|---|---|---|---|---|
| `claude-haiku-4-5` | `claude-haiku-4-5-20251001` | $1.00 | $0.10 | $5.00 | 200k tokens |
| `claude-sonnet-4-5` | `claude-sonnet-4-5-20250929` | $3.00 | $0.30 | $15.00 | 200k tokens |
| `claude-opus-4-8` (latest opus-4.x) | `claude-opus-4-8` | $5.00 | $0.50 | $25.00 | 1M tokens |

**Notes:**
- All three models are currently active (not deprecated/retired).
- Anthropic prompt caching requires explicit `cache_control` breakpoints in the request. Cache write fees: **5-minute cache** = 1.25× base input price; **1-hour cache** = 2.0× base input price. Cache read (hit) = 0.10× base input price (shown above).
- Batch API: 50% discount on both input and output for all three models.
- `claude-haiku-4-5` alias resolves to the dated snapshot `20251001`. `claude-sonnet-4-5` alias resolves to `20250929`. `claude-opus-4-8` uses a dateless format that is also a pinned snapshot (introduced with the 4.6 generation).
- The spec also mentions `claude-sonnet-4-6` ($3.00/$15.00 same tier as Sonnet 4.5) and `claude-opus-4-8` — both confirmed at the same price tier as their family equivalents above.
- Note: Opus 4.7 and later use a new tokenizer that may consume up to ~35% more tokens for the same text compared to earlier models — factor this into cost estimates.

**Source**: https://platform.claude.com/docs/en/about-claude/pricing (checked 2026-06-21)  
**Models reference**: https://platform.claude.com/docs/en/docs/about-claude/models (checked 2026-06-21)

---

### xAI model

Source: https://docs.x.ai/developers/models/grok-4.3 and https://docs.x.ai/developers/cost-tracking  
Checked: 2026-06-21

| Model | Input $/MTok | Cached input $/MTok | Output $/MTok | Context window |
|---|---|---|---|---|
| `grok-4.3` | $1.25 | $0.20 | $2.50 | 1,000,000 tokens |

**Notes:**
- xAI's API is OpenAI-compatible (base URL `https://api.x.ai/v1`).
- `grok-4.3` always spends reasoning tokens; reasoning tokens are billed as output tokens at the standard $2.50/MTok output rate.

**`cost_in_usd_ticks` — conversion and use:**

Unlike OpenAI and Anthropic, the xAI API returns the exact cost for every
inference call in a `cost_in_usd_ticks` field in the usage object.

```
Conversion: cost_usd = cost_in_usd_ticks / 10_000_000_000
```

That is: **1 USD = 10,000,000,000 ticks (10^10)**; 1 tick = 0.0000000001 USD
(0.1 nanodollars). This avoids floating-point rounding errors when accumulating
costs over many requests.

Example from the official docs:
```
cost_in_usd_ticks: 37_756_000  →  $0.0038
cost_in_usd_ticks: 200_000_000 →  $0.02
```

The harness should use `cost_in_usd_ticks / 1e10` directly for xAI calls rather
than computing from the token price table, and use the price table only as a
sanity-check bound.

**Sources:**
- Model card: https://docs.x.ai/developers/models/grok-4.3
- Cost tracking: https://docs.x.ai/developers/cost-tracking

---

## Rate Limits

### OpenAI — Tiered RPM / TPM

OpenAI rate limits are per API key and scale across 5 tiers based on cumulative
spend. The table below shows Tier 1 (new accounts) and Tier 5 (high-volume)
for the spec-listed models. Source: individual model pages at
https://developers.openai.com/api/docs/models/ (checked 2026-06-21).

| Model | Tier 1 RPM | Tier 1 TPM | Tier 5 RPM | Tier 5 TPM |
|---|---|---|---|---|
| `gpt-4.1-nano` | 500 | 200,000 | — | 150,000,000 |
| `gpt-4.1-mini` | 500 | 200,000 | — | — |
| `gpt-4o-mini` | 500 | 200,000 | — | — |
| `gpt-4o` | 500 | 30,000 | 10,000 | 30,000,000 |
| `gpt-4.1` | 500 | 30,000 | 10,000 | 30,000,000 |
| `gpt-5-mini` | 500 | 500,000 | 30,000 | 180,000,000 |
| `gpt-5` | 500 | 500,000 | 15,000 | 40,000,000 |
| `text-embedding-3-small` | 500 | 1,000,000 | — | — |

Tier advancement is automatic based on cumulative spend (Tier 1 → 2 at $5,
→ 3 at $50, → 4 at $250, → 5 at $1,000 cumulative spend). There is no free
quota for the API; a credit purchase is required.

**429 handling**: HTTP 429 means rate limit exceeded. The `retry-after` header
gives the seconds to wait. Do NOT differentiate from credit exhaustion via
status code alone — check the error body's `code` field.

---

### Anthropic — Tiered RPM / ITPM / OTPM

Anthropic limits are per organization, measured in RPM + input tokens per minute
(ITPM) + output tokens per minute (OTPM). Cache-read tokens do NOT count toward
ITPM for current Claude 4.x models (only uncached input and cache-write tokens
count), making prompt caching an effective throughput multiplier.

Source: https://platform.claude.com/docs/en/api/rate-limits (checked 2026-06-21)

**Tier 1** (requires $5 credit purchase; $500/month spend limit):

| Model class | RPM | ITPM | OTPM |
|---|---|---|---|
| Claude Opus 4.x (combined: 4.8, 4.7, 4.6, 4.5) | 50 | 500,000 | 80,000 |
| Claude Sonnet 4.x (combined: 4.6, 4.5) | 50 | 30,000 | 8,000 |
| Claude Haiku 4.5 | 50 | 50,000 | 10,000 |

**Tier 4** (requires $400 credit purchase; $200,000/month spend limit):

| Model class | RPM | ITPM | OTPM |
|---|---|---|---|
| Claude Opus 4.x | 4,000 | 10,000,000 | 800,000 |
| Claude Sonnet 4.x | 4,000 | 2,000,000 | 400,000 |
| Claude Haiku 4.5 | 4,000 | 4,000,000 | 800,000 |

Tier advancement is automatic. Tiers 1–4 are self-serve; above Tier 4 requires
contacting sales.

**Priority Tier** (separate service tier): available for committed-spend
customers; separate RPM/ITPM/OTPM pool, surfaced via
`anthropic-priority-*` response headers.

**Free quota**: New accounts receive a small free credit balance for testing.
No sustained free tier.

---

### xAI — Tiered RPM / TPM for grok-4.3

Source: https://docs.x.ai/developers/rate-limits (checked 2026-06-21)

| Tier | Spend threshold | RPM | TPM |
|---|---|---|---|
| Tier 0 (default) | — | 1,800 | 10,000,000 |
| Tier 1 | $50 cumulative | 2,400 | 15,000,000 |
| Tier 2 | $250 cumulative | 3,600 | 25,000,000 |
| Tier 3 | $1,000 cumulative | 6,000 | 45,000,000 |
| Tier 4 | $5,000 cumulative | 10,000 | 85,000,000 |

No per-day request limit is documented. No free trial quota is documented;
Tier 0 is the default for all accounts.

---

## Cost Formula Summary for `harness/pricing.py`

```python
# USD per 1M tokens, indexed by model id
# Source: official pricing pages, checked 2026-06-21
PRICES = {
    # OpenAI
    "gpt-4.1-nano":            {"in": 0.10,  "out": 0.40,  "cached_in": 0.025},
    "gpt-4.1-mini":            {"in": 0.40,  "out": 1.60,  "cached_in": 0.10},
    "gpt-4o-mini":             {"in": 0.15,  "out": 0.60,  "cached_in": 0.075},
    "gpt-4o":                  {"in": 2.50,  "out": 10.00, "cached_in": 1.25},
    "gpt-4.1":                 {"in": 2.00,  "out": 8.00,  "cached_in": 0.50},
    "gpt-5-mini":              {"in": 0.25,  "out": 2.00,  "cached_in": 0.025},
    "gpt-5":                   {"in": 1.25,  "out": 10.00, "cached_in": 0.125},
    "text-embedding-3-small":  {"in": 0.02,  "out": 0.00,  "cached_in": None},
    # Anthropic
    "claude-haiku-4-5":        {"in": 1.00,  "out": 5.00,  "cached_in": 0.10},
    "claude-haiku-4-5-20251001": {"in": 1.00, "out": 5.00, "cached_in": 0.10},
    "claude-sonnet-4-5":       {"in": 3.00,  "out": 15.00, "cached_in": 0.30},
    "claude-sonnet-4-5-20250929": {"in": 3.00, "out": 15.00, "cached_in": 0.30},
    "claude-opus-4-8":         {"in": 5.00,  "out": 25.00, "cached_in": 0.50},
    # xAI  (also use cost_in_usd_ticks / 1e10 from API response directly)
    "grok-4.3":                {"in": 1.25,  "out": 2.50,  "cached_in": 0.20},
}

def usd_for(model: str, prompt_tokens: int, completion_tokens: int,
            cached_tokens: int = 0) -> float:
    """Return estimated USD cost. Prices are per 1M tokens."""
    p = PRICES[model]
    uncached = prompt_tokens - cached_tokens
    cost = (uncached * p["in"] + completion_tokens * p["out"]) / 1_000_000
    if cached_tokens and p["cached_in"] is not None:
        cost += cached_tokens * p["cached_in"] / 1_000_000
    return cost
```

For xAI calls, prefer the API-returned value:

```python
# xAI returns cost_in_usd_ticks in usage; convert directly
usd = raw_response["usage"]["cost_in_usd_ticks"] / 10_000_000_000
```

---

## Budget guidance for this degree's POC runs

All POC runs use small task suites (≤ ~20 items each). Estimated per-run cost:

| POC | Typical model mix | Estimated cost |
|---|---|---|
| L0 smoke + baseline | cheap + strong over 3 suites | $0.05 – $0.20 |
| L1 heuristic router | cheap + strong on 36 items | $0.05 – $0.15 |
| L2 kNN / classifier | embed 36 items + routing runs | < $0.10 (embeddings cheap) |
| L3a cascade | cheap → mid → strong per item | $0.10 – $0.30 |
| L3b coding harness | multi-step coding agent on 12 items | $0.20 – $0.50 |
| X1 MoA | N×cheap + 1×strong | $0.20 – $0.60 |
| X5 Pareto benchmark | all routers over full suite | $1.00 – $3.00 |
| L-capstone | combined gateway, full suite | $0.50 – $2.00 |

Add `max_price` guards (OpenAI: `max_tokens` limits; per-run total budget checks
in the harness) on all automated runs to prevent runaway cost.

---

## Sources

| Resource | URL | Checked |
|---|---|---|
| OpenAI pricing index | https://developers.openai.com/api/docs/pricing | 2026-06-21 |
| OpenAI gpt-4.1-nano | https://developers.openai.com/api/docs/models/gpt-4.1-nano | 2026-06-21 |
| OpenAI gpt-4.1-mini | https://developers.openai.com/api/docs/models/gpt-4.1-mini | 2026-06-21 |
| OpenAI gpt-4o-mini | https://developers.openai.com/api/docs/models/gpt-4o-mini | 2026-06-21 |
| OpenAI gpt-4o | https://developers.openai.com/api/docs/models/gpt-4o | 2026-06-21 |
| OpenAI gpt-4.1 | https://developers.openai.com/api/docs/models/gpt-4.1 | 2026-06-21 |
| OpenAI gpt-5-mini | https://developers.openai.com/api/docs/models/gpt-5-mini | 2026-06-21 |
| OpenAI gpt-5 | https://developers.openai.com/api/docs/models/gpt-5 | 2026-06-21 |
| OpenAI text-embedding-3-small | https://developers.openai.com/api/docs/models/text-embedding-3-small | 2026-06-21 |
| Anthropic model pricing | https://platform.claude.com/docs/en/about-claude/pricing | 2026-06-21 |
| Anthropic models overview | https://platform.claude.com/docs/en/docs/about-claude/models | 2026-06-21 |
| Anthropic rate limits | https://platform.claude.com/docs/en/api/rate-limits | 2026-06-21 |
| xAI grok-4.3 model card | https://docs.x.ai/developers/models/grok-4.3 | 2026-06-21 |
| xAI cost tracking | https://docs.x.ai/developers/cost-tracking | 2026-06-21 |
| xAI rate limits | https://docs.x.ai/developers/rate-limits | 2026-06-21 |
