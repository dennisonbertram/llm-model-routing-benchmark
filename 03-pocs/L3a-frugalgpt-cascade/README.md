# L3a — FrugalGPT-Style LLM Cascade with Verification Gate

**Evidence tier: Live verified**
**Suite: 45 items (math×15, qa×12, coding×18) — gpt-4o-mini → verification gate → gpt-4.1**

## What this proves

Live verified: A cheap→strong cascade with a self-confidence gate over math/QA and a
cheap-LLM-judge verifier over coding is a real implementation of FrugalGPT-style routing.
It confirms the pattern works in code, makes real API calls, and measures the cascade's
actual cost vs. the baselines.

Live verified: The self-confidence gate (ask cheap to rate its own answer 0–1, escalate
below a threshold) fails on exactly the queries that NEED escalation. gpt-4o-mini returns
0.9 confidence for all six hard-math answers it gets wrong, making the gate useless at any
threshold (0.1–0.9 produce identical results). This overconfidence failure mode is a known
LLM property and is here measured directly, not assumed.

Live verified: The coding verifier (ask cheap "YES/NO: is this code correct?") works much
better — 18/18 correct on coding tasks, only 1 unnecessary escalation, perfect accuracy on
that discipline.

## Results table (Live verified — 2026-06-21)

| Strategy             | Acc   | Cost ($)  | Esc-rate | Cost vs strong |
| -------------------- | ----- | --------- | -------- | -------------- |
| always-cheap         | 0.844 | 0.00166   | —        | 8%             |
| cascade thr=0.1      | 0.844 | 0.00391   | 9%       | 18%            |
| cascade thr=0.3      | 0.844 | 0.00391   | 9%       | 18%            |
| cascade thr=0.5      | 0.844 | 0.00391   | 9%       | 18%            |
| cascade thr=0.7      | 0.844 | 0.00391   | 9%       | 18%            |
| cascade thr=0.9      | 0.844 | 0.00391   | 9%       | 18%            |
| always-strong        | 0.978 | 0.02148   | 100%     | 100%           |
| oracle               | 0.978 | 0.00225   | —        | 10%            |

All five threshold sweeps produce identical results because the confidence gate output
never crosses any threshold for the hard-math items. The cascade matches always-cheap
accuracy (0.844) at 18% of always-strong cost — a 2.4× overhead vs bare cheap due to gate call costs.

## Gate error analysis (Live verified)

| Gate outcome         | Count | Items                                    |
| -------------------- | ----- | ---------------------------------------- |
| False accepts        | 6     | m9,m10,m12,m13,m14,m15 (all hard math)  |
| Correct escalations  | 3     | escalated → strong → correct             |
| Wrong escalations    | 1     | m8: both models wrong                    |
| False escalations    | 2     | m1,m3: easy/correct, conf=0.0            |

**False accept rate: 6/27 = 22% on math/QA** (6 items where gate accepted wrong answer).
These 6 are exactly the hard-math items that cheap always gets wrong — the gate fails
uniformly on the items that most need escalation.

## Per-discipline breakdown (Live verified)

| Discipline | Acc    | Escalated | Cost     |
| ---------- | ------ | --------- | -------- |
| coding     | 18/18  | 1/18      | $0.00315 |
| math       | 8/15   | 3/15      | $0.00054 |
| qa         | 12/12  | 0/12      | $0.00022 |

Coding performs perfectly (100%) with only 1 escalation — verifier gate is effective there.
Math accuracy is unchanged from always-cheap (8/15) — gate does not help.
QA is fully handled by cheap — no escalations needed and all correct.

## Confidence probe (Live verified)

Confidence values returned by gpt-4o-mini for the hard-math items it gets wrong:
- m9 (answer "67", correct=47): conf=0.9
- m10 (answer "13", correct=16): conf=0.9
- m12 (answer "26", correct=28): conf=0.9
- m13 (answer "28", correct=35): conf=0.9
- m14 (answer "292.", correct=242): conf=0.9
- m15 (answer "420", correct=1260): conf=0.9

All return 0.9. Threshold sweep from 0.1 to 0.9 cannot distinguish any of them, so the
gate is completely non-discriminative for the items that matter most.

## Honest finding

Live verified: The cascade as implemented does **not beat always-cheap on accuracy** (both
0.844). It costs 2.4× more than always-cheap due to gate call overhead, while providing no
accuracy improvement on this suite. The cascade avoids always-strong's cost ($0.02148),
landing at 18% of that, but strictly dominates neither always-cheap (higher cost) nor
always-strong (lower accuracy).

This is the FrugalGPT failure mode: "the verifier must be more reliable than the generator."
When the cheap model is overconfident, self-confidence gating collapses to a fixed escalation
rate that the threshold parameter cannot tune.

The coding verifier (cheap LLM judge on code) is a different story: it works on this suite
with 0 false accepts and only 1 false escalation, achieving perfect accuracy at 5.5× less cost
than always-strong for coding tasks.

## What a real FrugalGPT system would do

- Use a **trained verifier**, not a prompted self-assessor. A second model or a purpose-trained
  binary classifier is far more reliable than asking the same model that produced the answer.
- Use **structural signals** (code syntax validity, numeric extraction, cross-check with a
  lookup) rather than pure confidence self-report.
- Or train the confidence probe specifically on hard examples where the calibration gap shows
  (see L2b-classifier-router for a proper supervised approach).

## How to reproduce (Live verified)

```bash
# Load credentials
set -a; . .agent-university/secrets.local.env; set +a

# Run cascade
python3 source/run_l3a.py

# Run behavioral tests
python3 -m pytest source/test_l3a.py -v
```

## Files

```
source/
  run_l3a.py          # FrugalGPT cascade + confidence gate + verifier + threshold sweep
  test_l3a.py         # Live behavioral tests (7 passed, 1 skipped until summary exists)
  green-output.txt    # Full stdout from real run
  red-output.txt      # ProviderError without credentials
  l3a_summary.json    # Machine-readable results
  .cache.json         # 52 cached gate/escalation calls (245 hits on re-runs)
```
