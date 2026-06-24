# S2 Live Evidence
Status: Complete with live evidence. Captured 2026-06-22. Live: OpenRouter (DeepSeek/Qwen/Gemini) + gpt-5.5. No mocks. Machine-readable: source/s2_results.json.
HIDDEN pass-fraction (4 hard coding, no leakage): gpt-5.5 1.000/$0.0301 ; best-single-cheap 0.950/$0.0011 ; repeated@8 0.950 (32 calls/$0.0085) ; AB-MCTS@8 0.950 (4 calls/$0.0004).
Claims supported: AB-MCTS is more sample-efficient than repeated sampling (same acc, 8x fewer calls); it does NOT beat best-single or the frontier here (correlated errors); search is bounded by verifier coverage; bandit concentrated on one arm.
Claims NOT supported: that AB-MCTS never helps (it wins where errors are uncorrelated + the verifier is complete — not this suite); large-n generality (n=4, gpt-5.5 saturates anything bigger we could author).
