# DR-001: Why Uniform token×price Cost Accounting

**Date**: 2026-06-21
**Status**: Accepted
**Evidence tier**: Live verified (L0; X5; capstone)

---

## Decision

Use `cost = Σ tokens × unit_price` from a reconciled price table (`pricing.py`) as the
uniform cost accounting method for all models and all POCs in this degree. Do not mix
provider-native USD fields with token×price in the same benchmark column.

---

## Context

OpenAI and Anthropic do not return USD in their API responses. Cost must be computed
client-side. xAI returns `cost_in_usd_ticks` in the usage object. Options considered:

1. **Uniform token×price** — compute cost from token counts and a price table reconciled
   from official pricing pages (with date and URL).
2. **Provider-native cost** — use whatever the provider returns; fall back to token×price
   for providers that don't return cost.
3. **Hybrid** — use native cost where available, token×price otherwise.

---

## Rationale

**Reproducibility.** Token×price from a versioned price table produces the same numbers
on any machine at any time given the same token counts. Provider-native cost fields can
change (e.g., due to prompt caching discounts, dynamic pricing, or API changes) without
any code change, making benchmark results non-reproducible.

**Comparability.** All rows in a Pareto table use the same accounting method. A table
that mixes methods (e.g., OpenAI via token×price, grok via native ticks) would have an
inconsistent cost axis — comparing a cached grok call to an uncached OpenAI call would
appear to favor grok by ~1.5× due to caching discounts.

**Transparency.** The price table is a committed file with a reconciliation date and
source URL. Any cost number in the degree can be re-derived from token counts + pricing.py.

**Simplicity.** One code path handles all providers. The per-provider exceptions (grok
reasoning token undercount, o-series billing mechanics) are documented in `pricing.py`
and `providers.py` as annotations, not as branching logic in the cost calculation.

---

## Consequences and accepted tradeoffs

- **Known divergence for grok-4.3**: native `cost_in_usd_ticks / 1e10` diverges ~1.5×
  from token×price for cached sessions. The harness preserves `native_cost_usd` in the
  response object for transparency, but the benchmark uses token×price. This is documented.
- **No caching discounts**: OpenAI's automatic prompt caching gives up to 50% discount
  on cached prompt tokens. Uniform token×price ignores this. On short prompts, the
  difference is negligible; on multi-turn conversations with long system prompts, the
  actual cost will be lower than the benchmark shows.
- **Price table staleness**: pricing.py was reconciled 2026-06-21. Model prices change.
  Any stakeholder reproducing this benchmark after a pricing change should update pricing.py
  before quoting numbers. The file header records the date and source URL.

---

## Evidence

- L0 README.md: "Cost = uniform tokens×price (pricing.py, reconciled)." (Live verified)
- results-digest.md: "Cost = uniform tokens×price (pricing.py, reconciled)." (Live verified)
- results-digest.md, Gotcha 3: "grok-4.x hides reasoning tokens... native cost still diverges ~1.5× from token×price (cached tokens) — trust the provider field for grok." (Live verified)
- X5 results table: all costs use uniform token×price; oracle, baselines, and all routers share the same accounting. (Live verified)
