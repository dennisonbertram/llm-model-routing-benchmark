# Known Failure Modes

**Target**: Model Routing — 01-llm-model-routing
**Gathered**: 2026-06-21 (WebFetch + WebSearch against live docs and papers)
**Evidence**: Research supported but not live verified (research files; failure triggering and mitigation are live-verified in L5-failure-modes-and-observability).

---

## Overview

Routing failure modes fall into three categories:

- **Decision failures**: the router picks the wrong model (misroute, judge error)
- **Infrastructure failures**: provider is unavailable or misbehaving (outage, 429, timeout)
- **Configuration/drift failures**: the router's assumptions about the world go stale (model-id drift, param incompatibility, price table staleness)

Each mode is catalogued below with: root cause, symptom, detection, and mitigation.

---

## FM-1: Misroute — cheap model silently wrong

**Description**: The router sends a query to a cheap model that cannot answer it correctly. The cheap model returns a plausible-looking but wrong answer. The system logs a 200 OK and records lower cost. No error is raised.

**Why it's dangerous**: This is the most dangerous failure mode — silent quality degradation. Standard HTTP error tracking misses it entirely. In production, "you route aggressively to cheap models, costs drop, everything looks fine — until retention metrics move." Users retry or abandon features rather than complaining explicitly. Source: https://tianpan.co/blog/2025-10-19-llm-routing-production (fetched 2026-06-21).

**Root causes**:
1. Routing threshold miscalibrated: confidence threshold for escalation is too low.
2. Router trained on a different query distribution than production traffic (distribution drift).
3. A cheap model has quietly improved or degraded between router training and deployment.

**Symptoms**:
- Accuracy metric on held-out suite drops vs baseline
- Retry rate increases in application logs
- Cheaper models receiving a disproportionate fraction of hard queries

**Detection**:
- Run a golden eval suite (the shared task suites in `tasks.py`) on every router deployment
- Track accuracy-per-model-tier in the routing ledger: if the cheap tier's accuracy falls below the threshold you calibrated at training time, the router is misrouting
- Monitor application-level quality signals (explicit feedback, task completion rate by model tier)

**Mitigation**:
- Use a verifier gate in the cascade: after the cheap model answers, a verifier (cheap model or LLM judge) scores the answer; escalate on low confidence (see FM-2 for verifier failure)
- Re-calibrate threshold monthly as traffic distribution shifts — treat the router itself as a production model with a retraining schedule
- Set a minimum escalation budget: never send more than X% of requests to the cheap tier without quality evidence

---

## FM-2: Verifier / judge error — wrong escalation decision

**Description**: In LLM cascades (FrugalGPT, AutoMix, X4-verification-cascade), a verifier/judge model assesses whether a cheap model's answer is correct and decides whether to escalate to a stronger model. A false positive (verifier says "correct" when wrong) lets a bad answer through. A false negative (verifier says "wrong" when correct) causes unnecessary escalation and wasted cost.

**Root cause**: LLM self-verification is unreliable. Research shows that "self-verification can be effective in cascading systems when combined with other mechanisms," but standalone self-verification is prone to overconfidence. Source: Dynamic Model Routing and Cascading survey — https://arxiv.org/html/2603.04445v2 (fetched 2026-06-21). Research on LLM judges also shows susceptibility to cognitive biases (position bias, verbosity bias).

**FrugalGPT-specific**: the generation scoring function that FrugalGPT uses to decide whether to stop the cascade "is uncertain" in cases where all APIs give the same answer — it cannot distinguish between a correct consensus and a consistently wrong one. Source: FrugalGPT paper analysis (https://ar5iv.labs.arxiv.org/html/2305.05176, fetched 2026-06-21).

**Symptoms**:
- False positives: accuracy on hard queries is lower than always-strong baseline
- False negatives: cost savings are lower than expected; strong model invoked too often

**Detection**:
- Compare verifier verdict against ground-truth labels on the held-out task suite
- Track verifier error rate separately from router accuracy

**Mitigation**:
- Use closed-form graders where possible (unit tests for coding, `exact_match`/`numeric_match` for QA/math) — these have zero error rate and are far more reliable than LLM judges
- For open-ended tasks, use the strongest available model as judge and disclose its error rate
- Combine self-verification with other signals (e.g., multiple samples, consistency checking) rather than relying on a single LLM self-assessment
- Tune the verification threshold conservatively: prefer false negatives (unnecessary escalation) over false positives (bad answer delivered)

---

## FM-3: Fallback storm

**Description**: A provider goes down (or starts returning 5xx/429). The router's fallback chain triggers. All or most requests fall back to the next tier. If the next tier also becomes overloaded (because it's receiving 10× its normal traffic), it starts returning 429s. The fallback chain cascades — each tier fails, pushing traffic to the next. Eventually all tiers are saturated.

**Root cause**: synchronized retry waves. When a large fleet of clients all receive errors at the same time and all retry with the same backoff schedule, they create synchronized bursts that overload the next tier. Source: https://www.getmaxim.ai/articles/failover-routing-strategies-for-llms-in-enterprise-ai-applications/ (fetched 2026-06-21).

**Symptoms**:
- Latency spikes across the board
- 429 errors appearing on normally-reliable tiers
- Cost spike (everything escalating to strong tier)
- The primary provider recovering but requests not returning to it

**Detection**:
- Monitor `routing_ledger.jsonl` for model distribution shift: if the cheap-tier fraction drops from 60% to 5% in 5 minutes, a fallback storm is in progress
- Alerting on 429 rate by provider tier

**Mitigation**:
- **Exponential backoff with jitter** on every retry: prevents synchronized retry waves. Jitter must be random per-request (not per-process).
- **Circuit breaker**: track the failure rate per provider; trip open after exceeding a threshold; skip the provider entirely for a cooldown period rather than waiting for timeouts on every request. LiteLLM Router implements `allowed_fails` + `cooldown_time` exactly for this. Source: LiteLLM routing docs (https://docs.litellm.ai/docs/routing, fetched 2026-06-21).
- **Budget cap on escalation**: `max_escalation_fraction` — if more than X% of requests are on the fallback tier, hold rather than cascading further (return an error or queue).
- **Separate retry budgets per tier**: don't let fallback chain depth be unbounded.

---

## FM-4: Cost runaway

**Description**: The router's cost-control assumptions break and cost spends far exceeds the expected budget. Common causes:
1. Fallback storm pushes everything to the expensive tier (see FM-3)
2. Reasoning models (grok-4.3, o-series) accumulate large reasoning-token costs that weren't accounted for in the price table
3. A cascade's escalation threshold is set too low, causing near-universal escalation
4. A cost-budget guard was not implemented, so a runaway loop accumulates unbounded spend

**Symptoms**:
- Billing alert fires
- `ledger.jsonl` shows all requests on the strong model
- Mean cost per request is 10× expected

**Detection**:
- Per-session and per-minute rolling cost tracked against a configurable budget cap
- Alert if rolling cost exceeds `max_usd_per_minute` threshold

**Mitigation**:
- **Hard cost budget guard** in the gateway: after each request, add cost to a rolling window; if the window exceeds the budget, return 429/503 with a `Retry-After` header rather than making more calls
- For reasoning models (grok-4.3, o-series): the price table must include reasoning tokens at their published rate; `cost_in_usd_ticks` (xAI) includes reasoning tokens in the billed amount, so no extra computation needed if using native cost
- For o-series: use `max_completion_tokens` (not `max_tokens`) to cap total output+reasoning token budget
- Test the budget guard explicitly in L5 by running a tight budget and verifying it trips

---

## FM-5: Provider outage / timeout / 429

**Description**: A provider is unreachable or slow. API calls hang until timeout or return 5xx/429. Without a timeout and fallback, the caller blocks indefinitely or receives an error with no recovery.

**Common sub-patterns**:
- **Complete outage** (5xx or connection refused): provider is down
- **Rate limit (429)**: the API key has exhausted its quota; "the provider is up but the requesting key has exhausted its quota." Source: https://www.getmaxim.ai/articles/failover-routing-strategies-for-llms-in-enterprise-ai-applications/ (fetched 2026-06-21)
- **Latency degradation**: provider is up but slow; response arrives after the application's UX SLA
- **Authentication failure**: key was rotated but the harness wasn't updated

**Detection**:
- Track per-provider HTTP status code distribution in the ledger
- Track per-call latency; alert on p95 > threshold

**Mitigation**:
- Always set a `timeout` on provider HTTP calls (e.g., 30s for a non-streaming request)
- On 429: read `Retry-After` header if present; otherwise use exponential backoff with jitter; do not immediately fall back to a stronger (and more expensive) model just because of a 429 — retry first
- On 5xx: fall back immediately to the next provider in the fallback chain
- On timeout: fall back with a reduced timeout on the fallback call (don't wait 30s twice)
- **Never treat a fallback provider as reliable if it hasn't received real traffic recently** — a cold backup is a guess, not a backup. Test fallback paths regularly.

---

## FM-6: Model-ID drift — model renamed or deprecated

**Description**: A provider renames, aliases, or deprecates a model ID. The router's model list contains the old ID. Requests to the old ID may:
- Silently redirect to a different (usually newer) model with different behavior, token pricing, and parameter support
- Return a 404 / "model not found" error
- Continue working for a deprecation grace period, then fail suddenly

**Examples**: OpenAI regularly deprecates model IDs (e.g., `gpt-4-0613` → sunset); Anthropic moves model aliases; providers may silently point an alias at a newer checkpoint.

"In practice, the set of LLMs may frequently grow or shrink, as new models are released and old models are deprecated." Source: web search results citing https://arxiv.org/pdf/2511.19933 (fetched 2026-06-21).

**Symptoms**:
- Sudden 404 / "model not found" errors for a previously working model
- Unexpected cost increase (alias redirected to a more expensive model)
- Accuracy regression (alias redirected to a model with different capability profile)

**Detection**:
- Compare `response.model` (the model actually used, as returned in the API response) against `requested_model`; log any discrepancy
- Periodically hit `/models` endpoint for each provider to check whether routing targets still exist
- Pin model IDs to dated versions (e.g., `gpt-4.1-mini-2025-04-14`) rather than floating aliases where possible

**Mitigation**:
- Use dated/versioned model IDs in the routing config; never use undated aliases (e.g., `gpt-4` vs `gpt-4-0613`) for production routing
- Log `response.model` on every call; alert when it doesn't match `request.model`
- Keep a `model_aliases` map in the price table: if a model is aliased, record both IDs and their prices

---

## FM-7: Parameter incompatibility — gpt-5 / o-series

**Description**: gpt-5 and o-series models have different API parameter constraints from standard GPT-4 models. Passing incompatible parameters causes a 400 error with an explicit message. The harness must branch on model family before assembling the request.

**Documented incompatibilities** (source: LiteLLM issue #13381 — https://github.com/BerriAI/litellm/issues/13381 and LiteLLM PR #13390 — https://github.com/BerriAI/litellm/pull/13390, fetched 2026-06-21):

| Parameter | Standard GPT-4 behavior | gpt-5 / o-series behavior |
|---|---|---|
| `max_tokens` | Accepted | **Rejected**: "Unsupported parameter: 'max_tokens' is not supported with this model. Use 'max_completion_tokens' instead." |
| `max_completion_tokens` | Not supported (older models) | **Required** for output+reasoning budget |
| `temperature` | Accepted, 0–2 range | Only `1` accepted (or omit); other values may return 400 or be silently clamped |

**Additional incompatibility**: o-series models (and grok-4.3) use reasoning tokens that appear in the completion token count but are not part of the visible output. If your token accounting assumes `completion_tokens = len(output)`, the cost will be underestimated.

**Mitigation** in `providers.py`:

```python
O_SERIES = {"o1", "o1-mini", "o3", "o3-mini", "o4-mini"}
GPT5_FAMILY = {"gpt-5", "gpt-5-mini"}

def build_request_body(model: str, messages: list, **opts) -> dict:
    body = {"model": model, "messages": messages}
    if model in O_SERIES | GPT5_FAMILY:
        if "max_tokens" in opts:
            body["max_completion_tokens"] = opts.pop("max_tokens")
        elif "max_completion_tokens" in opts:
            body["max_completion_tokens"] = opts["max_completion_tokens"]
        # Drop temperature — these models only support temperature=1
        opts.pop("temperature", None)
    else:
        if "max_tokens" in opts:
            body["max_tokens"] = opts["max_tokens"]
        if "temperature" in opts:
            body["temperature"] = opts["temperature"]
    body.update(opts)
    return body
```

LiteLLM's router handles this automatically as of PR #13390.

---

## FM-8: Oracle unrealizable in production

**Description**: The oracle router — which knows in advance which model will give the correct answer for each query — is used as an upper bound in benchmarks (RouterBench-style, RouteLLM, FrugalGPT). It defines the theoretical maximum cost reduction achievable by any router. In production, the oracle is **not deployable** because knowing whether a model will be correct requires either solving the query first or having a perfect quality predictor, which is the problem being solved.

**Why it matters for POC design**: When L5 and X5 benchmark results show that the best trained router achieves, e.g., 85% of the oracle's cost savings, this gap is *irreducible* — it is the fundamental limit of any routing system given the available signals. Do not present a router as "matching the oracle"; that claim is only achievable with label leakage.

**The oracle gap**: RouteLLM reports that its best router (matrix factorization) achieves strong results on MT-Bench and MMLU vs GPT-4 alone, but always below the oracle curve. Source: RouteLLM blog post — https://www.lmsys.org/blog/2024-07-01-routellm/ (fetched 2026-06-21). The exact oracle gap is dataset-specific and should be measured empirically in X5-router-benchmark-pareto.

**In our task suites**: the oracle can be computed offline after all runs complete: for each query, check which models got it right and what the cheapest correct model was. The oracle cost is the sum of cheapest-correct-model costs across all queries. This is the ceiling against which all router results are compared.

**Mitigation** (reporting discipline): always present router results as (accuracy%, cost, oracle_fraction) triplets. Never report cost savings without the accuracy at which they were measured.

---

## FM-9: Routing collapse (trained routers)

**Description**: Trained routers (classifiers, matrix factorization, embedding-kNN) can degenerate during training, collapsing to route almost all queries to one model. This makes the router behave like "always-cheap" or "always-strong" rather than learning to discriminate.

Source: "When Routing Collapses: On the Degenerate Convergence of LLM Routers" — https://arxiv.org/pdf/2602.03478 (fetched 2026-06-21). The paper introduces EquiRouter to address this.

**Symptoms**:
- Router sends >95% of queries to a single model despite a mixed-difficulty task set
- Trained router accuracy is no better than either always-cheap or always-strong baseline
- Pareto curve for the trained router is dominated by (below) the baseline curves

**Causes**:
- Imbalanced training labels (most labeled examples favor one model)
- No regularization to encourage balanced model utilization
- Threshold not swept during eval (reporting a single operating point rather than the full Pareto curve)

**Mitigation**:
- Always sweep thresholds and report the full Pareto curve, not a single point
- Check model distribution in the routing ledger: if one model gets >90% of traffic, something is wrong
- Regularize training to encourage balanced utilization
- Evaluate router with the same held-out split it was not trained on

---

## Summary table

| ID | Mode | Detection | Mitigation |
|---|---|---|---|
| FM-1 | Misroute — cheap model wrong | Per-task accuracy in ledger | Golden eval suite; verifier gate; distribution monitoring |
| FM-2 | Verifier / judge error | Verifier error rate vs gold | Closed-form graders; strong judge model; conservative threshold |
| FM-3 | Fallback storm | Model distribution shift in ledger | Backoff+jitter; circuit breaker; escalation cap |
| FM-4 | Cost runaway | Rolling cost exceeds budget | Hard cost budget guard; include reasoning tokens |
| FM-5 | Provider outage / 429 / timeout | Per-provider error rate | Timeout + retry + fallback chain; test cold backups |
| FM-6 | Model-ID drift | `response.model` != `request.model` | Pin versioned IDs; monitor `/models`; log discrepancies |
| FM-7 | Param incompatibility (gpt-5/o-series) | 400 error on `max_tokens` / `temperature` | Branch on model family in `providers.py` |
| FM-8 | Oracle unrealizable | N/A — design-time concern | Report as upper bound only; compute oracle offline |
| FM-9 | Routing collapse | Model distribution >95% one model | Sweep thresholds; report full Pareto; regularize training |

---

## Sources

- Tianpan.co LLM routing production: https://tianpan.co/blog/2025-10-19-llm-routing-production
- Dynamic Model Routing and Cascading survey: https://arxiv.org/html/2603.04445v2
- FrugalGPT (ar5iv): https://ar5iv.labs.arxiv.org/html/2305.05176
- When Routing Collapses (EquiRouter): https://arxiv.org/pdf/2602.03478
- LLM failover routing strategies: https://www.getmaxim.ai/articles/failover-routing-strategies-for-llms-in-enterprise-ai-applications/
- LiteLLM routing docs: https://docs.litellm.ai/docs/routing
- RouteLLM blog (LMSYS): https://www.lmsys.org/blog/2024-07-01-routellm/
- LiteLLM issue #13381 (gpt-5 max_tokens): https://github.com/BerriAI/litellm/issues/13381
- LiteLLM PR #13390 (fix): https://github.com/BerriAI/litellm/pull/13390
- Failure Modes in LLM Systems taxonomy: https://arxiv.org/pdf/2511.19933
