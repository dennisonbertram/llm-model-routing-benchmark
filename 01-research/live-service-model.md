# Live Service Model

**Target**: Model Routing — 01-llm-model-routing
**Gathered**: 2026-06-21 (WebFetch + WebSearch against live docs)
**Evidence**: Research supported but not live verified (research files; POC live verification is in 03-pocs/).

---

## What "live" means for this degree

The live substrate for this degree is the **set of real provider APIs** the router dispatches to. A router makes a routing decision (model selection), then executes a real API call, then records accuracy + cost + latency on the response. All measurement happens at the provider boundary, not inside the router itself.

Three providers are in scope (all verified reachable from this workspace as of 2026-06-21 per the spec):

| Provider | Base URL | Auth | Cost field in response? |
|---|---|---|---|
| OpenAI | `https://api.openai.com/v1` | `Authorization: Bearer $OPENAI_API_KEY` | No — must compute from price table |
| Anthropic | `https://api.anthropic.com/v1` | `x-api-key: $ANTHROPIC_API_KEY` | No — must compute from price table |
| xAI | `https://api.x.ai/v1` (OpenAI-compatible) | `Authorization: Bearer $XAI_API_KEY` | **Yes** — `usage.cost_in_usd_ticks` |
| OpenRouter (optional) | `https://openrouter.ai/api/v1` | `Authorization: Bearer $OPENROUTER_API_KEY` | **Yes** — `usage.cost` (USD) inline; also `GET /api/v1/generation?id=<gen-id>` |

---

## Measurement model: per-call record

Every router dispatch MUST record a structured record. The shared harness `providers.py` returns this shape:

```python
{
  "model": "gpt-4.1-mini",
  "prompt_tokens": 142,
  "completion_tokens": 38,
  "latency_ms": 831,
  "usd": 0.000049,     # computed by harness via pricing.py (see below)
  "text": "...",
  "raw": { ... }       # full provider response, for debugging
}
```

The harness derives `usd` from a price table (see `pricing-quotas-limits.md`), not from provider-returned cost — **except for xAI and OpenRouter**, which return cost natively.

Accuracy is scored separately via `judge.py` after the call returns.

---

## OpenAI cost accounting — price-table required

OpenAI chat completions (`POST /v1/chat/completions`) return token counts in `usage` but **no USD cost**:

```json
"usage": {
  "prompt_tokens": 142,
  "completion_tokens": 38,
  "total_tokens": 180
}
```

To compute cost:

```python
usd = (prompt_tokens / 1_000_000) * price_in_per_M + \
      (completion_tokens / 1_000_000) * price_out_per_M
```

Where prices are fetched from the OpenAI pricing page and stored in `pricing.py`. The price table must be updated when new models are added to the pool; the harness does not auto-fetch live prices.

Source: OpenAI API reference; `pricing-quotas-limits.md` records the price table with date and URL.

---

## Anthropic cost accounting — price-table required

Anthropic messages API (`POST /v1/messages`) similarly returns only token counts:

```json
"usage": {
  "input_tokens": 142,
  "output_tokens": 38
}
```

Same formula applies. Required headers: `x-api-key`, `anthropic-version: 2023-06-01`. Response content is at `content[0].text`, not `choices[0].message.content` like OpenAI.

Source: Anthropic API documentation; see `pricing-quotas-limits.md` for current prices.

---

## xAI cost accounting — native per-request USD via ticks

xAI's API (OpenAI-compatible at `https://api.x.ai/v1`) **does return cost per request** in a non-standard field:

```json
"usage": {
  "input_tokens": 199,
  "output_tokens": 1,
  "total_tokens": 200,
  "cost_in_usd_ticks": 158500
}
```

**Conversion**: 1 USD = 10,000,000,000 ticks (10^10).

```python
usd = response["usage"]["cost_in_usd_ticks"] / 1e10
```

The cost reflects actual billed amount after discounts, including all reasoning tokens (grok-4.3 always spends reasoning tokens by default) and server-side tool invocations. The xAI SDK exposes a `cost_usd` convenience property that performs this division automatically.

Source: xAI Cost Tracking documentation — https://docs.x.ai/developers/cost-tracking (fetched 2026-06-21)

**Harness note**: Even though xAI returns native cost, the harness MUST still verify the tick conversion against the price table during L0-smoke to confirm the conversion constant hasn't changed. Record both the raw ticks value and the converted USD in the per-call log.

---

## OpenRouter cost accounting — native USD inline and via /generation

If the optional OpenRouter key is present, OpenRouter returns cost directly in every chat completion response:

```json
"usage": {
  "cost": 0.0000049,          // total cost in USD
  "cost_details": {
    "upstream_inference_cost": 0.0000049,
    "upstream_inference_prompt_cost": 0.0000031,
    "upstream_inference_completions_cost": 0.0000018,
    "cache_discount": null
  }
}
```

For async/deferred cost retrieval, the GET endpoint returns:

```
GET https://openrouter.ai/api/v1/generation?id=<gen-id>
```

Response fields include `total_cost` (number, double, USD), `upstream_inference_cost`, `cache_discount`, `provider_name`, `latency`, `tokens_prompt`, `tokens_completion`, and native tokenizer variants.

**Caveat**: The generation record is written asynchronously. Calling `GET /generation` immediately after a completion call reliably returns 404; poll with backoff (≥6 seconds before first retry). Source: OpenRouter /generation API reference — https://openrouter.ai/docs/api/api-reference/generations/get-generation (fetched 2026-06-21)

---

## Unified vs per-provider cost accounting — implications for routing

A routing harness that spans providers must normalize cost to a single unit (USD) for Pareto comparison. The two approaches are:

**Per-provider price-table** (OpenAI, Anthropic): cost computation is offline; requires maintaining a price table. Prices change; a stale table silently underestimates or overestimates cost. The harness price table in `pricing.py` must record the fetch date and source URL.

**Native cost return** (xAI, OpenRouter): cost is exact and includes any provider-side discounts (caching, batching). No maintenance required, but the harness must still handle the field being absent (graceful fallback to price-table estimate).

Recommended pattern in the harness:

```python
def usd_for_response(model: str, response: dict) -> float:
    usage = response.get("usage", {})
    # xAI: native ticks
    if "cost_in_usd_ticks" in usage:
        return usage["cost_in_usd_ticks"] / 1e10
    # OpenRouter: native USD
    if "cost" in usage and usage["cost"] is not None:
        return float(usage["cost"])
    # OpenAI / Anthropic: price table
    pt = usage.get("prompt_tokens") or usage.get("input_tokens", 0)
    ct = usage.get("completion_tokens") or usage.get("output_tokens", 0)
    return usd_for(model, pt, ct)  # from pricing.py
```

---

## Latency measurement

Latency must wrap the entire HTTP round trip — from request dispatch to last byte received (or stream close). `providers.py` uses `time.perf_counter()` around the call. For streaming responses, latency is time-to-last-chunk, not time-to-first-token (TTFT). If TTFT matters for a POC, measure it separately.

---

## Wire-format incompatibilities that affect the measurement loop

| Model family | Incompatible param | Correct param | Effect if wrong |
|---|---|---|---|
| gpt-5 / o-series | `max_tokens` | `max_completion_tokens` | 400 error: "Unsupported parameter: 'max_tokens' is not supported with this model. Use 'max_completion_tokens' instead." |
| gpt-5 / o-series | `temperature` ≠ 1 | Omit or set to 1 | 400 / silently clamped (behavior varies by model version) |
| Anthropic | `messages[0].role` = `"system"` | Use `system` top-level param | 400 error |
| xAI grok-4.3 | (none known) | — | Always spends reasoning tokens; cost per call higher than expected from token count alone |

Sources: LiteLLM GitHub issue #13381 — https://github.com/BerriAI/litellm/issues/13381; OpenAI developer community thread; confirmed in LiteLLM PR #13390.

The harness `providers.py` branches on model family before assembling the request body. See `known-failure-modes.md` for the full discussion.

---

## Accuracy measurement

Accuracy is scored after the call returns, not during. The harness `judge.py` provides:

- `exact_match(gold, answer)` — normalized string equality for factual QA
- `numeric_match(gold, answer, tol)` — for math tasks
- `run_unit_tests(code, test_src)` — for coding tasks; executes produced code in a subprocess
- `judge_correct(task, answer)` — LLM judge (strong model) for open-ended tasks

A **per-item log** captures: model routed to, tokens, latency, USD, judge verdict, and the raw answer. This log is the primary evidence artifact for all POCs.

---

## Sources

- xAI Cost Tracking: https://docs.x.ai/developers/cost-tracking
- OpenRouter GET /generation API reference: https://openrouter.ai/docs/api/api-reference/generations/get-generation
- OpenRouter Usage Accounting: https://openrouter.ai/docs/cookbook/administration/usage-accounting
- LiteLLM GitHub issue #13381 (gpt-5 max_tokens): https://github.com/BerriAI/litellm/issues/13381
- LiteLLM PR #13390 (fix): https://github.com/BerriAI/litellm/pull/13390
