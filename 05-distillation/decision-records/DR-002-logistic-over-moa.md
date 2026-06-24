# DR-002: Why Logistic Classifier Over Ensemble Methods (MoA/Debate/Self-Consistency)

**Date**: 2026-06-21
**Status**: Accepted — based on live measured outcomes
**Evidence tier**: Live verified (X1; X2; X3; X5; capstone)

---

## Decision

Use a logistic regression classifier trained on embedding features as the primary
routing strategy for the deployed adaptive gateway. Do not use ensemble methods
(Mixture-of-Agents, multi-agent debate, self-consistency voting) as the primary
routing mechanism on workloads where the difficulty gap is concentrated in hard reasoning.

---

## Context

The degree explored seven routing strategies on the 45-task harness. The ensemble
strategies (X1, X2, X3) represent the "cheap models together beat strong" hypothesis
from Wang et al. (MoA), Du et al. (debate), and Wang et al. (self-consistency). The
classifier strategies (L2b, X5 logistic) represent the RouteLLM / Hybrid-LLM family.

The decision was made after live measurement, not from prior assumptions.

---

## Measured outcomes

**Live verified** (X1; X2; X3; X5):

| Strategy | Accuracy | Cost (45 tasks) | vs always-strong |
|---|---|---|---|
| always-cheap | 0.844 | $0.00166 | 0.08× |
| always-strong | 0.978 | $0.02148 | 1.0× |
| MoA (3 cheap + gpt-4o agg) | 0.956 | $0.10159 | **4.73× more expensive** |
| self-consistency@5 (math: 9/15) | — | — | worse than single strong |
| multi-agent debate | 0.957 | — | 3.84× strong cost |
| **logistic(thr=0.9) CV** | **0.978** | **$0.00291** | **7.4× cheaper** |
| **capstone adaptive(thr=0.8) CV** | **0.978** | **$0.00257** | **8.4× cheaper** |

---

## Why classifiers win here

**The difficulty gap is concentrated in a hard tail.** Only 6/45 tasks required the
strong model, all hard mathematical reasoning. The cheap model and the ensemble proposers
share the same reasoning deficit on these items. Running three cheap models produces
three wrong answers plus aggregation cost; the aggregator cannot synthesise a correct
answer from wrong inputs.

**A classifier routes without generating.** The classifier embeds the prompt once
(~$3.8e-07) and makes a routing decision based on learned features. There is no
additional model call until the router has decided where to send the request. An
ensemble, by contrast, calls N models before any decision is made — the cost is
unconditional on the routing outcome.

**The training cost is amortized.** The outcome matrix (L0 baseline) was collected once
at a total cost of ~$0.023. Every subsequent routing decision costs ~$3.8e-07 for
embedding. An ensemble pays full generation cost on every query regardless of difficulty.

---

## When ensembles would be preferred

The decision is workload-specific. Ensembles are a better choice when:
1. **Cheap models are individually competitive** on the target tasks and their errors
   are uncorrelated — e.g., different model families with different knowledge bases.
2. **No labeled history exists** and building an outcome matrix is not feasible.
3. **The target task benefits from diversity** of perspectives that individual models
   genuinely provide (open-ended generation, creative tasks, tasks without ground truth).
4. **The aggregation cost is low** — short outputs, same-model critique, majority vote.

None of these conditions hold for the hard-math workload in this degree.

---

## Evidence

- X1 README.md: "MoA costs $0.09966 — 4.64× more than always-strong at lower accuracy." (Live verified)
- X3 README.md: "debate acc=0.957 at 3.84× strong cost — dominated." (Live verified)
- X5 README.md: "logistic(thr=0.9) CV: acc=0.978, $0.00291 — 7.4× cheaper than always-strong." (Live verified)
- results-digest.md: "Big lesson: the win is routing that tail to a stronger model (predictive routers ≈ oracle, 7–8× cheaper than always-strong), NOT ganging up cheap models." (Live verified)
- results-digest.md, Gotcha 7: "Cheap-model ENSEMBLES did NOT beat one strong model on a hard-reasoning-gap workload." (Live verified)
