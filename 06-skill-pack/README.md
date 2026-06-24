# Skill Pack — LLM Model Routing

Entry point for the live-verified knowledge from degree `01-llm-model-routing`.
All 15 POCs (L0–L5, X1–X5, capstone) ran against live OpenAI, Anthropic, and xAI
APIs with no mocks. Every number in this skill pack traces to a committed POC.
Captured 2026-06-21/22.

**If you are a coding agent**, start with [agent-instructions.md](agent-instructions.md).
**If you are getting started fast**, start with [quickstart.md](quickstart.md).
**If you need the learning path**, see [curriculum.md](curriculum.md).
**Before deploying to production**, run through [live-service-checklist.md](live-service-checklist.md).

---

## What is live-verified

All 15 POCs ran against live providers on 2026-06-21/22.

| POC | What it proves |
|-----|----------------|
| L0-smoke-and-harness | 3-provider live access; baseline cost-quality gap (the routing prize) |
| L1-heuristic-router | Rule-based routing: 0.956 acc at 42% of strong cost |
| L2-embedding-knn-router | kNN on text-embedding-3-small: 0.955 acc, 88% cost reduction |
| L2b-classifier-router | Logistic classifier: oracle-level accuracy, 6.3x cheaper than strong |
| L3a-frugalgpt-cascade | Self-confidence gating failure; coding verifier success |
| L3b-harness-routing-coding-agent | opencode-style escalate loop: 1.000 acc, 7.5% of strong cost |
| L3c-openai-compatible-gateway-integration | Drop-in base_url override, 10/10 live tests |
| L4-routing-gateway-runtime | Live HTTP gateway, curl-verified, per-request ledger |
| L5-failure-modes-and-observability | 5 live failure modes triggered and recovered |
| X1-mixture-of-agents | MoA: 0.956 acc, $0.100 — 4.64x more expensive than single strong (NEGATIVE) |
| X2-self-consistency-vote | Self-consistency @5: 9/15 math vs 14/15 single strong (NEGATIVE) |
| X3-multi-agent-debate | Debate 3 models: 0.957 acc == strong, but 3.84x the cost (DOMINATED) |
| X4-verification-cascade-automix | AutoMix kNN: 0.978 acc, 71.6% savings vs strong; verifier 100% precise |
| X5-router-benchmark-pareto | Full Pareto frontier: logistic(thr=0.9) == strong at 7.4x cheaper |
| L-capstone-adaptive-routing-gateway | Adaptive gateway: 0.978 acc, 8.4x cheaper than strong |

## What is not live-verified

- Production-scale throughput or SLA beyond a local `http.server`
- Multi-region, multi-provider setups beyond OpenAI + Anthropic + xAI
- Offline or batched embedding pipelines beyond the 45-task harness
- OpenRouter optional backend (key not present in this workspace)

---

## Skill Pack Files

| File | Contents |
|------|----------|
| [index.md](index.md) | Full index of every file in this skill pack |
| [quickstart.md](quickstart.md) | Load keys, run the gateway, get a routed response |
| [curriculum.md](curriculum.md) | L0 to capstone learning path with time estimates |
| [agent-instructions.md](agent-instructions.md) | Imperative brief: what to build first, what to verify, what NOT to mock |
| [live-service-checklist.md](live-service-checklist.md) | Pre-deploy gates for a live routing service |

### Lessons (one per major strategy)

| File | Strategy | Honest verdict |
|------|----------|----------------|
| [lessons/L-heuristic-routing.md](lessons/L-heuristic-routing.md) | Rule/keyword/length scoring | Good baseline; plateaus at ~96% |
| [lessons/L-predictive-routing.md](lessons/L-predictive-routing.md) | kNN + logistic on embeddings | Best cost-quality ratio (near oracle) |
| [lessons/L-cascade-routing.md](lessons/L-cascade-routing.md) | FrugalGPT / AutoMix cascades | Self-confidence fails; trained verifier works |
| [lessons/L-ensemble-strategies.md](lessons/L-ensemble-strategies.md) | MoA / self-consistency / debate | Did NOT beat one strong model here (NEGATIVE) |
| [lessons/L-gateway-deployment.md](lessons/L-gateway-deployment.md) | OpenAI-compatible HTTP gateway | Live: base_url override works end-to-end |

### Labs (mapped to POCs)

| File | POC | What you run |
|------|-----|--------------|
| [labs/lab-L0-baseline.md](labs/lab-L0-baseline.md) | L0 | Baseline harness, 3-provider smoke |
| [labs/lab-L1-heuristic.md](labs/lab-L1-heuristic.md) | L1 | Heuristic router threshold sweep |
| [labs/lab-L2-knn.md](labs/lab-L2-knn.md) | L2 + L2b | kNN + logistic Pareto sweep |
| [labs/lab-L3-cascade.md](labs/lab-L3-cascade.md) | L3a + L3b | FrugalGPT gate + opencode escalation |
| [labs/lab-L4-gateway.md](labs/lab-L4-gateway.md) | L3c + L4 + L5 | HTTP gateway: run, curl, observe failures |
| [labs/lab-X-ensembles.md](labs/lab-X-ensembles.md) | X1–X4 | MoA, self-consistency, debate, AutoMix |
| [labs/lab-X5-benchmark.md](labs/lab-X5-benchmark.md) | X5 + capstone | Full Pareto benchmark + adaptive gateway |

### Recipes

| File | What it produces |
|------|-----------------|
| [recipes/R-001-heuristic-router.md](recipes/R-001-heuristic-router.md) | Copy-paste: prompt-scoring router, threshold sweep |
| [recipes/R-002-logistic-classifier-router.md](recipes/R-002-logistic-classifier-router.md) | Copy-paste: embed + train + threshold sweep |
| [recipes/R-003-cascade-with-verifier.md](recipes/R-003-cascade-with-verifier.md) | Copy-paste: cheap-first with independent verifier |
| [recipes/R-004-adaptive-gateway.md](recipes/R-004-adaptive-gateway.md) | Copy-paste: capstone gateway, budget guard, fallback |
| [recipes/R-005-pareto-benchmark.md](recipes/R-005-pareto-benchmark.md) | Copy-paste: run all routers and emit a Pareto table |

### Checklists

| File | When to use |
|------|-------------|
| [checklists/router-readiness.md](checklists/router-readiness.md) | Before shipping a router to production |
| [checklists/benchmark-validity.md](checklists/benchmark-validity.md) | Before reporting accuracy/cost numbers |

### Reference

| File | Contents |
|------|----------|
| [reference/model-pool.md](reference/model-pool.md) | Verified models, pricing, and pool config |
| [reference/harness-api.md](reference/harness-api.md) | Harness function signatures and module layout |
| [reference/pareto-numbers.md](reference/pareto-numbers.md) | Definitive live-measured Pareto table |

### Examples

| File | What it shows |
|------|--------------|
| [examples/gateway-curl.md](examples/gateway-curl.md) | Live curl session: easy Q routes cheap, hard Q routes strong |

### Troubleshooting

| File | Problem it solves |
|------|------------------|
| [troubleshooting/empty-response-reasoning-model.md](troubleshooting/empty-response-reasoning-model.md) | Blank content from gpt-5/o-series |
| [troubleshooting/cost-accounting-grok.md](troubleshooting/cost-accounting-grok.md) | grok-4.x hides reasoning tokens; ticks conversion |
| [troubleshooting/classifier-collapses-to-baseline.md](troubleshooting/classifier-collapses-to-baseline.md) | Logistic router stuck at cheap baseline accuracy |
| [troubleshooting/self-confidence-gate-non-discriminative.md](troubleshooting/self-confidence-gate-non-discriminative.md) | FrugalGPT gate accepts wrong answers at all thresholds |

---

## Source of Truth

Distillation artifacts (gotchas, patterns, recipes from `05-distillation/`) are the canonical
source. Skill-pack files link to or summarize them; when in doubt, follow the link to `05-distillation/`.
