# P-005: Threshold as the Cost-Quality Knob

**Category**: pattern
**Evidence tier**: Live verified (POCs L2, L2b, X4, X5, capstone)
**Source POCs**: L2-embedding-knn-router, L2b-classifier-router, X4-verification-cascade-automix, X5-router-benchmark-pareto, L-capstone-adaptive-routing-gateway

## Live verified

Every predictive router in this degree exposes a scalar threshold τ that continuously
trades cost against quality. Sweeping τ traces the **Pareto frontier** between always-cheap
(low cost, low accuracy) and always-strong (high cost, high accuracy).

Live-measured Pareto curve (logistic classifier, 5-fold CV, X5):

| τ    | Accuracy | Cost       | %cheap |
|------|----------|------------|--------|
| 0.70 | 0.956    | $0.00233   | 87%    |
| **0.90** | **0.978** | **$0.00291** | **74%** |
| —    | 0.978    | $0.02148   | 0%     | always-strong

Live-measured Pareto curve (kNN k=7, held-out test, L2):

| threshold | Accuracy | Cost       | %cheap |
|-----------|----------|------------|--------|
| 0.5       | 0.818    | $0.00098   | 95%    |
| 0.6       | 0.909    | $0.00118   | 82%    |
| **0.7**   | **0.955** | **$0.00136** | **68%** |

Live-measured Pareto curve (capstone, 5-fold CV):

| τ    | Accuracy | Cost       | %cheap |
|------|----------|------------|--------|
| 0.7  | 0.956    | $0.00227   | 82%    |
| **0.8** | **0.978** | **$0.00257** | **71%** |
| 0.9  | 0.978    | $0.00275   | 64%    |

## The shape

```
accuracy
  1.00 ────────────────────────────────── always-strong
  0.98                          thr=0.9 ●─────────────── (7.4× cheaper)
  0.97                    thr=0.8 ●
  0.96             thr=0.7 ●
                 kNN-0.7 ●
  0.93        kNN-0.6 ●
  0.91      kNN-0.5 ●
  0.84 ● always-cheap
       └──────────────────────────────── cost →
```

The threshold is the only parameter an operator needs to adjust to meet their SLA. Higher
τ = more conservative about routing cheap = more items escalated to strong = higher cost,
higher accuracy. Lower τ = more aggressive cheap routing = lower cost, lower accuracy.

## How to find the operating point for a given SLA

```python
def find_threshold(
    embeddings,   # (n, d) L2-normalized
    labels,       # cheap_correct per item
    usd_cheap,    # cost per item if served cheap
    usd_strong,   # cost per item if served strong
    accuracy_floor: float = 0.975,   # minimum acceptable accuracy
    router_fn = predict_logistic,    # (X, tau) -> p_cheap array
    cv_folds: int = 5,
) -> float:
    """
    Find the lowest τ that achieves accuracy >= accuracy_floor (via cross-validation).
    Returns the selected threshold.
    """
    best_tau  = 1.0
    best_cost = float("inf")
    for tau in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]:
        result = cross_validate(embeddings, labels, usd_cheap, usd_strong, tau, cv_folds)
        if result["accuracy"] >= accuracy_floor and result["total_usd"] < best_cost:
            best_tau  = tau
            best_cost = result["total_usd"]
    return best_tau
```

## Threshold behavior across router types

**Logistic classifier (L2b, X5)**:
- P(cheap_correct) clusters in a narrow range (0.74–0.91) due to class imbalance
- Effective threshold range is narrow: τ ∈ [0.75, 0.90]
- Below τ=0.75: collapses to always-cheap
- Above τ=0.90: collapses to always-strong

**k-NN router (L2)**:
- Threshold applied to weighted vote score ∈ [0, 1]
- Sweet spot is sharp: τ=0.6→0.7 jumps accuracy from 0.909 to 0.955 with only $0.00018 cost increase
- Hard-task embeddings cluster tightly; their neighbor votes concentrate near 0.6–0.7

**AutoMix (X4)**:
- Verifier confidence is nearly binary on this suite (0.0 or 1.0)
- τ=0.34, 0.67, 1.00 produce identical results (only one item has fractional confidence)
- On a more diverse query distribution, the threshold traces a smoother Pareto curve

## Never use a fixed threshold across workloads

The best threshold is **workload-specific**. A τ=0.9 that achieves oracle accuracy on this
benchmark may over-route to strong on a workload with a softer difficulty gap, wasting money.
Or it may under-route on a workload with a broader hard tail, missing accuracy targets.

Always select τ by cross-validating on representative held-out data from YOUR workload.

## The one exception: always set τ via CV, never by inspection

From L2b: the L2-normalized logistic output clusters so tightly (0.74–0.91) that inspecting
P(cheap_correct) on a few examples gives a misleading sense of the decision boundary. Only
cross-validation reveals whether τ=0.80 actually achieves oracle accuracy. (L2b)

## Evidence

- L2-embedding-knn-router/README.md — kNN threshold sweep, sharp sweet spot
- L2b-classifier-router/README.md — logistic threshold sweep, P-clustering diagnosis
- X4-verification-cascade-automix/README.md — AutoMix threshold behavior (near-binary)
- X5-router-benchmark-pareto/README.md — 5-fold CV Pareto, τ=0.9 as best realizable point
- L-capstone-adaptive-routing-gateway/README.md — capstone τ=0.8 operating point
