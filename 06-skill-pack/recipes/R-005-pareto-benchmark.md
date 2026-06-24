# Recipe R-005: Pareto Benchmark Harness

Live verified (X5; L0; 2026-06-21). Run all routers over one shared evaluation and emit
a cost-vs-quality Pareto frontier table.

Back to [index](../index.md).

---

## When to use

- Before claiming any router "works" — compare it against at least always-cheap, always-strong,
  random-50%, and the oracle ceiling.
- When evaluating a new workload — measure the oracle headroom first (how many items need strong?).

---

## Live benchmark results (X5; 45-task suite)

Live verified. From `03-pocs/X5-router-benchmark-pareto/README.md` and the results digest.

| router | accuracy | total $ | $/correct |
|--------|----------|---------|-----------|
| always-cheap (gpt-4o-mini) | 0.844 | 0.001662 | 4.4e-05 |
| always-strong (gpt-4.1) | 0.978 | 0.021482 | 4.88e-04 |
| random-50% (10 seeds) | 0.909 | 0.011765 | 2.88e-04 |
| heuristic | 0.933 | 0.005200 | 1.24e-04 |
| kNN (k=3) CV | 0.933 | 0.002211 | 5.3e-05 |
| kNN (k=5) CV | 0.889 | 0.002035 | 5.1e-05 |
| logistic (thr=0.7) CV | 0.956 | 0.002335 | 5.4e-05 |
| **logistic (thr=0.9) CV** | **0.978** | **0.002905** | 6.6e-05 |
| MoA (3 cheap + agg) | 0.956 | 0.101588 | 2.36e-03 |
| oracle (unrealizable ceiling) | 0.978 | 0.002143 | 4.9e-05 |

---

## Code: benchmark runner

```python
"""
Pareto benchmark: run all routers over the shared suite; emit cost-vs-quality table.
Uses the L0 labelset cache — no re-billing for deterministic routers.
Live verified: X5 ran this on 45 tasks on 2026-06-21.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
from tasks import ALL as SUITE
from cache import Cache
from metrics import format_table
from router_base import SingleModelRouter, run_suite
import random, json

CACHE = Cache(os.path.join(os.path.dirname(__file__), "..", "..", "harness", ".cache"))
CHEAP  = "gpt-4o-mini"
STRONG = "gpt-4.1"


# ── Baseline routers ───────────────────────────────────────────────────────

def always_cheap():
    return SingleModelRouter(CHEAP)

def always_strong():
    return SingleModelRouter(STRONG)

def random_50(seed: int = 42):
    class R:
        def route(self, item):
            random.seed(seed + hash(item["id"]))
            return random.choice([CHEAP, STRONG])
    return R()

def oracle():
    """Unrealizable ceiling — peeks at per-item correctness from cache."""
    labelset_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "harness", ".cache", "labelset.json"
    )
    with open(labelset_path) as f:
        ls = {d["id"]: d for d in json.load(f)}
    class Oracle:
        def route(self, item):
            d = ls.get(item["id"], {})
            return CHEAP if d.get("cheap_correct") else STRONG
    return Oracle()


# ── Run and report ─────────────────────────────────────────────────────────

def run_benchmark(routers: dict) -> list:
    """
    routers: {label: router_instance}
    Returns list of {label, accuracy, total_usd, usd_per_correct} dicts.
    """
    rows = []
    for label, router in routers.items():
        result = run_suite(router, SUITE, cache=CACHE)
        rows.append({
            "label":         label,
            "accuracy":      result.accuracy(),
            "total_usd":     result.total_usd(),
            "usd_per_correct": result.usd_per_correct(),
        })
        print(f"  {label:35s}  acc={result.accuracy():.3f}  ${result.total_usd():.6f}")
    return rows


# ── Main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Pareto Benchmark ===\n")

    # Import your learned routers here after training them
    # from logistic_router import LogisticRouter
    # from knn_router import KNNRouter

    routers = {
        "always-cheap":     always_cheap(),
        "always-strong":    always_strong(),
        "random-50%":       random_50(),
        "oracle (UNREALIZABLE)": oracle(),
        # Add your routers:
        # "logistic(thr=0.9)": LogisticRouter(threshold=0.9),
        # "kNN(k=3,thr=0.7)":  KNNRouter(k=3, threshold=0.7),
    }

    rows = run_benchmark(routers)
    print("\n" + format_table(rows))
    print("\nNOTE: oracle is the unrealizable ceiling — peeks at per-item correctness.")
    print("      Never compare a deployed router against oracle as if it were achievable.")
```

---

## Checklist for a valid benchmark

See [checklists/benchmark-validity.md](../checklists/benchmark-validity.md).

Critical rules:
- Include always-cheap, always-strong, and oracle (labeled "unrealizable ceiling") in every report.
- Use 5-fold CV or a strict held-out split for learned routers — no leakage.
- Report both accuracy AND cost (not just one).
- Do not tune the task suite or prompts to favor any router.
- Random-50% (10-seed average) is the minimum baseline to beat for a router to be useful.

## Source

`03-pocs/X5-router-benchmark-pareto/source/benchmark.py`
