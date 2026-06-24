# X4 — AutoMix-Style Verification Cascade

**Evidence: Live verified (2026-06-21).** Status: Complete with live evidence.

## What this proves

An AutoMix-style cascade where `gpt-4o-mini` (cheap) generates an answer, then
self-verifies it via k=3 independent "is this correct? yes/no" samples. The fraction
of 'yes' responses is the cheap model's confidence. If confidence < threshold T,
escalate to `gpt-4.1` (strong); otherwise accept the cheap answer.

Key findings — all from real, executed API calls:

1. **At T=0.34, the cascade matches strong-model accuracy (0.9778) at 28.4% of strong cost.**
   It correctly escalates 12 of 45 items (26.7%) and gets them right via `gpt-4.1`.
2. **The verifier is perfectly calibrated at the upper end**: all 33 high-confidence items
   (conf >= 0.67) are correct cheap answers — 100% precision. Low confidence (0.0–0.33)
   has only 45.5% correct — it correctly flags the hard items.
3. **The verifier overhead makes this worse than the oracle and comparable classifiers.**
   The cascade costs $0.006092 vs oracle $0.002140. The verifier adds k=3 calls per item
   ($0.003570 overhead for all 45), consuming the oracle gap completely. AutoMix is not
   a free lunch.
4. **Verifier confidence is nearly binary on this suite.** Almost all confidence scores
   land at 0.0 or 1.0 — the math items where cheap is wrong produce unanimous "no" votes,
   and the items cheap gets right produce unanimous "yes". The cascade converges cleanly
   with T as low as 0.34 (one "yes" out of three is enough).

## Live verified results table

| Router | Accuracy | Total cost (45 items) | vs cheap | Escalation rate |
|---|---|---|---|---|
| always-cheap (gpt-4o-mini) | 0.8444 | $0.001660 | 1.0x | 0% |
| always-strong (gpt-4.1) | 0.9778 | $0.021480 | 12.9x | 100% |
| **oracle** (cheapest-correct) | **0.9778** | **$0.002140** | **1.3x** | **13.3%** |
| AutoMix T=0.00 (accept all cheap) | 0.8444 | $0.005232 | 3.2x | 0% |
| AutoMix T=0.34 | **0.9778** | $0.006092 | 3.7x | 26.7% |
| AutoMix T=0.67 | **0.9778** | $0.006092 | 3.7x | 26.7% |
| AutoMix T=1.00 (escalate all) | **0.9778** | $0.006092 | 3.7x | 26.7% |

Note: T=0.34, 0.67, and 1.00 produce identical results because verifier confidence is nearly
binary — there is only one item (m14) with a fractional score (0.33), and it falls below all
three thresholds. The cost includes k=3 verifier calls per item ($0.003570 total verifier overhead).

## Verifier calibration (Live verified)

| Confidence bucket | n items | Cheap-correct rate |
|---|---|---|
| low (0.00–0.33) — "uncertain" | 11 | **45.5%** |
| mid (0.34–0.66) — "split votes" | 1 | 0.0% |
| high (0.67–1.00) — "confident" | 33 | **100%** |

The verifier signal is clean: high confidence means correct (100% precision), low confidence
flags uncertain items (but 55% of low-confidence items ARE wrong — reasonable recall). The
calibration curve validates that self-verification captures meaningful signal, not noise.

## Honest finding: AutoMix loses to the oracle and to classifiers on this suite

The oracle costs $0.002140 to achieve 0.9778 accuracy. The AutoMix cascade costs $0.006092 —
nearly 3x the oracle — for the same accuracy. The verifier overhead dominates.

This is consistent with the AutoMix paper's finding (Madaan et al., 2023): self-verification
via the cheap model is informative but adds non-trivial cost. The gain is most visible when
you compare against always-strong ($0.021480), where the cascade saves 71.6%. But routing
methods that do not pay per-item verification overhead (heuristic, embedding kNN, classifier)
will likely land closer to the oracle and be more cost-efficient.

A practical deployment implication: AutoMix-style verification is most valuable when you
cannot build a classifier (no labeled history), as the verifier provides signal without any
training phase. Once labeled data is available, a classifier router (L2b) will dominate it
on cost.

## Live confirmation trace (item m9)

```
item: m9 — "Find the number of integers from 1 to 100 inclusive that are divisible by 3 or 5"
cheap answer: '67'  (wrong — answer is 47)
verifier votes: [0, 0, 0]  confidence=0.00  verifier_usd=$5.49e-05
threshold=0.67: escalate=True
strong answer: '47'  cost=$7.80e-05  correct: True
```

The verifier correctly identified the cheap answer as wrong (unanimous "no"), triggering
escalation to strong. The strong model returned the correct answer (47).

## What the threshold sweep means

The threshold T controls the POMDP-lite cost-quality knob. Setting T=0 (never escalate) gives
cheap accuracy at cheap+verifier cost. Setting T>0 (escalate uncertain items) recovers strong
accuracy at cascaded cost. On this suite the knob has a clean binary transition at any T
between 0 and 0.34 — reflecting that the verifier signal is nearly deterministic.

In a real deployment over a more diverse query distribution (mixed difficulty, noisy verifier),
the threshold would trace a smoother Pareto curve with intermediate operating points.

## Run it

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd source
python3 run_x4.py            # full cascade sweep + calibration; writes x4_summary.json
python3 -m unittest test_x4  # 4 live behavioral tests (GREEN with keys)
```

RED (no keys): `ProviderError: Missing env var OPENAI_API_KEY` on the first live
strong-model call in the live confirmation step.
