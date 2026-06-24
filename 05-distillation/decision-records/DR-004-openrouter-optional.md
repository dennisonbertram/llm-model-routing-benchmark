# DR-004: Why OpenRouter Is Optional in This Degree

**Date**: 2026-06-21
**Status**: Accepted
**Evidence tier**: Live verified (L0) for the core degree; Research supported for OpenRouter-specific claims

---

## Decision

OpenRouter (`OPENROUTER_API_KEY`) is an optional enhancement in this degree. All 15
core POCs (L0–L5, X1–X5, capstone) run against OpenAI and Anthropic directly. If the
OpenRouter key is present, it can be used as an additional backend for open-weight
models and for native per-generation cost accounting. If absent, all POCs run fully
on direct provider access.

---

## Context

OpenRouter provides a single endpoint (`https://openrouter.ai/api/v1`) that proxies
to 300+ models including open-weight models (Qwen, Llama, DeepSeek, Mistral, Grok).
It also provides `GET /api/v1/generation?id=<gen-id>` which returns authoritative cost,
provider, and latency after each call — useful for cost accounting where provider-native
USD fields are absent.

The spec explicitly states: "If the key appears, add an OpenRouter backend to unlock
open models + native per-generation cost accounting. Until then, do NOT use OpenRouter."

---

## Rationale

**Avoiding credential dependency.** The core degree goal is to teach model routing
discipline — building the outcome matrix, training classifiers, evaluating on a Pareto
frontier. This is achievable with two tiers (cheap `gpt-4o-mini` and strong `gpt-4.1`)
from a single provider. Adding an OpenRouter dependency would make all POCs fail for
anyone who only has an OpenAI key.

**Separation of concerns.** OpenRouter's value-add features (provider routing controls,
fallback lists, multi-provider access) are covered in the separate `openrouter` degree
(`01-unified-inference-gateway`). Duplicating that content here would dilute both degrees.
The model-routing degree focuses on the routing decision itself — what model to use for
a given query — not on the mechanics of multi-provider delivery.

**The two-tier pool is sufficient to demonstrate all routing concepts.** A single
cheap/strong pair with a measurable accuracy gap is enough to demonstrate: heuristic
routing, predictive routing (embedding k-NN, logistic classifier), FrugalGPT cascades,
AutoMix verification, ensemble methods, and a deployed gateway. A larger model pool
adds interesting Pareto dimensions but is not required to establish the concepts.

**OpenRouter as an enhancement path.** Once the core degree concepts are established,
OpenRouter can be added to:
1. Expand the model pool to include open-weight models and measure how Qwen/Llama fit
   on the Pareto curve.
2. Use `GET /generation` for authoritative cost accounting, supplementing or replacing
   the token×price method.
3. Demonstrate multi-provider fallback as a routing strategy (covered in L5 at the
   single-provider level; OpenRouter extends this across providers).

---

## Consequences

- **gpt-4.1-nano and gpt-4.1-mini** are in the model pool (`config.py`) but not used as
  the primary cheap/strong pair. They could fill intermediate Pareto positions if benchmarked.
- **Open-weight models** (Qwen, Llama 3.x, DeepSeek) are not benchmarked in this degree.
  Their position on the Pareto frontier vs. gpt-4.1 and gpt-4o-mini is unknown from this
  degree. The Agent University `openrouter` degree covers these via OpenRouter.
- **Native per-generation cost** is not used. Token×price (DR-001) is the cost method.
  If OpenRouter is added, `GET /generation` could supplement or validate token×price.

---

## Evidence

- spec (`model-routing-spec.md`): "OPENROUTER_API_KEY — NOT on disk in this workspace. OPTIONAL enhancement. If the key appears, add an OpenRouter backend... Until then, do NOT use OpenRouter." (Spec decision)
- L0 README.md: all three providers (OpenAI, Anthropic, xAI) confirmed live without OpenRouter. (Live verified)
- results-digest.md: full 45-task benchmark completed without OpenRouter. (Live verified)
- openrouter degree (`01-unified-inference-gateway`): covers OpenRouter-specific features including GET /generation, provider routing controls, and multi-model fallback. (Research supported by that degree's live evidence)
