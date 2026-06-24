# Observability Strategy

The routing discipline lives or dies on observability: the most dangerous failure (FM-1, **silent
misroute** — a cheap model confidently wrong) returns HTTP 200 and degrades quality with **no error
signal**. So the primary evidence is not "did the call succeed" but "what did the router decide, what did
it cost, and was the answer right". Three layers: per-request routing+cost logging, the cost ledger, and
the aggregate metrics.

## Primary signal: per-request routing + cost record

Every routed answer goes through `harness/providers.chat`, which returns a normalized record:

```text
{ model, provider, text, prompt_tokens, completion_tokens, billed_completion_tokens,
  total_tokens, latency_ms, usd, finish_reason, raw_usage, native_cost_usd }
```

Cost is **uniformly computed** for every provider: `usd_for(model, prompt_tokens,
billed_completion_tokens)` = Σ tokens × unit price (from `pricing.PRICES`, reconciled against
`01-research/pricing-quotas-limits.md`). This makes cross-model comparison apples-to-apples.
`billed_completion_tokens` accounts for hidden reasoning tokens (OpenAI folds them into
`completion_tokens`; xAI/grok reports them only in `total`, so the harness bills `max(ct, total−pt)`).
xAI also returns a native `cost_in_usd_ticks` — recorded in `raw_usage`/`native_cost_usd` for
transparency but **not mixed** into the uniform cost (the ticks→USD factor is verified live in L0;
harness uses `1e-9`, xAI docs state `1e-10` = 10^10 ticks/USD — the L0 run records which is correct).

## The cost ledger (L4 / capstone)

The live HTTP gateway persists one **ledger row per request** to a ledger file:

```text
ts, request_id, path(cheap|cascade|ensemble), models_called[], prompt_tokens, completion_tokens,
usd, decision, latency_ms, escalated(bool), budget_trip(bool)
```

`usd` is the sum over all backend calls for that request. The ledger is the runtime evidence: it shows
distinct models chosen for distinct inputs, a running cost total, escalations, and budget trips — over
the wire, not in a unit test. The X5/capstone reports read directly from these rows.

## Aggregate metrics (`harness/metrics.py`)

Per router over a suite, `RunResult` accumulates and reports:

- `accuracy()` — fraction graded correct (deterministic grader).
- `total_usd()` — Σ uniform USD over all items.
- `usd_per_correct()` — cost efficiency (total_usd / #correct).
- `mean_latency()` — surfaces cascade/loop latency compounding (the coding-routing gotcha).
- `pct_cheap(cheap_models)` — routing mix; guards against **routing collapse** (a router silently equal
  to always-cheap or always-strong has `pct_cheap` at 0 or 1).
- `by_difficulty()` — accuracy split by easy/hard, exposing where a router under-routes hard items.
- `pareto_front(rows)` — the non-dominated frontier subset.

## Logging points per POC

1. **Pre-call**: model chosen, routing decision/path, item id, difficulty.
2. **Post-call**: tokens, `usd`, `finish_reason`, latency, grade (correct/incorrect).
3. **Post-run**: the `RunResult.row()` and, for benchmark POCs, the full table + frontier subset.

Logs go to stdout during development and to `green-output.txt` for the captured run; the distilled
evidence rows go to `04-logs/live-evidence-ledger.md`.

## Error observability

Real provider errors flow through `ProviderError`, which captures the **real** HTTP status + a truncated
body (first 500 chars). These are logged to `04-logs/error-log.md`. Bodies are **sanitized** — no API
key, no full request payload. Common cases the POCs exercise or document:

- Invalid model slug → real HTTP 4xx body captured (L5).
- 429 / 5xx → harness retries with backoff (1.5×(attempt+1)s) up to `retries`, then `ProviderError`
  (L5); fallback chain moves to the next model.
- Silent misroute (FM-1, 200 OK but wrong) → **not** caught by HTTP status; caught only by the verifier
  (L3a/X4) or the accuracy metric. This is why correctness is logged per item, not just success.

## What is NOT instrumented here (named honestly)

- No external APM/OTel/Honeycomb wiring — observability is file-based (ledger + logs + metrics tables),
  which is sufficient for the degree's evidence and keeps the POCs stdlib-only. Portkey/OTel-style
  gateway observability is referenced in research as the production path, **not** built here.
- No load testing of fallback storms — backoff+jitter + cooldown are implemented/documented as the
  mitigation but not stress-tested (labeled research-supported, not live-load-verified).

## Honesty note

Every number surfaced by this observability layer is a **measured** value from a real call or a
deterministic grade — never a target or an estimate. Where a metric is not yet measured, the artifact
says "TBD — measured live in <POC>".
