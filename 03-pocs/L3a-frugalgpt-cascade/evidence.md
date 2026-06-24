# Evidence — L3a FrugalGPT Cascade

Evidence tier: **Live verified**

## Live evidence

All numbers below come from real API calls executed 2026-06-21. Cascade gate calls (52
unique entries) are in `source/.cache.json`. Primary answers reuse `harness/.cache/labelset.json`
without re-billing.

### Gate call evidence

- Confidence gate: 27 math/QA items each received one confidence-rating call to gpt-4o-mini.
  Response format: a float string ("0.9", "1.0", "0.0"). Cached; re-runs are free.
- Coding verifier: 18 coding items each received one YES/NO verifier call to gpt-4o-mini.
  One returned "NO" (c13 — regex matching task), all others "YES".
- Escalated strong calls: 4 items were escalated (m1, m3, m8, and one coding). Each generated
  a fresh gpt-4.1 response; costs are measured from token counts × price table.

### Gate error observations

- gpt-4o-mini returns 0.9 confidence for all 6 hard-math items it answers incorrectly (m9,
  m10, m12, m13, m14, m15). Threshold sweep 0.1–0.9 produces identical results because no
  threshold can separate 0.9 (wrong answer) from 0.9 (right answer) for hard math.
- gpt-4o-mini returns 0.0 confidence for m1 (17+25=42, correct) and m3 ($15 sale price,
  correct) — false escalations on easy items it answers correctly.
- Coding verifier false-accepts: 0 (verifier is accurate on coding tasks in this suite).
- Coding verifier false escalations: 1 (c13 escalated, strong also correct — correct outcome
  but wasted a strong call).

### Test results

```
7 passed, 1 skipped (summary JSON test skipped until first run completes)
```

All live behavioral assertions pass: gate returns float in [0,1], verifier returns bool,
cascade costs less than always-strong, high-threshold escalates more than low-threshold.

## Provider evidence

- gpt-4o-mini: primary cheap model. Confidence gate: ~63–100 prompt tokens, 3 completion
  tokens per gate call. Verifier: ~108–407 prompt tokens, 1 completion token per call.
  Gate overhead cost: ~$0.00001–0.00003 per item.
- gpt-4.1: strong model. Escalation calls cost ~$0.0001–0.0010 per item depending on output
  length.

## Citations

FrugalGPT paper (not reproduced verbatim here, original methodology used as design guide):
Chen, Lingjiao, Matei Zaharia, and James Zou. "FrugalGPT: How to use large language models
while reducing cost and improving performance." arXiv:2305.05176 (2023).
Cited pattern: "the verifier must be more reliable than the generator."
