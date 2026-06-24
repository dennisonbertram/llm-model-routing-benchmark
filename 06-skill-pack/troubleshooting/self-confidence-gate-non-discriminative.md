# Troubleshooting: Self-Confidence Gate Returns 0.9 for Wrong Answers

Live verified (L3a; 2026-06-21). FrugalGPT-style self-confidence gating fails when
the cheap model is overconfident on its failure modes.

Back to [index](../index.md).

---

## Symptom

- All threshold values (0.1, 0.3, 0.5, 0.7, 0.9) produce identical cascade results.
- The cascade accuracy equals always-cheap, despite having a threshold sweep.
- The cascade costs 2.4x more than bare cheap (due to gate call overhead) with no benefit.

---

## Root cause

Live verified (L3a). gpt-4o-mini returned `confidence=0.9` for ALL SIX hard-math answers
it got wrong:

```
m9  (answer "67",  correct=47): conf=0.9
m10 (answer "13",  correct=16): conf=0.9
m12 (answer "26",  correct=28): conf=0.9
m13 (answer "28",  correct=35): conf=0.9
m14 (answer "292.",correct=242): conf=0.9
m15 (answer "420", correct=1260): conf=0.9
```

The gate is completely non-discriminative for the items that most need escalation.
This is a documented LLM property: models tend to be overconfident on categories
where they have systematic gaps, not just where they are uncertain.

The cascade at all thresholds: `acc=0.844, $0.00391` — same accuracy as always-cheap at
2.4x the cost (gate call overhead). A strictly dominated result.

---

## The fix: use an independent verifier

Self-confidence fails because you are asking the answer-generating model to evaluate its
own answer. Use an INDEPENDENT verification signal instead:

**Option 1: Code test execution (live-verified success — L3b)**
Run the produced code against hidden unit tests. Tests either pass or fail — no confidence
score, no calibration issues. Live result: 18/18 coding tasks, 0 false accepts, 1 unnecessary
escalation.

```python
def verify_code(code: str, grade_fn) -> bool:
    return bool(grade_fn(code))
```

**Option 2: Numeric extraction cross-check**
For math problems with a numeric gold answer, extract the number from the cheap model's
response and check it against a known range or a fast-path calculation. If the cheap model
returns a clearly implausible number, escalate.

**Option 3: Trained binary verifier**
Train a separate small classifier that predicts "is this answer correct?" using the prompt,
the answer, and features about the domain — but NOT using the generating model's own
confidence output.

**Option 4: Second independent model**
Ask a different model (not the generator) to judge the answer. A second model is more
reliable as a verifier than the generator evaluating itself.

---

## What the coding verifier (YES/NO judge) showed (L3a)

Live verified. Asking the cheap model "YES/NO: is this code correct?" (after generating it)
worked substantially better than self-confidence scoring on confidence 0–1:

| Metric | YES/NO judge | Confidence 0–1 |
|--------|-------------|----------------|
| False accepts (wrong code accepted) | 0 | 6 (hard math) |
| Unnecessary escalations | 1 | 3 (plus 6 false accepts) |
| Coding accuracy | 18/18 | 18/18 (different mechanism) |

The binary YES/NO question produces better calibration than an open-ended confidence score.
Still, for coding tasks, test execution is the gold standard.

---

## Key principle

> The verifier must be more reliable than the generator. Self-confidence fails when the
> cheap model is overconfident-and-wrong. A second model asked a binary question is better
> than self-reporting a continuous score. Structural verification (test execution) is best.

---

## Source

`03-pocs/L3a-frugalgpt-cascade/README.md`
`03-pocs/L3a-frugalgpt-cascade/evidence.md`
`.context/results-digest.md` Gotcha #6
