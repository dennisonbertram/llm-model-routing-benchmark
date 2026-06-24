# Lesson: Cascade Routing (FrugalGPT / AutoMix)

Live verified (L3a; L3b; X4; 2026-06-21). Cheap-first cascades with verification gates.

Back to [index](../index.md).

---

## What it is

A cascade router calls a cheap model first, then applies a verification gate. If the
cheap model's answer passes the gate, return it. If not, escalate to a strong model.

Two major variants:
- **Self-confidence gate (FrugalGPT)**: ask the cheap model to rate its own confidence (0–1).
- **Independent verifier**: run the answer through a separate check (code tests, a trained
  judge, a second model) before deciding to escalate.

---

## FrugalGPT self-confidence gate: FAILURE (L3a)

Live verified. From `03-pocs/L3a-frugalgpt-cascade/README.md`.

The self-confidence gate fails on exactly the items that need escalation:

| Failure | Detail |
|---------|--------|
| gpt-4o-mini confidence for ALL 6 wrong hard-math answers | 0.9 (overconfident-and-wrong) |
| Threshold sweep 0.1–0.9 | Identical results: acc=0.844 at $0.00391 |
| Net outcome | acc=0.844 (== always-cheap), $0.00391 (2.4x cheap cost) |

The cascade costs 2.4x more than bare cheap while providing no accuracy improvement.
The gate is completely non-discriminative for the items that matter most.

**Root cause:** When the cheap model is overconfident on a category it consistently fails,
the confidence score is useless as a threshold signal. The FrugalGPT paper notes that
"the verifier must be more reliable than the generator."

---

## Coding verifier (independent judge): SUCCESS (L3a)

Live verified. From `03-pocs/L3a-frugalgpt-cascade/README.md`.

A cheap-LLM-judge verifier ("YES/NO: is this code correct?") applied to coding tasks:

| Metric | Result |
|--------|--------|
| Coding accuracy | 18/18 (100%) |
| Unnecessary escalations | 1/18 |
| False accepts (wrong code accepted) | 0 |

The independent verifier works where self-confidence fails. The difference: a second model
evaluating the answer is more reliable than the answer-generating model evaluating itself.

---

## opencode escalation loop: SUCCESS (L3b)

Live verified. From `03-pocs/L3b-harness-routing-coding-agent/README.md`.

A multi-step loop: cheap writes code → run unit tests → escalate to strong on test failure.
This uses structural verification (test execution) rather than model self-report.

| Harness | accuracy | cost (18 tasks) | escalations |
|---------|----------|-----------------|-------------|
| all-cheap | 1.000 | $0.00148 | 0 |
| **routed (cheap-first)** | **1.000** | **$0.00148** | **0** |
| all-strong | 1.000 | $0.01967 | 0 |

Zero escalations because gpt-4o-mini solves all 18 coding tasks at temp=0. The repair
path was confirmed working via a synthetic deliberately-broken test.

The routed harness equals all-cheap cost (7.5% of all-strong) because the discipline
matters: coding saturates cheap; math does not. The escalation guard adds no overhead
when cheap is already sufficient.

---

## AutoMix (X4): partial success with caveats

Live verified. From `03-pocs/X4-verification-cascade-automix/README.md`.

AutoMix-style: cheap generates → cheap self-verifies → escalate to strong on low confidence.

| AutoMix (k=3 self-verify) | accuracy | savings vs always-strong | vs oracle |
|---------------------------|----------|--------------------------|-----------|
| 0.978 | 71.6% cheaper than strong | 2.85x oracle cost |

AutoMix achieves strong accuracy at 71.6% savings — impressive. However, the verifier
overhead eats 2.85x the oracle cost. The logistic classifier (capstone) reaches 71% cheap
routing with much lower overhead (1.20x oracle). The verifier was 100% precise on the
high-confidence bucket — a genuine positive finding.

---

## When cascade routing works

- **Independent structural verifier available**: code test execution, numeric extraction +
  cross-check, or a separate judge model — not self-reported confidence.
- **Escalation is rare**: when cheap already handles 80%+ of traffic correctly, the cascade
  overhead is small relative to the savings on the escalated minority.
- **Verifier is cheaper than strong model**: if the verifier call costs as much as just
  using strong directly, the cascade has no advantage.

## When cascade routing fails

- **Cheap model is overconfident on failure modes**: self-confidence returns 0.9 on wrong
  answers across all thresholds — the gate cannot discriminate.
- **Verifier adds substantial token cost**: AutoMix's verifier overhead made it 2.85x the
  oracle cost even though accuracy was matched.
- **Workload is already saturated at cheap tier**: if cheap is 100% accurate, a cascade just
  adds overhead without saving money (L3b: 0 escalations on coding).

---

## The key rule (from L3a)

> The verifier must be more reliable than the generator. Self-confidence gating fails
> when the cheap model is overconfident-and-wrong. Use structural verification (test
> execution, a trained classifier, a second independent model) instead.

---

## Recipe

[recipes/R-003-cascade-with-verifier.md](../recipes/R-003-cascade-with-verifier.md)

## POC sources

- `../03-pocs/L3a-frugalgpt-cascade/`
- `../03-pocs/L3b-harness-routing-coding-agent/`
- `../03-pocs/X4-verification-cascade-automix/`
