# Blocked Live Work — LLM Model Routing Degree

Items not live-verified, with root cause and unblocking path. As of 2026-06-22.

## BL-1: OpenRouter backend (OPTIONAL — key not in workspace)

**Status**: Optional enhancement, not required for degree completion.

**What is blocked**: Adding an OpenRouter backend to the adaptive gateway to unlock open models
(Qwen, Llama, DeepSeek, Mistral) and native per-generation cost accounting (`GET /generation`).

**Root cause**: `OPENROUTER_API_KEY` is not present in `.agent-university/secrets.local.env`
for this workspace. The spec explicitly marks OpenRouter optional.

**Unblocking path**: If the key is added to the secrets file, extend the gateway's provider
dispatch table with an OpenRouter backend, wire the `GET /generation` poll for authoritative
cost, and add a one-pass benchmark POC (e.g., X6-openrouter-open-models) to measure cost-quality
with open models as the "cheap" pool. The unified-inference-gateway degree already has a
reference implementation.

**Impact on existing corpus**: None. All existing POC numbers, routing logic, and evidence are
complete and unaffected.

## BL-2: gpt-5 / o-series at production inference prices

**Status**: Pricing estimated from pricing page; full inference suite not run at these prices.

**What is blocked**: Routing benchmark with gpt-5 as the "strong" model and gpt-4o-mini as cheap.
The cost ratio at gpt-5 prices would be larger, making routing even more valuable.

**Root cause**: gpt-5 was verified live in L0 (provider liveness confirmed) but the full 45-task
suite was not run against it due to cost discipline (pricing at time of research: $2.50/$10.00 per
1M in/out tokens estimated). Running the suite would cost roughly $0.02–$0.05 at those prices.

**Unblocking path**: Run L0 with `STRONG_DEFAULT=gpt-5` and recheck the oracle headroom.
Expected: oracle gap widens (gpt-5 solves more hard-math), routing premium increases.

## BL-3: grok-4.3 in the routing pool

**Status**: Provider liveness confirmed (L0 smoke); not included in the routing suite.

**What is blocked**: A benchmark comparing grok-4.3 as a strong model against gpt-4.1, and
measuring the cost of grok's reasoning overhead when it is the "strong" endpoint.

**Root cause**: grok-4.3 always spends reasoning tokens (bills total − prompt), the ticks
conversion is live-verified as /1e10 but native cost still diverges ~1.5× from token×price.
Fair cross-model cost comparison requires trust in provider-reported costs rather than our
uniform pricing model. Excluded to avoid misleading cost comparisons.

**Unblocking path**: Use `native_cost_usd` field (grok provider field in harness) for grok
calls specifically; add a `--native-cost` flag to the benchmark runner and re-measure.

## BL-4: Anthropic models as strong pool

**Status**: claude-haiku-4-5-20251001 was used as an ensemble member (X1, X3). claude-sonnet-4-6
and claude-opus-4-8 were not used as routing targets.

**What is blocked**: Routing with Anthropic mid/strong as the "strong" option — would demonstrate
cross-provider routing is wire-compatible.

**Root cause**: ANTHROPIC_API_KEY is available; the exclusion was a scope decision to keep the
main pool comparable (OpenAI only) and avoid cross-provider pricing normalization complexity.

**Unblocking path**: Wire Anthropic chat via the harness `providers.py` (already implemented);
add claude-sonnet or claude-opus as `config.STRONG_DEFAULT` in an X6 or extension POC.
