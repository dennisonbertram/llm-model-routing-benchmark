# Live Access Playbook — LLM Model Routing

Live verified. Covers: loading credentials, verifying provider reachability, the
minimum live calls needed to validate the harness, and what to do when a provider
is unreachable.

---

## 1. Loading credentials

**Live verified** (L0; all POCs)

Credentials live in `.agent-university/secrets.local.env` (gitignored). Load into the
current shell without printing values:

```bash
set -a; . .agent-university/secrets.local.env; set +a
```

Verify presence without printing the key:
```bash
[ -n "$OPENAI_API_KEY" ] && echo "OPENAI: SET" || echo "OPENAI: UNSET"
[ -n "$ANTHROPIC_API_KEY" ] && echo "ANTHROPIC: SET" || echo "ANTHROPIC: UNSET"
[ -n "$XAI_API_KEY" ] && echo "XAI: SET" || echo "XAI: UNSET"
```

The minimum key for all L-series POCs is `OPENAI_API_KEY`. Anthropic is required for
X1 (MoA uses `claude-haiku-4-5-20251001` as one of the ensemble proposers). xAI is
needed only for the grok-4.3 smoke in L0.

---

## 2. Smoke-testing provider reachability

**Live verified** (L0)

The L0 harness smoke tests three providers live. Run them as the minimum live access check:

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd model-routing/degrees/01-llm-model-routing/03-pocs/L0-smoke-and-harness/source
python3 test_l0.py    # GREEN: 3 live behavioral tests pass in ~5 seconds
```

Expected output (GREEN):
```
test_baselines_and_oracle ... ok
test_oracle_headroom ... ok
test_providers_live ... ok
----------------------------------------------------------------------
Ran 3 tests in 5.XXXs
OK
```

Expected output (RED, no credentials):
```
ERROR: test_providers_live
ProviderError: Missing env var OPENAI_API_KEY
```

---

## 3. Minimum live calls per provider

**Live verified** (L0)

Each provider requires one call to confirm reachability:

```python
# From L0 test_l0.py (abridged)
# OpenAI
result = chat("gpt-4o-mini", [{"role": "user", "content": "Say OK."}], max_tokens=4)
assert result.text.strip(), "gpt-4o-mini: empty response"
assert result.usd > 0, "gpt-4o-mini: zero cost"

# Anthropic
result = chat("claude-haiku-4-5-20251001", [{"role": "user", "content": "Say OK."}], max_tokens=4)
assert result.text.strip(), "claude-haiku: empty response"

# xAI (optional)
result = chat("grok-4.3", [{"role": "user", "content": "Say OK."}], max_tokens=4)
assert result.text.strip(), "grok-4.3: empty response"
```

The xAI smoke in L0 confirmed: grok-4.3 returns responses via the xAI OpenAI-compatible
endpoint with `cost_in_usd_ticks` in the usage object.

---

## 4. Reusing the outcome matrix to avoid re-billing

**Live verified** (L0; all later POCs)

Once L0 has run and built `harness/.cache/labelset.json`, all later POCs should import
it rather than re-calling both models on all 45 tasks. The `Cache` class manages this:

```python
from cache import Cache

cache = Cache("harness/.cache")  # relative to the POC's source dir

# This returns a cached response if (model, task_id) exists; calls live otherwise
result = cache.chat("gpt-4o-mini", messages, nonce=None)
```

Total cost to build the full outcome matrix (first run only):
- gpt-4o-mini × 45: ~$0.00166
- gpt-4.1 × 45: ~$0.02148
- Total: ~$0.023

All subsequent POC runs that reuse the cache pay $0 for the outcome matrix.

Embedding cache works the same way (`.embed-cache.json` per POC). The L2 embedding
cache for 45 prompts cost ~$0.000030 one-time.

---

## 5. Provider-specific failure modes

**Live verified** (L5)

Real error responses for common failures (triggered live against OpenAI API):

**Invalid model slug (HTTP 404):**
```
openai HTTP 404 for gpt-9000-doesnt-exist:
{"error": {"message": "The model `gpt-9000-doesnt-exist` does not exist or you do not have access to it.",
           "type": "invalid_request_error"}}
```
Recovery: fallback to `gpt-4o-mini`.

**max_tokens too large (HTTP 400):**
```
openai HTTP 400 for gpt-4o-mini:
{"error": {"message": "max_tokens is too large: 999999. This model supports at most 16384 completion tokens.",
           "type": "invalid_request_error", "param": "max_tokens", "code": "invalid_value"}}
```
Recovery: fallback with `max_tokens=64`.

**Network timeout:**
```
openai network error for gpt-4o-mini: <urlopen error timed out>
```
Recovery: retry with extended timeout (30s).

**Missing credentials (pre-call, no HTTP):**
```
ProviderError: Missing env var OPENAI_API_KEY
```
This is the expected RED state for all POCs when credentials are absent.

---

## 6. When a provider is temporarily unreachable

**Live verified** (L5)

The `resilient_call` pattern from L5:

```python
def resilient_call(attempts: list[dict]) -> dict:
    """
    attempts: list of {"model": ..., "messages": ..., "max_tokens": ..., "timeout": ...}
    Tries each in order; returns first success.
    """
    last_error = None
    for attempt in attempts:
        try:
            result = chat(**attempt)
            return result
        except ProviderError as e:
            log_json({"event": "attempt_failed", "error": str(e), **attempt})
            last_error = e
    raise last_error

# Usage: primary strong, fallback cheap
result = resilient_call([
    {"model": STRONG_DEFAULT, "messages": msgs, "max_tokens": 512, "timeout": 10},
    {"model": CHEAP_DEFAULT,  "messages": msgs, "max_tokens": 512, "timeout": 30},
])
```

The L5 fallback chain recovered from all 5 failure modes. FM2 (timeout) recovered via
the retry pattern with a different timeout parameter. FM1 and FM3 recovered via the
fallback model.

---

## Evidence

- L0 README.md: "Evidence: Live verified. Prove all 3 providers reachable live." (Live verified)
- L5 README.md: real error responses from OpenAI API, all 5 failure modes. (Live verified)
- L5 README.md: "All 9 behavioral tests pass against live providers." (Live verified)
- results-digest.md: "L4 runtime: 3 live curls routed; RED = HTTP 502 missing key." (Live verified)
