# No-Mock Enforcement Plan

## Why no mocks

This degree's entire value is **measured cost-vs-quality behavior of real models under real routing
decisions**. A mock cannot reveal any of the things the degree exists to prove: which model a router
actually picks, what an answer actually costs in tokens, whether a cheap model is silently wrong (FM-1
silent misroute), whether escalation actually fired, whether the cheap ensemble actually beats a single
SOTA model, or where a router actually sits on the Pareto frontier. A mocked response would let an agent
"prove" any savings number it likes — which is exactly the fabrication risk (R1) this degree must avoid.
Therefore **no mock, stub, recorded cassette, or HTTP interceptor may substitute for a real provider
response** when making a claim about:

- Which model/tier a router selected (routing decision)
- Cost figures (tokens, uniform USD, native xAI ticks)
- Accuracy / pass rate / grade of any answer
- Escalation behavior (did the cascade/verifier escalate; did the gate fire)
- Ensemble outcomes (MoA / self-consistency / debate vs single strong — win OR loss)
- Fallback behavior (did models[1] serve when models[0] failed)
- Real error bodies (invalid slug 4xx, 429, timeout) and recovery
- Budget-guard trips
- Where a router lands on the Pareto frontier

These require **real responses from real providers** (OpenAI / Anthropic / xAI). A mocked response hides
routing drift, real billing, schema/format failures, and the actual quality of cheap models.

## What counts as real evidence

A POC is green only with at least one of, recorded in `04-logs/live-evidence-ledger.md`:

1. **A real provider response** captured through `harness/providers.chat` / `embed` — with real
   `prompt_tokens` / `completion_tokens`, a `finish_reason`, and the model id actually served.
2. **A uniformly-computed USD cost** from `usd_for(model, pt, billed_ct)` over those real token counts
   (and, for xAI, the native `cost_in_usd_ticks` recorded alongside for transparency).
3. **An executed code test** — for coding POCs, the model's produced code run against hidden unit tests in
   a subprocess (`code_grader`), passing iff the subprocess exits 0.
4. **An over-the-wire transcript** — for L4/capstone, a real HTTP request/response + the ledger rows it
   produced.

The `green-output.txt` captures the full passing run; `red-output.txt` captures the prior failing run.
Both are part of the evidence.

## What MAY be unit-tested without live calls (clearly labeled)

These are internal helpers — testing them with synthetic inputs is fine, but such tests are labeled
**`Invalid for service evidence`** and may NOT back any routing/cost/quality claim:

- The numpy logistic-regression fit (loss-decreases / shapes) on synthetic vectors.
- `metrics.pareto_front` / `format_table` on hand-built rows.
- The heuristic feature extractor on fixed strings.
- The OpenAI-shape request/response adapter formatting (given a fixed harness result).
- The ledger writer / JSON serialization.
- The cache key function.

## Enforcement mechanisms

1. **Credentials guard, not mock**: each live test `@unittest.skipIf(missing_keys, ...)` — a missing key
   **skips** (and is recorded in `04-logs/access-blockers.md`), it never silently passes against a mock.
2. **Cache is not a mock**: `harness/cache.py` stores real first-run responses keyed on the exact call;
   a cache hit replays a **real** response (marked `cached: True`, latency zeroed, cost preserved). The
   first run of every pair is a real billed event. Clearing `.cache` re-bills and re-verifies. A cache
   entry is real evidence; a hand-written fixture is not.
3. **Ledger gate**: a POC marked green without real token/cost numbers in
   `04-logs/live-evidence-ledger.md` is "claimed green, unverified" — not green.
4. **Opus honesty review**: greps the distillation/skill-pack for any number not traceable to a captured
   live call or a cited source; checks every rank-bearing section carries an evidence label; flags any
   `Live verified` claim lacking ledger backing.

## Forbidden-pattern catalog

| Forbidden pattern | Why |
|---|---|
| `unittest.mock` / `responses` / `httpretty` / `respx` over the provider HTTP call | Hides the real routing decision, cost, and quality |
| Hardcoded `usd` / accuracy / savings-% fixture | Fabricates the exact numbers the degree must measure |
| A pre-recorded cassette standing in for a routing-variant run | Hides provider/model selection drift |
| A local model (Ollama/vLLM) posing as the routed backend | Not the real provider; cost/quality/routing not exercised |
| Skipping the deterministic grader and asserting "looks right" | Bypasses the real correctness signal (FM-1) |
| Asserting a cheap-ensemble win the run did not produce | Violates the honesty rule; loss is a valid result |
| Treating a hand-written number as `Live verified` | Only ledger-backed measured values are `Live verified` |
