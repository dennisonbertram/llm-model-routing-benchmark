# Observability Model

**Target**: Model Routing — LLM/model selection for cost-efficient agent inference
**Evidence status**: Research supported but not live verified (no POCs executed yet)
**Grounding**: Portkey LLM observability guide (portkey.ai); LiteLLM router docs (docs.litellm.ai); xAI cost tracking docs (docs.x.ai); OpenRouter observability pattern from `../../openrouter/degrees/01-unified-inference-gateway/01-research/observability-model.md`

---

## Why routing systems need richer observability than single-model systems

A single-model system has one cost centre, one failure mode, and one quality signal. A routing system multiplies each:

- **Multiple cost centres**: cheap model calls + strong model calls + verifier/judge calls each cost differently.
- **Multiple failure modes**: wrong route (misrouted-cheap), provider timeout, cascade budget exhausted, verifier false confidence.
- **Multiple quality signals**: per-item correctness AND the routing decision quality (did the router choose correctly given information available at route time?).

Without structured logs you cannot answer the only question that matters: *did the router improve cost-per-correct answer vs. always-strong?*

---

## Per-request log record

Every call through the harness (`harness/router_base.py`) should emit one structured record. The following schema is the minimum for POC evidence and cost accountability:

```python
@dataclass
class RoutingRecord:
    # Identity
    request_id: str          # UUID generated at route time
    timestamp_iso: str       # ISO-8601, UTC
    suite_item_id: str       # task ID from tasks.py

    # Routing decision
    router_name: str         # e.g. "heuristic", "knn", "classifier", "cascade", "oracle"
    routing_features: dict   # inputs used to make the decision (prompt length, embedding, score)
    model_selected: str      # model ID actually called first
    routing_decision_ms: int # wall-clock ms spent in router.route()

    # Fallback chain (empty list if no fallback occurred)
    fallback_chain: list[str]  # ordered list of model IDs tried before success
    fallback_reason: str | None  # "timeout" | "rate_limit" | "verifier_low" | "budget_exceeded" | None

    # Model call outcome
    model_final: str         # model ID that produced the accepted response
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int          # wall-clock ms from call start to first token or full response
    usd: float               # computed cost: pricing.usd_for(model, pt, ct)

    # Verifier / quality signal (None if not applicable)
    verifier_score: float | None  # 0.0–1.0; from judge or self-score
    grader_correct: bool | None   # final ground-truth grade (for offline evaluation)

    # Cascade-specific (None for non-cascade routers)
    cascade_step: int | None    # which step in the cascade produced the accepted answer (0=first)
    cascade_total_usd: float | None  # cumulative cost including discarded steps
```

### Routing features — what to log

The `routing_features` dict is router-specific. Log everything the router used so you can later audit decisions:

| Router type | Features to log |
|---|---|
| Heuristic | `prompt_len`, `keyword_hits`, `complexity_score` |
| kNN | `embedding_model`, `k`, `neighbor_labels`, `vote_fraction` |
| Classifier | `embedding_model`, `logit`, `threshold`, `predicted_class` |
| Cascade | `verifier_model`, `step_scores`, `threshold` |
| Ensemble (MoA) | `proposer_models`, `aggregator_model`, `agreement_score` |

**Why log features, not just the decision**: if a router misroutes a hard item to the cheap model, you need the features to understand whether the decision was reasonable given available information (weak signal, borderline threshold) or clearly wrong (high-confidence wrong route). Without features you can only see the outcome, not debug the policy.

---

## The cost ledger

The cost ledger is an append-only log of every USD amount spent, accumulated across a POC run. It answers "how much did this routing strategy cost to answer the eval suite?"

### Accumulation pattern

```python
# harness/metrics.py
class CostLedger:
    def __init__(self):
        self._rows: list[dict] = []

    def record(self, rec: RoutingRecord):
        self._rows.append({
            "request_id": rec.request_id,
            "model_final": rec.model_final,
            "usd": rec.usd,
            "cascade_total_usd": rec.cascade_total_usd or rec.usd,
            "correct": rec.grader_correct,
            "timestamp": rec.timestamp_iso,
        })

    def total_usd(self) -> float:
        return sum(r["cascade_total_usd"] for r in self._rows)

    def usd_per_correct(self) -> float:
        correct = [r for r in self._rows if r["correct"]]
        if not correct:
            return float("inf")
        return sum(r["cascade_total_usd"] for r in correct) / len(correct)
```

**Cascade cost gotcha**: in a FrugalGPT-style cascade, a single item may consume two or three model calls (cheap → mid → strong) before the verifier accepts an answer. The cost of all rejected calls is still real cost. `cascade_total_usd` must include ALL steps, not just the final accepted call. See `testing-model.md` for why this matters at the Pareto frontier.

### xAI cost accounting

xAI's Grok returns `cost_in_usd_ticks` in the `usage` object. Conversion: `cost_usd = cost_in_usd_ticks / 10_000_000_000`. This is the actual billed amount inclusive of reasoning tokens (Grok 4.3 always generates reasoning tokens). The `pricing.py` harness module should use this field directly when calling xAI rather than a token × price table, since grok-4.3 has opaque reasoning token counts.

Source: xAI cost tracking docs — https://docs.x.ai/developers/cost-tracking (inferred from docs, not live verified).

### OpenAI / Anthropic cost accounting

Neither OpenAI nor Anthropic return USD in the response. The harness computes cost as:

```python
# harness/pricing.py
PRICE_TABLE = {
    "gpt-4.1-nano":   {"in": 0.10, "out": 0.40},   # USD per 1M tokens
    "gpt-4.1-mini":   {"in": 0.40, "out": 1.60},
    "gpt-4o-mini":    {"in": 0.15, "out": 0.60},
    "gpt-4.1":        {"in": 2.00, "out": 8.00},
    "gpt-4o":         {"in": 2.50, "out": 10.00},
    # ... see pricing-quotas-limits.md for full verified table
    "claude-haiku-4-5-20251001":   {"in": 0.80, "out": 4.00},
    "claude-sonnet-4-5-20250929":  {"in": 3.00, "out": 15.00},
    "claude-opus-4-8":             {"in": 15.00, "out": 75.00},
}

def usd_for(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    p = PRICE_TABLE[model]
    return (prompt_tokens * p["in"] + completion_tokens * p["out"]) / 1_000_000
```

**Pricing drift warning**: model prices change without notice. Every POC report must state the pricing table version and fetch date. See `pricing-quotas-limits.md` for the live-fetched table.

---

## Key metrics

These are the metrics emitted by `harness/metrics.py` at the end of each suite run:

| Metric | Formula | What it measures |
|---|---|---|
| `accuracy` | correct_count / total_items | Overall quality |
| `total_usd` | Σ cascade_total_usd | Total spend for this run |
| `usd_per_correct` | total_usd / correct_count | Cost efficiency — the primary routing metric |
| `mean_latency_ms` | mean(latency_ms per item) | User-facing speed |
| `p95_latency_ms` | 95th percentile latency | Tail latency for agent loops |
| `pct_routed_cheap` | cheap_model_calls / total_calls | What fraction the router sends to cheap |
| `pct_routed_strong` | strong_model_calls / total_calls | Inverse of above |
| `cascade_avg_steps` | mean(cascade_step + 1) | Average cascade depth (cascade routers only) |
| `verifier_accept_rate` | accepted_steps / total_cascade_steps | Verifier calibration |
| `fallback_rate` | requests_with_fallback / total_requests | Provider reliability signal |
| `misroute_rate` | items where router chose cheap but correct answer required strong / total | Router error analysis |

### The primary metric: $/correct

`usd_per_correct` is more informative than accuracy alone. A router that achieves 80% accuracy at $0.0001/correct may be better than one achieving 90% accuracy at $0.001/correct, depending on your budget. The Pareto plot visualises the frontier across all configurations.

### % routed cheap

`pct_routed_cheap` is the "routing aggressiveness" signal. At one extreme, always-cheap routes 100% cheap and has the lowest cost but worst accuracy. At the other, always-strong routes 0% cheap. A well-calibrated router should route 60–80% cheap on a suite designed with mixed difficulty (some easy items solvable by cheap models). If the router routes <30% cheap, it is conservative and leaving cost savings on the table. If it routes >90% cheap, verify the accuracy hasn't collapsed.

---

## What to log as evidence per POC

Each POC's `evidence.md` and `04-logs/live-evidence-ledger.md` must record:

```
# Minimum evidence entry per POC run
run_id: <UUID>
router: <name>
date: 2026-XX-XX
suite: <suite name>
n_items: <int>
accuracy: <float>
total_usd: <float>
usd_per_correct: <float>
pct_routed_cheap: <float>
mean_latency_ms: <float>
fallback_rate: <float>
sample_routing_records:
  - request_id: <uuid>
    model_selected: <model id>
    model_final: <model id>
    usd: <float>
    correct: <bool>
    routing_features: {<key>: <value>}
```

At least three sample `routing_records` should be included in evidence — one where the router correctly sent to cheap, one where it correctly escalated to strong, and one fallback or misroute if present.

---

## Fallback chain logging

Fallbacks are triggered by: provider timeout (>N seconds), HTTP 429 rate limit, invalid model slug, or verifier-rejected answer (cascade escalation). Each fallback step must be logged:

```python
fallback_chain = []
for model in cascade_order:
    try:
        result = chat(model, messages, timeout=timeout_secs)
        score = judge.score(item, result.text)
        if score >= verifier_threshold:
            break
        fallback_chain.append({"model": model, "reason": "verifier_low", "score": score})
    except ProviderTimeout:
        fallback_chain.append({"model": model, "reason": "timeout"})
    except RateLimit:
        fallback_chain.append({"model": model, "reason": "rate_limit"})
```

L5 (`L5-failure-modes-and-observability`) is the dedicated POC for exercising and logging all failure paths. It must demonstrate at least three distinct fallback reasons.

---

## Cost budget guard

The budget guard prevents runaway spending on a single suite run. Implemented in `router_base.run_suite()`:

```python
MAX_RUN_USD = 2.00  # configurable per POC

if ledger.total_usd() > MAX_RUN_USD:
    raise BudgetExceeded(f"Run exceeded ${MAX_RUN_USD:.2f} after {i+1} items")
```

When the budget guard trips, the partial run result is still written to the evidence ledger (with `status: budget_exceeded`). The partial accuracy and cost are reported as-is, not extrapolated to the full suite.

---

## Observability for the gateway POC

L4 (`L4-routing-gateway-runtime`) runs the router as a live HTTP server. Each incoming request to the gateway generates one routing record as above, plus a gateway-level record:

```
gateway_request_id: <uuid>  # opaque to the caller
caller_latency_ms: <int>     # wall-clock from gateway receive to response sent
upstream_request_id: <uuid>  # the RoutingRecord.request_id
http_status: 200 | 500 | 429
```

The gateway persists records to a JSONL file (one record per line) rather than an in-memory accumulator. This survives crashes and is the evidence for "routing gateway in production."

---

## Sources

- Portkey LLM observability guide: https://portkey.ai/blog/the-complete-guide-to-llm-observability/
- LiteLLM router docs (logging): https://docs.litellm.ai/docs/routing
- LiteLLM router architecture (fallbacks): https://docs.litellm.ai/docs/router_architecture
- xAI cost tracking: https://docs.x.ai/developers/cost-tracking
- OpenTelemetry LLM observability: https://opentelemetry.io/blog/2024/llm-observability/
- Braintrust gateway observability: https://www.braintrust.dev/articles/best-llm-gateways-observability-2026
