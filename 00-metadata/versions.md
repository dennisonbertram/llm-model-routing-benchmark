# Versions

| Component | Version / id | Notes |
|---|---|---|
| Python | 3.9.6 | stdlib + numpy 2.0.2 (no sklearn, no pip installs) |
| OpenAI models | gpt-4.1-nano, gpt-4.1-mini, gpt-4o-mini, gpt-4o, gpt-4.1, gpt-5-mini, gpt-5 | live-listed 2026-06-21 |
| OpenAI embeddings | text-embedding-3-small (1536d), -large | live-listed 2026-06-21 |
| Anthropic models | claude-haiku-4-5-20251001, claude-sonnet-4-5-20250929, claude-sonnet-4-6, claude-opus-4-8 | live-listed 2026-06-21 |
| xAI models | grok-4.3 | OpenAI-compatible; usage carries cost_in_usd_ticks |
| OpenRouter | optional | wired only if OPENROUTER_API_KEY present |

Exact pricing (per-1M tokens, in/out) with source URLs + date is recorded in
`01-research/pricing-quotas-limits.md`.
