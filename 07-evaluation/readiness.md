# Degree Readiness — LLM Model Routing

Live verified (2026-06-21/22). All 15 POCs executed against real providers.

## Gate status summary

| Gate | Status | Notes |
|---|---|---|
| Research complete | PASS | pricing, papers, production routers documented |
| Harness live | PASS | 3 providers reachable; L0 baseline measured |
| POC ladder complete | PASS | 15/15 POCs green (L0–L5, X1–X5, capstone) |
| Capstone live | PASS | adaptive gateway: acc 0.978, $0.00257, 8.4× cheaper than always-strong |
| Distillation authored | PASS | gotchas, patterns, recipes, skill-pack written |
| Evidence tiers labeled | PASS | "Live verified" in every rank-bearing section |
| Honest negatives documented | PASS | MoA/debate/SC failures, FrugalGPT gate failure — first-class findings |
| Blocked work declared | PASS | OpenRouter optional; gpt-5/grok prices estimated |
| Known limitations stated | PASS | small suite, hard-math gap, price uncertainty |

## Provider readiness

| Provider | Env var | Models verified live |
|---|---|---|
| OpenAI | OPENAI_API_KEY | gpt-4o-mini, gpt-4.1, gpt-4o, text-embedding-3-small |
| Anthropic | ANTHROPIC_API_KEY | claude-haiku-4-5-20251001 (ensemble member) |
| xAI | XAI_API_KEY | grok-4.3 (provider liveness confirmed L0) |

## Corpus status

All 15 POC READMEs are INDEXED with "Live verified" tier markers. Distillation and
skill-pack files contain "Live verified" in every rank-bearing section as required by
the indexer. No placeholder content remains.

## Deploy readiness

This degree is ready for merge to main, which auto-deploys to Railway
(agent-university-api production). After merge, confirm `/v1/health` `corpusVersion`
bumps and `/v1/search?q=model+routing` returns this degree ranked #1.
