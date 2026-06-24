"""Price table (USD per 1,000,000 tokens) for the model pool.

Provenance: list-price estimates seeded 2026-06-21; reconciled against the official pricing
pages recorded in `01-research/pricing-quotas-limits.md`. Cost in this degree is computed
UNIFORMLY as  cost = (prompt_tokens/1e6)*in + (completion_tokens/1e6)*out  for ALL providers,
so cross-model cost comparisons are apples-to-apples. (xAI also returns a native
`cost_in_usd_ticks`; we record it in raw evidence but do not mix cost methods.)

If a price here disagrees with the researched pricing file, the researched file wins — update
PRICES and re-run any affected POC. Reasoning tokens (xAI/o-series) are billed as output tokens.
"""

# model id -> (input_usd_per_1M, output_usd_per_1M)
PRICES = {
    # OpenAI
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4.1": (2.00, 8.00),
    "gpt-5-nano": (0.05, 0.40),
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5": (1.25, 10.00),
    # Frontier reasoning tier (openai.com/api/pricing, aipricing.guru — checked 2026-06-22)
    "gpt-5.5": (5.00, 30.00),
    "gpt-5.4": (2.50, 15.00),
    "text-embedding-3-small": (0.02, 0.0),
    "text-embedding-3-large": (0.13, 0.0),
    # Anthropic
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-4-5-20250929": (3.00, 15.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-8": (15.00, 75.00),
    # xAI  (reasoning tokens billed as output at the output rate)
    "grok-4.3": (1.25, 2.50),
    # OpenRouter diverse pool (per-1M from OpenRouter /models, fetched 2026-06-22). Used as a
    # guaranteed fallback when OpenRouter's inline usage.cost is absent; usage.cost wins when present.
    "deepseek/deepseek-chat-v3.1": (0.210, 0.790),
    "qwen/qwen-2.5-72b-instruct": (0.360, 0.400),
    "meta-llama/llama-3.3-70b-instruct": (0.100, 0.320),
    "mistralai/mistral-medium-3-5": (1.500, 7.500),
    "google/gemini-2.5-flash-lite-preview-09-2025": (0.100, 0.400),
    "deepseek/deepseek-r1-0528": (0.500, 2.150),
    # cheap-ensemble trio (OpenRouter /models, 2026-06-23)
    "google/gemma-4-31b-it": (0.12, 0.35),
    "deepseek/deepseek-v4-flash": (0.09, 0.18),
    "deepseek/deepseek-v4-pro": (0.43, 0.87),
    "z-ai/glm-5.2": (0.98, 3.08),
    "z-ai/glm-4.7-flash": (0.06, 0.40),
    "mistralai/mistral-small-2603": (0.15, 0.60),
    "google/gemini-3.5-flash": (1.50, 9.00),
    # current cheap reasoners (OpenRouter /models, 2026-06-23)
    "qwen/qwen3-235b-a22b-thinking-2507": (0.10, 0.10),
    "deepseek/deepseek-v3.2": (0.229, 0.343),
    "minimax/minimax-m2.5": (0.15, 0.90),
    # remaining bench-registry models — added so the cost axis is the SAME source (local price
    # table) for every model and never depends on OpenRouter's flaky inline usage.cost (a missing
    # entry here previously made llama-4-maverick error -> counted wrong). 2026-06-23.
    "qwen/qwen3-235b-a22b-2507": (0.09, 0.10),
    "moonshotai/kimi-k2.5": (0.375, 2.025),
    "google/gemini-3.1-flash-lite": (0.25, 1.50),
    "meta-llama/llama-4-maverick": (0.15, 0.60),
    "amazon/nova-lite-v1": (0.06, 0.24),
    # Sakana Fugu (console.sakana.ai/pricing, 2026-06-22): fugu-ultra $5/$30 per 1M, billed on ALL
    # tokens INCLUDING orchestration. fugu (mini) bills at the top-tier underlying-model rate — we
    # estimate it at the same $5/$30 ceiling (labeled estimate; the visible vs orchestration token
    # split is what dominates cost, not the rate).
    "fugu-ultra": (5.00, 30.00),
    "fugu-ultra-20260615": (5.00, 30.00),
    "fugu": (5.00, 30.00),
}

# Core pool (gpt-4.1-nano/mini, gpt-4o-mini, gpt-4.1, claude-haiku/sonnet-4-5, grok-4.3) was
# reconciled 2026-06-21 against the official pricing pages recorded in
# 01-research/pricing-quotas-limits.md. gpt-5 / gpt-5-mini / claude-opus-4-8 remain list-price
# estimates for the tiers that aren't on the critical cost-comparison path.
ESTIMATED = False
ESTIMATE_ONLY = {"gpt-5", "gpt-5-mini", "claude-opus-4-8"}


def usd_for(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pin, pout = PRICES.get(model, (None, None))
    if pin is None:
        # Unknown model: fall back to a conservative mid price and flag via 0 only if truly unknown.
        # Routing demos must not silently price an unknown model at 0.
        raise KeyError(f"No price for model {model!r}; add it to pricing.PRICES")
    return (prompt_tokens / 1e6) * pin + (completion_tokens / 1e6) * pout
