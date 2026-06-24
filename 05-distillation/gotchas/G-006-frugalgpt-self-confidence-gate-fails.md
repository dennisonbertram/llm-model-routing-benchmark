# G-006: FrugalGPT self-confidence gating fails — cheap models are overconfident when wrong

**Category**: gotcha
**Severity**: high
**Evidence tier**: Live verified
**Source POC**: L3a-frugalgpt-cascade

## What

Live verified. In the L3a FrugalGPT cascade, `gpt-4o-mini` returned a self-reported confidence of 0.9 for all 6 hard-math items it answered incorrectly. No threshold in the sweep [0.1, 0.3, 0.5, 0.7, 0.9] triggered escalation for those items, because 0.9 >= any threshold ≤ 0.9. The entire threshold sweep was flat: all five thresholds produced identical accuracy (0.844) and identical cost ($0.00391).

Worse, the calibration was inverted: the model returned confidence 0.0 for two easy, correct answers (m1: 17+25=42; m3: 25% off $20 = $15) — it was most conservative on items that needed no escalation and most permissive on items that needed escalation most.

Result: the FrugalGPT cascade achieved exactly the same accuracy as always-cheap, at 2.4× the cost due to gate call overhead.

## Why it matters

Self-reported confidence is a commonly cited technique for cascade routing. This experiment shows it fails on hard-math tasks: the cheap model reliably reports high confidence even when its answer is wrong. A router that relies on this gate will incur the overhead of gate calls while achieving zero escalation benefit on the task distribution that matters most.

## Root cause

LLMs are known to be poorly calibrated on tasks that require multi-step reasoning. For tasks where the model follows a plausible-but-wrong reasoning chain (e.g., a hard combinatorics problem), it reaches a definite answer and reports high confidence. The confidence self-report reflects the model's certainty about its (wrong) reasoning path, not the correctness of the answer.

## Fix

Do not use self-reported LLM confidence as the escalation gate in a cascade router. Use one of these alternatives instead:

1. **Independent verifier with structural check**: For coding tasks, run the produced code against test cases. This achieved 18/18 correct classifications in L3b with 0 false accepts (Live verified).
2. **Trained classifier on embeddings**: Use a logistic regression or k-NN over the query embedding to predict cheap-model correctness before generating the answer. This achieves oracle-level accuracy without per-call gate overhead (L2b, capstone).
3. **Consistency-based escalation**: Sample 3 cheap responses at temperature > 0 and escalate only if they disagree (X4 AutoMix verifier). More expensive than a pre-call classifier but does not rely on self-reported confidence.

If self-consistency is used (X4 style), the cheap model's answers must actually vary — verify this by checking entropy across samples before deploying.

## Regression note

If a FrugalGPT-style gate is added to any router, include a benchmark check that the gate triggers escalation on at least one hard item in the test suite. If it never escalates, the gate has no discriminative power and is pure overhead.

## Evidence

- Source: `03-pocs/L3a-frugalgpt-cascade/surprises.md`, Surprise 1: "All five thresholds (0.1, 0.3, 0.5, 0.7, 0.9) produce identical accuracy (0.844) and identical cost ($0.00391). The reason: gpt-4o-mini returns 0.9 for all six hard-math items it gets wrong." (Live verified)
- Source: `03-pocs/L3a-frugalgpt-cascade/surprises.md`, Surprise 2: "The model returns 0.9 for all wrong hard-math answers, but returns 0.0 for two easy, correct math answers (m1: 17+25=42; m3: 25% off $20 = $15). The calibration is inverted." (Live verified)
- Source: results-digest.md, L3a: "0.844 (== cheap) at $0.00391, 2.4× cheap cost, NO accuracy gain — self-confidence gate non-discriminative (cheap reports 0.9 confidence even when wrong). HONEST FAILURE." (Live verified)
- Source: results-digest.md, Gotchas item 6: "FrugalGPT self-confidence gating fails when the cheap model is overconfident-and-wrong → use an independent verifier or run code tests, not self-reported confidence." (Live verified)
