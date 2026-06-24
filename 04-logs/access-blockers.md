# Access Blockers

# Access Blocker

Timestamp: 2026-06-21
Service: OpenRouter (https://openrouter.ai)
Required access: OpenRouter API key (`sk-or-...`)
Minimum scopes: inference (chat/completions) + GET /generation cost accounting
Environment variables: OPENROUTER_API_KEY
Blocked POCs: none are *blocked* — every POC runs on OpenAI/Anthropic/xAI. OpenRouter only
  *enhances* the ensemble POCs (open models: Qwen/Llama/DeepSeek/Mistral) and adds native unified
  per-generation cost accounting.
What cannot be tested without it: open-weight-model routing/ensembles via a single unified key;
  OpenRouter's own Auto Router behavior; GET /generation cost reconciliation.
Why mocks are forbidden: routing claims are only valid against real model responses + real cost.
Future-agent prerequisite: to reproduce the open-model ensemble variants, set OPENROUTER_API_KEY.
Status: RESOLVED 2026-06-22 — OPENROUTER_API_KEY provided; diverse pool (DeepSeek/Qwen/Gemini/Llama/
  Mistral) live-verified and used for the S1/S2 AB-MCTS track.

# Access Blocker

Timestamp: 2026-06-22
Service: Sakana Fugu (https://api.sakana.ai/v1)
Required access: Sakana API key (`fish_...`) + an ACTIVE SUBSCRIPTION (Standard/Pro/Max or pay-as-you-go)
Minimum scopes: inference on models `fugu` / `fugu-ultra`
Environment variables: SAKANA_API_KEY
Blocked POCs: S3 (real Fugu head-to-head) — initially blocked: the key authenticated and listed models
  but inference returned `{"error":{"message":"No active subscription","type":"usage_limit_reached"}}`.
What cannot be tested without it: real Fugu Mini/Ultra inference (only the model list is readable without a sub).
Why mocks are forbidden: orchestration claims are only valid against the real conductor's real cost+latency.
Future-agent prerequisite: activate a subscription on the Sakana account behind the key.
Status: RESOLVED 2026-06-22 — subscription activated; S3 now Complete with live evidence
  (fugu-ultra matches gpt-5.5 at 12.2x cost / 5.6x latency; fugu-mini 0.905 at 4x cost).
