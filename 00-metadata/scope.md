# Scope

## In scope
- Routing **decisions**: which model (or combination of models) serves a given task.
- Strategies: heuristic, embedding-kNN, trained classifier, cascade w/ verification, harness
  per-step routing, ensembles (MoA / self-consistency / debate), oracle upper bound.
- Disciplines: coding (primary), QA/knowledge, math/reasoning.
- Cost-vs-quality measurement on a Pareto frontier; an OpenAI-compatible routing gateway runtime.

## Out of scope
- Training new base models or fine-tuning router backbones on large datasets (we train only tiny
  logistic/kNN routers on locally-generated labels).
- Production-scale load testing, multi-region deployment, and SLA engineering.
- Provider-specific billing reconciliation beyond the per-call cost we compute/observe.
