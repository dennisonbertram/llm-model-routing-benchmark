# P-001: Predictive Routing vs the Oracle Ceiling

**Category**: pattern
**Evidence tier**: Live verified (POCs L0, L2b, X5, capstone)
**Source POCs**: L0-smoke-and-harness, L2b-classifier-router, X5-router-benchmark-pareto, L-capstone-adaptive-routing-gateway

## Live verified

The oracle (cheapest-correct per task) is the **unrealizable ceiling**: it peeks at the
ground-truth answer to assign each task to the cheapest model that gets it right. No
deployed router can match it exactly — it requires knowing the answer before asking.

Live measurements on the 45-task benchmark:

| Router                      | Accuracy | Cost       | vs always-strong |
|-----------------------------|----------|------------|-----------------|
| always-cheap (gpt-4o-mini)  | 0.844    | $0.00166   | 7.7%            |
| **oracle (unrealizable)**   | **0.978** | **$0.00214** | **10.0%**     |
| logistic (τ=0.9) CV         | 0.978    | $0.00291   | 13.5%           |
| capstone adaptive (τ=0.8)   | 0.978    | $0.00257   | 12.0%           |
| always-strong (gpt-4.1)     | 0.978    | $0.02148   | 100%            |

**The trained logistic router matches the oracle's accuracy at only 1.36× the oracle's
cost.** The oracle costs $0.00214; the best realizable router costs $0.00257–$0.00291.
The gap between them is narrow — trained predictive routers nearly close it. (X5, capstone)

## The shape

```
       accuracy
  1.0  ─────────────────────────── oracle ─── always-strong
                                (unrealizable)
  0.97                               ▲
                      logistic-0.9 ──┘ (realizable, 7.4× cheaper than strong)
  0.95            logistic-0.7
                 kNN-k3
  0.93
  0.92
  0.90         kNN-k5
  0.88
  0.84 always-cheap ────────────────────────────────────────────
       $0.001  $0.002  $0.003  $0.005  $0.010  $0.022
                              cost →
```

The oracle sits above and to the left of every realizable router because it knows which
model is correct before calling either. The best trained router (logistic at τ=0.9) reaches
the oracle's accuracy level while paying 1.36× the oracle's cost. (X5)

## The pattern

**Report the oracle separately.** Do not mix oracle numbers into comparisons with realizable
routers. The oracle is a benchmark calibration tool, not a deployment target.

**Use the oracle to measure routing opportunity.** The gap between always-cheap and the
oracle tells you the maximum cost savings available from any routing method. On this benchmark:

- Always-cheap: $0.00166, acc 0.844
- Oracle:        $0.00214, acc 0.978
- The routing prize: +13.4pp accuracy at only 1.3× cheap cost
- Only 6/45 tasks actually needed the strong model (all hard math: m9, m10, m12–m15)
- 38/45 (84%) could be served cheaply without any accuracy loss (L0)

**When the realizable router nearly matches the oracle, you've captured most of the
routing value.** The capstone at $0.00257 is only 1.20× the oracle bound — at that point,
further optimization has diminishing returns. (capstone)

## When to use

- Use oracle cost as the benchmark calibration denominator: "realizable router achieves X%
  of oracle savings" is a meaningful metric; "router matches always-strong at 13% of its cost"
  is another.
- Use the oracle to diagnose whether a workload is actually routable: if oracle cost ≈ 
  always-cheap cost, the workload is already easy and routing provides no value.
- Do NOT use oracle accuracy/cost in a comparison table without explicitly labeling it as
  "(unrealizable ceiling)". Presenting it alongside realizable routers misleads readers.

## Evidence

- L0-smoke-and-harness/README.md — oracle definition, 6 tasks need strong, headroom measurement
- X5-router-benchmark-pareto/README.md — Pareto frontier, oracle row labeled "(unrealizable ceiling)"
- L-capstone-adaptive-routing-gateway/README.md — capstone at 1.20× oracle
- results-digest.md lines 14–15 — oracle authoritative numbers
