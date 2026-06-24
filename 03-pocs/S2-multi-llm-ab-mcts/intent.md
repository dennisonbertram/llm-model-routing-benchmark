# POC Intent
POC level: S2 — Multi-LLM AB-MCTS (Sakana's open method)
Concept introduced: adaptive branching tree search (wider-vs-deeper) with a per-model Thompson bandit + a real verifier.
Prior concepts reused: the frozen harness, the hard suite (S0), the diverse OpenRouter pool (S1), public/hidden split.
Live service boundary: live OpenRouter calls (DeepSeek/Qwen/Gemini) + gpt-5.5 reference.
What this must prove: whether adaptive multi-model search beats best-single / repeated-sampling / the frontier, with real numbers — win OR loss.
What would count as cheating: scoring on the same tests the search optimizes (leakage); claiming a win inside noise; faking the bandit.
