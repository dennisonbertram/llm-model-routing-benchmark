# P-002: Route the Hard Tail — Not Ensemble Everything

**Category**: pattern
**Evidence tier**: Live verified (POCs L0, X1, X2, X5)
**Source POCs**: L0-smoke-and-harness, X1-mixture-of-agents, X5-router-benchmark-pareto

## Live verified

On the 45-task benchmark: **6 of 45 tasks (13%) need the strong model.** All six are
multi-step combinatorics/reasoning math (m9, m10, m12, m13, m14, m15). The cheap model
(`gpt-4o-mini`) handles 38/45 (84%) correctly. The hard tail is **narrow and concentrated**
in one discipline. (L0)

When cheap-model ensembles were deployed to cover this tail:

| Ensemble strategy              | Accuracy | Cost        | vs always-strong |
|--------------------------------|----------|-------------|-----------------|
| MoA (3 cheap + aggregator)     | 0.956    | $0.10159    | 4.73× **more**  |
| self-consistency@5 (math only) | 9/15     | —           | worse than 1× strong (14/15) |
| always-strong (gpt-4.1)        | 0.978    | $0.02148    | 1×              |
| logistic router (τ=0.9)        | 0.978    | $0.00291    | 7.4× cheaper    |

**MoA costs 4.73× more than always-strong AND achieves lower accuracy.** The hard-math tail
(m9–m15) is a failure of reasoning capacity, not a lack of diversity — re-aggregating three
wrong proposals does not produce the correct answer. (X1, X5)

Self-consistency barely helped: +1 correct answer on math (9/15 vs 8/15 for single cheap)
while a single strong call gets 14/15. (X5)

## The pattern

```
        difficulty distribution
        ────────────────────────
        easy/medium   ████████████████████████████████  84% (38/45)
        hard tail     ██                                16% (7/45, incl. m8 both-wrong)
        ─────────────────────────────────────────────
        routing:
           easy/medium  → cheap model
           hard tail    → strong model   ← route this, don't ensemble it
```

The routing prize comes from correctly identifying and escalating the hard tail. Ensembling
cheap models over the hard tail amplifies cost without fixing the underlying reasoning gap.

**Route the hard tail — do not ensemble it.**

## Why ensembling fails on a hard tail

A cheap-model ensemble has correlated errors on the hard tail: all three cheap proposers
in MoA gave wrong answers for the same hard-math items (m9, m10, m12–m15). The aggregator
receives three wrong proposals and synthesizes a wrong final answer. (X1)

Self-consistency (majority vote over k samples) cannot overcome this either: the cheap model
systematically applies the wrong reasoning strategy to hard combinatorics problems. More
samples of the same wrong approach do not converge to the correct answer. (X5)

Ensemble methods can pay off when:
- Cheap model members are individually competitive on the hard items
- Members' errors are uncorrelated (different model families, different pretraining)
- The aggregator can detect when all proposals are wrong

None of these held on this benchmark suite.

## How to identify your hard tail

```python
# From the outcome matrix (built in R-009):
hard_items = [
    task for task in suite
    if not outcome_matrix[f"gpt-4o-mini|{task.id}"]["correct"]
    and outcome_matrix[f"gpt-4.1|{task.id}"]["correct"]
]
print(f"Hard tail: {len(hard_items)}/{len(suite)} items need strong model")
for item in hard_items:
    print(f"  {item.id}: {item.discipline} / {item.difficulty}")
```

Live verified output (L0):
```
Hard tail: 6/45 items need strong model
  m9:  math / hard
  m10: math / hard
  m12: math / hard
  m13: math / hard
  m14: math / hard
  m15: math / hard
```

All six are hard math — the discipline matters more than the difficulty label for routing. (L0, L3b)

## Actionable guidance

1. Measure your hard tail before deciding on a routing strategy.
2. If the hard tail is narrow (< 20% of traffic) and concentrated in one discipline,
   use predictive routing (R-001, R-002) to escalate those items.
3. If the hard tail is wide and distributed, evaluate MoA only if cheap members have
   uncorrelated errors on your specific workload.
4. Never deploy MoA without measuring its cost on YOUR workload. On long-output tasks
   (code, detailed explanations), the aggregation call can dominate total cost.

## Evidence

- L0-smoke-and-harness/README.md — hard tail characterization (6/45 tasks, all hard math)
- X1-mixture-of-agents/README.md — MoA failure on hard math, per-discipline breakdown
- X5-router-benchmark-pareto/README.md — MoA vs strong comparison, self-consistency math result
- results-digest.md lines 22–23, 47, 57 — authoritative numbers
