# Lab: X1–X4 — Ensemble Strategies

Live verified (X1; X2; X3; X4; 2026-06-21). Run MoA, self-consistency, debate, AutoMix
and observe the live measured outcomes — including the NEGATIVE findings.

Back to [index](../index.md).

---

## Goal

Measure each ensemble strategy on the 45-task suite and compare to always-strong. Observe
that none of them dominates always-strong on both cost AND accuracy on this workload.

---

## Commands: X1 Mixture-of-Agents

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd model-routing/degrees/01-llm-model-routing/03-pocs/X1-mixture-of-agents/source

python3 test_x1.py     # 3 tests pass (hits cache)
python3 run_x1.py      # full suite; first run costs ~$0.10; warm cache = $0 re-runs
```

Expected (live-measured):
```
MoA (3 cheap + gpt-4o agg): acc=0.956  $0.09966
always-strong gpt-4.1:       acc=0.978  $0.02148
```

MoA: +11.2pp over cheap, but 4.64x MORE expensive than strong AND less accurate.

---

## Commands: X2 Self-consistency

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/X2-self-consistency-vote/source
python3 run_x2.py
```

Expected (live-measured, math only):
```
self-consistency @5 cheap: 9/15
single cheap:              8/15
single strong:            14/15
```

---

## Commands: X3 Debate

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/X3-multi-agent-debate/source
python3 run_x3.py
```

Expected (live-measured):
```
debate 3 models 1 round: acc=0.957  $0.006278 (23-task sub-suite; 3.84x strong-on-subset)
always-strong:           acc=0.978  $0.021
```

Debate is dominated: same accuracy as strong at 3.84x the cost.

---

## Commands: X4 AutoMix

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/X4-verification-cascade-automix/source
python3 run_x4.py
```

Expected (live-measured):
```
AutoMix k=3 self-verify: acc=0.978  71.6% savings vs strong  (but 2.85x oracle cost)
```

---

## What to observe

The negative findings are the point of this lab:

1. **MoA is more expensive than strong AND less accurate.** This is the correct measured
   outcome for this workload. It is not a bug. Report it honestly.
2. **Self-consistency @5 barely helps cheap on math.** 9/15 vs 8/15. The 5 additional samples
   do not give gpt-4o-mini the reasoning capacity to solve hard combinatorics.
3. **Debate is dominated.** Equal accuracy to strong at 3.84x its cost. No use case here.
4. **AutoMix is accurate but inefficient.** It matches strong at 71.6% savings — better than
   MoA/debate — but its verifier overhead makes it 2.85x the oracle. The logistic classifier
   does better.

These are first-class publishable findings, not failures of the experiments.

---

## POC sources

- `../03-pocs/X1-mixture-of-agents/`
- `../03-pocs/X2-self-consistency-vote/`
- `../03-pocs/X3-multi-agent-debate/`
- `../03-pocs/X4-verification-cascade-automix/`
