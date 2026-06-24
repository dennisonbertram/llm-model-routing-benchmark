# A-002: Trusting Self-Reported Confidence — Using the Generator's Own Confidence to Gate Escalation

**Category**: anti-pattern
**Severity**: critical — the gate fails on exactly the items that need escalation
**Evidence tier**: Live verified
**Source POC**: L3a-frugalgpt-cascade

---

## What the anti-pattern looks like

Live verified. Prompting the cheap model to rate its own answer (0–1 confidence score),
then escalating to strong only when confidence falls below a threshold. This is the
naive FrugalGPT-style implementation when the verifier is not independently trained.

Measured result on 45-task harness (2026-06-21):

| Strategy | Accuracy | Cost | Escalation rate |
|---|---|---|---|
| always-cheap | 0.844 | $0.00166 | — |
| cascade thr=0.1 | 0.844 | $0.00391 | 9% |
| cascade thr=0.3 | 0.844 | $0.00391 | 9% |
| cascade thr=0.5 | 0.844 | $0.00391 | 9% |
| cascade thr=0.7 | 0.844 | $0.00391 | 9% |
| cascade thr=0.9 | 0.844 | $0.00391 | 9% |
| always-strong | 0.978 | $0.02148 | 100% |

All five threshold sweeps produce **identical results**. The cascade matches
always-cheap accuracy (0.844) at 2.4× its cost due to gate call overhead — strictly
dominated by both baselines on the Pareto plane.

---

## Root cause

`gpt-4o-mini` returned confidence=0.9 for every hard-math answer it got wrong:

| Item | Cheap answer | Correct answer | Confidence reported |
|---|---|---|---|
| m9 | "67" | 47 | 0.9 |
| m10 | "13" | 16 | 0.9 |
| m12 | "26" | 28 | 0.9 |
| m13 | "28" | 35 | 0.9 |
| m14 | "292." | 242 | 0.9 |
| m15 | "420" | 1260 | 0.9 |

Every item that needed escalation reported maximum confidence. No threshold sweep can
distinguish them from correct answers — the gate is non-discriminative on the tail that
matters most. This is a known property of LLMs: they are poorly calibrated
(overconfident) precisely in domains where their knowledge or reasoning is weakest.

False accept rate: 6/27 = 22% on math/QA tasks (the 6 items where cheap is wrong).

---

## Why the coding verifier works

The per-discipline breakdown reveals a different story for coding (L3a):

| Discipline | Accuracy | Escalated | Cost |
|---|---|---|---|
| coding | 18/18 | 1/18 | $0.00315 |
| math | 8/15 | 3/15 | $0.00054 |
| qa | 12/12 | 0/12 | $0.00022 |

Coding achieves 100% accuracy with 0 false accepts and 1 false escalation. Why?
Because the coding verifier asks "YES/NO: is this code correct?" — a structural
question that can be answered by inspection, not by introspection about the model's
own knowledge. The model can evaluate syntax, obvious logic errors, and output format
without self-knowledge of its reasoning quality.

This distinction is key: **verification is most reliable when correctness can be
checked structurally or by an independent process**, not when it requires the generator
to self-assess its epistemic state.

---

## Fix

**Live verified** (L3a; X4; capstone)

Use an independent verifier, not a self-assessor:

1. **Run the produced code against unit tests** (L3b) — this is always correct and
   never overconfident. Test execution is the gold standard for coding tasks.

2. **Use a trained binary classifier** (L2b) — logistic regression trained on labeled
   examples predicts P(cheap_correct) from embedding features. This is an external model
   and not subject to the generator's overconfidence.

3. **Use k independent verifier calls** (X4, AutoMix-style) — asking the same model
   multiple times with temperature > 0 provides a weak confidence signal (unanimous
   "no" from 3 calls does flag hard-math errors correctly in X4). This is better than
   a single self-confidence score but adds overhead (see A-004 on AutoMix cost).

4. **Use structural signals** (numeric extraction, cross-check with a lookup, format
   validation) where the domain permits.

If you need a cascade before labels are available, use AutoMix (X4) over naive
self-confidence. Once labels are available, use the classifier (L2b / X5 logistic).

---

## Evidence

- L3a README.md: "gpt-4o-mini returns 0.9 confidence for all six hard-math answers it gets wrong... Sweeping threshold from 0.1 to 0.9 cannot distinguish any of them." (Live verified)
- L3a README.md, Confidence probe table: all six hard-math wrong items return conf=0.9. (Live verified)
- L3a README.md: "cascade acc=0.844 at $0.00391 — same accuracy as always-cheap, 2.4× higher cost." (Live verified)
- results-digest.md, Gotcha 6: "FrugalGPT self-confidence gating fails when the cheap model is overconfident-and-wrong → use an independent verifier or run code tests, not self-reported confidence." (Live verified)
- results-digest.md, L3a headline: "FrugalGPT cascade: 0.844 (== cheap) at $0.00391, 2.4× cheap cost, NO accuracy gain — self-confidence gate non-discriminative." (Live verified)
