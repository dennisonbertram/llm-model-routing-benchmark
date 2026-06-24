# Deployment Model

**Target**: Model Routing — 01-llm-model-routing
**Gathered**: 2026-06-21 (WebFetch + WebSearch against live docs)
**Evidence**: Research supported but not live verified (research files; POC live verification is in 03-pocs/).

---

## Two deployment shapes

Routing lives at two different layers in a production AI stack:

1. **Gateway layer**: a deployed HTTP service that exposes an OpenAI-compatible `/chat/completions` endpoint; clients call it without knowing a router is present. This is the capstone shape (L3c, L4, L-capstone).

2. **Harness layer**: routing built directly into the agent harness; each step in an agentic workflow selects a model based on the step's role or difficulty. This is the opencode / oh-my-opencode pattern.

The two shapes compose: a harness can call a routing gateway, or route directly to provider APIs.

---

## Shape 1 — Routing as a deployed OpenAI-compatible gateway

### The interface contract

Any client that calls `POST /chat/completions` against an OpenAI-compatible base URL gets transparent routing. The router:

1. Receives the request
2. Applies its routing policy (heuristic, classifier, cascade, etc.) to select a model
3. Forwards the request to the selected provider
4. Returns the provider's response (possibly reformatted to OpenAI shape)
5. Records: routing decision, model used, tokens, latency, cost

The client sees a standard OpenAI chat completion response and is unaware of which model was selected.

### Minimal local gateway — Python stdlib

For the L4 POC, the gateway runs as a local HTTP server (Python `http.server` or `socketserver`), reachable on `localhost:8080`. No framework required. The essential handler:

```python
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
from providers import chat
from router_base import MyRouter

router = MyRouter()

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404); return
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        model = router.route(body)           # routing decision
        result = chat(model, body["messages"])
        resp = {
            "id": "chatcmpl-routed",
            "object": "chat.completion",
            "model": model,
            "choices": [{"message": {"role": "assistant", "content": result["text"]},
                         "finish_reason": "stop", "index": 0}],
            "usage": {"prompt_tokens": result["prompt_tokens"],
                      "completion_tokens": result["completion_tokens"],
                      "total_tokens": result["prompt_tokens"] + result["completion_tokens"],
                      "_router_usd": result["usd"],
                      "_router_latency_ms": result["latency_ms"]}
        }
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(resp).encode())

HTTPServer(("localhost", 8080), Handler).serve_forever()
```

A real client (OpenAI SDK, curl, LangChain, AI SDK) can then call `base_url=http://localhost:8080/v1`.

### Cost ledger persistence

Every routing decision is appended to a JSON ledger (`ledger.jsonl`). Each line:

```json
{"ts": 1719000000, "request_id": "r-001", "routed_to": "gpt-4.1-mini",
 "prompt_tokens": 142, "completion_tokens": 38, "usd": 0.000049,
 "latency_ms": 831, "routing_policy": "heuristic-v1"}
```

The ledger is the observability artifact for L4 evidence. Query it for: cost-per-policy, model distribution, tail latency.

---

## Shape 2 — Harness routing (opencode style)

### The pattern

In a multi-step agentic workflow, each step has a role (planning, code editing, test fixing, summarization) and a difficulty (cheap/quick vs. expensive/deep). The harness selects a model per step rather than using one model for the entire session.

This is the core architecture of opencode and its oh-my-opencode extension. Source: analysis of oh-my-opencode documentation — https://www.glukhov.org/ai-devtools/opencode/oh-my-opencode-agents/ (fetched 2026-06-21).

### Agent/role taxonomy

oh-my-opencode organizes agents into four groups by model affinity:

| Group | Agents | Model family | Rationale |
|---|---|---|---|
| Communicators / orchestrators | Sisyphus, Metis | Claude / Kimi / GLM | Long detailed instruction-following prompts (~1,100 lines); mechanics-driven |
| Dual-prompt (detect family at runtime) | Prometheus, Atlas | Claude **or** GPT | `isGptModel()` at runtime picks prompt variant: mechanics-driven for Claude, principle-driven for GPT |
| GPT-native | Hephaestus, Oracle, Momus | GPT-5.x | Designed for GPT's autonomous goal-oriented reasoning; no Claude equivalent prompt |
| Utility runners | Explore, Librarian, Multimodal Looker | Fastest/cheapest available | Retrieval, pattern matching — cost-sensitive, quality-tolerant |

Source: oh-my-opencode documentation (fetched 2026-06-21).

### Category-based routing

Delegation is via a `category` rather than a hardcoded model, which allows the config to change the model behind a category without touching agent code:

| Category | Purpose | Default resolution |
|---|---|---|
| `quick` | Simple single-file tasks | Claude Haiku → Gemini Flash → GPT-5-Nano |
| `deep` | Complex multi-file logic | GPT-5.3 Codex → Claude Opus → Gemini 3.1 Pro |
| `ultrabrain` | Architecture decisions | GPT-5.4 (xhigh) → Gemini 3.1 Pro → Claude Opus |
| `unspecified-high` | General complex work | Claude Opus → GPT-5.4 (high) → GLM-5 |

Source: oh-my-opencode documentation (fetched 2026-06-21). Note: these are the oh-my-opencode defaults for its model pool, not the model pool for this degree's POCs.

### Fallback chain structure

Each agent in oh-my-opencode carries an explicit fallback chain:

```
Sisyphus: claude-opus-4-6 → kimi-k2.5 → gpt-5.4 → glm-5 → big-pickle
```

Priority order across providers: native anthropic/openai/google > Kimi for Coding > GitHub Copilot > Venice > OpenCode Go > Z.ai.

For the L3b harness routing POC in this degree, the coding agent implements a simpler three-step model:

```
plan step     → cheap model (gpt-4.1-nano / claude-haiku)
edit step     → complexity-routed (cheap for simple, strong for hard)
fix/verify    → cheap model; escalate to strong if tests fail again
```

The fallback chain is: chosen model → next tier in the chain → error if all fail.

### Per-step model selection config

```python
STEP_MODEL_MAP = {
    "plan": "gpt-4.1-mini",
    "edit_simple": "gpt-4.1-mini",
    "edit_hard": "gpt-4.1",
    "fix": "gpt-4.1-mini",
    "fix_escalated": "gpt-4.1",
}

FALLBACK_CHAIN = {
    "gpt-4.1-mini": "claude-haiku-4-5-20251001",
    "gpt-4.1":      "claude-sonnet-4-6",
}
```

---

## Production routing services

The following are deployed commercial/OSS routing services that expose an OpenAI-compatible gateway. These are alternatives to building your own; their architecture informs the degree's capstone.

### LiteLLM Router + Proxy

LiteLLM is an open-source library + self-hosted proxy that unifies 100+ models under an OpenAI-compatible interface. Source: https://docs.litellm.ai/docs/routing (fetched 2026-06-21).

**Routing strategies** (set via `routing_strategy` param on `Router`):

| Strategy | Behavior |
|---|---|
| `simple-shuffle` (default) | Weighted random selection based on RPM/TPM limits; recommended for production |
| `latency-based-routing` | Routes to deployment with lowest recent response time; uses `ttl` averaging window |
| `usage-based-routing` | Routes to deployment with lowest current TPM usage; requires Redis for cross-process tracking |
| `least-busy` | Routes to deployment with fewest concurrent requests |
| `cost-based-routing` | Prioritizes lowest-cost deployments using LiteLLM's model cost map |
| Custom | Extend `CustomRoutingStrategyBase` |

**Routing groups** allow per-model strategies without multiple routers:

```yaml
router_settings:
  routing_strategy: simple-shuffle
  routing_groups:
    - group_name: latency-sensitive
      models: [gpt-4o]
      routing_strategy: latency-based-routing
```

**Reliability**: automatic cooldown after N failures (`allowed_fails`), retries with exponential backoff, fallback chains defined in `router_settings.fallbacks`. Pre-call checks can filter deployments by context window fit or region.

**Gateway shape**: the proxy is a self-hosted Docker container; clients point at `http://localhost:4000` with the OpenAI SDK.

### OpenRouter Auto Router

`openrouter/auto` is OpenRouter's managed routing service, powered by NotDiamond. Source: https://openrouter.ai/docs/features/model-routing (per the OpenRouter live-service-model.md in this repo).

- Drop-in: set `model: "openrouter/auto"` in any OpenAI-compatible call
- Routing is fully managed; no infrastructure to deploy
- Default `cost_quality_tradeoff`: 7 (0 = cheapest, 10 = best quality); tuned via the `auto-router` plugin
- No extra routing fee; billed at the selected model's rate
- Combines with `require_parameters: true` to prevent routing to providers that don't support structured output or tools
- `session_id` pins the model for a session's lifetime (prevents mid-session model switching)

**Limitation**: model selection is opaque (NotDiamond internals). Not suitable when you need a deterministic audit trail of which model handled each request.

### Martian

Martian is a commercial routing service from a San Francisco startup. Source: https://route.withmartian.com/ and https://www.everydev.ai/tools/martian (research 2026-06-21).

- Drop-in OpenAI-compatible endpoint
- Analyzes prompts in real-time and routes to the "optimal" model based on performance, cost, and reliability signals
- Exposes `max_cost` and willingness-to-pay controls in the request
- Automatic failover across providers
- Provides benchmarking reports per workload
- Free tier: 2,500 requests; metered paid usage; enterprise VPC/SLA options
- Reported cost reductions of "20% to 97%" vs always-strong, according to Martian's marketing materials (this claim is not independently verified by this degree; treat as unverified vendor claim)

### Unify

Unify is a data-driven routing service with a universal API. Source: https://docs.unify.ai/ and https://xnavi.ai/tools/unify (research 2026-06-21).

- Base URL: `https://api.unify.ai/v0/`; uses `model@provider` syntax to specify both model and provider in a single slug (e.g., `gpt-4o@openai`)
- Single API key covers all supported providers
- Dynamic routing: automatically selects the best `model@provider` combination based on user-defined quality/cost/latency weights (adjustable sliders in the dashboard)
- `GET /v0/providers` lists available providers; `GET /v0/endpoints` lists available `model@provider` endpoints
- The "system chooses" mode picks the optimal combination without requiring manual provider specification

---

## Comparison: gateway vs harness routing

| Dimension | Gateway (L4 shape) | Harness (L3b shape) |
|---|---|---|
| Transparency to client | Fully transparent — client sees OpenAI API | Client is the harness; model selection is in code |
| Routing granularity | Per-request | Per-agent-step / per-difficulty |
| Latency overhead | 1 extra HTTP hop | None (direct SDK call) |
| Observability | Centralized ledger | Per-step log in harness |
| Model switching mid-session | Possible per request | Controlled by step map |
| Fallback complexity | Handled by gateway | Handled by harness fallback chain |
| Deployment complexity | Requires running a service | No additional service |

---

## Sources

- LiteLLM Router docs: https://docs.litellm.ai/docs/routing
- OpenRouter Auto Router docs: https://openrouter.ai/docs/features/model-routing
- Martian: https://route.withmartian.com/ and https://www.everydev.ai/tools/martian
- Unify AI: https://docs.unify.ai/basics/welcome and https://xnavi.ai/tools/unify
- oh-my-opencode agent model routing: https://www.glukhov.org/ai-devtools/opencode/oh-my-opencode-agents/
