"""Unified provider layer for the Model Routing degree.

One function, `chat(model, messages, ...)`, that hits the REAL provider API for OpenAI,
Anthropic, and xAI (and OpenRouter if OPENROUTER_API_KEY is set). Returns a normalized dict
with text, token counts, latency, and uniformly-computed USD cost. Stdlib only (urllib) so POC
workers need no pip installs.

NO MOCKS. Every call here crosses a real service boundary. Keys are read from the environment
(load `.agent-university/secrets.local.env` first) and never logged.
"""
import json
import os
import time
import urllib.error
import urllib.request

from pricing import PRICES, usd_for

OPENAI_BASE = "https://api.openai.com/v1"
ANTHROPIC_BASE = "https://api.anthropic.com/v1"
XAI_BASE = "https://api.x.ai/v1"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
SAKANA_BASE = "https://api.sakana.ai/v1"  # Fugu: OpenAI-compatible multi-agent orchestrator


class ProviderError(RuntimeError):
    pass


def provider_of(model: str) -> str:
    if model.startswith("openrouter/"):
        return "openrouter"
    if model.startswith("fugu"):
        return "sakana"
    if model.startswith("grok"):
        return "xai"
    if model.startswith("claude"):
        return "anthropic"
    return "openai"  # gpt-*, o-series, text-embedding-*


def _is_reasoning(model: str) -> bool:
    # Models that spend hidden reasoning tokens: gpt-5 / o-series (OpenAI) and grok-4.x (xAI).
    return (model.startswith("gpt-5") or model.startswith("o1") or model.startswith("o3")
            or model.startswith("o4") or model.startswith("grok-4"))


def _openai_family_no_temp(model: str) -> bool:
    # gpt-5 / o-series reject custom temperature and use max_completion_tokens.
    return model.startswith("gpt-5") or model.startswith("o1") or model.startswith("o3") or model.startswith("o4")


# Reasoning models burn the completion budget on hidden reasoning before emitting any visible
# text. With a small max_tokens they return "" (finish_reason "length"). Floor their budget so
# they actually answer. This makes them legitimately more expensive — which is realistic.
REASONING_FLOOR = 2048


def _post(url: str, headers: dict, payload: dict, timeout: float) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise ProviderError(f"Missing env var {name}; load .agent-university/secrets.local.env")
    return v


def chat(model, messages, max_tokens=512, temperature=0.0, timeout=60.0, system=None,
         extra=None, retries=2):
    """Call a chat model. `messages` is a list of {role, content}. `system` (optional) is a
    system prompt. Returns:
      {model, provider, text, prompt_tokens, completion_tokens, total_tokens,
       latency_ms, usd, finish_reason, raw_usage, native_cost_usd|None}
    Raises ProviderError after exhausting retries.
    """
    provider = provider_of(model)
    last_err = None
    for attempt in range(retries + 1):
        try:
            t0 = time.time()
            if provider == "anthropic":
                out = _chat_anthropic(model, messages, max_tokens, temperature, timeout, system, extra)
            elif provider == "sakana":
                out = _chat_openai_compatible(SAKANA_BASE, _env("SAKANA_API_KEY"), model, messages,
                                              max_tokens, temperature, timeout, system, extra)
            elif provider == "xai":
                out = _chat_openai_compatible(XAI_BASE, _env("XAI_API_KEY"), model, messages,
                                              max_tokens, temperature, timeout, system, extra)
            elif provider == "openrouter":
                real = model[len("openrouter/"):]
                out = _chat_openai_compatible(OPENROUTER_BASE, _env("OPENROUTER_API_KEY"), real,
                                              messages, max_tokens, temperature, timeout, system, extra)
                out["model"] = model
            else:
                out = _chat_openai_compatible(OPENAI_BASE, _env("OPENAI_API_KEY"), model, messages,
                                              max_tokens, temperature, timeout, system, extra)
            out["latency_ms"] = int((time.time() - t0) * 1000)
            out["provider"] = provider
            price_key = model[len("openrouter/"):] if provider == "openrouter" else model
            billed_ct = out.get("billed_completion_tokens", out["completion_tokens"])
            if price_key in PRICES:
                out["usd"] = usd_for(price_key, out["prompt_tokens"], billed_ct)
            elif out.get("native_cost_usd") is not None:
                out["usd"] = out["native_cost_usd"]  # last resort (OpenRouter open models w/o local price)
            else:
                raise ProviderError(f"No price for {price_key}; add it to pricing.PRICES")
            return out
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:500]
            last_err = ProviderError(f"{provider} HTTP {e.code} for {model}: {body}")
            # Retry only on 429/5xx
            if e.code in (429, 500, 502, 503, 529) and attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise last_err
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = ProviderError(f"{provider} network error for {model}: {e}")
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise last_err
    raise last_err


def _chat_openai_compatible(base, key, model, messages, max_tokens, temperature, timeout, system, extra):
    msgs = list(messages)
    if system:
        msgs = [{"role": "system", "content": system}] + msgs
    payload = {"model": model, "messages": msgs}
    budget = max(max_tokens, REASONING_FLOOR) if _is_reasoning(model) else max_tokens
    if _openai_family_no_temp(model):
        payload["max_completion_tokens"] = budget
    else:
        payload["max_tokens"] = budget
        if not (model.startswith("grok-4") and temperature == 0.0):
            payload["temperature"] = temperature
    if base == OPENROUTER_BASE:
        payload["usage"] = {"include": True}  # ask OpenRouter to return real USD cost inline
    if extra:
        payload.update(extra)
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if base == OPENROUTER_BASE:
        headers["HTTP-Referer"] = "https://agent-university.local"
        headers["X-Title"] = "agent-university-model-routing"
    d = _post(f"{base}/chat/completions", headers, payload, timeout)
    choice = (d.get("choices") or [{}])[0]
    text = (choice.get("message") or {}).get("content") or ""
    usage = d.get("usage") or {}
    pt = usage.get("prompt_tokens", 0)
    ct = usage.get("completion_tokens", 0)
    total = usage.get("total_tokens", pt + ct)
    # Fugu (Sakana) bills ORCHESTRATION tokens too: the multi-agent conductor consumes large
    # internal token counts. usage exposes them; total = pt + ct + orch_in + orch_out. Bill the
    # input-side (pt + orch_in) at the input rate and the output-side (ct + orch_out) at output.
    orch_in = (usage.get("prompt_tokens_details") or {}).get("orchestration_input_tokens", 0) or 0
    orch_out = (usage.get("completion_tokens_details") or {}).get("orchestration_output_tokens", 0) or 0
    if orch_in or orch_out:
        pt = pt + orch_in
        billed_ct = ct + orch_out
    else:
        # Reasoning tokens are billed as output. OpenAI folds them INTO completion_tokens; xAI/grok
        # reports them only in total (completion_tokens excludes reasoning). Bill the larger.
        billed_ct = max(ct, total - pt) if total and total > pt else ct
    native = None
    if "cost_in_usd_ticks" in usage:  # xAI
        native = usage["cost_in_usd_ticks"] / 1e10  # xAI docs: 1 USD = 1e10 ticks (cost-tracking page)
    elif usage.get("cost") is not None:  # OpenRouter returns real USD when usage.include=true
        native = float(usage["cost"])
    return {
        "model": model, "text": text,
        "prompt_tokens": pt, "completion_tokens": ct, "billed_completion_tokens": billed_ct,
        "total_tokens": total,
        "finish_reason": choice.get("finish_reason"), "raw_usage": usage, "native_cost_usd": native,
    }


def _chat_anthropic(model, messages, max_tokens, temperature, timeout, system, extra):
    payload = {"model": model, "max_tokens": max_tokens, "temperature": temperature,
               "messages": [{"role": m["role"], "content": m["content"]} for m in messages]}
    if system:
        payload["system"] = system
    if extra:
        payload.update(extra)
    headers = {"x-api-key": _env("ANTHROPIC_API_KEY"), "anthropic-version": "2023-06-01",
               "Content-Type": "application/json"}
    d = _post(f"{ANTHROPIC_BASE}/messages", headers, payload, timeout)
    parts = d.get("content") or []
    text = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
    usage = d.get("usage") or {}
    pt = usage.get("input_tokens", 0)
    ct = usage.get("output_tokens", 0)
    return {
        "model": model, "text": text,
        "prompt_tokens": pt, "completion_tokens": ct, "billed_completion_tokens": ct,
        "total_tokens": pt + ct,
        "finish_reason": d.get("stop_reason"), "raw_usage": usage, "native_cost_usd": None,
    }


def embed(texts, model="text-embedding-3-small", timeout=60.0):
    """Return (vectors: list[list[float]], usd). OpenAI embeddings."""
    if isinstance(texts, str):
        texts = [texts]
    payload = {"model": model, "input": texts}
    headers = {"Authorization": f"Bearer {_env('OPENAI_API_KEY')}", "Content-Type": "application/json"}
    d = _post(f"{OPENAI_BASE}/embeddings", headers, payload, timeout)
    vecs = [row["embedding"] for row in d["data"]]
    usage = d.get("usage") or {}
    usd = usd_for(model, usage.get("prompt_tokens", 0), 0)
    return vecs, usd
