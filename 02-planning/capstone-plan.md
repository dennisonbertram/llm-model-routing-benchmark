# Capstone Plan

**Name**: Adaptive routing gateway (classifier + cascade + ensemble-fallback + budget guard, served
OpenAI-compatible, benchmarked on the Pareto frontier)
**Degree level**: L-capstone
**Depends on**: L2b (classifier prediction), L3a + X4 (cascade with verification), X1 + X2 (ensemble
fallback for hard queries), L5 (budget guard + failure handling), L3c + L4 (OpenAI-compatible gateway +
cost ledger), X5 (benchmark methodology + oracle) — all confirmed green first.
**Execution**: coordinator-run (serial, one shared cache, budget-bounded).

## What it builds

A single live **adaptive gateway** that an OpenAI-style client calls transparently. For each request:

1. Accepts an OpenAI-shaped `{"model": "router-adaptive", "messages": [...]}` request over the live
   local HTTP server (L4).
2. **Classifies** the query with the L2b logistic-regression model on its embedding → predicts whether
   a cheap model is good enough and an initial difficulty/tier.
3. Routes:
   - predicted-easy → **cheap** model directly;
   - predicted-medium → **cascade** (cheap → verify → escalate to strong on low confidence, L3a/X4);
   - predicted-hard → **ensemble fallback** (cheap MoA/self-consistency, X1/X2) before, or instead of,
     a single strong call — the exact policy is chosen by what X5 showed actually dominates random.
4. Enforces a **cost-budget guard**: a per-request cap and a per-run cap (default $0.10/run); a pre-call
   check stops before any call that would exceed the cap and reports the trip (L5).
5. On a backend failure (invalid slug / timeout / 429), follows a **fallback chain** to a working model
   (L5); never crashes the request.
6. Writes a **ledger row** per request: served model(s), prompt/completion tokens, uniformly-computed
   USD, routing decision/path, latency (L4 / observability-strategy).
7. Returns an OpenAI-shaped response object with `choices[0].message.content` + `usage`.

The capstone is then **benchmarked via X5**: its router row is run over the shared suite and placed on
the cost-vs-quality Pareto frontier next to the four baselines (always-cheap, always-strong, random,
oracle). The honest claim is its **position on the frontier**, with real numbers — not a target.

## Gateway request/response contract (target shape)

```text
POST /v1/chat/completions
{ "model": "router-adaptive", "messages": [{"role":"user","content": "..."}] }

200 OK
{
  "id": "...",
  "model": "<served backend model id>",   # the model the router actually chose
  "choices": [{ "index": 0, "message": {"role":"assistant","content": "..."},
                "finish_reason": "stop" }],
  "usage": { "prompt_tokens": <int>, "completion_tokens": <int>, "total_tokens": <int> }
}
```

Side-channel (header or ledger, not in the OpenAI body): `routing_decision`, `path`
(`cheap|cascade|ensemble`), `usd`, `escalated` (bool), `budget_remaining`.

## Ledger row (target)

```text
ts, request_id, path, models_called[], prompt_tokens, completion_tokens, usd, decision, latency_ms,
escalated, budget_trip(bool)
```

`usd` is the uniformly-computed `usd_for(model, pt, billed_ct)` summed over all backend calls for the
request. No estimated/invented cost; every number traces to a real call.

## Map back to prior POCs

| Capstone component | Proven in |
|---|---|
| OpenAI-compatible request/response adapter | L3c |
| Live local HTTP server + cost ledger | L4 |
| Classifier tier prediction (numpy logistic regression) | L2b (labels from L2 real runs) |
| Cascade with verification gate | L3a |
| Self-verification + escalate variant | X4 |
| Ensemble fallback for hard queries (MoA / self-consistency) | X1 / X2 |
| Cost-budget guard + fallback chain + sanitized errors | L5 |
| Pareto benchmark + oracle ceiling | X5 |
| Baselines anchoring the frontier | L0 |

## Fault-tolerance proof

The test injects a bad first model into the fallback chain (`["bad-model-xyz", "gpt-4o-mini"]`). The
gateway must: not crash on the first-model failure; complete using the working model; return a valid
OpenAI-shaped body; record the **actually served** model in `model` and the ledger (not the requested
bad model).

## Budget-guard proof

A forced over-budget run (cap set very low) must **stop before** the next backend call and report the
trip in the ledger (`budget_trip = true`); no call is made after the cap is reached.

## Benchmark / honesty proof

The capstone's X5 row must (1) **dominate random** (≥ accuracy at ≤ cost, one strict), (2) sit **at or
below oracle** accuracy (oracle is the unrealizable ceiling), and (3) be reported **truthfully** wherever
it lands relative to the naive baselines and the simpler routers — including any case where a simpler
router (e.g. the bare cascade) matches or beats it. All numbers TBD — measured live in the capstone run.

## Definition of done

- [ ] Live gateway: an easy item routes cheap and a hard item routes strong/ensemble (decision in the ledger).
- [ ] Fault-tolerance: injected bad-first-model recovers via fallback; valid OpenAI-shaped body returned.
- [ ] Budget guard: a forced over-budget run trips the cap and stops before the next call.
- [ ] Observability: a ledger row per request with model(s), real tokens, uniform USD, decision, latency.
- [ ] Benchmark: the capstone row is computed via X5, dominates random, sits at/below oracle, and its
      frontier position is reported with real numbers (win or loss).
- [ ] Evidence: real provider responses + token/cost numbers recorded in `04-logs/live-evidence-ledger.md`.
- [ ] No fabricated metrics anywhere; every figure traces to a captured live call.
