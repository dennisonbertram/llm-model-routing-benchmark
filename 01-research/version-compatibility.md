# Version Compatibility

**Target**: Model Routing — LLM/model selection for cost-efficient agent inference
**Evidence status**: Research supported but not live verified unless marked [LIVE] (no POCs executed yet)
**Grounding**: OpenAI deprecations page (developers.openai.com); Anthropic OpenAI SDK compatibility docs (platform.claude.com); xAI Grok API docs; community-confirmed OpenAI forum threads on max_completion_tokens / temperature restrictions

---

## The fundamental problem: model IDs are not stable

A multi-provider router that hard-codes model IDs will silently break when:
- A dated snapshot is deprecated and removed from the API.
- An alias (`gpt-4o`) resolves to a different underlying checkpoint with different parameter requirements.
- A provider renames or retires a model without a grace period (common for preview models).
- A provider's wire format changes for a new model family (e.g. o-series adding `max_completion_tokens`).

The only safe posture is: **pin dated snapshot IDs in the harness price table and fallback chain, and probe `/models` at startup to detect drift early.**

---

## OpenAI model IDs — naming conventions and deprecation cadence

### Snapshot IDs vs aliases

OpenAI exposes two kinds of model identifiers:

| Kind | Example | Behaviour |
|---|---|---|
| Dated snapshot | `gpt-4o-2024-11-20`, `gpt-5-2025-08-07` | Pinned — always refers to the same checkpoint |
| Alias | `gpt-4o`, `gpt-5.5`, `o3-mini` | Resolves to the current recommended snapshot; changes silently |

**For routers**: always pin dated snapshots in `pricing.py`, `tasks.py`, and the fallback chain. Use aliases only for one-off exploratory calls where reproducibility does not matter.

The harness verified model pool (from the spec, 2026-06-21):
- `gpt-4.1-nano`, `gpt-4.1-mini`, `gpt-4o-mini`, `gpt-4o`, `gpt-4.1`, `gpt-5-mini`, `gpt-5`

Note: `gpt-5-2025-08-07` (the dated snapshot for `gpt-5`) is scheduled for deprecation in the June 2026 wave per the OpenAI deprecations page; the replacement is `gpt-5.5`. Verify current availability via `/v1/models` at POC run time. Source: https://developers.openai.com/api/docs/deprecations

### Notice periods

From the OpenAI deprecations policy (research supported, not live verified):

| Model class | Minimum notice |
|---|---|
| Generally available models | 6 months |
| Specialized variants (e.g. chat-latest, Codex) | 3 months |
| Preview models | 2 weeks |

**Do not use preview model IDs** (those containing "preview" in the slug) in the harness fallback chain for any POC claiming production-readiness evidence. They may disappear with 2 weeks notice.

---

## o-series and gpt-5 parameter quirks

OpenAI's reasoning model families (o1, o3, o4-mini, and now gpt-5 family which incorporates reasoning) have different parameter requirements from the standard chat completions models. These are **wire-level incompatibilities** a router harness must branch on.

### `max_completion_tokens` vs `max_tokens`

- **o1, o3, o4-mini, gpt-5 family**: require `max_completion_tokens`. The `max_tokens` parameter returns a 400 error.
- **GPT-4o, gpt-4.1, gpt-4o-mini, gpt-4.1-nano/mini**: accept `max_tokens` (still supported) and also accept `max_completion_tokens`.

Sources: OpenAI community confirmed (https://community.openai.com/t/api-stopped-working-max-tokens-and-temperature-no-longer-allowed/1110863); GitHub issues tracking the breakage across multiple tools (https://github.com/danny-avila/LibreChat/issues/10737; https://github.com/simonw/llm/issues/724). *Research supported but not live verified against our pool.*

### `temperature` not supported on reasoning models

The o3, o3-mini, and reasoning-mode gpt-5 variants reject the `temperature` parameter. Setting it causes a 400 error: "Unsupported parameter: 'temperature'".

Also unsupported on reasoning models: `top_p`, `frequency_penalty`, `presence_penalty`, `logit_bias`, `n > 1`, `logprobs`.

Sources: OpenAI community forum (https://community.openai.com/t/o3-mini-unsupported-parameter-temperature/1140846); GitHub openai-python issue 2072 (https://github.com/openai/openai-python/issues/2072). *Research supported but not live verified.*

### Harness branching pattern

The `providers.py` harness module must detect model family and adjust parameters:

```python
# harness/providers.py — family detection
def _is_reasoning_model(model: str) -> bool:
    """True for o-series and gpt-5 family that reject temperature."""
    prefixes = ("o1", "o3", "o4", "gpt-5")
    return any(model.startswith(p) for p in prefixes)

def _build_params(model: str, max_tokens: int, temperature: float) -> dict:
    params = {}
    if _is_reasoning_model(model):
        params["max_completion_tokens"] = max_tokens
        # temperature omitted — not supported
    else:
        params["max_tokens"] = max_tokens
        params["temperature"] = temperature
    return params
```

**Validate live**: the L0 smoke POC must call each model in the pool with the appropriate params and record which family detection branch fired. Any model that returns a 400 on a parameter mismatch should be caught and logged in `04-logs/live-evidence-ledger.md`.

---

## Anthropic — native `/v1/messages` vs OpenAI compatibility endpoint

### Two distinct wire formats

Anthropic provides two endpoints:

| Endpoint | Purpose | Recommended for |
|---|---|---|
| `POST https://api.anthropic.com/v1/messages` | Native Anthropic API | Production, full feature access |
| `POST https://api.anthropic.com/v1/` (via OpenAI SDK base_url) | OpenAI compatibility layer | Quick testing only |

The harness `providers.py` uses the native `/v1/messages` endpoint directly for Anthropic models. The OpenAI compatibility layer is explicitly **not** for production use per Anthropic's docs: "This compatibility layer is primarily intended to test and compare model capabilities, and is not considered a long-term or production-ready solution."

Source: https://platform.claude.com/docs/en/api/openai-sdk (Anthropic, fetched 2026-06-21)

### Native format requirements

```python
# harness/providers.py — Anthropic native call
import httpx

def _call_anthropic(model: str, messages: list[dict], max_tokens: int, temperature: float) -> dict:
    headers = {
        "x-api-key": os.environ["ANTHROPIC_API_KEY"],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    # Extract system message — Anthropic requires it top-level, not in messages array
    system_msg = None
    filtered_messages = []
    for m in messages:
        if m["role"] == "system":
            system_msg = (system_msg + "\n" + m["content"]) if system_msg else m["content"]
        else:
            filtered_messages.append(m)

    body = {
        "model": model,
        "messages": filtered_messages,
        "max_tokens": max_tokens,  # REQUIRED on every Anthropic call
        "temperature": temperature,
    }
    if system_msg:
        body["system"] = system_msg  # top-level, not a message

    resp = httpx.post("https://api.anthropic.com/v1/messages", headers=headers, json=body)
    resp.raise_for_status()
    data = resp.json()
    return {
        "text": data["content"][0]["text"],  # NOTE: content[0].text, not choices[0].message.content
        "prompt_tokens": data["usage"]["input_tokens"],
        "completion_tokens": data["usage"]["output_tokens"],
    }
```

### Key wire-format differences from OpenAI

| Aspect | OpenAI (`/v1/chat/completions`) | Anthropic (`/v1/messages`) |
|---|---|---|
| Auth header | `Authorization: Bearer sk-...` | `x-api-key: sk-ant-...` |
| Version header | Not required | `anthropic-version: 2023-06-01` (required) |
| System message | `{"role": "system", "content": "..."}` in messages array | Top-level `"system": "..."` field |
| Multiple system messages | Supported | Not supported — must be concatenated |
| `max_tokens` | Optional (default varies) | **Required** on every call |
| Response content | `choices[0].message.content` | `content[0].text` |
| Response token counts | `usage.prompt_tokens`, `usage.completion_tokens` | `usage.input_tokens`, `usage.output_tokens` |
| Cost | Not returned | Not returned |

**No-USD from either provider**: both OpenAI and Anthropic require the harness to compute cost from a local price table (`pricing.py`). Only xAI returns actual billed cost in the response (`cost_in_usd_ticks`).

### Features not available in Anthropic OpenAI-compat mode

From Anthropic docs (fetched 2026-06-21):
- Prompt caching (requires native API)
- `response_format` / structured outputs (ignored in compat mode)
- `strict` parameter for function calling (ignored)
- `reasoning_effort` (ignored)
- Extended thinking full output (partial support only)

The harness uses the native endpoint so all features are available. If a POC uses prompt caching for cost reduction, it must use the native endpoint.

---

## xAI — OpenAI-compatible with a cost field

xAI's API (`https://api.x.ai/v1`) is OpenAI-compatible: it accepts `POST /v1/chat/completions` with an OpenAI-format request body. The key differences:

### Grok-4.3 always generates reasoning tokens

`grok-4.3` generates internal reasoning tokens on every request. These count toward billing at the output token rate. There is no way to disable reasoning in grok-4.3 (unlike o3-mini's `reasoning_effort: low` option). The harness must account for this when estimating costs from the price table.

**Configurable effort for newer grok models**: per xAI docs, newer Grok variants support `reasoning_effort: none | low | medium | high`. Lower effort means fewer hidden reasoning tokens. The spec model `grok-4.3` always reasons; check the live model list if a cheaper grok variant is needed.

### cost_in_usd_ticks

xAI returns `cost_in_usd_ticks` in the `usage` object. This is the only provider in our pool that returns actual billed cost in the response. Conversion:

```python
def xai_ticks_to_usd(ticks: int) -> float:
    return ticks / 10_000_000_000  # 1 USD = 10^10 ticks
```

Source: https://docs.x.ai/developers/cost-tracking (fetched 2026-06-21, inferred from docs).

Use `cost_in_usd_ticks` for xAI cost accounting rather than the price table, since reasoning token counts are opaque. Record both the ticks value and the converted USD in the evidence ledger.

---

## Live `/models` probe at startup

Model IDs drift. The harness should probe `/models` (or equivalent) at startup to catch deprecated IDs before they cause 404/400 errors mid-run.

```python
# harness/providers.py — startup model availability check
def check_model_available(model: str) -> bool:
    """Probe the provider's model list. Returns False if model is not found."""
    provider = _detect_provider(model)
    if provider == "openai":
        resp = httpx.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"}
        )
        resp.raise_for_status()
        available = {m["id"] for m in resp.json()["data"]}
        return model in available
    elif provider == "anthropic":
        # Anthropic /v1/models endpoint (check live)
        resp = httpx.get(
            "https://api.anthropic.com/v1/models",
            headers={
                "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                "anthropic-version": "2023-06-01",
            }
        )
        resp.raise_for_status()
        available = {m["id"] for m in resp.json()["data"]}
        return model in available
    elif provider == "xai":
        resp = httpx.get(
            "https://api.x.ai/v1/models",
            headers={"Authorization": f"Bearer {os.environ['XAI_API_KEY']}"}
        )
        resp.raise_for_status()
        available = {m["id"] for m in resp.json()["data"]}
        return model in available
    return True  # Unknown provider — don't block
```

**L0 smoke POC requirement**: the L0 startup check must call this function for every model in the harness pool and record the result. Any model that returns `False` must be excluded from POC runs and noted in the evidence ledger with date.

---

## Provider-ID detection

The harness detects provider from model ID prefix:

```python
def _detect_provider(model: str) -> str:
    if model.startswith("claude-"):
        return "anthropic"
    elif model.startswith("grok-"):
        return "xai"
    else:
        return "openai"  # gpt-*, o1-*, o3-*, gpt-5*
```

**Caveat**: this heuristic works for the spec model pool. If OpenRouter is added later, model IDs have the form `provider/model` (e.g. `anthropic/claude-opus-4-8`), which requires a different detection path.

---

## Known drift / open questions to resolve in L0

| Question | Status | Resolve in |
|---|---|---|
| Are all spec-listed gpt-4.1/gpt-5 model IDs still available via `/v1/models` as of run date? | Unverified | L0 smoke |
| Does `gpt-4o-mini` still accept `max_tokens` or only `max_completion_tokens`? | Research suggests `max_tokens` still works for non-o-series; verify | L0 smoke |
| Does `grok-4.3` accept `temperature` or does it silently ignore it? | xAI is OpenAI-compat but grok-4.3 always reasons; temperature semantics unclear | L0 smoke |
| Exact Anthropic `/v1/models` endpoint URL and response schema | Inferred from pattern; not confirmed live | L0 smoke |
| Which field in xAI response contains `cost_in_usd_ticks`? Confirm it is in `usage` | Docs say `usage` object; confirm exact nesting live | L0 smoke |

Log confirmed answers + response snippets in `04-logs/live-evidence-ledger.md` at L0 run time.

---

## Versioning checklist before each POC run

1. Run `check_model_available()` for every model in the run's pool.
2. Check the OpenAI deprecations page for any newly announced deprecations: https://developers.openai.com/api/docs/deprecations
3. Confirm `pricing.py` prices match the current published rates (see `pricing-quotas-limits.md`).
4. For any o-series or gpt-5 family model: confirm `_is_reasoning_model()` returns `True` so temperature is not sent.
5. Record the SDK version used (`openai` Python package, `anthropic` Python package, `httpx`) in the evidence ledger.

---

## Sources

- OpenAI deprecations page: https://developers.openai.com/api/docs/deprecations
- OpenAI community forum — max_tokens/temperature: https://community.openai.com/t/api-stopped-working-max-tokens-and-temperature-no-longer-allowed/1110863
- OpenAI community forum — o3-mini temperature: https://community.openai.com/t/o3-mini-unsupported-parameter-temperature/1140846
- LibreChat issue on reasoning model params: https://github.com/danny-avila/LibreChat/issues/10737
- openai-python issue 2072: https://github.com/openai/openai-python/issues/2072
- Anthropic OpenAI SDK compatibility docs: https://platform.claude.com/docs/en/api/openai-sdk
- xAI cost tracking docs: https://docs.x.ai/developers/cost-tracking
- OpenAI list models reference: https://platform.openai.com/docs/api-reference/models/list
