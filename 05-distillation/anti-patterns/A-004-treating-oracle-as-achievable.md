# A-004: Treating the Oracle as Achievable — Reporting Oracle Cost as the Expected Router Gain

**Category**: anti-pattern
**Severity**: medium — leads to unrealistic expectations and misleading benchmarks
**Evidence tier**: Live verified
**Source POCs**: L0-smoke-and-harness, X5-router-benchmark-pareto, L-capstone-adaptive-routing-gateway

---

## What the anti-pattern looks like

Presenting the oracle cost ($0.00214 in this degree) as the target a good router should
reach, or showing a deployed router's savings relative to the oracle as if closing that
gap fully were possible in production.

The oracle is defined as: for each task, use the cheapest model that answers correctly,
using foreknowledge of the correct answer before routing. It is a retrospective lower
bound on cost at a given accuracy level, not a deployable policy.

---

## Why it matters

**Live verified** (X5; capstone) — the best deployed router in this degree:

| Router | Accuracy | Cost | vs oracle |
|---|---|---|---|
| oracle (unrealizable ceiling) | 0.978 | $0.00214 | 1.0× |
| capstone adaptive(thr=0.8) CV | 0.978 | $0.00257 | 1.20× (20% above) |
| X5 logistic(thr=0.9) CV | 0.978 | $0.00291 | 1.36× (36% above) |
| always-strong | 0.978 | $0.02148 | 10.0× |

The oracle gap (from $0.00214 to $0.00257 in the capstone) is real and unavoidable:
the router must pay to occasionally route a task to strong that cheap would have gotten
right (false positives). It cannot know which tasks cheap will fail without running cheap
first (which is the cascade pattern) or training a classifier (which only approximates).

Closing the oracle gap to zero would require a perfect predictor with zero false negatives
and zero false positives — which would require knowing the correct answer before asking.

---

## How to report the oracle correctly

**Live verified** (X5; capstone)

1. Always label the oracle row clearly: `oracle (unrealizable ceiling)` or
   `oracle (cheapest-correct, unrealizable)`. Never include it in the realizable Pareto
   frontier without this label.

2. Show the oracle in the same table as deployed routers so readers can see the gap.
   Do not omit it — a table showing only deployed routers without the oracle makes the
   best router look more impressive than it is.

3. Quote deployed router performance relative to always-strong, not relative to the
   oracle. "7.4× cheaper than always-strong" is the meaningful claim. "36% above the
   oracle" is context, not a criticism.

The X5 benchmark table from this degree (correctly formatted):

```
always-cheap        acc=0.844  $0.00166   <- cost floor (realizable)
k-NN(k=5) CV        acc=0.889  $0.00203   <- realizable
k-NN(k=3) CV        acc=0.933  $0.00221   <- realizable
logistic(thr=0.7)   acc=0.956  $0.00233   <- realizable
logistic(thr=0.9)   acc=0.978  $0.00291   <- realizable (matches strong, 7.4× cheaper)
oracle              acc=0.978  $0.00214   <- UNREALIZABLE ceiling
always-strong       acc=0.978  $0.02148   <- cost ceiling (realizable)
```

---

## A secondary trap: using the oracle to validate a test set

The oracle requires running both cheap and strong on every item to determine correctness.
That process — the outcome matrix — is expensive to collect (you pay for both models on
every task). Once built, it is a labeling cost that must be amortized over future
routing decisions. For small suites (45 tasks in this degree), the outcome matrix is
cheap. For production use with millions of tasks, sampling is necessary. Never re-collect
the outcome matrix per deployment.

---

## Evidence

- results-digest.md: "ORACLE (cheapest-correct): acc 0.978, $0.00214 (~10% of strong cost; charge cheap for unsolvable m8)." (Live verified)
- results-digest.md: "Oracle is an UNREALIZABLE ceiling (peeks at correctness) — report it separately from realizable routers." (Live verified, Gotcha 10)
- X5 README.md: "oracle (cheapest-correct, unrealizable ceiling) | 0.978 | 0.002143" (Live verified)
- Capstone README.md: "oracle (ceiling, unrealizable) | 0.978 | $0.00214 | —" with explicit label. (Live verified)
