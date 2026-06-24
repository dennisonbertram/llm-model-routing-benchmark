# Evidence

**Live verified (2026-06-21).** All numbers below come from real API calls.

## API calls made

- 135 new live calls for the verifier (k=3 per item, 45 items = 135 calls) at temperature=0.8.
  These are the novel behavior. All cached in `source/.cache.json` after first run.
- 1 live call to `gpt-4.1` (strong) for the live confirmation trace of item m9.
- Answer calls for cheap/strong models reuse `harness/.cache/labelset.json` — no re-billing.

## Verifier live confirmation (item m9)

```
item: m9 — "Find the number of integers from 1 to 100 inclusive that are divisible by 3 or 5"
cheap answer: '67'  (cached=True from harness)
cheap correct: False
verifier votes: [0, 0, 0]  confidence=0.00  verifier_usd=$5.49e-05
threshold=0.67: escalate=True
strong answer: '47'  cost=$7.80e-05
strong correct: True
```

Provider: OpenAI. Model: gpt-4o-mini (verifier), gpt-4.1 (escalation).

## Calibration evidence

| Confidence bucket | n | Cheap-correct rate |
|---|---|---|
| low (0.0–0.33) | 11 | 0.455 |
| mid (0.34–0.66) | 1 | 0.000 |
| high (0.67–1.00) | 33 | 1.000 |

Source: live verifier votes over all 45 items, recorded in `source/x4_summary.json`.

## Cost evidence

- AutoMix T=0.67: acc=0.9778, cost=$0.006092 (live-measured, 45 items).
- Verifier overhead: 135 calls × ~$2.64e-05/call ≈ $0.003570 total verifier cost.
- Answer cost at T=0.67: $0.006092 - $0.003570 ≈ $0.002522 (cheap + escalated strong).

## Baseline cross-reference

Baseline numbers (always-cheap, always-strong, oracle) sourced from L0 live run
(`L0-smoke-and-harness/source/l0_summary.json`) — not re-measured here.

## Test run output

4/4 behavioral tests pass. See `source/green-output.txt` for full run output.
