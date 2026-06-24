# P-004: Cache the Outcome Matrix for Reproducible Benchmarking

**Category**: pattern
**Evidence tier**: Live verified (POCs L0, X5)
**Source POCs**: L0-smoke-and-harness, X5-router-benchmark-pareto

## Live verified

The X5 benchmark evaluated 10 different router strategies over 45 tasks. After the first run
that built the outcome matrix, all subsequent router evaluations ran instantly with zero new
API calls. The X5 benchmark cached 255 entries; re-runs showed 0 misses. (X5 evidence.md)

The L0 outcome matrix (`harness/.cache/labelset.json`) stores per-task correctness and USD
for both `gpt-4o-mini` and `gpt-4.1`. Every subsequent POC imports this matrix to evaluate
against the same ground-truth baseline without re-billing. (L0)

## The pattern

**Build the outcome matrix once; replay from it for free.**

The outcome matrix records — for every `(model, task)` pair — the response text, whether
it was correct, and the USD cost. Once built, any router can be evaluated by replaying the
matrix: "for each task, if the router chose model M, what was M's correctness and cost?"

```
outcome_matrix = {
    "gpt-4o-mini|m1": {"text": "...", "correct": True,  "usd": 3.7e-06},
    "gpt-4o-mini|m9": {"text": "67",  "correct": False, "usd": 4.2e-06},
    "gpt-4.1|m9":     {"text": "47",  "correct": True,  "usd": 2.1e-04},
    ...
}
```

## Building the cache (one-time, live calls required)

```python
from cache import Cache
from providers import chat
import json

def build_outcome_matrix(
    suite: list,
    models: list[str],
    cache_path: str = "harness/.cache/labelset.json",
) -> dict:
    """
    Run both models over the full suite. Cache every response.
    Returns the outcome matrix. Skips already-cached (model, task) pairs.
    """
    cache  = Cache(cache_path)
    matrix = {}
    for task in suite:
        for model in models:
            key = f"{model}|{task.id}"
            # Cache.chat uses (model, messages) as the cache key
            result  = cache.chat(model, [{"role": "user", "content": task.prompt}])
            correct = task.grade(result.text)
            matrix[key] = {
                "text":    result.text,
                "correct": correct,
                "usd":     result.usd,
            }
    return matrix
```

## Evaluating any router from the matrix (zero API cost)

```python
def eval_router(router_fn, suite, matrix):
    """
    Score a router against the pre-built outcome matrix.
    router_fn: (task) -> "gpt-4o-mini" | "gpt-4.1"
    Returns: {accuracy, total_usd, per_task: [...]}
    """
    results = []
    for task in suite:
        model   = router_fn(task)
        entry   = matrix[f"{model}|{task.id}"]
        results.append({
            "task_id": task.id,
            "model":   model,
            "correct": entry["correct"],
            "usd":     entry["usd"],
        })
    accuracy  = sum(r["correct"] for r in results) / len(results)
    total_usd = sum(r["usd"]     for r in results)
    return {"accuracy": accuracy, "total_usd": total_usd, "per_task": results}
```

## Cache key design for reproducibility

The cache key must be deterministic and include everything that affects the response.
For temperature=0 calls (deterministic), the key is `(model, messages_hash)`. For
temperature>0 (self-consistency, MoA), add a `nonce` to distinguish independent samples:

```python
# From cache.py (harness)
def chat(self, model, messages, temperature=0.0, nonce=None, **kwargs):
    """
    nonce: pass a distinct nonce per sample when temperature > 0.
    Without a nonce, two calls with the same (model, messages) at temp>0
    return the same cached response — defeating the point of sampling.
    """
    key = self._make_key(model, messages, temperature, nonce)
    if key in self._store:
        return self._store[key]
    result = chat_live(model, messages, temperature=temperature, **kwargs)
    self._store[key] = result
    self._save()
    return result
```

The X5 benchmark used `nonce=f"verify_{i}"` for k-sample self-consistency to ensure each
of the k draws was independent.

## When NOT to use the outcome matrix

- **When evaluating a router on a new query distribution**: the matrix only covers the
  45-task suite. For novel prompts, new live calls are required.
- **When the model pool changes**: if you add a new model (e.g., `gpt-4.1-nano`), the
  matrix must be extended with new live calls for that model on every suite task.
- **When model behavior changes**: provider updates can change outputs. Refresh the matrix
  periodically if benchmark reproducibility across time matters.

## Outcome matrix vs harness cache

The outcome matrix is a **semantic artifact**: it stores per-task correctness judgments
that require a human or LLM judge to produce. The harness cache is a **transport artifact**:
it stores raw HTTP responses. They serve different purposes:

| Artifact          | Stores         | Purpose                    | Built by  |
|-------------------|---------------|----------------------------|-----------|
| `labelset.json`   | correctness + USD per (model, task) | router training + benchmark replay | L0 run |
| `harness/.cache/` | raw API responses                   | avoid re-billing            | any POC   |

The labelset is consumed by kNN (R-002) and logistic (R-001) as training labels.
The harness cache is consumed by every POC to avoid redundant API calls.

## Evidence

- L0-smoke-and-harness/README.md — harness design, cache structure, labelset location
- X5-router-benchmark-pareto/evidence.md — "255 cache entries, 0 misses on re-run"
- results-digest.md lines 12–15 — outcome matrix built from L0 baseline
