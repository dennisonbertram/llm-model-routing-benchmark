# Authentication and Authorization

**Target**: Model Routing — provider auth shapes
**Degree**: 01-llm-model-routing
**Gathered**: 2026-06-21
**Sources**: Official provider docs fetched via WebFetch (URLs listed at end); harness source `harness/providers.py` (coordinator-built, live-verified 2026-06-21 against real provider endpoints); Anthropic API reference at `platform.claude.com/docs/en/api/getting-started`; xAI API reference at `docs.x.ai/docs/api-reference`.

Evidence labels used in this file:
- **[DOCS]** — sourced from official provider documentation (fetched 2026-06-21)
- **[HARNESS]** — reflected in `harness/providers.py`, which ran successfully against live endpoints

---

## Overview

This degree calls three providers directly and optionally one gateway. Each has a distinct auth shape:

| Provider | Auth header | Header name | Key env var |
|---|---|---|---|
| OpenAI | Bearer token | `Authorization: Bearer $KEY` | `OPENAI_API_KEY` |
| Anthropic | API key | `x-api-key: $KEY` | `ANTHROPIC_API_KEY` |
| xAI (Grok) | Bearer token (OpenAI-compatible) | `Authorization: Bearer $KEY` | `XAI_API_KEY` |
| OpenRouter (optional) | Bearer token | `Authorization: Bearer $KEY` | `OPENROUTER_API_KEY` |

All four providers require `Content-Type: application/json`. **[DOCS + HARNESS]**

---

## OpenAI

### Authentication

```
POST https://api.openai.com/v1/chat/completions
Authorization: Bearer $OPENAI_API_KEY
Content-Type: application/json
```

Keys begin with `sk-proj-` (project keys) or `sk-` (legacy personal keys). **[DOCS]**

### Model family branching — required by the harness

The harness detects the model family and branches on two parameters: **[HARNESS]**

```python
def _openai_family_no_temp(model: str) -> bool:
    return (model.startswith("gpt-5") or model.startswith("o1")
            or model.startswith("o3") or model.startswith("o4"))
```

For `gpt-5*` and `o*` (reasoning/o-series) families:
- Use `max_completion_tokens` instead of `max_tokens` **[HARNESS; DOCS — OpenAI Responses API guide, 2026-06-21]**
- Do **not** send `temperature` — these models reject it **[HARNESS]**

For all other models (`gpt-4.1-*`, `gpt-4o*`):
- Use `max_tokens`
- Send `temperature` normally

The harness handles this automatically. POC code that calls `chat()` does not need to branch.

### Embeddings endpoint

```
POST https://api.openai.com/v1/embeddings
Authorization: Bearer $OPENAI_API_KEY
Content-Type: application/json
```

The `embed()` function in the harness uses `text-embedding-3-small` by default. **[HARNESS]**

### Key creation

Keys are created via https://platform.openai.com/api-keys. Project keys are the recommended type. **[DOCS]**

---

## Anthropic

### Authentication — two required headers

```
POST https://api.anthropic.com/v1/messages
x-api-key: $ANTHROPIC_API_KEY
anthropic-version: 2023-06-01
Content-Type: application/json
```

Both `x-api-key` and `anthropic-version` are **required** on every request. The version value `2023-06-01` is the current stable version as of 2026-06-21. **[DOCS — platform.claude.com/docs/en/api/getting-started, 2026-06-21]**

An alternative `Authorization: Bearer <token>` form exists for Workload Identity Federation (short-lived access tokens from `POST /v1/oauth/token`), but this degree uses the static `x-api-key` form. **[DOCS]**

### Required `max_tokens` parameter

Unlike OpenAI, Anthropic's Messages API **requires** `max_tokens` in every request body. The model will not infer a default. **[DOCS — platform.claude.com/docs/en/api/messages/create, 2026-06-21]**

```json
{
  "model": "claude-haiku-4-5-20251001",
  "max_tokens": 512,
  "messages": [{"role": "user", "content": "Hello"}]
}
```

### Response content extraction

Anthropic returns `content` as an array of typed blocks. Text blocks are extracted as: **[HARNESS]**

```python
parts = d.get("content") or []
text = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
```

Token usage fields differ from OpenAI: `input_tokens` (not `prompt_tokens`) and `output_tokens` (not `completion_tokens`). The harness normalizes these. **[HARNESS]**

### System prompt

Anthropic separates the system prompt from the messages array: it is a top-level `"system"` key in the request body, not a `{"role": "system", ...}` message. The harness handles this via the `system` parameter on `chat()`. **[HARNESS]**

### Key creation

Keys are created via https://platform.claude.com/settings/keys. **[DOCS]**

---

## xAI (Grok)

### Authentication — OpenAI-compatible

```
POST https://api.x.ai/v1/chat/completions
Authorization: Bearer $XAI_API_KEY
Content-Type: application/json
```

xAI's API is OpenAI wire-compatible. The same `_chat_openai_compatible()` function in the harness handles both OpenAI and xAI calls — only the base URL and key env var differ. **[HARNESS + DOCS — docs.x.ai/docs/overview, 2026-06-21]**

### Reasoning tokens and `cost_in_usd_ticks`

`grok-4.3` is a reasoning model. The `reasoning_effort` parameter defaults to `"low"` when not specified, meaning **reasoning tokens are spent on every call by default**. **[DOCS — docs.x.ai/docs/api-reference, 2026-06-21]**

Reasoning tokens appear in:
```json
"usage": {
  "completion_tokens_details": {"reasoning_tokens": 110, ...},
  "cost_in_usd_ticks": 123456789
}
```

The `cost_in_usd_ticks` field is an integer. Conversion: **10,000,000,000 ticks = $1 USD** (i.e., 1 tick ≈ $0.0000000001). **[DOCS — docs.x.ai/docs/api-reference, 2026-06-21]**

The harness converts ticks to USD and stores them as `native_cost_usd` for transparency, but uses the standard PRICES table for cross-provider comparisons. **[HARNESS]**

```python
if "cost_in_usd_ticks" in usage:  # xAI
    native = usage["cost_in_usd_ticks"] * 1e-9  # ticks -> USD
```

Note: The harness currently applies a factor of `1e-9` (one billionth). The spec and docs cite 10 billion ticks per dollar (`1e-10`). **This conversion factor must be verified against a real live call in L0.** Mark the evidence in `L0-smoke-and-harness/evidence.md` with the verified conversion.

### Key creation

Keys are created via https://console.x.ai. **[DOCS — inferred from docs.x.ai/docs/quickstart]**

---

## OpenRouter (optional)

### Authentication

```
POST https://openrouter.ai/api/v1/chat/completions
Authorization: Bearer $OPENROUTER_API_KEY
Content-Type: application/json
```

Keys begin with `sk-or-v1-`. **[DOCS — openrouter.ai/docs/quickstart, 2026-06-21]**

### Optional attribution headers

```
HTTP-Referer: https://agent-university.local
X-Title: agent-university-model-routing
```

These are recommended but not required. They appear on openrouter.ai leaderboards. The harness sends them when the target base URL is `OPENROUTER_BASE`. **[HARNESS + DOCS]**

### When OpenRouter is active

OpenRouter is only used if `OPENROUTER_API_KEY` is set in the environment. The harness detects this via the model id prefix `openrouter/` — e.g. `openrouter/meta-llama/llama-3.3-70b-instruct`. If the key is absent, do not route any model through OpenRouter. **[HARNESS + SPEC]**

See `configuration-and-env-vars.md` for the full OpenRouter model pool config.

---

## Auth errors — what to expect

| Provider | Error on bad key | HTTP status |
|---|---|---|
| OpenAI | `{"error": {"type": "invalid_api_key", ...}}` | 401 |
| Anthropic | `{"type": "error", "error": {"type": "authentication_error", ...}}` | 401 |
| xAI | OpenAI-compatible error shape | 401 |
| OpenRouter | `{"error": {"code": 401, ...}}` | 401 |

The harness raises `ProviderError` on any 4xx. The `L5-failure-modes-and-observability` POC exercises auth error paths deliberately. **[SPEC]**

---

## Secret handling summary

- Never log key values. Use the first 8 chars + `...` pattern for fingerprinting in logs: `key[:8] + "..."`
- Never commit `.agent-university/secrets.local.env`
- Check presence without printing: `[ -n "$OPENAI_API_KEY" ] && echo SET || echo UNSET`
- Full policy: `security-model.md`

---

## Sources

- Anthropic API overview (authentication table): https://platform.claude.com/docs/en/api/getting-started (fetched 2026-06-21)
- Anthropic Messages API reference (max_tokens required): https://platform.claude.com/docs/en/api/messages/create (fetched 2026-06-21)
- xAI API reference (cost_in_usd_ticks, reasoning_effort default): https://docs.x.ai/docs/api-reference (fetched 2026-06-21)
- xAI quickstart (base URL, Bearer auth): https://docs.x.ai/docs/quickstart (fetched 2026-06-21)
- OpenRouter quickstart (Bearer format, optional headers): https://openrouter.ai/docs/quickstart (fetched 2026-06-21)
- Harness source: `harness/providers.py` (coordinator-built, 2026-06-21)
