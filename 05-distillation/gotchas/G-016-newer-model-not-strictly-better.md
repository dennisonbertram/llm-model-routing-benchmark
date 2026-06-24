# G-016: A newer / pricier model is not strictly better per item

**Evidence: Live verified (2026-06-22, X6).**

## Symptom
You upgrade the "strong" tier to a newer, more expensive model expecting a free accuracy win, and
instead pay more for the same (or worse) results on your workload.

## Live root cause
In X6, `gpt-5.4` ($2.50/$15 per 1M) was run against the same 45-task suite as `gpt-4.1` ($2/$8):

- Both scored **0.978** overall.
- `gpt-5.4` **fixed `m8`** (gold 14) that `gpt-4.1` missed — but **broke `m10`** (gold 16) that
  `gpt-4.1` had solved. Net accuracy change: zero.
- `gpt-5.4` cost **1.8×** more.

So on this workload `gpt-5.4` is **strictly dominated** by `gpt-4.1` (equal accuracy, higher cost).
Model quality is non-monotonic per item even across version numbers — the newer model has a
different error set, not a strictly smaller one. (Compare G-... on cheap-model non-monotonicity:
`gpt-4o-mini` likewise failed items `gpt-4.1-nano` solved.)

## Fix
- **Measure every candidate tier on your own tasks** before promoting it. Re-run the outcome matrix
  (cheap/mid/strong/frontier per task) and recompute the Pareto frontier; keep a model only if it is
  non-dominated.
- The frontier model that DID help in X6 was `gpt-5.5` (1.000 vs 0.978) — but only on the hard tail,
  and at 5.6× cost, so route to it rather than default to it (see
  [R-011](../recipes/R-011-frontier-tier-3-tier-routing.md)).

## Regression note
The benchmark harness (X5/R-009) is the regression test: add the new model to the outcome matrix and
confirm it lands on the realizable frontier. If it is dominated, do not add the tier.
