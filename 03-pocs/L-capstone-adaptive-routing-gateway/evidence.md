# L-Capstone Live Evidence

Status: Complete with live evidence. Evidence strength: Strong. Captured 2026-06-21.
Live services: OpenAI (chat + embeddings), Anthropic. Real local HTTP server. No mocks.

## Honest CV benchmark (45 tasks, 5-fold, no leakage)
adaptive(thr=0.8): acc=0.978, $0.00257 (8.4x cheaper than always-strong $0.02148; 1.20x oracle $0.00214).
Full sweep + baselines in green-output.txt.

## Live gateway (curl)
- auto + "capital of France" -> classifier p_cheap=0.97 -> gpt-4o-mini -> "Paris."
- auto + "arrange BALLOON"   -> classifier p_cheap=0.38 -> gpt-4.1     -> "1260" (correct)
- forced gpt-4o-mini          -> honored (decision=forced)
- gateway-ledger.jsonl persisted with decision/model/usd/latency per request.

## Live reliability
- Budget guard ($0.00025 cap): reqs 5-6 forced to cheap (decision=budget_guard...).
- Fallback: bad strong slug -> fell back to gpt-4o-mini (fallback_from=yes), request still answered.

## Claims supported
- A deployable adaptive gateway matches strong accuracy at ~1/8 the cost, near the oracle.
- Budget guard, provider fallback, and OpenAI-compatible routing all work against live providers.

## Claims NOT supported
- Production-scale throughput/SLA; multi-region; persistence beyond the local ledger file.
- That thr=0.8 is universally optimal (it is best on THIS 45-task CV).
