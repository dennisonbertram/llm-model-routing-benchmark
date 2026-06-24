# R-004: AutoMix Self-Verification Cascade

**Category**: recipe
**Evidence tier**: Live verified (POC X4)
**Source POC**: X4-verification-cascade-automix

## Live verified

An AutoMix-style cascade where the cheap model generates AND self-verifies (k=3 independent
YES/NO samples), then escalates to strong when verification confidence falls below threshold T:

- At T=0.34: **acc 0.978, total cost $0.006092 — 71.6% savings vs always-strong ($0.02148)**
- Verifier is **100% precise at the high-confidence end**: all 33 high-confidence items
  (confidence ≥ 0.67) are correct cheap answers. Low-confidence bucket (0.00–0.33): only
  45.5% correct — correctly flags the hard items. (X4)

Honest finding: the verifier overhead ($0.003570 total for 45 items, k=3 calls each) consumes
the oracle headroom. The cascade costs $0.006092 vs oracle $0.002140 — nearly 3× the oracle
— for the same accuracy. A classifier router (R-001) reaches 0.978 accuracy at $0.00257–$0.00291
without paying per-item verification overhead. (X4)

**When AutoMix is useful**: when you have no labeled history to train a classifier and need a
training-free escalation mechanism. Once labeled data accumulates, replace it with R-001.

## Architecture

```
query
  │
  ▼
cheap model generates  →  answer_cheap
  │
  ▼
k=3 independent YES/NO verifier calls (cheap model judges its own answer):
  "Is this answer correct? YES or NO."
  confidence = count("YES") / k
  │
  ├── confidence ≥ T  →  return answer_cheap
  └── confidence < T  →  escalate to strong model  →  return answer_strong
```

## Snippet (copy-paste-ready)

```python
from providers import chat

def automix_cascade(
    prompt: str,
    cheap_model:  str = "gpt-4o-mini",
    strong_model: str = "gpt-4.1",
    k: int = 3,
    threshold: float = 0.34,
    cache=None,
) -> dict:
    """
    AutoMix: cheap generates → cheap self-verifies (k samples) → escalate if uncertain.
    cache: optional Cache instance to avoid re-billing identical calls
    """
    call = cache.chat if cache else chat

    # 1. Cheap generates
    gen = call(cheap_model, [{"role": "user", "content": prompt}],
               temperature=0.0)
    answer_cheap = gen.text
    total_usd    = gen.usd

    # 2. k-sample self-verification
    verify_prompt = (
        f"Question: {prompt}\n\nProposed answer: {answer_cheap}\n\n"
        f"Is this answer correct? Reply with YES or NO only."
    )
    yes_count = 0
    for i in range(k):
        vr = call(cheap_model, [{"role": "user", "content": verify_prompt}],
                  temperature=0.7, nonce=f"verify_{i}")
        total_usd += vr.usd
        if vr.text.strip().upper().startswith("YES"):
            yes_count += 1
    confidence = yes_count / k

    # 3. Escalate if uncertain
    if confidence < threshold:
        strong = call(strong_model, [{"role": "user", "content": prompt}],
                      temperature=0.0)
        return {
            "answer":     strong.text,
            "confidence": confidence,
            "escalated":  True,
            "usd":        total_usd + strong.usd,
        }
    return {
        "answer":     answer_cheap,
        "confidence": confidence,
        "escalated":  False,
        "usd":        total_usd,
    }
```

## Threshold sweep (live, X4)

Live verified: On the 45-task benchmark, verifier confidence is nearly binary — almost all
scores land at 0.0 or 1.0. The cascade converges cleanly at any T between 0 and 0.34.

| T    | acc   | total cost  | escalation rate | notes |
|------|-------|-------------|-----------------|-------|
| 0.00 | 0.844 | $0.005232   | 0%              | accept all cheap (verifier still runs) |
| 0.34 | 0.978 | $0.006092   | 26.7%           | matches strong accuracy |
| 0.67 | 0.978 | $0.006092   | 26.7%           | identical (binary verifier) |
| 1.00 | 0.978 | $0.006092   | 26.7%           | identical |

Note: T=0.34, 0.67, 1.00 produce identical results because only one item (m14) has
fractional confidence (0.33), and it falls below all three thresholds. (X4)

## Verifier calibration (live, X4)

| Confidence bucket | n items | Cheap-correct rate |
|-------------------|---------|--------------------|
| 0.00–0.33 (low)   | 11      | 45.5%              |
| 0.34–0.66 (mid)   | 1       | 0.0%               |
| **0.67–1.00 (high)** | **33** | **100%**        |

High precision at the high end means: if the verifier is confident, accept the cheap answer.
The verifier signal is real, not noise.

## Live confirmation trace (item m9, X4)

```
item m9: "Find integers 1–100 divisible by 3 or 5"
cheap answer: '67'  (wrong; correct is 47)
verifier votes: [0, 0, 0]   confidence=0.00   verifier_usd=$5.49e-05
threshold=0.67: escalate=True
strong answer: '47'  cost=$7.80e-05  correct: True
```

## Cost comparison vs alternatives (X4, L2b, capstone)

| Router                   | Accuracy | Cost       | notes |
|--------------------------|----------|------------|-------|
| always-cheap             | 0.844    | $0.00166   |       |
| always-strong            | 0.978    | $0.02148   |       |
| oracle (unrealizable)    | 0.978    | $0.00214   |       |
| **AutoMix T=0.34**       | **0.978** | **$0.00609** | 2.85× oracle |
| logistic router (τ=0.9) | 0.978    | $0.00291   | from X5; no verifier overhead |
| capstone (τ=0.8)         | 0.978    | $0.00257   | from capstone CV |

AutoMix wins over always-strong (71.6% savings) but loses to a trained classifier on cost.

## Evidence

- X4-verification-cascade-automix/README.md — full results, calibration table, live trace
- results-digest.md line 41 — authoritative numbers (0.978 at 71.6% savings, 2.85× oracle)
