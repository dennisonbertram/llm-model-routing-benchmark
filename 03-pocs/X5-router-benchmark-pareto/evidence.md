# X5 Live Evidence

Status: Complete with live evidence. Evidence strength: Strong. Captured 2026-06-21.
Live services: OpenAI (embeddings + chat), Anthropic (ensemble member). No mocks.
Full machine-readable results: `source/benchmark_results.json`; console log: `source/green-output.txt`.

## Realizable Pareto frontier (live)
```
always-cheap        acc=0.844  $0.00166
k-NN(k=5) cv        acc=0.889  $0.00203
k-NN(k=3) cv        acc=0.933  $0.00221
logistic(thr=0.7)   acc=0.956  $0.00233
logistic(thr=0.9)   acc=0.978  $0.00291   = always-strong accuracy at 7.4x lower cost
ceiling: oracle     acc=0.978  $0.00214   (unrealizable)
```
always-strong = 0.978 @ $0.02148; random-50% = 0.909 @ $0.01177 (dominated by all learned routers).

## Ensemble reference points (live, fresh calls)
- MoA (gpt-4o-mini + gpt-4.1-mini + claude-haiku-4-5, aggregated by gpt-4o): 0.956 acc @ $0.10159.
- self-consistency@5 (gpt-4o-mini, temp 0.7) on math: 9/15 vs single cheap 8/15 vs single strong 14/15.
- Cache after first run: 255 entries, 0 misses on re-run (reproducible at zero further cost).

## Claims supported
- A deployable (CV, no-leakage) router matches strong accuracy at ~14% of strong cost.
- Learned routers strictly dominate random routing.
- On THIS suite, a cheap-model ensemble (MoA) and self-consistency do NOT beat a single strong model.

## Claims NOT supported
- That MoA/self-consistency never help (they help on other workloads/model pools — not measured here).
- That thr=0.9 is optimal in general (it is the best point on THIS 45-task CV; pick the threshold per workload + budget).
