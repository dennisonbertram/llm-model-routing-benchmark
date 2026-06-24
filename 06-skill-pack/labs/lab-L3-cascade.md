# Lab: L3 — Cascade Routing

Live verified (L3a; L3b; 2026-06-21). FrugalGPT self-confidence failure and opencode escalation success.

Back to [index](../index.md).

---

## Goal

Measure the self-confidence gate on math/QA (observe the failure) and the test-execution
escalation loop on coding (observe the success). Understand which verification approaches work.

---

## Commands: L3a FrugalGPT

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd model-routing/degrees/01-llm-model-routing/03-pocs/L3a-frugalgpt-cascade/source

python3 -m pytest test_l3a.py -v    # GREEN: 7 tests pass, 1 skipped
python3 run_l3a.py                   # prints threshold sweep + confidence probe
```

Expected output (all thresholds identical — the failure):
```
cascade thr=0.1: acc=0.844  $0.00391
cascade thr=0.5: acc=0.844  $0.00391
cascade thr=0.9: acc=0.844  $0.00391
```

Confidence probe for hard math items:
```
m9 (wrong answer "67"): conf=0.9
m10 (wrong answer "13"): conf=0.9
m12 (wrong answer "26"): conf=0.9
...all six: conf=0.9
```

---

## Commands: L3b opencode escalation

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/L3b-harness-routing-coding-agent/source
python3 run_l3b.py
```

Expected output (live-measured):
```
routed harness: acc=1.000  $0.00148  escalations=0
all-cheap:      acc=1.000  $0.00148
all-strong:     acc=1.000  $0.01967
```

---

## What to observe

**L3a failure mode:**
- The self-confidence gate returns 0.9 for every hard-math wrong answer.
- Every threshold from 0.1 to 0.9 produces identical routing decisions.
- The cascade costs 2.4x more than bare cheap (gate call overhead) with no accuracy gain.

**L3b success:**
- Zero escalations on all 18 coding tasks — gpt-4o-mini solves them all at temp=0.
- The repair loop is verified working via a synthetic broken test.
- The key insight: discipline matters more than difficulty label. Coding saturates cheap; math does not.

---

## The lesson

Self-confidence gating fails when the cheap model is overconfident on its failure modes.
Use structural verification (code test execution, a trained classifier, an independent judge)
instead of asking the generating model to evaluate its own answer.

---

## POC sources

- `../03-pocs/L3a-frugalgpt-cascade/`
- `../03-pocs/L3b-harness-routing-coding-agent/`
