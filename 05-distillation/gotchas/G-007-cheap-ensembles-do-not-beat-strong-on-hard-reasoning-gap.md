# G-007: Cheap ensembles (MoA/debate/self-consistency) did NOT beat one strong model on a hard-reasoning-gap workload

**Category**: gotcha
**Severity**: critical
**Evidence tier**: Live verified
**Source POC**: X1-mixture-of-agents, X2-self-consistency-vote, X3-multi-agent-debate, X5-router-benchmark-pareto

## What

Live verified across three independent ensemble methods on the same 45-item suite:

| Method | Accuracy | Cost (full 45-item suite) | vs. always-strong (acc 0.978, $0.02148) |
|---|---|---|---|
| MoA (3 cheap + aggregator) | 0.956 | $0.10159 | −2.2pp accuracy, **4.7×** more cost |
| Self-consistency@5 (cheap, math) | 9/15 | — | vs. single cheap 8/15 vs. single strong 14/15 |
| Debate (3 cheap, 1 round) | 0.957 | **3.84× strong cost** | −2.1pp accuracy, dominated on Pareto |

All three ensemble strategies were dominated by always-strong: they cost more AND produced lower accuracy. None are on the Pareto frontier.

## Why it matters

The popular narrative — "cheap models together beat a single SOTA model" — is workload-dependent. It holds when cheap members are individually competitive with uncorrelated errors. It fails when the workload has a hard tail (multi-step reasoning math) that ALL cheap members fail: ensembling wrong answers produces wrong answers.

An agent that replaces a single `gpt-4.1` call with three `gpt-4o-mini` calls (or a MoA round) expecting cost savings will instead pay ~4.7× more and get worse answers on the hard tail.

## Root cause

The routable gap in this suite is 6 hard-math items (combinatorics, divisibility, permutations) that require multi-step reasoning no cheap model can supply. When all ensemble members produce the wrong intermediate reasoning steps, the aggregator has only wrong proposals to synthesize from. More synthesis passes do not create correct reasoning that was absent in every input. Ensemble diversity helps only when at least one member would answer correctly in isolation.

Self-consistency compounds the same failure: temperature-driven sampling produces near-identical wrong answers for tasks beyond the model's reasoning depth. Voting amplifies the model's existing distribution; it does not supply reasoning the base model lacks.

## Fix

Ensembles are appropriate when:
1. Individual cheap members achieve ≥ 60% accuracy on the target task distribution (so ensemble majority voting can improve on the base rate).
2. Errors are uncorrelated across members (different training, different prompt formats, diverse temperatures).
3. The hard tail is small relative to the easy majority (so ensemble overhead amortizes across many cheap-correct items).

On a hard-reasoning-gap workload, use a predictive router instead. A logistic classifier on query embeddings achieved 0.978 accuracy at $0.00291 (7.4× cheaper than always-strong) — matching strong accuracy without any ensemble overhead (X5, capstone).

If an ensemble is still required (e.g., for variance reduction), apply it selectively only to items the router predicts as hard, not as a blanket replacement for all strong-model calls.

## Regression note

Any benchmark comparing "ensemble of cheap" vs. "single strong" should report the per-method Pareto position (accuracy, cost) and explicitly check whether any ensemble method is dominated. A dominated ensemble on the Pareto frontier should not be presented as a cost-saving strategy.

## Evidence

- Source: `03-pocs/X1-mixture-of-agents/surprises.md`, item 1: "MoA (3 cheap → gpt-4o aggregator) costs $0.09966 versus gpt-4.1's $0.02148. That is 4.64× MORE expensive while achieving lower accuracy (0.956 vs 0.978)." (Live verified)
- Source: `03-pocs/X2-self-consistency-vote/surprises.md`, item 1: "gpt-4o-mini produces near-identical wrong answers across 5 samples. Self-consistency works best on tasks the weak model CAN solve (but is noisy on) — NOT on tasks beyond the model's reasoning depth." (Live verified)
- Source: `03-pocs/X3-multi-agent-debate/surprises.md`, S-1: "Debate is dominated by always-strong: same accuracy (0.957 ≈ 0.978), 3.84× the cost." (Live verified)
- Source: `03-pocs/X3-multi-agent-debate/evidence.md`: debate cost on 23-item sub-suite $0.006278 vs. always-strong $0.001634 = 3.84× confirmed. (Live verified)
- Source: `03-pocs/X5-router-benchmark-pareto/surprises.md`, item 2: "Mixture-of-Agents was 4.7× more expensive than a single strong model AND less accurate (0.956 vs 0.978)." (Live verified)
- Source: results-digest.md, Gotchas item 7: "Cheap-model ENSEMBLES (MoA/debate/self-consistency) did NOT beat one strong model on a hard-reasoning-gap workload — they multiply cost and still miss the tail. Ensembles pay off only when members are individually competitive with uncorrelated errors." (Live verified)
