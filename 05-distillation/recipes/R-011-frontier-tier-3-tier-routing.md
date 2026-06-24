# R-011: Multi-Tier Routing — reserve a frontier model for the hard tail

**Evidence: Live verified (2026-06-22, X6).**

When a frontier reasoning model (e.g. GPT-5.5) is available, do NOT route everything to it — it is
overkill (and slow) for the 90%+ of requests a cheap model already handles. Add it as a **third
tier** reachable only when the router is confident the task is genuinely hard. One CV-trained
logistic classifier that predicts `P(cheap is correct)` drives all three tiers with two thresholds.

## Live result (X6, 45-task suite)

| router | accuracy | cost | note |
|---|---|---|---|
| always gpt-5.5 | 1.000 | $0.11943 | frontier-everything — wasteful + ~2.8 s/call |
| **realizable 3-tier router** | **1.000** | **$0.00405** | 32→cheap, 12→gpt-4.1, **1→gpt-5.5** |
| 3-tier oracle (unrealizable) | 1.000 | $0.00372 | ceiling |

**The 3-tier router reaches 100% accuracy at 30× lower cost than always-gpt-5.5** by sending only
the single genuinely-hard item to the frontier model. (Live verified.)

## Recipe

```python
# one classifier score P(cheap correct), two thresholds -> three tiers
def route(prompt, clf, hi=0.8, lo=0.5):
    p = clf.p_cheap_ok(prompt)          # trained on the live outcome matrix (see R-002)
    if p >= hi: return "gpt-4o-mini"    # confident cheap is enough
    if p <= lo: return "gpt-5.5"        # looks hard -> frontier reasoning model
    return "gpt-4.1"                    # mid tier
```

- Train the classifier exactly as in [R-002](R-002-logistic-classifier-router.md) (embeddings +
  numpy logistic regression on `cheap_correct` labels). The same single score generalizes to N
  tiers — you do not need a separate classifier per tier for a clean capability ladder.
- Pick `hi`/`lo` from your cost budget and the measured Pareto sweep; higher `hi` and `lo` push more
  traffic up (more accuracy, more cost).

## Why it works (Live verified)
A frontier model earns its premium ONLY on the hard tail (X6: GPT-5.5 was 5.6× the cost of gpt-4.1
and only mattered on the items gpt-4.1 missed). Routing converts "too expensive to use everywhere"
into "used for the 2% that need it" — capturing the higher ceiling at cheap-model-adjacent cost.

## Caveat (Live verified)
A higher version number is not a capability guarantee: in X6, `gpt-5.4` matched `gpt-4.1`'s accuracy
at 1.8× the cost (fixed one hard item, broke another) — strictly dominated. Measure each candidate
tier on your own tasks before adding it. See [G-016](../gotchas/G-016-newer-model-not-strictly-better.md).
