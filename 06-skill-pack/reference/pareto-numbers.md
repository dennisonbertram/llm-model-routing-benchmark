# Reference: Definitive Pareto Numbers

Live verified (L0; X5; capstone; 2026-06-21). Every number here is from committed POC
evidence. No invented numbers. No rounded-away precision.

Back to [index](../index.md).

---

## Full-suite Pareto table (45 tasks: 15 math, 12 QA, 18 coding)

Live verified. From `03-pocs/X5-router-benchmark-pareto/README.md` and `.context/results-digest.md`.

| router | accuracy | total $ | $/correct | notes |
|--------|----------|---------|-----------|-------|
| always-cheap (gpt-4o-mini) | 0.844 | 0.001662 | 4.4e-05 | floor |
| always-strong (gpt-4.1) | 0.978 | 0.021482 | 4.88e-04 | 12.9x cheap |
| random-50% (10 seeds avg) | 0.909 | 0.011765 | 2.88e-04 | dominated |
| heuristic (prompt cues) | 0.933 | 0.005200 | 1.24e-04 | |
| kNN (k=3) 5-fold CV | 0.933 | 0.002211 | 5.3e-05 | |
| kNN (k=5) 5-fold CV | 0.889 | 0.002035 | 5.1e-05 | |
| logistic (thr=0.7) 5-fold CV | 0.956 | 0.002335 | 5.4e-05 | |
| **logistic (thr=0.9) 5-fold CV** | **0.978** | **0.002905** | 6.6e-05 | **7.4x cheaper than strong** |
| MoA (3 cheap + gpt-4o agg) | 0.956 | 0.101588 | 2.36e-03 | DOMINATED: 4.7x more than strong |
| _oracle (cheapest-correct)_ | _0.978_ | _0.002143_ | _4.9e-05_ | **UNREALIZABLE ceiling** |

Sources: `03-pocs/X5-router-benchmark-pareto/README.md`, `.context/results-digest.md`

---

## Realizable Pareto frontier

Live verified. Only deployable routers (excludes oracle):

```
always-cheap        acc=0.844  $0.00166
kNN(k=5) CV         acc=0.889  $0.00203
kNN(k=3) CV         acc=0.933  $0.00221
logistic(thr=0.7)   acc=0.956  $0.00233
logistic(thr=0.9)   acc=0.978  $0.00291   <- matches strong, 7.4x cheaper
```

Each step up the frontier gains accuracy at modest cost increase. MoA is NOT on the
frontier (dominated by always-strong on both cost and accuracy).

---

## Capstone CV results (45 tasks, 5-fold, adaptive gateway)

Live verified. From `03-pocs/L-capstone-adaptive-routing-gateway/evidence.md`.

| Router | accuracy | cost | pct_cheap |
|--------|----------|------|-----------|
| adaptive(thr=0.5) | 0.844 | $0.00176 | 98% |
| adaptive(thr=0.6) | 0.844 | $0.00176 | 98% |
| adaptive(thr=0.7) | 0.956 | $0.00227 | 82% |
| **adaptive(thr=0.8)** | **0.978** | **$0.00257** | **71%** |
| adaptive(thr=0.9) | 0.978 | $0.00275 | 64% |

Best: adaptive(thr=0.8) — acc=0.978, $0.00257, 8.4x cheaper than always-strong, 1.20x oracle.

---

## Per-POC headline numbers

Live verified. All from committed evidence files.

| POC | Headline |
|-----|----------|
| L0 | always-cheap: acc=0.844, $0.00166; always-strong: acc=0.978, $0.02148; oracle: acc=0.978, $0.00214 |
| L1 | heuristic(thr=0.40): acc=0.956, $0.00902, 42% of strong cost |
| L2 | kNN(k=7,thr=0.7) held-out: acc=0.955, $0.00136, 88% cost reduction |
| L2b | logistic(thr=0.80) test set: acc=1.000, $0.000773, 6.3x cheaper than strong |
| L3a | cascade ALL thresholds: acc=0.844, $0.00391 (FAILURE — gate non-discriminative) |
| L3b | routed coding harness: acc=1.000, $0.00148, 0 escalations (7.5% of all-strong cost) |
| L3c | gateway integration: 10/10 live tests; base_url override works |
| L4 | 3 live curls: $0.001087 total; per-request JSONL ledger confirmed |
| L5 | 5 live failure modes; 9/9 behavioral tests green |
| X1 | MoA: acc=0.956, $0.09966 (4.64x more than strong AND less accurate) |
| X2 | self-consistency @5 math: 9/15 vs 14/15 single strong |
| X3 | debate 3 models: acc=0.957, $0.006278 on a 23-task sub-suite (3.84x the $0.001634 always-strong cost on those same 23 tasks — dominated; not run on full 45) |
| X4 | AutoMix kNN: acc=0.978, 71.6% savings vs strong; 2.85x oracle cost |
| X5 | logistic(thr=0.9): acc=0.978, $0.00291 — 7.4x cheaper than strong |
| capstone | adaptive(thr=0.8) CV: acc=0.978, $0.00257, 8.4x cheaper, 1.20x oracle |

---

## Oracle breakdown

Live verified (L0). The oracle routes cheap for 39/45 tasks:

| Items needing strong | m9, m10, m12, m13, m14, m15 (6 items, all hard math) |
|---------------------|-------------------------------------------------------|
| Both models wrong | m8 (oracle charges cheap) |
| Cheap sufficient | 38/45 items |

This is why routing pays: 84.4% of traffic can go to the cheap model without accuracy loss.
The entire routing prize comes from correctly handling the 13.3% hard-math tail.
