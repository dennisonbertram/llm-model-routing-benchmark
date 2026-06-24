# Integrations — Model Routing in Real Systems and Frameworks

**Target**: Model Routing  
**Degree**: 01-llm-model-routing  
**Gathered**: 2026-06-21 (WebFetch of official docs; GitHub READMEs; Aider, OpenCode, LiteLLM, semantic-router, NotDiamond, Vercel AI SDK documentation)  
**Status**: Research supported but not live verified. Config snippets are drawn from official documentation fetched during research. Verify against current docs at build time — library APIs change.

---

## Integration Map

| System | Routing Surface | Mechanism |
|---|---|---|
| OpenAI-compatible gateway | HTTP `POST /v1/chat/completions`, `model` field encodes router | All router types expose the same wire format |
| LiteLLM Router | `Router(model_list, routing_strategy)` Python class | Load-balancing + fallback across model groups |
| RouteLLM OSS | OpenAI client drop-in, `model="router-mf-0.11593"` | Trained classifiers; threshold in model string |
| NotDiamond | `client.model_router.select_model()` → call selected model | External routing service; returns recommended model |
| Vercel AI SDK | `generateText({ model: "provider/model-id" })` | Model as a swappable string; per-request selection |
| LangChain | `ChatOpenAI(model_name=..., openai_api_base=...)` | Any OpenAI-compatible backend; model swapped at init |
| OpenCode | `opencode.json` per-agent and per-command `model` field | Static config; per-agent specialization |
| Aider | `--model`, `--architect`, `--editor-model`, `--weak-model` | CLI flags; architect/editor/weak trinity |
| semantic-router (Aurelio) | `SemanticRouter(encoder, routes)` → `.name` | Intent classification via embedding; routes to handler |

---

## OpenAI-Compatible Gateway Shape

Any routing system that exposes the OpenAI `/v1/chat/completions` wire format is a drop-in for any client written against the OpenAI SDK. The canonical shape:

```
POST /v1/chat/completions
Authorization: Bearer <token>
Content-Type: application/json

{
  "model": "<logical-model-or-router-id>",
  "messages": [{"role": "user", "content": "..."}],
  "max_tokens": 512
}
```

**Client-side, only two constructor arguments change:**

```python
# Python — swap baseURL + apiKey; everything else identical
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:6060/v1",   # your local router gateway
    api_key="not-checked",                  # or your gateway token
)

response = client.chat.completions.create(
    model="router-mf-0.11593",             # encodes router type + threshold
    messages=[{"role": "user", "content": "What is merge sort?"}],
)
print(response.choices[0].message.content)
```

This pattern is used by RouteLLM (see below), OpenRouter, LiteLLM proxy, and the L4-routing-gateway-runtime and L3c-openai-compatible-gateway-integration POCs in this degree.

---

## LiteLLM Router

LiteLLM's `Router` class load-balances and falls back across a pool of model deployments. The `model_list` maps logical model aliases to real provider+model combos with optional TPM/RPM limits and weights.

**Source:** https://docs.litellm.ai/docs/routing

### Instantiation and Routing Strategies

```python
import os
from litellm import Router

model_list = [
    {
        "model_name": "strong",           # logical alias
        "litellm_params": {
            "model": "gpt-4o",
            "api_key": os.environ["OPENAI_API_KEY"],
        },
        "model_info": {"id": "openai-gpt4o"},
    },
    {
        "model_name": "cheap",
        "litellm_params": {
            "model": "gpt-4.1-nano",
            "api_key": os.environ["OPENAI_API_KEY"],
        },
        "model_info": {"id": "openai-nano"},
    },
]

# Cost-based routing: always picks the cheapest deployment
router = Router(model_list=model_list, routing_strategy="cost-based-routing")

# Request using logical alias
response = router.completion(
    model="cheap",
    messages=[{"role": "user", "content": "Hello!"}],
)
# hidden_params["model_id"] shows which deployment was selected
print(response._hidden_params["model_id"])
```

Available `routing_strategy` values:

| Strategy | Behavior |
|---|---|
| `simple-shuffle` (default) | Random weighted; recommended for most production use |
| `latency-based-routing` | Picks deployment with lowest measured response time |
| `usage-based-routing-v2` | Routes to deployment with lowest current TPM usage |
| `least-busy` | Fewest concurrent in-flight calls |
| `cost-based-routing` | Picks lowest-cost deployment per `litellm_model_cost_map` |

### Fallbacks

```python
# Python Router
router = Router(
    model_list=model_list,
    fallbacks=[{"cheap": ["strong"]}],    # if cheap fails, escalate to strong
    num_retries=2,
    cooldown_time=60,                      # seconds to cool down a failing deployment
)
```

```yaml
# YAML Proxy (litellm_proxy_config.yaml)
router_settings:
  fallbacks: [{"cheap": ["strong"]}]
  context_window_fallbacks: [{"cheap": ["strong"]}]
  content_policy_fallbacks: [{"cheap": ["strong"]}]
```

Fallbacks are tried in order; the first succeeding model's response is returned.

### Distributed Setup (Redis)

```python
router = Router(
    model_list=model_list,
    redis_host=os.environ["REDIS_HOST"],
    redis_password=os.environ["REDIS_PASSWORD"],
    redis_port=os.environ["REDIS_PORT"],
    routing_strategy="usage-based-routing-v2",
    num_retries=3,
    cache_responses=True,
)
```

Redis shares usage state across multiple proxy instances — required when running multiple LiteLLM Proxy replicas behind a load balancer.

---

## RouteLLM OSS — OpenAI Client Drop-in

RouteLLM replaces the OpenAI client with a `Controller` that intercepts calls and routes based on a trained classifier. The classifier is pre-trained on Chatbot Arena preference data (80k battles).

**Source:** https://github.com/lm-sys/RouteLLM

```python
from routellm.controller import Controller

client = Controller(
    routers=["mf"],                              # matrix factorization (recommended)
    strong_model="gpt-4o",
    weak_model="gpt-4.1-nano",
)

# The model string encodes: router type + decision threshold
# Threshold calibration: python -m routellm.calibrate_threshold --routers mf --strong-model-pct 0.5
# Example output: "For 50.0% strong model calls for mf, threshold = 0.11593"
response = client.chat.completions.create(
    model="router-mf-0.11593",                   # route-{type}-{threshold}
    messages=[{"role": "user", "content": "Explain gradient descent."}],
)
print(response.choices[0].message.content)
```

Available router types: `mf` (matrix factorization), `sw_ranking` (similarity-weighted Elo), `bert`, `causal_llm`. The `mf` router is recommended.

**Threshold calibration** determines what fraction of queries go to the strong model:

```bash
python -m routellm.calibrate_threshold \
    --routers mf \
    --strong-model-pct 0.2    # route ~20% to strong model
# Outputs: threshold value to use in the model string
```

For coding agent use, pick `strong-model-pct` based on your cost budget vs. quality floor requirement.

---

## NotDiamond — External Router Service

NotDiamond is a hosted routing service that predicts which model in a candidate set will perform best for a given query. It returns a recommendation; the caller is responsible for making the actual LLM call using their preferred SDK.

**Source:** https://docs.notdiamond.ai/docs/quickstart-routing

```python
import os
from notdiamond import NotDiamond

client = NotDiamond(api_key=os.environ["NOTDIAMOND_API_KEY"])

result = client.model_router.select_model(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Concisely explain merge sort."},
    ],
    llm_providers=[
        {"provider": "openai", "model": "gpt-4o"},
        {"provider": "openai", "model": "gpt-4.1-nano"},
        {"provider": "anthropic", "model": "claude-sonnet-4-6"},
    ],
    tradeoff="cost",   # "cost", "latency", or None (quality)
)

print("Recommended model:", result.provider.model)
# Then call the recommended model with your preferred SDK
```

The `tradeoff` parameter controls the optimization objective. The call to NotDiamond is separate from the LLM call — add both to your latency budget.

---

## Vercel AI SDK — Per-Request Model Selection

The Vercel AI SDK's `generateText` and `streamText` accept a `model` parameter that can be swapped per request. The SDK normalizes provider differences behind a unified interface.

**Source:** https://ai-sdk.dev/docs/ai-sdk-core/generating-text

```typescript
import { generateText, streamText } from 'ai';

// Swap model string to change provider — no other code changes needed
const cheapModel = "openai/gpt-4.1-nano";
const strongModel = "anthropic/claude-sonnet-4-6";

async function routedGenerate(prompt: string, useStrong: boolean) {
    const { text } = await generateText({
        model: useStrong ? strongModel : cheapModel,
        prompt,
    });
    return text;
}

// Streaming with dynamic model selection
const result = streamText({
    model: isComplexQuery(prompt) ? strongModel : cheapModel,
    prompt,
    onError({ error }) { console.error(error); },
});
for await (const textPart of result.textStream) {
    process.stdout.write(textPart);
}
```

**Pattern for routing:** wrap `generateText` / `streamText` in a thin function that selects the model string based on heuristics, classifier output, or cascade logic. The model string is the only routing seam.

For use with OpenRouter, the `@openrouter/ai-sdk-provider` adapter provides `createOpenRouter()` which maps to the same `generateText`/`streamText` interface (see `openrouter` degree `integrations.md`).

---

## LangChain — OpenAI-Compatible Base URL

LangChain's `ChatOpenAI` class accepts a custom `openai_api_base` (Python) or `configuration.baseURL` (TypeScript), making it compatible with any OpenAI-shaped gateway including LiteLLM Proxy and RouteLLM.

```python
from langchain_openai import ChatOpenAI

# Route via LiteLLM Proxy or any OpenAI-compatible gateway
llm_cheap = ChatOpenAI(
    model_name="gpt-4.1-nano",
    openai_api_base="http://localhost:4000/v1",   # LiteLLM Proxy
    openai_api_key="not-checked",
)

llm_strong = ChatOpenAI(
    model_name="claude-sonnet-4-6",
    openai_api_base="http://localhost:4000/v1",
    openai_api_key="not-checked",
)

# Router function
def route(query: str):
    if len(query) > 500 or "architecture" in query.lower():
        return llm_strong.invoke(query)
    return llm_cheap.invoke(query)
```

For direct provider access without a gateway:

```python
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

llm_cheap = ChatOpenAI(model="gpt-4.1-nano")
llm_strong = ChatAnthropic(model="claude-sonnet-4-6")
```

---

## OpenCode — Per-Agent and Per-Command Model Config

OpenCode's `opencode.json` config allows different models per agent and per command, enabling static harness routing: fast/cheap models for lightweight tasks, strong models for deep reasoning or architectural work.

**Source:** https://opencode.ai/docs/config/

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "anthropic/claude-sonnet-4-6",
  "small_model": "anthropic/claude-haiku-4-5",

  "agent": {
    "code-reviewer": {
      "description": "Reviews code for correctness and style",
      "model": "anthropic/claude-sonnet-4-6",
      "prompt": "You are a senior code reviewer. Be concise.",
      "tools": { "write": false }
    },
    "title-generator": {
      "description": "Generates PR/commit titles",
      "model": "anthropic/claude-haiku-4-5",
      "prompt": "Generate a short, imperative commit title."
    }
  },

  "command": {
    "quick-fix": {
      "template": "Fix the immediate syntax error in the current file.",
      "description": "Fast syntax fix",
      "model": "anthropic/claude-haiku-4-5"
    },
    "deep-refactor": {
      "template": "Analyze and refactor this module for readability and performance.",
      "description": "Deep refactor",
      "model": "anthropic/claude-sonnet-4-6"
    }
  }
}
```

**Config precedence:** project `opencode.json` > global `~/.config/opencode/opencode.json` > remote organizational defaults.

The `small_model` key maps to lightweight tasks like title generation. Per-agent and per-command overrides apply only to that agent/command; the top-level `model` remains the default for all other interactions.

---

## Aider — Architect / Editor / Weak Trinity

Aider exposes three distinct model slots, each mapped to a different task in the coding workflow:

| Slot | Flag | Purpose | Recommended tier |
|---|---|---|---|
| Main / Architect | `--model` / `--architect` | Plans the change; high-level reasoning | Strong (frontier model) |
| Editor | `--editor-model` | Applies the plan as structured diff output | Mid (precise at diffs) |
| Weak | `--weak-model` | Commit messages; chat history summarization | Cheap (haiku / mini tier) |

**Source:** https://aider.chat/docs/config/options.html — https://aider.chat/2024/09/26/architect.html

```bash
# Architect mode: strong planner, separate editor
export ANTHROPIC_API_KEY=...
export OPENAI_API_KEY=...

# Claude Sonnet as both planner and editor
aider --sonnet --architect

# Strong planner + cheap editor
aider --model claude-sonnet-4-6 \
      --architect \
      --editor-model gpt-4.1-nano \
      --weak-model gpt-4.1-nano

# OpenAI-native stack
aider --model gpt-4o --architect \
      --editor-model gpt-4.1-mini \
      --weak-model gpt-4.1-nano
```

**Environment variable equivalents** (for `.aider.conf.yml` or CI):

```
AIDER_MODEL=claude-sonnet-4-6
AIDER_ARCHITECT=1
AIDER_EDITOR_MODEL=gpt-4.1-nano
AIDER_WEAK_MODEL=gpt-4.1-nano
```

The architect/editor split exists because frontier models plan brilliantly but sometimes produce malformed diffs, while cheaper models are more reliable at precise diff output. The weak model is used for commit messages only — cheapest available is fine.

The paper's benchmark (from the aider.chat architect blog, 2024-09-26) reports: o1-preview (architect) + DeepSeek or o1-mini (editor) reached 85% pass rate on the aider coding benchmark; o1-preview + Claude 3.5 Sonnet (editor) reached 82.7%.

---

## semantic-router (Aurelio) — Intent-Based Routing

semantic-router classifies query intent via embedding similarity, then dispatches to a configured handler or model. It is not a model router in the cost/quality sense — it is a **topic/intent classifier** that can be used as the routing layer feeding a model selector.

**Source:** https://github.com/aurelio-labs/semantic-router — https://docs.aurelio.ai/semantic-router/user-guide/guides/semantic-router

```python
from semantic_router import Route
from semantic_router.encoders import OpenAIEncoder
from semantic_router.routers import SemanticRouter
import os

# Define intent routes with example utterances
coding_route = Route(
    name="coding",
    utterances=[
        "write a function to sort a list",
        "debug this Python code",
        "implement a binary search tree",
        "how do I handle exceptions in async code",
    ],
)

factual_route = Route(
    name="factual_qa",
    utterances=[
        "what is the capital of France",
        "who wrote Hamlet",
        "what year did WWII end",
    ],
)

routes = [coding_route, factual_route]

encoder = OpenAIEncoder(openai_api_key=os.environ["OPENAI_API_KEY"])
router = SemanticRouter(encoder=encoder, routes=routes, auto_sync="local")

# Route a query
result = router("write a recursive fibonacci function")
print(result.name)  # "coding"
# → dispatch to strong coding model

result2 = router("what is the speed of light")
print(result2.name)  # "factual_qa"
# → dispatch to cheap QA model

result3 = router("tell me a joke")
print(result3.name)  # None — no route matched; use fallback
```

**Pattern for model routing:** use `result.name` to select among a pool of models:

```python
MODEL_MAP = {
    "coding":     "claude-sonnet-4-6",    # strong model for code
    "factual_qa": "gpt-4.1-nano",         # cheap model for factual QA
    None:         "gpt-4.1-mini",         # default for unmatched queries
}

model_id = MODEL_MAP[result.name]
```

Route types: **static** routes return the route name; **dynamic** routes make an LLM call to extract parameter values from the query (useful for structured dispatch with arguments).

---

## Integration Selection Guide

| Starting point | Recommended integration | Why |
|---|---|---|
| Need trained cost/quality router from preference data | RouteLLM OSS | Pre-trained classifiers; threshold = cost knob |
| Need external routing-as-a-service | NotDiamond | Hosted; returns recommended model; caller handles LLM call |
| Multi-provider load balancing + fallback | LiteLLM Router | Handles retries, cooldown, cost/latency strategies |
| TypeScript / Next.js app with dynamic model selection | Vercel AI SDK | Model string is the only routing seam; no lock-in |
| Coding agent with role-differentiated models | Aider architect mode | Architect + editor + weak trinity; CLI or env vars |
| OpenCode per-agent specialization | opencode.json `agent.model` | Static per-agent assignment; cheap for light tasks |
| Intent/topic-based dispatch to different models | semantic-router (Aurelio) | Embedding-based intent classification; no LLM needed for routing step |
| OpenAI-compatible clients routing to any backend | Any OpenAI-shaped gateway | `base_url` + `api_key` swap; model string = router decision |

---

## Sources

- https://docs.litellm.ai/docs/routing — LiteLLM Router
- https://docs.litellm.ai/docs/proxy/reliability — LiteLLM Fallbacks
- https://github.com/lm-sys/RouteLLM — RouteLLM code
- https://www.lmsys.org/blog/2024-07-01-routellm/ — RouteLLM blog
- https://docs.notdiamond.ai/docs/quickstart-routing — NotDiamond quickstart
- https://ai-sdk.dev/docs/ai-sdk-core/generating-text — Vercel AI SDK generateText
- https://opencode.ai/docs/config/ — OpenCode config
- https://aider.chat/docs/config/options.html — Aider options
- https://aider.chat/2024/09/26/architect.html — Aider architect mode
- https://github.com/aurelio-labs/semantic-router — semantic-router
- https://docs.aurelio.ai/semantic-router/user-guide/guides/semantic-router — semantic-router docs
