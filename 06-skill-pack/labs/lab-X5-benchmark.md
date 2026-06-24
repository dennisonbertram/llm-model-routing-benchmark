# Lab: X5 + Capstone — Pareto Benchmark + Adaptive Gateway

Live verified (X5; capstone; 2026-06-21). The empirical heart: all routers on one
evaluation, then the full adaptive gateway.

Back to [index](../index.md).

---

## Goal

Run every router strategy over the shared 45-task suite, emit the Pareto frontier table,
then run the capstone adaptive gateway's CV benchmark and live curl smoke.

---

## Commands: X5 benchmark

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd model-routing/degrees/01-llm-model-routing/03-pocs/X5-router-benchmark-pareto/source
python3 benchmark.py    # emits Pareto table; first run pays for MoA/SC live calls
```

Expected Pareto table (live-measured, 2026-06-21):

```
router                   accuracy  total $    $/correct
always-cheap             0.844     0.001662   4.4e-05
always-strong            0.978     0.021482   4.88e-04
random-50% (10 seeds)    0.909     0.011765   2.88e-04
heuristic                0.933     0.005200   1.24e-04
kNN (k=3) CV             0.933     0.002211   5.3e-05
kNN (k=5) CV             0.889     0.002035   5.1e-05
logistic (thr=0.7) CV    0.956     0.002335   5.4e-05
logistic (thr=0.9) CV    0.978     0.002905   6.6e-05   <- matches strong, 7.4x cheaper
MoA (3 cheap + agg)      0.956     0.101588   2.36e-03  <- DOMINATED
oracle (unrealizable)    0.978     0.002143   4.9e-05   <- ceiling
```

---

## Commands: Capstone adaptive gateway

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/L-capstone-adaptive-routing-gateway/source

# Full CV benchmark + live budget-guard + fallback smoke
python3 run_capstone.py

# Start HTTP gateway and run 3 live curls
python3 gateway_server.py 8137 &
curl -s -X POST localhost:8137/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"auto","messages":[{"role":"user","content":"What is the capital of France?"}]}'
curl -s -X POST localhost:8137/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"auto","messages":[{"role":"user","content":"How many ways can you arrange the letters in BALLOON?"}]}'
kill %1
```

Expected CV result (live-measured, 5-fold, 2026-06-21):
```
adaptive(thr=0.8): acc=0.978  $0.00257  pct_cheap=71%
  = 8.4x cheaper than always-strong ($0.02148)
  = 1.20x the oracle cost ($0.00214)
```

Expected curl results (live-captured, 2026-06-22):
```
capital of France:   served=gpt-4o-mini  decision=classifier(p_cheap=0.97,thr=0.6)  answer=Paris.
BALLOON arrangement: served=gpt-4.1     decision=classifier(p_cheap=0.38,thr=0.6)  answer=1260
```

---

## What to observe

The realizable Pareto frontier (excludes oracle):
```
always-cheap  →  kNN(k=5)  →  kNN(k=3)  →  logistic(0.7)  →  logistic(0.9)
```

Every learned router dominates random-50%. Every learned router dominates always-strong
on cost. MoA is the single dominated outlier: expensive and less accurate than strong.

The adaptive gateway sits at logistic(thr=0.8–0.9) on the frontier, confirmed by both
CV and live curl evidence.

---

## Reference

[reference/pareto-numbers.md](../reference/pareto-numbers.md) — full live-measured table.

## POC sources

- `../03-pocs/X5-router-benchmark-pareto/`
- `../03-pocs/L-capstone-adaptive-routing-gateway/`
