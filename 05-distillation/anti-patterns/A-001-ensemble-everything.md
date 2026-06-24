# A-001: Ensemble-Everything — Using MoA/debate/self-consistency to beat a strong model

**Category**: anti-pattern
**Severity**: high — multiplies cost without accuracy gain on hard-reasoning workloads
**Evidence tier**: Live verified
**Source POCs**: X1-mixture-of-agents, X2-self-consistency-vote, X3-multi-agent-debate, X5-router-benchmark-pareto

---

## What the anti-pattern looks like

Live verified. Building a multi-model ensemble (Mixture-of-Agents, multi-agent debate,
or self-consistency voting) of cheap models as a substitute for routing hard queries to a
stronger model — on the assumption that "N weak models together beat one strong model."

Measured results on the 45-task harness (2026-06-21):

| Ensemble strategy | Accuracy | Cost | vs always-strong |
|---|---|---|---|
| MoA (3 cheap + gpt-4o aggregator) | 0.956 | $0.10159 | **4.7× more expensive, 2.2pp less accurate** |
| self-consistency@5 (cheap, math only) | 9/15 | — | vs strong 14/15 — barely moves the needle |
| multi-agent debate (3 models, 1 round) | 0.957 | — | 3.84× strong cost, still 2.1pp below |
| always-strong (single call) | 0.978 | $0.02148 | 1.0× |

MoA cost $0.10159 — **4.7× more than always-strong** — and still scored 2.2 percentage
points below it. A single `gpt-4.1` call dominates every ensemble strategy on both cost
and accuracy on this workload.

---

## Why this happens

The accuracy gap in this suite is concentrated in hard mathematical reasoning (m9, m10,
m12, m13, m14, m15). All cheap models in the pool share the same reasoning deficit for
these tasks. Running three of them and aggregating their outputs produces three wrong
answers plus an aggregation call — none of the proposals contain the correct reasoning,
so the aggregator cannot synthesise a correct answer from wrong inputs.

For the X1 2-layer MoA test on the 8 hard math items: single strong (gpt-4.1) scored
7/8; MoA-1L scored 6/8; MoA-2L (additional aggregation pass) also scored 6/8. The
second aggregation layer added cost and no accuracy.

The token cost of aggregation compounds the problem: coding tasks produce 700-token
outputs. Three proposals × 700 output tokens × mid-tier aggregation model makes each
query significantly more expensive than a single strong call.

---

## When ensembles do make sense (not demonstrated in this degree)

Ensembles pay off when:
1. Members are individually competitive (each cheap model achieves >90% on the task
   category where the ensemble is applied).
2. Errors are uncorrelated across models (different model families, different knowledge
   cut-offs, different reasoning strategies).
3. The aggregation step is cheap (short answers, same-model critique, not long synthesis).
4. Latency is constrained and parallel cheap calls are faster than a single strong call.

MoA's published results (Wang et al., Together AI, 2024) are on benchmarks where the
above conditions hold more closely. The measured result here — on a workload whose
difficulty is a hard tail — is a clear loss. Report what you measure, not what you expect.

---

## Fix

**Live verified** (X5; capstone) — use a predictive router instead of an ensemble:

1. Build the outcome matrix: run cheap and strong once each, record per-item correctness.
2. Embed prompts with `text-embedding-3-small`.
3. Train a logistic classifier to predict P(cheap_correct).
4. Set the threshold τ to meet your accuracy SLA.

The logistic router at τ=0.9 (X5, 5-fold CV): acc=0.978, $0.00291 — matches strong
accuracy at 7.4× lower cost. This dominates every ensemble strategy measured in this degree.

---

## Evidence

- X1 README.md: "MoA costs $0.09966 — 60× more than single cheap, 4.64× more than always-strong at lower accuracy (0.956 vs 0.978)." (Live verified)
- X2 README.md: self-consistency@5 on hard math: 9/15 vs single strong 14/15. (Live verified)
- X3 README.md: debate acc=0.957 at 3.84× strong cost. (Live verified)
- X5 README.md results table: "MoA (3 cheap + aggregator): 0.956, $0.10159 — 4.7× more than always-strong." (Live verified)
- results-digest.md, Gotcha 7: "Cheap-model ENSEMBLES (MoA/debate/self-consistency) did NOT beat one strong model on a hard-reasoning-gap workload — they multiply cost and still miss the tail." (Live verified)
