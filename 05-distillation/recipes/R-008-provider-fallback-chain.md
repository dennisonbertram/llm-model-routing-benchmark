# R-008: Provider Fallback Chain

**Category**: recipe
**Evidence tier**: Live verified (POCs L5, L-capstone)
**Source POCs**: L5-failure-modes-and-observability, L-capstone-adaptive-routing-gateway

## Live verified

Five real failure modes triggered against the live OpenAI API, each recovered by a fallback
chain (L5). All 9 behavioral tests green.

| Failure mode              | Real provider response          | Recovery                        |
|---------------------------|---------------------------------|---------------------------------|
| Invalid model slug        | HTTP 404: "model does not exist" | fallback to gpt-4o-mini        |
| Sub-millisecond timeout   | `<urlopen error timed out>`     | retry with timeout=30s          |
| max_tokens over limit     | HTTP 400: "supports at most 16384" | fallback with max_tokens=64   |
| Budget guard trips        | refused by guard (no HTTP call) | `no_model_fits_budget`          |
| Verifier correct, no escalation | cheap answered correctly   | no escalation needed            |

Live verified (capstone): a deliberately bad strong model slug → gateway fell back to
gpt-4o-mini and still returned an answer (`fallback_from=yes`). (L-capstone)

## Snippet (copy-paste-ready)

```python
import urllib.request, urllib.error, json, time

class ProviderError(Exception):
    def __init__(self, msg, status=None, body=None):
        super().__init__(msg)
        self.status = status
        self.body   = body

def _chat_once(model: str, messages: list[dict], **kwargs) -> dict:
    """Single attempt; raises ProviderError on HTTP/network failure."""
    from providers import chat  # harness chat wrapper
    try:
        return chat(model, messages, **kwargs)
    except Exception as e:
        raise ProviderError(str(e)) from e

def resilient_call(
    attempts: list[dict],
    log_fn=None,
) -> dict:
    """
    Try each attempt in order; return the first success.
    Each attempt dict: {"model": ..., "kwargs": {...}, "label": ...}

    Example:
        resilient_call([
            {"model": "gpt-4.1",      "kwargs": {"max_tokens": 512}, "label": "primary"},
            {"model": "gpt-4o-mini",  "kwargs": {"max_tokens": 512}, "label": "fallback"},
        ])
    """
    last_error = None
    for attempt in attempts:
        model  = attempt["model"]
        kwargs = attempt.get("kwargs", {})
        label  = attempt.get("label", model)
        try:
            result = _chat_once(model, attempt["messages"], **kwargs)
            if log_fn:
                log_fn({"event": f"{label}_success", "model": model,
                        "usd": result.usd, "latency_ms": result.latency_ms})
            return result
        except ProviderError as e:
            last_error = e
            if log_fn:
                log_fn({"event": f"{label}_failure", "model": model, "error": str(e)})
    raise last_error or ProviderError("all attempts failed")
```

## Common fallback patterns

**Pattern 1: bad slug → cheap fallback**
```python
result = resilient_call([
    {"model": intended_strong, "messages": msgs, "kwargs": {}, "label": "primary"},
    {"model": "gpt-4o-mini",   "messages": msgs, "kwargs": {}, "label": "fallback"},
])
```

**Pattern 2: timeout retry with increased timeout**
```python
result = resilient_call([
    {"model": "gpt-4o-mini", "messages": msgs,
     "kwargs": {"timeout": 1},  "label": "fast_attempt"},
    {"model": "gpt-4o-mini", "messages": msgs,
     "kwargs": {"timeout": 30}, "label": "normal_timeout"},
])
```

**Pattern 3: max_tokens over limit → smaller budget fallback**
```python
result = resilient_call([
    {"model": "gpt-4o-mini", "messages": msgs,
     "kwargs": {"max_tokens": 999999}, "label": "overlimit"},     # will 400
    {"model": "gpt-4o-mini", "messages": msgs,
     "kwargs": {"max_tokens": 64},     "label": "safe_budget"},   # safe fallback
])
```

**Pattern 4: full chain (strong → mid → cheap)**
```python
result = resilient_call([
    {"model": "gpt-4.1",     "messages": msgs, "kwargs": {}, "label": "strong"},
    {"model": "gpt-4o",      "messages": msgs, "kwargs": {}, "label": "mid"},
    {"model": "gpt-4o-mini", "messages": msgs, "kwargs": {}, "label": "cheap"},
])
```

## Real error responses captured (L5)

OpenAI HTTP 404 (invalid slug):
```
"The model `gpt-9000-doesnt-exist` does not exist or you do not have access to it."
```

OpenAI HTTP 400 (max_tokens over limit):
```
"max_tokens is too large: 999999. This model supports at most 16384 completion tokens."
```

OpenAI network timeout:
```
"<urlopen error timed out>"
```

All three are wrapped by `ProviderError` in the harness. Catch `ProviderError` to handle all
provider failures uniformly.

## Structured log contract (live format, L5)

```json
{"ts": "23:49:37", "event": "fm1_invalid_slug",   "model": "gpt-9000-doesnt-exist", "outcome": "failure", "error": "openai HTTP 404 ..."}
{"ts": "23:49:38", "event": "fm1_fallback_success","model": "gpt-4o-mini",           "outcome": "success", "usd": 3.75e-06, "latency_ms": 444}
```

Log every attempt (success or failure). Include `model`, `outcome`, `error`, `usd`,
`latency_ms`. Never log the API key value.

## Gotchas (live-discovered, L5)

- `ProviderError` wraps HTTP 404, HTTP 400, and `urllib.error.URLError` (timeout/network)
  uniformly. A single `except ProviderError` catches all three.
- The gateway health endpoint (`/v1/health`) responds even when no API key is configured.
  HTTP 502 only appears when an actual upstream model call is attempted. Test health-check
  availability independently from credential validity. (L4)
- `max_tokens=999999` triggers HTTP 400, not a network error. The fallback chain handles it
  the same way, but the appropriate recovery is to reduce `max_tokens`, not to switch models.

## Evidence

- L5-failure-modes-and-observability/README.md — 5 FM table, real HTTP error bodies, log excerpts
- L-capstone-adaptive-routing-gateway/README.md — fallback_from=yes capstone live behavior
- results-digest.md lines 38–39 — L5 authoritative numbers
