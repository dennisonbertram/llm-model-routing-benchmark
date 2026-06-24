# Methodology

This document describes the experimental design in enough detail to reproduce or falsify the result. The short version: **measure each `(model, task)` pair once, live; evaluate every routing/ensemble strategy offline over those measurements.**

## 1. The task suite

All headline numbers come from the `superhard` suite — **56 tasks**, generated deterministically by [`03-pocs/S5-superhard-frontier/source/superhard.py`](03-pocs/S5-superhard-frontier/source/superhard.py) via `gen(seed=7)`. Properties chosen on purpose:

- **Integer answers.** Every task has a single correct integer. This is what makes *majority vote* well-defined (you can't majority-vote two essays or two code snippets) and lets grading be exact.
- **Brute-force gold.** Each task's correct answer is computed by direct enumeration/simulation in Python, not by an LLM judge — so "correct" is provably correct, with no judge noise contaminating the comparison.
- **Hard enough to break the frontier.** The suite was selected so a frontier model (GPT-5.5) drops below 1.0 — otherwise there is no headroom to tell routing strategies apart. GPT-5.5 lands at 46/56.
- **Sub-variety within one regime.** Inclusion–exclusion counts, nonlinear modular recurrences, subset-sum-mod, constrained permutations, lattice-path counts, Burnside/necklace counting, and combinatorial games (Sprague–Grundy). All are number-theory/combinatorics with integer answers. This is **one regime** — see the construct-validity caveat in the README.

The `sh016`–`sh025` block is a nonlinear modular-recurrence family that turns out to be a **shared blind spot**: no model in the pool solves any of them, which is why the oracle ceiling caps at 46/56.

## 2. The model pool

17 models, declared in [`bench/registry.json`](bench/registry.json) with their per-1M input/output prices. `gpt-5.5` is the **reference** (the accuracy bar and the cascade escalation target). The pool spans:

- OpenAI direct: `gpt-5.5`, `gpt-5-nano`, `gpt-4.1`, `gpt-4o-mini`.
- OpenRouter open/diverse: `deepseek-v4-pro/flash`, `qwen3-235b-a22b-thinking-2507`, `qwen3-235b-a22b-2507`, `glm-5.2`, `glm-4.7-flash`, `kimi-k2.5`, `minimax-m2.5`, `llama-4-maverick`, `gemini-3.1-flash-lite`, `nova-lite-v1`.
- Sakana orchestration: `fugu` (mini), `fugu-ultra` (largest conductor).

## 3. Measurement — the outcome matrix

[`bench/matrix.py`](bench/matrix.py) calls each model on each task **once**, at `temperature=0`, and records `{ans, ok, usd, lat}`. Design choices that matter for validity:

- **Answer extraction:** `ans` = the last integer in the response. `ok` is `grade(text)`, which for this suite is exactly `last_int(text) == gold` — so the correctness flag and the extracted answer always agree (verified: 0 disagreements across all cells). The raw text is *not* retained (a known limitation).
- **Token budget:** every model gets a uniform **16,000-token** budget. (An earlier version gave only substring-matched "reasoners" 16k and everyone else 6k; that truncated non-reasoners and understated them — GLM-4.7-flash lost 31 answers to the 6k cap. Fixed and re-measured.)
- **Operational vs. capability failure:** timeouts, rate-limits, and transient parse errors are **re-measured**, not silently counted as wrong. A genuine no-integer answer (after a fair retry at the full budget) counts as wrong.
- **Resumable + budget-capped:** re-running skips already-measured cells; a USD cap stops new measurement. This is what makes adding a model cheap.

## 4. Cost accounting

[`harness/pricing.py`](harness/pricing.py) holds a per-1M price table; [`harness/providers.py`](harness/providers.py) computes `usd` per call uniformly from that table (input tokens × input rate + output tokens × output rate). Notes:

- **Uniform source.** Every model's cost comes from the same local table, so the cost axis is comparable across providers (rather than mixing each provider's inline billing).
- **Fugu orchestration billing.** Sakana Fugu's multi-agent conductor consumes large internal/orchestration token counts. The usage payload exposes them, and they are billed *in full* at Fugu's $5/$30-per-1M rate — i.e. `total = visible + orchestration`. This is why Fugu costs 3–7× a single GPT-5.5 call despite the same accuracy.

## 5. Strategy evaluation (offline)

[`bench/combos.py`](bench/combos.py) evaluates strategies over the matrix with **no API calls**:

- `solo(model)` — one model's accuracy and cost.
- `vote(members)` — majority vote on the integer answer; ties break to the first member.
- `consensus_escalate(members, ref)` — if all members agree, use that answer (cost = members); else escalate to the reference (cost = members + ref). Cheap when members usually agree.
- `oracle(members)` — any member correct → correct; pay all. The unrealizable upper bound.
- `pareto(rows)` — the non-dominated set (no other config is both more accurate and cheaper).

[`bench/run.py`](bench/run.py) measures + evaluates all k≤4 combinations and writes `leaderboard_<suite>.md` + `results_<suite>.json`. [`bench/report.py`](bench/report.py) renders the human report (`Model-Routing-vs-Fugu.{md,pdf}`) from the same computed data — one source of truth, no number drift.

## 6. Fugu access note

Sakana Fugu has two billing modes: a weekly-capped **subscription** and **pay-as-you-go (consumption)** billing. Fugu was measured on a pay-as-you-go key after the subscription's weekly quota was exhausted mid-run; all 56 Fugu cells in the published matrix are clean answers (no rate-limit contamination). The gentle measurement path (retries, low concurrency, long timeout) is [`bench/measure_fugu.py`](bench/measure_fugu.py); the rate-limit repair pass is [`bench/repair_fugu.py`](bench/repair_fugu.py).

## 7. What would change the conclusion

This is a falsifiable result. It would be overturned by, for example:

- A model (or ensemble) that solves a task `gpt-5.5` misses → the oracle rises above 46/56. (None in this pool does; check via the snippet in the README.)
- A different task regime — especially **coding or open-ended/agentic tasks graded by execution or a verifier** — where orchestration's error-decorrelation can actually exceed a single model. The framework supports new suites: add them in [`bench/suites.py`](bench/suites.py).
- Larger n / multiple seeds collapsing or widening the within-noise gaps (e.g. GPT-5.5 vs gpt-5-nano's one-task difference).
