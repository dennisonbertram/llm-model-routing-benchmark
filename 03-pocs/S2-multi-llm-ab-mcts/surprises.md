# Surprises (live)
1. AB-MCTS@8 used only 4 LLM calls (not 32) — it early-stops at PUBLIC-perfect, but that candidate still fails a HIDDEN edge case. The search is blind to failures its verifier can't see. "A searcher is only as good as its verifier" (the paper's caveat, live).
2. AB-MCTS matched repeated-sampling accuracy at 8x fewer calls / ~20x lower cost — the efficiency win is real even when the accuracy win is not.
3. The Thompson bandit concentrated ALL pulls on one model (qwen). Diversity bought nothing because the pool's errors were correlated (all 3 fail the same item's same hidden cases) — the opposite of Sakana's ARC condition (complementary models).
4. Cheap diverse models are individually ~0.95 on hard coding — nearly the frontier — so the headroom for orchestration was tiny to begin with.
