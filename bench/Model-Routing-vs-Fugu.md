# Model routing — combinations vs. Sakana Fugu

_Cost · accuracy · latency of single models, ensemble methods, and multi-agent orchestration on one identical task stack._

**Suite** `superhard` — 56 brute-force-graded hard-math (integer-answer) tasks · 17 models measured live · ~$23 total API spend · generated 2026-06-23

## The question

Does Sakana Fugu's multi-agent orchestration — or any cheap ensemble — beat a single strong model on genuinely hard problems? Every model and method below ran on the **same 56 tasks**, the same integer grader, and the same cost accounting (Fugu billed on every token, orchestration included).

## The answer

On this suite, **nothing beats a single strong model** — orchestration and voting only change the *price* of reaching the same ceiling. Both Fugu conductors solve the **exact same 46 tasks** as one GPT-5.5 call (0.821), at 3.2× (mini) and 7.2× (ultra) the cost and up to ~76s/task. A cheap majority vote ties that accuracy at **45× cheaper than Fugu-Ultra**, and a single cheap model (gpt-5-nano) lands one task back at 18.2× cheaper.

**Headline numbers**

- **0.821** — GPT-5.5 = Fugu-mini = Fugu-Ultra = the oracle ceiling, all identical (46/56).
- **7.2×** — Fugu-Ultra costs this much more than GPT-5.5 for the same 46 tasks (~76s/task).
- **18.2×** — gpt-5-nano vs GPT-5.5, 1 task back (45/56) — within noise.
- **6.2×** — cheapest majority vote that ties GPT-5.5's 0.821.

## The comparison — one stack, every method

_56 tasks · Fugu vs single models vs combination methods · sorted by accuracy, then cost._

| Method | Configuration | Accuracy | n | $/task | vs GPT-5.5 | Latency | How it works |
|---|---|---|---|---|---|---|---|
| Oracle ceiling | `best-of-pool per task` | **0.821** | 46/56 | — | — | — | unrealizable ceiling of the whole pool |
| Majority vote | `qwen3-235b-a22b-2507+glm-4.7-flash+gpt-5-nano` | **0.821** | 46/56 | $0.0051 | 6.2× cheaper | 122s | majority vote on the integer answer |
| Consensus cascade | `deepseek-v4-flash+gpt-5-nano → gpt-5.5` | **0.821** | 46/56 | $0.0194 | 1.6× cheaper | 61s | cheap members agree → trust; disagree → escalate |
| Single model | `gpt-5.5` | **0.821** | 46/56 | $0.0319 | 1.0× | 16s | frontier reference — the bar to beat |
| Orchestration (Fugu) | `fugu (mini)` | **0.821** | 46/56 | $0.1014 | 3.2× pricier | 26s | Sakana multi-agent conductor (mini) |
| Orchestration (Fugu) | `fugu-ultra` | **0.821** | 46/56 | $0.2306 | 7.2× pricier | 76s | Sakana multi-agent conductor (largest) |
| Single model | `gpt-5-nano` | **0.804** | 45/56 | $0.0018 | 18.2× cheaper | 31s | cheap single model |
| Single model | `deepseek-v4-pro` | **0.804** | 45/56 | $0.0025 | 12.8× cheaper | 42s | mid single model |
| Single model | `deepseek-v4-flash` | **0.732** | 41/56 | $0.00049 | 64.6× cheaper | 46s | cheap single model |

## Cost vs. accuracy — realizable Pareto frontier

_The non-dominated set: no other config is both more accurate and cheaper._

| Accuracy | n | $/task | × cheaper than GPT-5.5 | strategy | members |
|---|---|---|---|---|---|
| 0.107 | 6/56 | $0.00002 | 1703.5× | solo | `gemini-3.1-flash-lite` |
| 0.732 | 41/56 | $0.00049 | 64.6× | solo | `deepseek-v4-flash` |
| 0.804 | 45/56 | $0.0018 | 18.2× | solo | `gpt-5-nano` |
| 0.821 | 46/56 | $0.0051 | 6.2× | vote-3 | `qwen3-235b-a22b-2507+glm-4.7-flash+gpt-5-nano` |

_Oracle ceiling (best-of-pool per task) = 0.821 = GPT-5.5 solo — so no realizable config rises above the single strong model._

## What this means for routing

- **Orchestration added zero accuracy here.** Fugu-mini and Fugu-Ultra each solve the *identical 46 tasks* as one GPT-5.5 call — not one more — at 3.2× and 7.2× the cost and up to ~76s/task.
- **Ensembling matches the frontier cheaper, never beats it (on this suite).** The pool oracle equals GPT-5.5; no cheaper model or either Fugu solves a task GPT-5.5 misses. Voting/cascading only reach 0.821 for less money.
- **A shared blind spot caps everyone.** 10 of 56 tasks (a nonlinear modular-recurrence family, `sh016–sh025`) are unsolved by all 17 models including both conductors — no ensemble can vote a correct answer into existence.
- **The cheap lever is real, the accuracy gap is not.** gpt-5-nano is 1 task behind GPT-5.5 (45 vs 46 of 56) — one task, within noise — at 18.2× cheaper. Treat the strong single models as accuracy-tied; route on cost and latency.

## Method & limitations

> Independently method-audited by OpenAI Codex (GPT-5, read-only) with no view of the author's reasoning; its findings were folded in (token-fairness fix, operational-vs-capability separation, the caveats below).

- **Exact-answer math only.** All tasks are integer-answer number-theory/combinatorics. These conclusions describe that regime; they need not hold for coding, open-ended reasoning, or agentic work — the domain multi-agent orchestration is actually pitched for. This is a fair test of orchestration on hard *exact* problems, not of orchestration in general.
- **Small n, single run.** Each (model, task) measured once at temperature 0; n=56. One task = 1.8 points, so accuracy differences within ~1–2 tasks (e.g. 0.821 vs gpt-5-nano 0.804) are **within noise** — read same-accuracy models as tied. No confidence intervals or repeated seeds.
- **Token fairness (fixed).** Every model gets the same 16k-token budget; an earlier 6k cap truncated some models and understated them (GLM-4.7-flash lost 31 answers) — those cells were re-measured.
- **Operational ≠ capability.** Timeouts, rate-limits, and transient errors were re-measured rather than counted wrong. Fugu was measured on a pay-as-you-go key after its weekly subscription quota was exhausted mid-run; all 56 Fugu cells here are clean answers.
- **Reproducibility gap.** The grader is "last integer in the response"; raw response text was not retained, so post-hoc extraction audits aren't possible (future runs will save raw text + finish_reason).

## Appendix — all single models (56 tasks)

| Model | Tier | Accuracy | n | $/task | vs GPT-5.5 | Latency |
|---|---|---|---|---|---|---|
| `kimi-k2.5` | mid | **0.821** | 46/56 | $0.0167 | 1.9× cheaper | 196s |
| `gpt-5.5` | frontier | **0.821** | 46/56 | $0.0319 | 1.0× | 16s |
| `fugu` | orchestrator | **0.821** | 46/56 | $0.1014 | 3.2× pricier | 26s |
| `fugu-ultra` | orchestrator | **0.821** | 46/56 | $0.2306 | 7.2× pricier | 76s |
| `gpt-5-nano` | cheap | **0.804** | 45/56 | $0.0018 | 18.2× cheaper | 31s |
| `deepseek-v4-pro` | mid | **0.804** | 45/56 | $0.0025 | 12.8× cheaper | 42s |
| `minimax-m2.5` | cheap | **0.768** | 43/56 | $0.0054 | 5.9× cheaper | 113s |
| `glm-4.7-flash` | cheap | **0.750** | 42/56 | $0.0025 | 12.6× cheaper | 88s |
| `glm-5.2` | mid | **0.750** | 42/56 | $0.0129 | 2.5× cheaper | 74s |
| `deepseek-v4-flash` | cheap | **0.732** | 41/56 | $0.00049 | 64.6× cheaper | 46s |
| `qwen3-235b-a22b-thinking-2507` | cheap-reasoner | **0.679** | 38/56 | $0.0014 | 22.6× cheaper | 196s |
| `qwen3-235b-a22b-2507` | cheap | **0.571** | 32/56 | $0.00087 | 36.8× cheaper | 61s |
| `llama-4-maverick` | cheap | **0.339** | 19/56 | $0.00088 | 36.1× cheaper | 21s |
| `gemini-3.1-flash-lite` | cheap | **0.107** | 6/56 | $0.00002 | 1703.5× cheaper | 0.7s |
| `gpt-4.1` | strong | **0.071** | 4/56 | $0.00013 | 248.8× cheaper | 0.7s |
| `nova-lite-v1` | ultra-cheap | **0.054** | 3/56 | $0.00024 | 131.8× cheaper | 3.6s |
| `gpt-4o-mini` | cheap | **0.036** | 2/56 | $0.00009 | 367.1× cheaper | 2.6s |

---
_Reproducible: `registry.json` → `run.py --suite superhard` → `measure_fugu.py` (Fugu) → `report.py` (this document + the PDF). The outcome matrix is cached, so adding a model fills only its column and re-scores every combination for free._
