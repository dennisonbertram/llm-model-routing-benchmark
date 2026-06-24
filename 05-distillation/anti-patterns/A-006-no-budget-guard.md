# A-006: No Budget Guard — Deploying a Router Without a Hard USD Ceiling

**Category**: anti-pattern
**Severity**: medium — leads to unbounded spend in production, especially for strong-heavy traffic
**Evidence tier**: Live verified
**Source POCs**: L5-failure-modes-and-observability, L-capstone-adaptive-routing-gateway

---

## What the anti-pattern looks like

Shipping a routing gateway that routes to the strong model whenever the classifier
decides it is needed — without any mechanism to stop routing to the strong model once
a per-session or per-request cost cap has been exceeded.

This is particularly dangerous when:
- The classifier has a high false-negative rate (routes too many items to strong)
- The workload shifts (suddenly more hard-math queries than usual)
- A client issues pathological prompts that always score below the routing threshold

---

## What happens without a guard

Without a budget guard, a session that triggers the strong model on every request will
spend `n_requests × strong_cost_per_request`. For `gpt-4.1` on coding tasks, this can
reach $0.002–$0.003 per request. A 100-request session would cost $0.20–$0.30. For a
multi-tenant gateway serving thousands of sessions, unbounded strong-routing can exhaust
a budget quickly.

---

## How the budget guard works (live verified)

**Live verified** (L5; capstone)

The capstone gateway (`run_capstone.py`) and the L5 failure-mode tests implement a
`remaining_budget` guard that checks estimated cost before accepting each request:

1. Compute the estimated cost of the routing decision (cheap or strong).
2. If `estimated_cost > remaining_budget`, downgrade to cheap.
3. If even cheap would exceed the budget, refuse the request with
   `decision=budget_guard(spent=$X>=cap)` and HTTP 429.

L5 live result with `budget=$0.000015` across 4 requests:

| Request | Decision | Model | USD spent | Running total |
|---|---|---|---|---|
| b1 | accepted | gpt-4o-mini | $0.00000405 | $0.00000405 |
| b2 | accepted | gpt-4o-mini | $0.00000375 | $0.00000780 |
| b3 | accepted | gpt-4o-mini | $0.00000360 | $0.00001140 |
| b4 | **refused** | — | — | remaining $0.00000360 < cheapest model $0.00000375 |

Capstone live result with `budget=$0.00025` on 6 requests: requests 1–4 routed
normally; requests 5–6 forced cheap by the budget guard.

---

## The guard does not eliminate cost surprises — it contains them

**Live verified** (L5)

Note: the budget guard uses estimated cost from token count, not actual billed cost.
For very short answers (~$0.000004 each), the budget cap fires after ~3–4 requests at a
$0.000015 cap. At production scale where answers are longer and strong-model calls cost
$0.001–$0.002, the same guard fires much sooner.

The guard should be set based on:
- The maximum acceptable spend per session (user-facing: link to billing SLA)
- The expected request volume and mix
- The cost-per-request distribution (profile on your real workload first)

Do not set the cap so low that it fires on the first legitimate strong-model request.
Profile the cost distribution before calibrating the guard.

---

## Structured observability is required for the budget guard to be auditable

**Live verified** (L5; L4)

The budget guard emits structured log lines so every decision is auditable:

```json
{"ts": "23:49:48", "event": "budget_guard", "task": "b4", "decision": "refused",
 "reason": "no_model_fits_budget", "remaining_usd": 3.6e-06}
```

Without a per-request cost log, you cannot tell after the fact whether the guard fired
appropriately, whether it was too aggressive, or whether spend is tracking to plan.
The JSONL ledger (`cost-ledger.jsonl` in L4, `gateway-ledger.jsonl` in the capstone)
is the audit trail that makes the guard meaningful.

---

## Evidence

- L5 README.md, FM4: "Budget: $0.000015. The guard correctly refused b4 because even the cheapest model ($0.00000375) would have exceeded the $0.00000360 remaining." (Live verified)
- Capstone README.md: "Budget guard ($0.00025 cap): reqs 5–6 forced cheap." (Live verified)
- results-digest.md, Gotcha 8: "Cost-budget guard only bites when per-call cost is real (short answers are ~$0.0001 each)." (Live verified)
- L4 README.md: "The ledger enables offline cost audit, routing pattern analysis, and budget guard implementation in later POCs." (Live verified)
