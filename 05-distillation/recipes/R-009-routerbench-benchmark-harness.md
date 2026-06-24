# R-009: RouterBench-Style Benchmark Harness

**Category**: recipe
**Evidence tier**: Live verified (POCs L0, X5)
**Source POCs**: L0-smoke-and-harness, X5-router-benchmark-pareto

## Live verified

A RouterBench-style benchmark runs every router strategy over one shared evaluation suite
and reports a cost-vs-quality Pareto frontier. This is the empirical heart of the degree.
All numbers in the Pareto table below are live-measured.

Full benchmark results (45 tasks: 15 math, 12 QA, 18 coding; 5-fold CV for predictive routers):

| Router                         | Accuracy | Total cost  | $/correct  |
|--------------------------------|----------|-------------|------------|
| always-cheap (`gpt-4o-mini`)   | 0.844    | $0.001662   | $4.4e-05   |
| always-strong (`gpt-4.1`)      | 0.978    | $0.021482   | $4.88e-04  |
| random-50% (10 seeds)          | 0.909    | $0.011765   | $2.88e-04  |
| heuristic (prompt cues)        | 0.933    | $0.005200   | $1.24e-04  |
| k-NN (k=3) CV                  | 0.933    | $0.002211   | $5.3e-05   |
| k-NN (k=5) CV                  | 0.889    | $0.002035   | $5.1e-05   |
| logistic (thr=0.7) CV          | 0.956    | $0.002335   | $5.4e-05   |
| **logistic (thr=0.9) CV**      | **0.978** | **$0.002905** | $6.6e-05 |
| MoA (3 cheap + aggregator)     | 0.956    | $0.101588   | $2.36e-03  |
| _oracle (unrealizable ceiling)_ | _0.978_ | _$0.002143_ | _$4.9e-05_ |

Key finding: every learned router dominates random routing on both cost and quality.
MoA is dominated by always-strong on both axes. (X5)

## The outcome matrix — run once, benchmark for free

The key to reproducible, cost-free benchmarking is the **outcome matrix**: pre-compute each
model's per-task response and grade it once. Router strategies are then evaluated by
replaying from this matrix — no new API calls needed.

```python
# Build the outcome matrix (one-time, expensive)
outcome_matrix = {}
for task in suite:
    for model in [CHEAP, STRONG]:
        key = f"{model}|{task.id}"
        if key not in cache:
            result = chat(model, [{"role": "user", "content": task.prompt}])
            cache[key] = {"text": result.text, "usd": result.usd}
        cached = cache[key]
        outcome_matrix[key] = {
            "correct": task.grade(cached["text"]),
            "usd":     cached["usd"],
        }

# Save for all future benchmark runs
import json
with open("outcome_matrix.json", "w") as f:
    json.dump(outcome_matrix, f)
```

## Evaluating a router from the outcome matrix

```python
def eval_router_from_matrix(
    router_fn,           # (task) -> "cheap" | "strong"
    suite: list,
    matrix: dict,
    cheap_model:  str = "gpt-4o-mini",
    strong_model: str = "gpt-4.1",
) -> dict:
    """
    Score a router against the outcome matrix. Zero new API calls.
    router_fn receives a task and returns a model choice.
    """
    correct = 0
    total_usd = 0.0
    for task in suite:
        choice = router_fn(task)
        model  = cheap_model if choice == "cheap" else strong_model
        entry  = matrix[f"{model}|{task.id}"]
        if entry["correct"]:
            correct += 1
        total_usd += entry["usd"]
    return {
        "accuracy":  correct / len(suite),
        "total_usd": total_usd,
    }
```

## 5-fold cross-validation for predictive routers (no oracle leakage)

For routers that train on labels (kNN, logistic), use k-fold CV so every task is held out
exactly once. Never use the same fold for both training and evaluation.

```python
import numpy as np

def five_fold_cv(embeddings, labels, usd_cheap, usd_strong, router_factory, tau):
    """
    embeddings: (n, d) float64, L2-normalized
    labels:     (n,) int — cheap_correct (1) or not (0)
    router_factory: fn(train_X, train_y, tau) -> router (callable on test vecs)
    """
    n = len(labels)
    fold_size = n // 5
    correct_total = 0
    cost_total    = 0.0

    for fold in range(5):
        test_start = fold * fold_size
        test_end   = (fold + 1) * fold_size if fold < 4 else n

        test_idx  = list(range(test_start, test_end))
        train_idx = [i for i in range(n) if i not in set(test_idx)]

        train_X = embeddings[train_idx]
        train_y = np.array(labels)[train_idx].astype(float)
        test_X  = embeddings[test_idx]
        test_y  = np.array(labels)[test_idx]

        router = router_factory(train_X, train_y, tau)

        for i, idx in enumerate(test_idx):
            p_cheap = router(test_X[i])
            use_cheap = p_cheap >= tau
            correct_total += test_y[i] if use_cheap else (1 - (1 - test_y[i]))  # from matrix
            cost_total    += usd_cheap[idx] if use_cheap else usd_strong[idx]

    return {
        "accuracy":  correct_total / n,
        "total_usd": cost_total,
    }
```

## Pareto frontier filter

```python
def pareto_front(results: list[dict]) -> list[dict]:
    """
    Keep only routers not dominated by any other (higher acc AND lower cost).
    results: list of {"name": ..., "accuracy": float, "total_usd": float}
    """
    frontier = []
    for r in results:
        dominated = any(
            other["accuracy"] >= r["accuracy"] and other["total_usd"] <= r["total_usd"]
            and other is not r
            for other in results
        )
        if not dominated:
            frontier.append(r)
    return sorted(frontier, key=lambda x: x["total_usd"])
```

## What to include in a complete benchmark report

1. Always-cheap, always-strong baselines (the floor and ceiling)
2. Oracle (cheapest-correct per task) — labeled as **unrealizable ceiling**; never a
   realizable deployment target
3. Random-50% — the "no routing skill" baseline; any trained router should dominate this
4. Heuristic, kNN, classifier at their best operating point(s) from CV
5. MoA / self-consistency if you run them — report the REAL cost even if expensive
6. The Pareto frontier (routers not dominated on both axes)

## Cache strategy (live-verified, X5)

Cache every `(model, task, nonce)` response to disk. After the first run (warm-up), all
router evaluations are instant and free. The X5 benchmark cached 255 entries; re-runs
showed 0 misses. (X5 evidence.md)

Never share the inference cache between separate benchmark runs if you are testing for
reproducibility — create a fresh cache key per evaluation.

## Evidence

- L0-smoke-and-harness/README.md — baseline measurements and harness design
- X5-router-benchmark-pareto/README.md — full benchmark table, Pareto frontier, MoA numbers
- X5-router-benchmark-pareto/evidence.md — cache stats, supported/unsupported claims
- results-digest.md lines 12–24 — authoritative benchmark numbers
