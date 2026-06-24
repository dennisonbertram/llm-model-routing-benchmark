# Surprises

## 1. Verifier confidence is nearly binary (not graded)

Expected the verifier to produce a range of confidence scores across the threshold
sweep, enabling a smooth cost-quality trade-off curve. Instead, almost every item
lands at exactly 0.0 (all three "no" votes) or 1.0 (all three "yes" votes). Only
one item (m14, coin-change permutations) produced a fractional score of 0.33.

This means T=0.34, T=0.67, and T=1.00 all produce identical escalation decisions
(and identical cost/accuracy). The threshold knob is effectively a binary switch on
this suite, not a continuous dial.

Likely cause: the cheap model (gpt-4o-mini) is either confidently right or
confidently wrong. It does not hedge — it answers definitively, and the verifier
votes match that confidence. A more diverse query distribution (where cheap partially
reasons through a problem) would likely produce more graded confidence.

## 2. Verifier overhead dominates — AutoMix does NOT beat the oracle on cost

The oracle costs $0.002140 at 0.9778 accuracy. AutoMix at T=0.67 costs $0.006092
(nearly 3x the oracle) for the same accuracy. The k=3 verifier calls add $0.003570
total overhead, which exceeds the savings from avoiding strong model calls on the
38/45 easy items.

This is an honest negative finding against AutoMix as a cost optimization strategy
compared to the oracle. AutoMix's advantage over always-strong is still real
(71.6% cost reduction), but the comparison point that matters most is the oracle —
and a good classifier router should get close to oracle without per-item verifier
overhead. Users of this suite should NOT choose AutoMix over a trained classifier
unless they cannot build a training set.

## 3. Cheap model verifying its own answers works surprisingly well

Despite skepticism about self-evaluation, the verifier achieves 100% precision on
high-confidence items and correctly flags all hard-math failures. The cheap model
genuinely "knows what it doesn't know" on this task distribution — at least at
the coarse binary level.

The mechanism: when the cheap model's answer is wrong (e.g., it gave "67" for
a divisibility problem), it evaluates the same wrong answer and consistently
replies "no" to all three verification samples, suggesting the model's internal
representation of the problem is inconsistent enough to trigger self-doubt.

## 4. math items m1, m2, m3, m6 had low verifier confidence despite being correct

These easy math items (17+25, 144/12, sale price, 3x+7=28) produced confidence=0.0
(all three "no" votes) despite the cheap answer being correct. The verifier
underestimates confidence for these — a precision failure (false low-confidence).
If the threshold T were set to escalate ALL low-confidence items (T=1.0), these
would be unnecessarily escalated to the strong model, adding cost with no accuracy
gain.

The actual cascade handles this correctly at T=0.67 because we don't escalate
items with conf=0.0 — wait, we do. T=1.0 means: escalate unless conf >= 1.0.
For T=0.34, items with conf=0.0 are escalated (conf < 0.34). So at T=0.34, all 11
low-confidence items are escalated, including the 5 correct ones (m1, m2, m3, m6,
m11). This is the false-positive escalation tax.

The measured escalation rate at T=0.34 is 26.7% (12/45), which includes 5
correct cheap items being unnecessarily sent to strong. This is waste — the
verifier cannot distinguish "cheap is correct but uncertain" from "cheap is wrong".
