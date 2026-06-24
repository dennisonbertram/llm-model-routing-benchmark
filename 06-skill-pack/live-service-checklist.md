# Live-Service Checklist — LLM Model Routing Gateway

Live verified. Gates to pass before shipping a routing gateway to any environment where
real traffic or real money is involved. Derived from the live failure modes triggered in L5
and the capstone's observability contract.

Back to [index](index.md).

---

## 1. Credential and provider readiness

Live verified (L0; L5).

- [ ] `OPENAI_API_KEY` is set and the account has credits. Check: `[ -n "$OPENAI_API_KEY" ] && echo SET || echo UNSET`
- [ ] Live smoke: make one real call to each provider in the pool before starting the gateway.
      A 401/403 means a bad key; a 402 means no credits. Do not start serving traffic on an unfunded key.
- [ ] The `REASONING_FLOOR=2048` guard is in place for any reasoning model in the pool
      (gpt-5, o-series, grok). Blank content from a reasoning model is not a model failure —
      it is a budget starvation caused by calling without the floor.
- [ ] For gpt-5/o-series: `max_completion_tokens` (not `max_tokens`), and no `temperature` param.
- [ ] For grok-4.x: cost is tracked from `native_cost_usd` (provider's field), not tokens × price.
      Ticks conversion: `cost_in_usd_ticks / 1e10`. Record the conversion factor in a comment.

---

## 2. Router validity

Live verified (L2b; X5; capstone).

- [ ] The router was benchmarked on a labeled evaluation suite with no leakage (held-out or CV).
- [ ] The Pareto table includes: always-cheap baseline, always-strong baseline, and the oracle
      labeled "unrealizable ceiling." Do not compare a deployable router against the oracle as
      if the oracle were achievable.
- [ ] The router dominates random-50% on both accuracy AND cost. If it does not, it is not
      useful. Random-50% baseline: acc=0.909, $0.01177 on the 45-task suite.
- [ ] The decision threshold was swept across its range and the operating point was chosen
      deliberately (not just the highest-accuracy point). The operator understands the cost at
      each threshold level.
- [ ] Ensemble strategies (MoA, self-consistency, debate) have been measured on YOUR workload,
      not assumed to win. On a hard-reasoning-tail workload, they may cost more than strong
      while being less accurate. (X1: $0.100 MoA vs $0.021 strong; X2: 9/15 @5 vs 14/15 single.)

---

## 3. Failure mode coverage

Live verified (L5).

- [ ] Invalid model slug (HTTP 404) is handled: fallback chain recovers, does not crash.
      Live error: `"The model 'gpt-9000-doesnt-exist' does not exist or you do not have access to it."`
- [ ] Network timeout is handled: retry with normal timeout, then fall back. Do not propagate
      `urllib.error.URLError` to the client.
- [ ] `max_tokens` overlimit (HTTP 400) is handled: retry with a capped value (e.g., 64 tokens).
      Live error: `"max_tokens is too large: 999999. This model supports at most 16384."`
- [ ] Cost-budget guard is tested with a synthetic low cap: confirm requests are refused
      (`no_model_fits_budget`) after the cap is exceeded, and that accepted requests accumulate
      actual measured cost (not estimated).
- [ ] Verifier/escalation path is tested end-to-end: at least one synthetic test confirms that
      a known-failing cheap-model answer triggers the escalation to strong.

---

## 4. Observability contract

Live verified (L5; capstone).

- [ ] Every request emits a structured JSON log line containing:
      `ts`, `decision`, `served_model`, `usd`, `latency_ms`, `fallback_from`, `escalated`.
- [ ] No API key or secret value appears in any log line. Verify with a test that scans log
      output for the known key prefix.
- [ ] `p_cheap` (or equivalent classifier probability) is included in the `decision` field
      so every routing decision is auditable: `"classifier(p_cheap=0.97,thr=0.6)"`.
- [ ] The cost ledger is append-only JSONL, not in-memory only. Confirm it survives a gateway
      restart.
- [ ] `fallback_from` is recorded when a fallback fires, so you can distinguish "routed cheap
      by design" from "routed cheap because primary failed."

---

## 5. Wire-format compliance

Live verified (L3c; L4; capstone).

- [ ] The gateway returns a valid OpenAI-shaped `chat.completion` object with:
      - `model` = the ACTUALLY-served model (never `"auto"`)
      - `choices[0].message.content` = non-null text
      - `usage` with `prompt_tokens`, `completion_tokens`, `total_tokens`
- [ ] A standard `openai.OpenAI(base_url=..., api_key="x")` client can call the gateway
      without modification.
- [ ] Any non-standard fields (e.g., `x_routing_decision`, `x_routing`) are in a named
      extension field. Standard clients ignore them.
- [ ] The gateway returns HTTP 200 only when it has a valid answer. Bad requests return 4xx.
      Upstream provider failures that exhausted the fallback chain return 5xx.

---

## 6. Cost and economics sanity check

Live verified (L0; X5; capstone).

- [ ] The measured cost of the deployed router is less than always-strong on your workload.
      If it is not, you are either mis-configured or the workload has no routing leverage.
- [ ] The accuracy of the deployed router is at or above the always-cheap baseline.
      A router that costs more than cheap AND achieves only cheap accuracy is a net loss.
      (L3a FrugalGPT: $0.00391 at acc=0.844 — both conditions failed.)
- [ ] Per-call cost is real, not estimated. The harness computes `usd = tokens × unit_price`
      from a reconciled price table. Use the same price table for the gateway cost ledger.
- [ ] The budget guard cap is set based on your real per-call cost profile (short answers
      ~$0.0001 each at cheap model prices; the guard only bites when the session hits the cap).
