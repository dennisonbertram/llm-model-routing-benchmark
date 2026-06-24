# R-003: FrugalGPT Cascade — and Why Self-Confidence Gating Fails

**Category**: recipe
**Evidence tier**: Live verified (POC L3a)
**Source POC**: L3a-frugalgpt-cascade

## Live verified — the failure mode

Live verified: A FrugalGPT cheap→strong cascade with a **self-confidence gate** (ask the cheap
model to score its own answer 0–1 and escalate below a threshold) produced **acc 0.844, $0.00391
— identical to always-cheap accuracy at 2.4× its cost, with zero accuracy gain**. (L3a)

The gate is completely non-discriminative for the items that most need escalation. gpt-4o-mini
returns confidence=0.9 for ALL SIX hard-math items it answers incorrectly (m9, m10, m12, m13,
m14, m15). The threshold parameter is irrelevant: sweeping from 0.1 to 0.9 produces identical
results — acc 0.844, cost $0.00391, 9% escalation rate — because the hard items are never
escalated. (L3a)

Confidence probe (live values from L3a):

| Item | Cheap answer | Gold | Confidence returned |
|------|-------------|------|---------------------|
| m9   | 67          | 47   | 0.9                 |
| m10  | 13          | 16   | 0.9                 |
| m12  | 26          | 28   | 0.9                 |
| m13  | 28          | 35   | 0.9                 |
| m14  | 292.        | 242  | 0.9                 |
| m15  | 420         | 1260 | 0.9                 |

**This is the FrugalGPT failure mode**: "the verifier must be more reliable than the
generator." When the cheap model is overconfident on its mistakes, self-confidence gating
collapses to a fixed escalation rate the threshold cannot tune. (L3a)

## Live verified — the coding verifier THAT DID work

Live verified: Replacing the self-confidence gate with an **independent code-correctness
verifier** (ask the cheap model "YES/NO: is this code correct?") on the 18 coding tasks:
**18/18 correct, only 1 unnecessary escalation, 0 false accepts**. (L3a)

Per-discipline breakdown:

| Discipline | Accuracy | Escalated | Cost     |
|------------|----------|-----------|----------|
| coding     | 18/18    | 1/18      | $0.00315 |
| math       | 8/15     | 3/15      | $0.00054 |
| qa         | 12/12    | 0/12      | $0.00022 |

The coding verifier works because code has **structural correctness signals** a model can
assess without executing it (syntax, obvious logic errors). The self-confidence path on
math has no such signal — the model cannot tell it computed a combinatorics answer wrong.

## The cascade in code (generic cheap→gate→strong pattern)

```python
def frugalgpt_cascade(
    prompt: str,
    cheap_model: str,
    strong_model: str,
    discipline: str,           # "coding" or "math"/"qa"
    escalation_threshold: float = 0.7,
    cache=None,
) -> dict:
    """
    Cheap generates → gate assesses → escalate to strong if gate fails.
    WARN: self-confidence gate fails for math/qa (see above).
    For coding, use the YES/NO code-correctness verifier instead.
    """
    call = cache.chat if cache else chat

    # 1. Cheap generates
    cheap_result = call(cheap_model, [{"role": "user", "content": prompt}])
    answer = cheap_result.text

    # 2. Gate
    if discipline == "coding":
        # independent verifier: ask cheap to judge the code, not itself
        gate_prompt = (
            f"Is the following Python code correct and complete? "
            f"Answer YES or NO only.\n\n```python\n{answer}\n```"
        )
        gate_result = call(cheap_model, [{"role": "user", "content": gate_prompt}])
        gate_ok = gate_result.text.strip().upper().startswith("YES")
        confidence = 1.0 if gate_ok else 0.0
    else:
        # self-confidence gate — NOTE: fails on hard math (see warning above)
        gate_prompt = (
            f"How confident are you in this answer? Rate 0.0 (not sure) to 1.0 (certain)."
            f"\n\nQuestion: {prompt}\nAnswer: {answer}\n\nRespond with only a decimal."
        )
        gate_result = call(cheap_model, [{"role": "user", "content": gate_prompt}])
        try:
            confidence = float(gate_result.text.strip())
        except ValueError:
            confidence = 0.5

    total_usd = cheap_result.usd + gate_result.usd

    # 3. Escalate if needed
    if confidence < escalation_threshold:
        strong_result = call(strong_model, [{"role": "user", "content": prompt}])
        answer    = strong_result.text
        total_usd += strong_result.usd
        escalated  = True
    else:
        escalated = False

    return {
        "answer":     answer,
        "confidence": confidence,
        "escalated":  escalated,
        "usd":        total_usd,
    }
```

## What a real FrugalGPT system requires

1. **A trained verifier, not prompted self-assessment.** A second model or a purpose-trained
   binary classifier is far more reliable than asking the generator to rate its own answer.
2. **Structural signals for the verifier.** Code execution, numeric extraction + cross-check,
   or knowledge-base lookup. Pure self-reported confidence from the same model adds cost without
   discrimination. (L3a)
3. **Or use a classifier router** (R-001). Once a labeled history exists, a logistic classifier
   delivers oracle-level accuracy at far lower cost than any cascade with per-item gate calls.

## Cost structure

| Strategy         | Acc   | Cost ($)  | vs always-cheap | Notes |
|------------------|-------|-----------|-----------------|-------|
| always-cheap     | 0.844 | 0.00166   | 1.0×            |       |
| cascade thr=0.1–0.9 | 0.844 | 0.00391 | 2.4×          | all thresholds identical (L3a) |
| oracle           | 0.978 | 0.00214   | 1.3×            | unrealizable ceiling (L0) |
| always-strong    | 0.978 | 0.02148   | 12.9×           |       |

The cascade dominates neither always-cheap (higher cost) nor always-strong (lower accuracy).

## Evidence

- L3a-frugalgpt-cascade/README.md — full results table, confidence probe, per-discipline breakdown
- L3a-frugalgpt-cascade/evidence.md — gate error analysis, false-accept count
- results-digest.md lines 35–36 — authoritative numbers
