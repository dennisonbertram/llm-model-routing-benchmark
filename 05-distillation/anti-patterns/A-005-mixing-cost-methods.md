# A-005: Mixing Cost Methods — Combining token×price, Native Provider Cost, and Estimated Cost in One Benchmark

**Category**: anti-pattern
**Severity**: high — produces non-comparable numbers across models and providers
**Evidence tier**: Live verified
**Source POC**: L0-smoke-and-harness

---

## What the anti-pattern looks like

Using `tokens × price` for some models, native `cost_in_usd` fields for others, and
estimated costs (without running real calls) for others — in the same benchmark table.
The result: apples-to-oranges cost comparisons that make one routing strategy look
cheaper or more expensive than it actually is relative to another.

---

## Root cause: providers report cost differently

**Live verified** (L0):

- **OpenAI and Anthropic**: do NOT return USD in API responses. Cost must be computed
  client-side as `cost = prompt_tokens × price_in + completion_tokens × price_out`.
- **xAI (grok-4.x)**: returns `cost_in_usd_ticks` in the usage object.
  Conversion: `usd = cost_in_usd_ticks / 1e10` (NOT `/1e9` — a factor-of-10 error).
  Additionally, `completion_tokens` hides reasoning tokens; the billed completion is
  `total_tokens - prompt_tokens`. Even with correct conversion, uniform `tokens × price`
  diverges ~1.5× from native cost for cached sessions because of reasoning token billing.
- **Reasoning models (o-series, gpt-5)**: reasoning tokens are billed as output tokens
  but do not appear in `completion_tokens` in older API versions. The model spends its
  token budget on hidden chain-of-thought before emitting visible content.

If you use different methods for different models in the same Pareto table, the cost
axis is not comparable.

---

## The fix: uniform method + explicit exception documentation

**Live verified** (L0; X5; capstone)

The harness `pricing.py` uses `cost = Σ tokens × unit_price` for all models. This
produces consistent, reproducible numbers even when individual model costs diverge from
native provider cost. The exceptions are documented explicitly:

```python
# pricing.py — uniform token×price (reconciled 2026-06-21)
# NOTE: grok-4.3 ticks-to-USD conversion is /1e10 (not /1e9)
# NOTE: grok-4.3 native cost diverges ~1.5× from tokens×price for cached sessions
#       → trust native_cost_usd for grok; tokens×price is approximate only
# NOTE: o-series reasoning tokens billed as output; apply REASONING_FLOOR=2048
```

When you must report both uniform and native costs (e.g., to show the grok divergence),
label each column explicitly: `usd (tokens×price)` vs `usd (provider-native)`. Never
mix them in the same column without labeling.

---

## A secondary trap: not caching and paying twice

Because each live API call costs real money, the harness uses an on-disk response cache
(`harness/.cache/labelset.json`, per-POC `.cache.json`). Predictive routers score against
the pre-measured outcome matrix rather than re-billing. If your benchmark re-runs live
calls for every router sweep, you will pay N × M times (N routers × M tasks) when you
should pay once (build the outcome matrix once, score all routers from it).

In this degree, the full outcome matrix (45 tasks × 2 models = 90 calls) is the
single-payment foundation. All later POCs reuse it. The only new live calls after L0 are
for embeddings, ensemble calls (X1, X2, X3), and live-confirmation samples.

---

## How to detect this anti-pattern in existing benchmarks

- Look for rows labeled "estimated," "projected," or "from pricing page" in a results table.
  These are not comparable to measured values.
- Check whether ensemble costs include the aggregator model's call. MoA, debate, and
  self-consistency all require additional calls beyond the N proposer calls.
- Verify that verifier call costs (AutoMix k=3 self-verification) are included in the
  total. X4's AutoMix at T=0.34 cost $0.006092, of which $0.003570 was verifier overhead.
  A table that counts only cheap+strong escalation calls would show $0.002522 — $0.003570
  too low.

---

## Evidence

- L0 README.md: "Cost = uniform tokens×price (pricing.py, reconciled)." (Live verified)
- results-digest.md, Gotcha 3: "grok-4.x hides reasoning tokens from `completion_tokens` but bills them (bill total−prompt); ticks→USD is `/1e10` (NOT 1e9); native cost still diverges ~1.5× from token×price (cached tokens) — trust the provider field for grok." (Live verified)
- X4 README.md: "The cost includes k=3 verifier calls per item ($0.003570 total verifier overhead)." (Live verified)
- results-digest.md, Suite description: "Cost = uniform tokens×price (pricing.py, reconciled)." (Live verified)
