"""Aggregation/judge helpers for ensemble routers (Mixture-of-Agents, debate).

These are NOT the final grader — final correctness is always the task's deterministic grader.
These helpers only implement the *combination* step where multiple proposals must be fused or
ranked, which inherently needs a model.
"""
import re

import config


def _chat(cache, model, prompt, max_tokens=700, temperature=0.0, system=None):
    if cache is not None:
        return cache.chat(model, [{"role": "user", "content": prompt}], max_tokens=max_tokens,
                          temperature=temperature, system=system)
    from providers import chat
    return chat(model, [{"role": "user", "content": prompt}], max_tokens=max_tokens,
                temperature=temperature, system=system)


def aggregate_moa(question, proposals, model=None, cache=None, max_tokens=700):
    """Mixture-of-Agents aggregator: synthesize a single high-quality answer from N proposals.
    Returns {text, usd, latency_ms}. (Wang et al., Mixture-of-Agents.)"""
    model = model or config.MID_DEFAULT
    listed = "\n\n".join(f"[Response {i+1}]\n{p}" for i, p in enumerate(proposals))
    system = ("You have been provided with responses from several models to the latest user query. "
              "Synthesize them into a single, high-quality, correct answer. Do not merely copy; "
              "critically evaluate, fix errors, and follow the question's exact output format.")
    prompt = f"User query:\n{question}\n\nCandidate responses:\n{listed}\n\nFinal answer:"
    r = _chat(cache, model, prompt, max_tokens=max_tokens, system=system)
    return {"text": r["text"], "usd": r["usd"], "latency_ms": r["latency_ms"]}


def pick_best(question, proposals, model=None, cache=None):
    """Judge picks the best proposal index (1-based in the prompt). Returns {index, usd, latency_ms}."""
    model = model or config.JUDGE_MODEL
    listed = "\n\n".join(f"[{i+1}]\n{p}" for i, p in enumerate(proposals))
    prompt = (f"Question:\n{question}\n\nCandidate answers:\n{listed}\n\n"
              f"Which candidate is most correct? Reply with ONLY the number (1-{len(proposals)}).")
    r = _chat(cache, model, prompt, max_tokens=8)
    nums = re.findall(r"\d+", r["text"])
    idx = (int(nums[0]) - 1) if nums else 0
    idx = max(0, min(idx, len(proposals) - 1))
    return {"index": idx, "usd": r["usd"], "latency_ms": r["latency_ms"]}
