# Lab: L1 — Heuristic Router

Live verified (L1; 2026-06-21). Rule-based routing threshold sweep.

Back to [index](../index.md).

---

## Goal

Build a prompt-scoring heuristic, sweep its threshold from 0.20 to 0.70, and confirm it
lands between the two baselines on the Pareto frontier.

---

## Commands

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd model-routing/degrees/01-llm-model-routing/03-pocs/L1-heuristic-router/source
python3 run_l1.py     # threshold sweep + 3 live confirmation calls
```

---

## Expected output (live-measured, 2026-06-21)

```
thr=0.20  acc=0.978  $0.02002
thr=0.30  acc=0.956  $0.01402
thr=0.40  acc=0.956  $0.00902   <- selected: best tradeoff
thr=0.50  acc=0.889  $0.00317
thr=0.60  acc=0.844  $0.00298
thr=0.70  acc=0.844  ~$0.00177  (routes nothing)
```

Live confirmation calls (3 items):
- m1 (easy math): score=0.045 → gpt-4o-mini (correct)
- m9 (hard math): score=0.490 → gpt-4.1 (correct, oracle target)
- c1 (easy coding): score=0.286 → gpt-4o-mini (correct)

---

## What to observe

- Threshold is the knob: thr=0.40 gives 0.956 acc at 42% of strong cost.
- The heuristic plateaus: thr=0.20 reaches strong accuracy but at 93% of strong cost.
  No prompt-only rule reaches oracle efficiency.
- False positives (5 items over-routed) are the dominant waste. Predictive routers (L2/L2b)
  will eliminate most of these.

---

## POC source

`../03-pocs/L1-heuristic-router/`
