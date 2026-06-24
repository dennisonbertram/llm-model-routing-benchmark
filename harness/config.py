"""Model pool for the routing experiments — all live-verified 2026-06-21.

Tiers are ordered cheapest -> strongest. The canonical "cheap vs strong" pair used in the
headline routing demos is (CHEAP_DEFAULT, STRONG_DEFAULT): both OpenAI, clean per-token cost,
no hidden reasoning tokens — so the cost-quality gap is unambiguous.
"""

CHEAP = ["gpt-4.1-nano", "gpt-4o-mini", "claude-haiku-4-5-20251001"]
MID = ["gpt-4.1-mini", "gpt-4o", "claude-sonnet-4-5-20250929"]
STRONG = ["gpt-4.1", "claude-opus-4-8"]            # strong, non-reasoning, reliable
FRONTIER_REASONING = ["gpt-5-mini", "gpt-5"]       # reasoning models (help math; cost/latency higher)
CROSS_PROVIDER = ["grok-4.3"]                      # optional; reasons by default, reconcile cost

EMBED_MODEL = "text-embedding-3-small"
JUDGE_MODEL = "gpt-4.1"                             # strong, cross-family from claude/grok answers

CHEAP_DEFAULT = "gpt-4o-mini"
MID_DEFAULT = "gpt-4o"
STRONG_DEFAULT = "gpt-4.1"

# A diverse set of cheap models for ensemble POCs (Mixture-of-Agents, debate): different families
# so their errors are less correlated.
ENSEMBLE_CHEAP = ["gpt-4o-mini", "gpt-4.1-mini", "claude-haiku-4-5-20251001"]
