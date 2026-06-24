# S2 — Multi-LLM AB-MCTS over a diverse pool (faithful Sakana reproduction)

**Evidence: Live verified (2026-06-22).** Status: Complete with live evidence.

This reproduces the one **open, published** layer behind Sakana Fugu: **Multi-LLM AB-MCTS**
(arXiv:2503.04412 / TreeQuest). A vendored AB-MCTS-A (Beta/Jeffreys-prior posteriors, Thompson
sampling over GEN-vs-refine actions, one bandit arm per model — `source/abmcts.py`, ~120 lines
stdlib+numpy because TreeQuest needs Python 3.11 and this repo is 3.9) searches over a **diverse,
individually-non-saturating** pool — DeepSeek-chat-v3.1, Qwen-2.5-72B, Gemini-2.5-flash-lite (via
OpenRouter) — mirroring Sakana's ARC-AGI-2 setup (o4-mini + Gemini + DeepSeek). We use the **coding**
slice because a code-runner is the reliable verifier the method requires.

**No leakage:** each task's asserts are split into PUBLIC (search/verifier signal) and HELD-OUT
HIDDEN (final eval). The search and refine-feedback only ever see PUBLIC tests; we report HIDDEN.

## Live results (4 hard coding tasks; HIDDEN pass-fraction)

| method | hidden acc | solved | LLM calls | cost |
|---|---|---|---|---|
| **gpt-5.5 solo (reference ceiling)** | **1.000** | 4/4 | 4 | $0.0301 |
| best single cheap model (deepseek solo) | 0.950 | 3/4 | 4 | $0.0011 |
| repeated-sampling @1 | 0.887 | 2/4 | 4 | $0.0014 |
| repeated-sampling @8 | 0.950 | 3/4 | 32 | $0.0085 |
| **AB-MCTS (multi-LLM) @1** | 0.950 | 3/4 | 4 | $0.0004 |
| **AB-MCTS (multi-LLM) @8** | 0.950 | 3/4 | **4** | **$0.0004** |

## What this shows (honest)

1. **Adaptive multi-model search did NOT beat the best single model, and did NOT close the gap to
   the frontier.** AB-MCTS, repeated sampling, and best-single all plateau at **0.950**; only gpt-5.5
   reaches 1.000. The cheap pool fails the *same* hard item's *same* hidden edge cases — **correlated
   errors**, so there is nothing complementary for the search to exploit. (Sakana's ARC win came from
   *uncorrelated* complementary models; that condition isn't met here.)
2. **AB-MCTS is genuinely more sample-efficient than repeated sampling** — same 0.950 accuracy at
   **8× fewer calls and ~20× lower cost** (4 calls/$0.0004 vs 32 calls/$0.0085 at budget 8). This
   matches the paper's core claim (adaptive branching beats naive sampling per unit compute).
3. **Search is bounded by verifier quality.** AB-MCTS early-stops when a candidate passes all PUBLIC
   tests — but that candidate still fails a HIDDEN edge case the public tests don't cover, so the
   search has no signal to keep improving. This is the paper's own caveat ("assumes a reliable score
   evaluator") made concrete: *a router/searcher is only as good as its verifier.*
4. **The bandit concentrated on one arm** (qwen got all pulls; per-arm counts in `s2_results.json`).
   With correlated success on easy items and correlated failure on the hard one, model *diversity*
   bought nothing — echoing the Self-MoA finding that arm-strength beats diversity when errors correlate.

**Verdict:** orchestrating cheap models with adaptive search is *more efficient than naive sampling*
but **does not beat a single stronger model** when the gap is a real capability gap with correlated
failures and an imperfect verifier. The degree's thesis holds: **route the hard tail to a stronger
model.** (The *real* Fugu, over frontier models, is measured in S3.)

## Run it

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd source && python3 run_s2.py   # -> s2_results.json ; abmcts.py is the vendored engine
```
Small-n caveat: 4 coding tasks (gpt-5.5 saturates everything larger we could author — see S0). The
*direction* (efficiency win, no accuracy win, verifier-bounded) is robust; absolute deltas are n=4.
