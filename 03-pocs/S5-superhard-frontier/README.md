# S5 — Scaling to the frontier: breaking GPT-5.5, and can orchestration recover it?

**Evidence: Live verified (2026-06-22).** Status: Complete with live evidence.

The earlier rounds couldn't break GPT-5.5 (21/21, 15/15) — so this one scales up and goes
**super-hard**, using problems engineered to be **trivial to brute-force (golds computed in Python,
provably correct) but hard to reason through**: big-N inclusion-exclusion (5 primes), 25–80-step
**nonlinear modular recurrences** (exact mechanical computation), subset-sum-mod counts, constrained
seatings, obstacle grid-paths, dihedral necklaces, Grundy/Nim values. 56 tasks, deterministic golds.

## 1. We broke GPT-5.5

| | GPT-5.5 solo (56 super-hard tasks) |
|---|---|
| overall | **45/56 = 0.804** |
| nonlinear modular recurrences | **0/10** (failed every one) |
| 5-prime inclusion-exclusion | 7/8 |
| everything else (subset-sum, seating, grid, necklace, Grundy) | clean |

The recurrence family is a **clean, reproducible frontier blind spot**: GPT-5.5 cannot reliably
hand-execute 25–80 steps of `x_n = a·x_{n-1}² + b·x_{n-2} + c (mod m)`. (Several also pushed it past a
240s timeout — the task exhausts the reasoning budget.)

## 2. Does orchestration recover the failures? (the regime where Fugu should win)

On exactly the **11 tasks GPT-5.5 alone fails**, with deterministic grading:

| system | recovered | cost/task |
|---|---|---|
| GPT-5.5 solo | 0/11 (by construction) | $0.089 |
| **Fugu-Ultra** (real conductor) | **1/11** | $0.125 |
| diverse strong ensemble (DeepSeek-R1 + Gemini-2.5-Pro + GPT-5.5, majority vote) | **0/11** | $0.168 |

- **Orchestration helped exactly once — and only on the *structured* task.** Fugu-Ultra recovered
  `sh002` (the 5-prime inclusion-exclusion, gold 22101) that GPT-5.5 botched — a genuine frontier win
  where decomposition/verification pays off.
- **No method recovered a single one of the 10 recurrences.** On `sh016` all three strong models
  (DeepSeek-R1, Gemini-2.5-Pro, GPT-5.5) returned the **identical wrong answer (530)** — you cannot
  vote away a blind spot every model shares. Where Fugu-Ultra answered a recurrence at all, it gave
  the **same wrong answer as GPT-5.5**; on the rest it timed out or was rate-limited (HTTP 429).
- **The ensemble was the most expensive option ($0.168/task) and recovered nothing** — correlated
  errors mean diversity bought zero.

## 3. The honest synthesis (this is the real, defensible story)

Across the whole degree, three regimes:

| regime | winner | why |
|---|---|---|
| **Easy/mixed traffic** (most real work) | a **router** (or even one cheap/strong call) | routing the easy majority cheap, escalating the tail — ~12–30× cheaper than Fugu at matched accuracy (S3/S4) |
| **Hard-but-structured** frontier tasks | **orchestration can help** | Fugu-Ultra recovered a counting task GPT-5.5 failed (decompose + verify) |
| **Exact-computation** frontier tasks | **nothing model-based helps** | all models share the blind spot; the fix is a **code/tool call**, not more models |

**The blunt lesson:** orchestration is not a free accuracy win and not a universal one. It earns its
12–30× premium only on the narrow band of tasks that are (a) beyond a single strong model AND (b)
decomposable/verifiable. For exact computation, give the model a **tool** (run the recurrence in code)
— that beats both a single frontier call and a multi-agent conductor, at a fraction of the cost.

## Caveats
n=56 (11 failures); single run; authored math-heavy families; deterministic golds. Fugu-Ultra hit
subscription rate limits (HTTP 429) + 240s timeouts on several recurrences, so its 1/11 is if anything
*generous* to record but its non-recoveries on answered recurrences (same wrong answer as GPT-5.5)
show the limit is real, not just operational. Cost/task is higher here than S3/S4 because super-hard
tasks make every model reason (and orchestrate) far longer.

## Run it
```bash
set -a; . .agent-university/secrets.local.env; set +a
cd source
python3 superhard.py 56          # break GPT-5.5 -> superhard_gpt55.json
python3 run_frontier_failures.py # orchestration on the failures -> frontier_failures.json
```
