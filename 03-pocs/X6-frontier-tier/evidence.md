# X6 Live Evidence

Status: Complete with live evidence. Evidence strength: Strong. Captured 2026-06-22.
Live services: OpenAI (gpt-5.5, gpt-5.4 chat + embeddings). No mocks. Machine-readable: source/x6_summary.json, source/x6_3tier_summary.json.

## Frontier models over 45 tasks
| model | acc | hard-math(7) | cost | vs gpt-4.1 | latency |
|---|---|---|---|---|---|
| gpt-5.4 | 0.978 | 6/7 | $0.03958 | 1.8x | 1367ms |
| gpt-5.5 | 1.000 | 7/7 | $0.11943 | 5.6x | 2753ms |
m8 (neither cheap nor gpt-4.1 solved, gold=14): gpt-5.4=True, gpt-5.5=True.
Non-monotonic: gpt-5.4 fixed m8 but broke m10 (gold=16) -> net 0.978, dominated by gpt-4.1.

## Realizable 3-tier router (cheap -> gpt-4.1 -> gpt-5.5), CV logistic, two thresholds
best (hi=0.8, lo=0.5): acc=1.000, $0.00405 -> 30x cheaper than always-gpt-5.5 ($0.11943), 1.09x the 3-tier oracle ($0.00372).
Routes 32->cheap, 12->gpt-4.1, 1->gpt-5.5.

## Claims supported
- GPT-5.5 raises the achievable ceiling to 100% (clears the hard-math tail incl. m8) at 5.6x gpt-4.1 cost.
- A deployable 3-tier router captures that 100% ceiling at ~1/30th the always-gpt-5.5 cost.
- A newer model (gpt-5.4) is not automatically better per item and can be strictly dominated on cost.

## Claims NOT supported
- That gpt-5.5 is worth it for easy/standard tasks (it is not — route to it only for the hard tail).
- Generalization beyond this 45-task suite (small, hard-math-concentrated); these are demonstrations.
