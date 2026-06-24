# Commands — L2 Embedding k-NN Router

## Prerequisites

Load credentials:
```bash
set -a; . .agent-university/secrets.local.env; set +a
```

Requires: `OPENAI_API_KEY` (for embeddings and live confirmation calls).

## Run behavioral tests (GREEN = all pass)

```bash
python3 model-routing/degrees/01-llm-model-routing/03-pocs/L2-embedding-knn-router/source/test_l2.py
```

Expected: `Ran 6 tests in ~0.4s   OK`
First run: embeds 45 prompts live (~$0.00003). Subsequent runs: all cached (free).

## Run full evaluation + sweep

```bash
python3 model-routing/degrees/01-llm-model-routing/03-pocs/L2-embedding-knn-router/source/run_l2.py
```

Prints: baseline table, k/threshold sweep, live confirmation of 3 routing decisions,
final summary table. Writes `source/l2_results.json`.

## Reproduce RED output (missing credentials)

```bash
unset OPENAI_API_KEY
python3 model-routing/degrees/01-llm-model-routing/03-pocs/L2-embedding-knn-router/source/test_l2.py
# -> ProviderError: Missing env var OPENAI_API_KEY
```

## Inspect results JSON

```bash
python3 -c "
import json
with open('model-routing/degrees/01-llm-model-routing/03-pocs/L2-embedding-knn-router/source/l2_results.json') as f:
    r = json.load(f)
print('best:', r['best'])
print('sweep count:', len(r['sweep']))
"
```

## Cache files

- `.embed-cache.json` — prompt-text-keyed embedding vectors; paid once, free thereafter
- `.chat-cache.json` — harness Cache for live confirmation calls

Neither file touches `harness/.cache/labelset.json`.
