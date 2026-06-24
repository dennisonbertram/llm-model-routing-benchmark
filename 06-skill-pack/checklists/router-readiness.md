# Checklist: Router Readiness

Live verified (L5; capstone; 2026-06-21/22). Gates before shipping a router to any
environment with real traffic or real money.

Back to [index](../index.md). See also: [live-service-checklist.md](../live-service-checklist.md).

---

## Pre-flight

- [ ] `OPENAI_API_KEY` is set and funded. Unfunded key returns 402 (looks like rate limit).
- [ ] Live smoke passes: one real call to each provider in the pool returns content.
- [ ] `REASONING_FLOOR=2048` is applied for any reasoning model (gpt-5, o-series, grok).
- [ ] gpt-5/o-series: using `max_completion_tokens`, no `temperature` param.
- [ ] grok-4.x: cost tracked from `native_cost_usd`, not tokens × price.

## Router validity

- [ ] Benchmarked on a labeled evaluation suite with no leakage (held-out or CV).
- [ ] Pareto table includes always-cheap, always-strong, oracle (labeled "unrealizable ceiling").
- [ ] Router dominates random-50% on BOTH accuracy AND cost.
      (random-50% baseline: acc=0.909, $0.01177 on the 45-task suite)
- [ ] Threshold was swept and the operating point was chosen deliberately.
- [ ] Ensemble strategies were measured on YOUR workload — not assumed to win.
      (MoA: $0.100 on this suite, 4.64x more than strong — NEGATIVE finding)

## Failure mode coverage

- [ ] Invalid model slug (HTTP 404) → fallback chain recovers.
- [ ] Network timeout → retry with normal timeout, then fallback.
- [ ] `max_tokens` overlimit (HTTP 400) → fallback with capped value.
- [ ] Budget guard tested with synthetic low cap → refused after cap exceeded.
- [ ] Verifier/escalation path tested end-to-end with at least one synthetic failing input.

## Observability

- [ ] Every request logs: ts, decision, served_model, usd, latency_ms, fallback_from, escalated.
- [ ] No API key value in any log line (test explicitly).
- [ ] `p_cheap` (or equivalent) in decision string for auditability.
- [ ] Cost ledger is append-only JSONL; survives gateway restart.
- [ ] `fallback_from` recorded when fallback fires.

## Wire format

- [ ] Response `model` = actually-served model (never "auto").
- [ ] `choices[0].message.content` is non-null.
- [ ] openai.OpenAI(base_url=...) client can call the gateway without modification.
- [ ] HTTP 200 only on valid answers; 4xx on bad requests; 5xx on exhausted fallbacks.

## Economics sanity

- [ ] Deployed router costs less than always-strong on your workload.
- [ ] Deployed router accuracy >= always-cheap baseline.
- [ ] A cascade that costs more than cheap AND achieves only cheap accuracy is a loss
      (L3a FrugalGPT: $0.00391 at acc=0.844 — both conditions failed).
