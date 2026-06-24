# Index — LLM Model Routing Skill Pack

Every file in this skill pack. No orphans. Start with [README.md](README.md).

Live verified (2026-06-21/22). 15 POCs green. Pool: gpt-4o-mini (cheap), gpt-4.1 (strong).
45-task suite: 15 math, 12 QA, 18 coding.

---

## Top-level orientation

| File | Purpose |
|------|---------|
| [README.md](README.md) | Entry point: what is live-verified, what is not, file map |
| [index.md](index.md) | This file |
| [quickstart.md](quickstart.md) | Five commands to load keys, run the gateway, get a routed response |
| [curriculum.md](curriculum.md) | Ordered learning path L0 through capstone |
| [agent-instructions.md](agent-instructions.md) | Imperative brief for a coding agent building a router |
| [live-service-checklist.md](live-service-checklist.md) | Pre-deploy gates for a live routing service |

---

## Lessons

| File | Strategy | POC(s) |
|------|----------|--------|
| [lessons/L-heuristic-routing.md](lessons/L-heuristic-routing.md) | Rule/keyword/length scoring | L1 |
| [lessons/L-predictive-routing.md](lessons/L-predictive-routing.md) | Embedding kNN + logistic classifier | L2, L2b, X5 |
| [lessons/L-cascade-routing.md](lessons/L-cascade-routing.md) | LLM cascade with verification gate | L3a, X4 |
| [lessons/L-ensemble-strategies.md](lessons/L-ensemble-strategies.md) | MoA, self-consistency, debate | X1, X2, X3 |
| [lessons/L-gateway-deployment.md](lessons/L-gateway-deployment.md) | OpenAI-compatible gateway runtime | L3c, L4, L5, capstone |

---

## Labs

| File | POC mapping | Skills practiced |
|------|-------------|-----------------|
| [labs/lab-L0-baseline.md](labs/lab-L0-baseline.md) | L0 | Harness setup, baseline measurement, oracle computation |
| [labs/lab-L1-heuristic.md](labs/lab-L1-heuristic.md) | L1 | Feature scoring, threshold sweep, Pareto plot |
| [labs/lab-L2-knn.md](labs/lab-L2-knn.md) | L2, L2b | Embed prompts, kNN vote, logistic training, threshold sweep |
| [labs/lab-L3-cascade.md](labs/lab-L3-cascade.md) | L3a, L3b | Cascade loop, verifier patterns, escalation on failure |
| [labs/lab-L4-gateway.md](labs/lab-L4-gateway.md) | L3c, L4, L5 | HTTP gateway, curl, failure injection, observability |
| [labs/lab-X-ensembles.md](labs/lab-X-ensembles.md) | X1, X2, X3, X4 | MoA, self-consistency, debate, AutoMix |
| [labs/lab-X5-benchmark.md](labs/lab-X5-benchmark.md) | X5, capstone | Full benchmark, adaptive gateway CV |

---

## Recipes

| File | What it produces |
|------|-----------------|
| [recipes/R-001-heuristic-router.md](recipes/R-001-heuristic-router.md) | Prompt-scoring heuristic router |
| [recipes/R-002-logistic-classifier-router.md](recipes/R-002-logistic-classifier-router.md) | Embed + train + threshold sweep |
| [recipes/R-003-cascade-with-verifier.md](recipes/R-003-cascade-with-verifier.md) | Cheap-first cascade with independent verifier |
| [recipes/R-004-adaptive-gateway.md](recipes/R-004-adaptive-gateway.md) | Capstone gateway: adaptive routing + budget guard + fallback |
| [recipes/R-005-pareto-benchmark.md](recipes/R-005-pareto-benchmark.md) | Pareto frontier benchmark harness |

---

## Checklists

| File | When to use |
|------|-------------|
| [checklists/router-readiness.md](checklists/router-readiness.md) | Pre-ship gate for any router |
| [checklists/benchmark-validity.md](checklists/benchmark-validity.md) | Pre-report gate for accuracy/cost numbers |

---

## Reference

| File | Contents |
|------|----------|
| [reference/model-pool.md](reference/model-pool.md) | Pool config, verified models, pricing, gotchas per provider |
| [reference/harness-api.md](reference/harness-api.md) | Full harness API: chat(), embed(), Router, run_suite(), metrics |
| [reference/pareto-numbers.md](reference/pareto-numbers.md) | Definitive Pareto table (live-measured, no invented numbers) |

---

## Examples

| File | What it demonstrates |
|------|---------------------|
| [examples/gateway-curl.md](examples/gateway-curl.md) | Curl session against the live capstone gateway |

---

## Troubleshooting

| File | Symptom |
|------|---------|
| [troubleshooting/empty-response-reasoning-model.md](troubleshooting/empty-response-reasoning-model.md) | gpt-5 / o-series returns blank content |
| [troubleshooting/cost-accounting-grok.md](troubleshooting/cost-accounting-grok.md) | grok-4.x cost diverges from tokens × price |
| [troubleshooting/classifier-collapses-to-baseline.md](troubleshooting/classifier-collapses-to-baseline.md) | Logistic router always routes cheap |
| [troubleshooting/self-confidence-gate-non-discriminative.md](troubleshooting/self-confidence-gate-non-discriminative.md) | FrugalGPT gate returns 0.9 confidence even when wrong |

---

## Distillation source artifacts (05-distillation/ — canonical, linked not duplicated)

| Artifact | Contents |
|----------|----------|
| [`../05-distillation/gotchas/G-001-reasoning-model-empty-content-small-budget.md`](../05-distillation/gotchas/G-001-reasoning-model-empty-content-small-budget.md) | Reasoning model blank content under small budget |

---

## POC source directories (03-pocs/ — green evidence on record)

| POC | README |
|-----|--------|
| L0 smoke + harness | [`../03-pocs/L0-smoke-and-harness/README.md`](../03-pocs/L0-smoke-and-harness/README.md) |
| L1 heuristic router | [`../03-pocs/L1-heuristic-router/README.md`](../03-pocs/L1-heuristic-router/README.md) |
| L2 embedding kNN | [`../03-pocs/L2-embedding-knn-router/README.md`](../03-pocs/L2-embedding-knn-router/README.md) |
| L2b classifier | [`../03-pocs/L2b-classifier-router/README.md`](../03-pocs/L2b-classifier-router/README.md) |
| L3a FrugalGPT | [`../03-pocs/L3a-frugalgpt-cascade/README.md`](../03-pocs/L3a-frugalgpt-cascade/README.md) |
| L3b harness routing | [`../03-pocs/L3b-harness-routing-coding-agent/README.md`](../03-pocs/L3b-harness-routing-coding-agent/README.md) |
| L3c gateway integration | [`../03-pocs/L3c-openai-compatible-gateway-integration/README.md`](../03-pocs/L3c-openai-compatible-gateway-integration/README.md) |
| L4 gateway runtime | [`../03-pocs/L4-routing-gateway-runtime/README.md`](../03-pocs/L4-routing-gateway-runtime/README.md) |
| L5 failure modes | [`../03-pocs/L5-failure-modes-and-observability/README.md`](../03-pocs/L5-failure-modes-and-observability/README.md) |
| X1 mixture-of-agents | [`../03-pocs/X1-mixture-of-agents/README.md`](../03-pocs/X1-mixture-of-agents/README.md) |
| X2 self-consistency | [`../03-pocs/X2-self-consistency-vote/README.md`](../03-pocs/X2-self-consistency-vote/README.md) |
| X3 debate | [`../03-pocs/X3-multi-agent-debate/README.md`](../03-pocs/X3-multi-agent-debate/README.md) |
| X4 AutoMix | [`../03-pocs/X4-verification-cascade-automix/README.md`](../03-pocs/X4-verification-cascade-automix/README.md) |
| X5 benchmark Pareto | [`../03-pocs/X5-router-benchmark-pareto/README.md`](../03-pocs/X5-router-benchmark-pareto/README.md) |
| L-capstone | [`../03-pocs/L-capstone-adaptive-routing-gateway/README.md`](../03-pocs/L-capstone-adaptive-routing-gateway/README.md) |
