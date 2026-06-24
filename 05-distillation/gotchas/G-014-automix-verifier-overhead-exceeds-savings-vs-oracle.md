# G-014: AutoMix verifier overhead exceeds routing savings — it does not beat a trained classifier vs. oracle

**Category**: gotcha
**Severity**: medium
**Evidence tier**: Live verified
**Source POC**: X4-verification-cascade-automix

## What

Live verified. AutoMix at threshold T=0.67 achieved acc 0.978 at $0.006092. The oracle costs $0.002140 at the same accuracy. AutoMix is 2.85× more expensive than the oracle despite routing 71.6% of items to the cheap model.

The k=3 verifier calls (3 consistency-check samples per item) added $0.003570 total overhead — more than the cost of the oracle's entire routing budget. This makes AutoMix strictly worse than a trained logistic classifier on cost vs. oracle distance, while being strictly better than always-strong (71.6% savings vs. strong at $0.02148).

The verifier's confidence scores were nearly binary (0.0 or 1.0 for 44/45 items), making the threshold T a binary switch rather than a continuous dial. Only one item (m14) produced a fractional confidence (0.33).

## Why it matters

AutoMix is commonly cited as a way to get near-oracle routing without a training set. On a workload where cheap and strong models are clearly separated by item difficulty, the verifier overhead dominates. The correct comparison is against a trained classifier, not just always-strong.

An agent that adopts AutoMix to save on strong-model calls will save ~72% vs. always-strong but pay 2.85× what a logistic classifier would cost for the same accuracy — because the classifier makes the routing decision before any inference call, while the verifier requires running cheap inference first.

## Root cause

The verifier in AutoMix runs the cheap model first, then runs k=3 verification samples to assess confidence, then escalates if confidence is below T. Even when the cheap answer is correct (38/45 items), 3 additional verification calls are made. On a short-answer suite where each cheap call costs ~$0.000004–$0.0002, those 3 verification calls double or triple the per-item cost.

The verifier is worth the overhead only when:
1. A training set is unavailable (can't train a classifier).
2. The escalation rate is low (< 10% of items escalate), so verifier cost amortizes well.
3. Per-verification call cost is significantly cheaper than the primary inference (e.g., verifying with a nano model after generating with mini).

## Fix

Use a trained classifier (L2b logistic or L2 k-NN) when labeled data is available — it approaches oracle cost without per-item verifier overhead. Use AutoMix only when:
- No training labels exist (cold start).
- The cheap model's self-verification is substantially cheaper than the primary inference.

If using AutoMix, minimize verifier cost: use the cheapest available model for verification, use k=1 or k=2 samples, and apply the verifier only to items the heuristic router flags as uncertain (not all items).

## Regression note

When benchmarking AutoMix alongside a classifier, report both costs vs. the oracle (not just vs. always-strong). AutoMix's 71.6% savings headline vs. strong is correct but incomplete; vs. oracle it is 2.85× more expensive.

## Evidence

- Source: `03-pocs/X4-verification-cascade-automix/surprises.md`, item 2: "The oracle costs $0.002140 at 0.9778 accuracy. AutoMix at T=0.67 costs $0.006092 (nearly 3x the oracle) for the same accuracy. The k=3 verifier calls add $0.003570 total overhead, which exceeds the savings from avoiding strong model calls on the 38/45 easy items." (Live verified)
- Source: `03-pocs/X4-verification-cascade-automix/surprises.md`, item 1: "Almost every item lands at exactly 0.0 (all three 'no' votes) or 1.0 (all three 'yes' votes). The threshold knob is effectively a binary switch on this suite, not a continuous dial." (Live verified)
- Source: results-digest.md, X4: "0.978 at 71.6% savings vs always-strong, but 2.85× oracle (verifier overhead eats headroom); verifier 100% precise on high-confidence bucket." (Live verified)
