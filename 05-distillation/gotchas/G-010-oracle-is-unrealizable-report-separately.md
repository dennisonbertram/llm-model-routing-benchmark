# G-010: Oracle is an unrealizable ceiling — report it separately from realizable routers

**Category**: gotcha
**Severity**: medium
**Evidence tier**: Live verified
**Source POC**: L0-smoke-and-harness, X5-router-benchmark-pareto

## What

Live verified. The oracle router (always route to the cheapest model that answers correctly for each item) achieved acc 0.978 at $0.00214 — approximately 10% of the cost of always-strong. This appears to be the target to beat. But the oracle peeks at the correct answer for each item before routing — it is not a router any real system can implement.

In the X5 Pareto benchmark, the oracle is listed as a separate "unrealizable ceiling" row. The realizable frontier runs: always-cheap → kNN(k=5) → kNN(k=3) → logistic(0.7) → logistic(0.9). The best realizable router (logistic thr=0.9) reaches acc 0.978 at $0.00291 — matching oracle accuracy at 1.36× oracle cost. This is the correct comparison: the logistic router essentially closes the gap to oracle.

## Why it matters

Papers and benchmarks that compare a learned router against the oracle in a Pareto plot are showing the maximum achievable gap, which is useful for motivation. But an agent-builder comparing their router to the oracle as a target to "beat" will consistently underestimate their router's quality — the oracle sets an impossible standard by using information (per-item ground-truth correctness) that is not available at routing time.

Conversely, reporting only "our router achieves 90% of oracle savings" without also reporting what the router costs versus always-cheap and always-strong gives an incomplete picture of Pareto position.

## Root cause

The oracle is computed retrospectively by running both models on every item and assigning the cheaper correct call. It requires knowing each item's correct answer before routing — defeating the purpose of routing. In the live suite (L0, X5), the oracle was computed from the cached label set `harness/.cache/labelset.json` which stores both models' correctness per item.

## Fix

Always report three reference points in any router benchmark table:

| Ref | Description | Why include |
|---|---|---|
| always-cheap | Cheapest model on everything | Lower bound on quality |
| always-strong | Strongest model on everything | Upper bound on quality |
| oracle | Unrealizable ceiling (peeks at correctness) | Shows maximum headroom |

List all realizable routers separately and label the oracle explicitly as "(unrealizable)" or "(peeks at correctness — not deployable)". Never use the oracle as the denominator in a savings percentage without this caveat.

In the L0 suite: oracle acc 0.978 at $0.00214; always-strong acc 0.978 at $0.02148; the oracle saves 90% vs. always-strong. The best realizable router saves 86.5% (logistic thr=0.9, $0.00291). Both numbers are valid; the oracle savings number must not be attributed to the learned router.

## Regression note

Benchmark reporting scripts should compute oracle cost only from a committed label set, not from a new live run. Include a comment that the oracle row requires pre-computed ground truth. Flag any router that claims cost below oracle cost — this would indicate a measurement error.

## Evidence

- Source: results-digest.md, L0 baseline: "ORACLE (cheapest-correct): acc 0.978, $0.00214 (~10% of strong cost; charge cheap for unsolvable m8)." (Live verified)
- Source: results-digest.md, X5: "Realizable frontier: always-cheap → kNN(k=5) → kNN(k=3) → logistic(0.7) → logistic(0.9); oracle is the unrealizable ceiling." (Live verified)
- Source: results-digest.md, Gotchas item 10: "Oracle is an UNREALIZABLE ceiling (peeks at correctness) — report it separately from realizable routers." (Live verified)
