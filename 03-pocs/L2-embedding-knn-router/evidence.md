# Evidence — L2 Embedding k-NN Router

**Evidence tier: Live verified (2026-06-21)**

## Live embedding call

Live verified: 45 prompts embedded in a single `text-embedding-3-small` call.

```
  Embedding 45 uncached prompts (text-embedding-3-small, LIVE)...
  Live embed call: 45 prompts -> $0.00003
  Embedding dimension: 1536
```

Provider: OpenAI `POST /v1/embeddings`, model `text-embedding-3-small`.
Cost: ~$0.000030 one-time on the first (cold-cache) run; `green-output.txt` shows $0.00 because that capture was a warm-cache re-run (all 45 embeddings already in `.embed-cache.json`).

## Test results (GREEN — 6/6 pass)

Live verified: `python3 source/test_l2.py` with real API keys:

```
test_cosine_similarity_range ... ok
test_embeddings_live ... ok
test_knn_accuracy_bounded_by_oracle ... ok
test_knn_pareto_property ... ok
test_knn_routes_some_strong ... ok
test_no_oracle_leakage ... ok

Ran 6 tests in 0.369s

OK
```

## Router sweep results (22-item test split)

Live verified: baselines computed from `labelset_export.json` (pre-measured outcome matrix,
no re-billing). Router routes each item based only on embedding k-NN vote.

| k | thresh | acc | cost | %cheap |
|---|---|---|---|---|
| 7 | 0.7 | **0.955** | **$0.00136** | 68% |
| 3 | 0.7 | 0.955 | $0.00143 | 64% |
| 5 | 0.7 | 0.955 | $0.00146 | 59% |
| 5 | 0.6 | 0.909 | $0.00123 | 77% |
| 1 | 0.4–0.7 | 0.909 | $0.00118 | 82% |
| always-cheap | — | 0.818 | $0.00088 | 100% |
| always-strong | — | 0.955 | $0.01104 | 0% |
| oracle | — | 0.955 | $0.00122 | N/A |

## Live API confirmation

Live verified: 3 routing decisions confirmed against real providers (2026-06-21):

| task | route | model | live_correct | cached_correct | match |
|---|---|---|---|---|---|
| m2 | cheap | gpt-4o-mini | True | True | OK |
| m4 | strong | gpt-4.1 | True | True | OK |
| m6 | cheap | gpt-4o-mini | True | True | OK |

All three confirmations match cached labels. The strong-model call (m4) returned at $5.00e-05.

## What is NOT live-verified

- Re-running the full 45-item suite through the APIs (intentionally avoided via outcome matrix
  to save cost — the RouterBench methodology).
- Embedding quality on out-of-distribution prompts (only in-distribution on the 45-task suite).
