# Commands — L2b Classifier Router

## Prerequisites

Load credentials (required for embedding API calls):

```bash
set -a; . .agent-university/secrets.local.env; set +a
```

## Run the tests (live behavioral tests)

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/L2b-classifier-router/source
python3 test_l2b.py -v
```

Expected: 6 tests pass (`OK`). Requires `OPENAI_API_KEY` (for embedding).
Embeddings cached after first run — subsequent runs hit the local `.embed_cache.json`.

## Run the full POC

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/L2b-classifier-router/source
python3 run_l2b.py
```

Outputs:
- Embedding cost (cached = $0.00 after first run)
- Train/test split and label distribution
- Logistic regression training log (loss + train_acc per 50 epochs)
- P(cheap_correct) distribution on test set
- Full Pareto threshold sweep table
- Live confirmation embedding + routing decision
- Summary table comparing baselines vs classifier at selected thresholds
- `l2b_summary.json` with all measured numbers

## Interpret the Pareto curve

Key thresholds:
- τ < 0.75: collapses to always-cheap (all probabilities exceed threshold)
- τ = 0.75: first non-collapsing point; acc=0.923, cost=$0.000468
- τ = 0.80: **best operating point** — oracle accuracy (1.000), cost=$0.000773
- τ = 0.85: still oracle accuracy, slightly more expensive ($0.000922)
- τ > 0.90: approaches always-strong territory

## Cache notes

- `.embed_cache.json` — 45 prompt embeddings; created on first run (≈$2.85e-05 estimated; cache was warm on captured run); cached forever
- Do NOT modify `harness/.cache/labelset.json` or `harness/.cache/labelset_export.json`
- The POC uses its own cache file; the harness cache is read-only from this POC's perspective
