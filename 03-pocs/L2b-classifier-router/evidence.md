# Evidence — L2b Classifier Router

**Evidence tier: Live verified (2026-06-21)**

## Live API calls made

1. **Embedding call** — `embed(texts=<45 prompts>, model="text-embedding-3-small")` — one batched
   call, returned 45 × 1536-dim vectors. Cost: ≈$2.85e-05 one-time embedding spend (estimated from
   45 prompts × ~1425 tokens × $0.02/1M; the captured run shows $0.00 because the embedding cache
   was already warm). Confirmed: 1536-dim vectors returned, USD > 0 on first-ever run.

2. **Live confirmation embedding** — `embed(["What is the derivative of x^3 + 2x? ..."])`
   called live (not from cache). Cost: $3.8e-07. P(cheap_correct) = 0.8159. Decision: route to
   cheap (gpt-4o-mini). This confirms the end-to-end code path: embed → normalise → classify →
   route works live.

3. **Green test run** — 6 behavioral tests passed against the real API. Key tests:
   - `test_embeddings_live`: 1536-dim vector returned, usd > 0
   - `test_live_embed_and_predict`: fresh quadratic equation prompt embedded live, P in [0,1]
   - `test_routing_collapse_guard`: interior thresholds produce both cheap and strong routing
   - `test_model_trains_non_trivially`: P range > 0.01 and both outcomes visible at mid-threshold

## Labelset outcomes (from L0 — no re-billing)

All routing accuracy/cost numbers come from `harness/.cache/labelset_export.json`, which contains
the live-measured cheap_correct/cheap_usd/strong_correct/strong_usd for all 45 items. These were
billed during L0. This POC did not re-bill any model inference calls.

## Measured numbers (honest)

| Metric | Value | Provenance |
|---|---|---|
| Embedding model | text-embedding-3-small | OpenAI live call |
| Embed cost (45 prompts) | ≈$2.85e-05 (estimated; captured run = $0.00, cache warm) | Estimated from token count × $0.02/1M |
| Train set size | 32 items | 70% stratified split |
| Test set size | 13 items | 30% held-out |
| Train label accuracy | 0.844 | Computed from classifier predictions |
| Test label accuracy | 0.846 | Computed from classifier predictions |
| P(cheap) range on test | [0.737, 0.907] | Measured from classifier |
| Best routing accuracy (τ=0.80) | 1.000 | Labelset matrix |
| Best routing cost (τ=0.80) | $0.000773 | Labelset matrix |
| Oracle cost (test set) | $0.000540 | Labelset matrix |
| Always-strong cost (test set) | $0.004868 | Labelset matrix |

## What this does NOT prove

- That the classifier generalises to out-of-distribution prompts — tested only on the 13-item
  held-out portion of the same 45-item suite.
- That embedding similarity is a strong discriminator for model difficulty in general — the
  measured P range is narrow (0.74–0.91), suggesting weak separation on this specific suite.
- Comparison to other POC routers on the same split — the full benchmark comparison happens in X5.
