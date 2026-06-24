# Configuration and Environment Variables

**Target**: Model Routing — env vars, model pool, and OpenRouter setup
**Degree**: 01-llm-model-routing
**Gathered**: 2026-06-21
**Sources**: `harness/providers.py`, `harness/pricing.py` (coordinator-built); spec `.context/model-routing-spec.md`; provider pricing pages (see `pricing-quotas-limits.md`).

Evidence labels:
- **[HARNESS]** — directly reflected in `harness/providers.py` or `harness/pricing.py`
- **[SPEC]** — from the verified spec (coordinator-confirmed)
- **[DOCS]** — from official provider documentation

---

## Required environment variables

| Variable | Provider | Required | Notes |
|---|---|---|---|
| `OPENAI_API_KEY` | OpenAI | Yes | Chat completions + embeddings (`text-embedding-3-small`) |
| `ANTHROPIC_API_KEY` | Anthropic | Yes | Messages API |
| `XAI_API_KEY` | xAI | Yes | Grok, OpenAI-compatible |
| `OPENROUTER_API_KEY` | OpenRouter | No — optional | Unlocks open models; harness auto-detects if set |

Load from the gitignored secrets file:

```bash
set -a; . /path/to/.agent-university/secrets.local.env; set +a
```

Verify without printing values:

```bash
for v in OPENAI_API_KEY ANTHROPIC_API_KEY XAI_API_KEY; do
    [ -n "${!v}" ] && echo "$v: SET" || echo "$v: MISSING (required)"
done
[ -n "$OPENROUTER_API_KEY" ] && echo "OPENROUTER_API_KEY: SET (OpenRouter enabled)" \
                              || echo "OPENROUTER_API_KEY: unset (optional, skip open models)"
```

---

## Base URLs (hardcoded in harness)

```python
OPENAI_BASE    = "https://api.openai.com/v1"
ANTHROPIC_BASE = "https://api.anthropic.com/v1"
XAI_BASE       = "https://api.x.ai/v1"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
```

These are not configurable via environment variables — they are constants in `providers.py`. To change a base URL (e.g., for local proxying or OpenRouter BYOK), edit `harness/providers.py` via the coordinator. **[HARNESS]**

---

## Model pool — three-tier configuration

The pool spans cheap / mid / strong tiers per provider. Tier assignment is for documentation and routing heuristics; the harness itself has no tier concept — tiers are implemented in router code.

### Cheap tier (per-call cost well under $0.001 for typical queries)

| Model | Provider | Input $/M | Output $/M |
|---|---|---|---|
| `gpt-4.1-nano` | OpenAI | 0.10 | 0.40 |
| `gpt-4.1-mini` | OpenAI | 0.40 | 1.60 |
| `gpt-4o-mini` | OpenAI | 0.15 | 0.60 |
| `claude-haiku-4-5-20251001` | Anthropic | 1.00 | 5.00 |

### Mid tier

| Model | Provider | Input $/M | Output $/M |
|---|---|---|---|
| `gpt-4.1` | OpenAI | 2.00 | 8.00 |
| `gpt-5-mini` | OpenAI | 0.25 | 2.00 |
| `claude-sonnet-4-5-20250929` | Anthropic | 3.00 | 15.00 |
| `claude-sonnet-4-6` | Anthropic | 3.00 | 15.00 |
| `grok-4.3` | xAI | 3.00 | 15.00 |

### Strong tier (used for baselines, judge, and hard-query escalation)

| Model | Provider | Input $/M | Output $/M |
|---|---|---|---|
| `gpt-4o` | OpenAI | 2.50 | 10.00 |
| `gpt-5` | OpenAI | 1.25 | 10.00 |
| `claude-opus-4-8` | Anthropic | 15.00 | 75.00 |

Prices are estimates seeded 2026-06-21. The canonical source is `pricing-quotas-limits.md`. If a price there disagrees with `PRICES` in `pricing.py`, the research file wins — update `PRICES` and re-run affected POCs. **[HARNESS]**

### Embeddings

| Model | Provider | Input $/M | Output $/M |
|---|---|---|---|
| `text-embedding-3-small` | OpenAI | 0.02 | — |
| `text-embedding-3-large` | OpenAI | 0.13 | — |

The harness `embed()` defaults to `text-embedding-3-small`. Used by the kNN and classifier routers (L2, L2b). **[HARNESS]**

---

## Provider detection — how the harness routes by model id

```python
def provider_of(model: str) -> str:
    if model.startswith("openrouter/"):
        return "openrouter"
    if model.startswith("grok"):
        return "xai"
    if model.startswith("claude"):
        return "anthropic"
    return "openai"  # gpt-*, o-series, text-embedding-*
```

To call a specific model, pass its exact id string to `chat()`:

```python
from providers import chat
result = chat("gpt-4.1-nano", [{"role": "user", "content": "Hello"}])
result = chat("claude-haiku-4-5-20251001", [{"role": "user", "content": "Hello"}])
result = chat("grok-4.3", [{"role": "user", "content": "Hello"}])
```

**[HARNESS]**

---

## Model family parameter branching

Some OpenAI models (`gpt-5*`, `o1*`, `o3*`, `o4*`) reject `temperature` and require `max_completion_tokens` instead of `max_tokens`. The harness branches automatically: **[HARNESS]**

```python
def _openai_family_no_temp(model: str) -> bool:
    return (model.startswith("gpt-5") or model.startswith("o1")
            or model.startswith("o3") or model.startswith("o4"))

# In payload construction:
if _openai_family_no_temp(model):
    payload["max_completion_tokens"] = max_tokens
else:
    payload["max_tokens"] = max_tokens
    payload["temperature"] = temperature
```

POC code does not need to handle this — `chat()` manages it internally.

---

## Adding OpenRouter (when key is available)

If `OPENROUTER_API_KEY` is set, prefix any open model id with `openrouter/`:

```python
result = chat("openrouter/meta-llama/llama-3.3-70b-instruct",
              [{"role": "user", "content": "Hello"}])
result = chat("openrouter/qwen/qwen-2.5-72b-instruct",
              [{"role": "user", "content": "Hello"}])
```

The harness strips the `openrouter/` prefix before sending to the API and restores it in the returned `model` field. **[HARNESS]**

For open models served via OpenRouter, add a price entry in `pricing.PRICES`. If no price entry exists and the response includes a generation cost from OpenRouter's API, the harness falls back to `native_cost_usd` — but this path is a last resort and requires coordinator review. **[HARNESS]**

### OpenRouter attribution headers (sent automatically)

When routing through OpenRouter, the harness sends two optional headers: **[HARNESS]**

```python
headers["HTTP-Referer"] = "https://agent-university.local"
headers["X-Title"] = "agent-university-model-routing"
```

These identify the degree in OpenRouter's dashboard and leaderboards. They do not affect billing or routing.

---

## Harness configuration knobs (passed as `extra=` dict)

The `chat()` function accepts an `extra` dict that is merged into the request payload last. Use this to pass provider-specific parameters without modifying the harness:

```python
# xAI: set explicit reasoning effort
result = chat("grok-4.3", messages, extra={"reasoning_effort": "none"})

# Anthropic: extended thinking (if supported by model)
result = chat("claude-sonnet-4-6", messages, extra={"thinking": {"type": "enabled", "budget_tokens": 1000}})

# OpenAI: structured output
result = chat("gpt-4.1", messages, extra={"response_format": {"type": "json_object"}})
```

Use `extra` sparingly and document its use in the POC's `commands.md`. **[HARNESS]**

---

## Anthropic-specific: `anthropic-version` header

The harness hardcodes `anthropic-version: 2023-06-01`. This is the current stable version as of 2026-06-21. **[HARNESS + DOCS]** Do not bump this value without verifying that all models in the pool remain compatible.

---

## Sources

- Harness source: `harness/providers.py` (coordinator-built, 2026-06-21)
- Harness source: `harness/pricing.py` (coordinator-built, 2026-06-21)
- Spec: `.context/model-routing-spec.md`
- Provider pricing: `01-research/pricing-quotas-limits.md` (to be populated by Workflow 1 research agent)
- OpenAI embeddings: https://platform.openai.com/docs/models#embeddings (Inferred from docs)
