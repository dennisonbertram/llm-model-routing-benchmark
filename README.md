# LLM Model-Routing Benchmark — combinations vs. Sakana Fugu

**Does multi-agent orchestration — or any cheap ensemble — beat a single strong model on genuinely hard problems?**

This repository is the full, reproducible record of a live experiment that answers that question on one task regime, with the **raw measurements included** so you can check every number yourself. It was extracted from an internal "Agent University" degree and is self-contained.

> **Headline result (live-measured, independently audited):** on a suite of 56 hard, exact-answer math/combinatorics problems, **orchestration and ensembling never beat the best single model.** GPT-5.5, Sakana **Fugu-mini**, and Sakana **Fugu-Ultra** each solve the **identical 46 / 56** tasks — same set, cell for cell — at **1×, 3.2×, and 7.2× the cost** respectively. The win is entirely about price: a single cheap model (`gpt-5-nano`) lands one task back at **18× cheaper**, and a cheap majority vote ties the frontier at **6× cheaper**. No combination exceeds the single strong model, because the pool's *oracle ceiling equals GPT-5.5*.

This is a result about **hard exact-answer math**, not a universal claim. See [Limitations](#limitations) — coding and open-ended/agentic tasks (where orchestration is actually pitched) are explicitly **not** tested here.

> 📝 **The essay:** [**The Committee and the Expert**](the-committee-and-the-expert.md) — the argument behind these numbers: why a coordinated crowd of cheaper models can't out-think one expert on a single hard problem, why their *disagreement* is the real signal, and where multi-model coordination might actually win (hint: not prompts — projects).

---

## The result

All 17 models ran on the **same 56 tasks**, with the **same integer grader** and the **same cost accounting** (Fugu billed on every token, orchestration included). Full report: **[`bench/Model-Routing-vs-Fugu.md`](bench/Model-Routing-vs-Fugu.md)** (and a typeset PDF alongside it).

| Method | Configuration | Accuracy | $/task | vs GPT-5.5 | Latency |
|---|---|---|---|---|---|
| Oracle ceiling | best-of-pool per task | 0.821 (46/56) | — | — | — |
| Majority vote | qwen3-2507 + glm-4.7-flash + gpt-5-nano | 0.821 (46/56) | $0.0051 | 6.2× cheaper | 122s |
| Consensus cascade | deepseek-v4-flash + gpt-5-nano → gpt-5.5 | 0.821 (46/56) | $0.0194 | 1.6× cheaper | 61s |
| **GPT-5.5** (single) | — | **0.821** (46/56) | $0.0319 | 1× | 16s |
| **Fugu-mini** (orchestration) | — | **0.821** (46/56) | $0.1014 | **3.2× pricier** | 26s |
| **Fugu-Ultra** (orchestration) | — | **0.821** (46/56) | $0.2306 | **7.2× pricier** | 76s |
| gpt-5-nano (single) | — | 0.804 (45/56) | $0.0018 | 18× cheaper | 31s |
| deepseek-v4-pro (single) | — | 0.804 (45/56) | $0.0025 | 13× cheaper | 42s |
| deepseek-v4-flash (single) | — | 0.732 (41/56) | $0.0005 | 65× cheaper | 46s |

Three independent facts make the case airtight:

1. **`gpt-5.5`, `fugu`, `fugu-ultra`, and `kimi-k2.5` all solve the exact same 46 tasks** — verifiable from the raw matrix.
2. **No model in the pool solves a single task GPT-5.5 misses** → the oracle ceiling = GPT-5.5 = 46/56.
3. **10 tasks (`sh016`–`sh025`, a nonlinear modular-recurrence family) are unsolved by all 17 models** including both conductors — no ensemble can vote a correct answer into existence.

---

## How to check the work (peer review)

Everything needed to reproduce or falsify the result is here. You do **not** need API keys to re-derive the numbers — only to re-run the live measurements.

**The raw data is the artifact.** [`bench/matrix_superhard.json`](bench/matrix_superhard.json) holds every `(model, task)` measurement:

```json
"gpt-5.5": { "sh002": { "ans": 22101, "ok": 1, "usd": 0.0159, "lat": 9704 }, ... }
```

`ans` = the model's extracted integer answer · `ok` = correct (1/0) · `usd` = measured cost · `lat` = latency (ms).

**Re-derive any headline number in a few lines** — the combination logic is pure functions over that matrix ([`bench/combos.py`](bench/combos.py)):

```python
import json, sys; sys.path.insert(0, "bench"); sys.path.insert(0, "harness")
import suites, combos
tasks = suites.load("superhard"); gold = {t["id"]: t["gold"] for t in tasks}
m = json.load(open("bench/matrix_superhard.json"))
for x in ["gpt-5.5", "fugu", "fugu-ultra"]:
    acc, cost = combos.solo(m, x, tasks, gold)
    print(x, round(acc * 56), "/56", round(cost, 4))
# verify the identical-set claim:
cs = lambda x: {t["id"] for t in tasks if m[x][t["id"]]["ans"] == gold[t["id"]]}
print("fugu-ultra solves a task gpt-5.5 misses?", bool(cs("fugu-ultra") - cs("gpt-5.5")))
```

**The tasks and their gold answers are generated deterministically** and graded by brute force — not by an LLM judge — in [`03-pocs/S5-superhard-frontier/source/superhard.py`](03-pocs/S5-superhard-frontier/source/superhard.py) (`gen(seed=7)`). Regenerate them and check the golds yourself.

**The cost/latency accounting** lives in [`harness/providers.py`](harness/providers.py) + [`harness/pricing.py`](harness/pricing.py) (uniform price-table accounting; Fugu's orchestration tokens billed at $5/$30 per 1M).

---

## Reproduce the live measurements

```bash
# Python 3.9+, standard library only for the core benchmark (numpy only for some embedding POCs)
export OPENAI_API_KEY=...        # OpenAI direct models (gpt-5.5, gpt-5-nano, gpt-4.1, gpt-4o-mini)
export OPENROUTER_API_KEY=...    # the open/diverse pool (deepseek, qwen, glm, kimi, minimax, llama, gemini, nova)
export SAKANA_API_KEY=...        # Sakana Fugu (fugu, fugu-ultra) — needs a pay-as-you-go key

cd bench
python3 run.py --suite superhard           # measure each (model,task) once → matrix; evaluate all combos
python3 measure_fugu.py                     # measure Fugu gently (retries, low concurrency)
python3 report.py                           # regenerate Model-Routing-vs-Fugu.{md,pdf}
```

The outcome matrix is **cached and resumable**: adding a model to [`bench/registry.json`](bench/registry.json) and re-running fills only that model's column and re-scores every combination for free. Total live spend for the published run was **~$23**.

See [`bench/README.md`](bench/README.md) for framework details and [`METHODOLOGY.md`](METHODOLOGY.md) for the full experimental design.

---

## What's measured, and why combinations are "free"

The core idea is an **outcome matrix**: measure each `(model, task)` pair **once**, live, and persist `{answer, correct, cost, latency}`. That single expensive step is in [`bench/matrix.py`](bench/matrix.py). Every routing/ensemble strategy is then evaluated **offline** over the matrix with no further API calls ([`bench/combos.py`](bench/combos.py)):

- **solo** — one model.
- **majority vote** — the integer answer most members agree on.
- **consensus cascade** — cheap members answer; if they agree, trust it; if not, escalate to the reference model (FrugalGPT/AutoMix-style).
- **oracle** — a member is right → counted right. The unrealizable ceiling of the pool.

Because evaluation is offline, the published run scored **3,000+ combinations** from one set of measurements.

---

## Repository map

| Path | What it is |
|---|---|
| [`the-committee-and-the-expert.md`](the-committee-and-the-expert.md) | The essay — the argument and the reframe (prompts vs. projects) |
| [`METHODOLOGY.md`](METHODOLOGY.md) | Experimental design, grading, cost model, combination strategies, corrections |
| [`bench/`](bench/) | The benchmark framework + the published report (`Model-Routing-vs-Fugu.{md,pdf}`) and raw data (`matrix_superhard.json`, `leaderboard_superhard.md`, `results_superhard.json`) |
| [`harness/`](harness/) | Multi-provider chat substrate: `providers.py`, `pricing.py`, `judge.py`, `metrics.py`, `router_base.py` |
| [`03-pocs/`](03-pocs/) | The experiments, each with red→green live evidence: routers (`L1`–`L2b`), cascades (`L3a`–`L3c`), gateway (`L4`), failure modes (`L5`), ensembles (`X1`–`X4`), Pareto benchmark (`X5`), frontier tier (`X6`), Fugu track (`S0`–`S5`) |
| [`01-research/`](01-research/) | Background research: capability map, cost model, failure modes, security model |
| [`02-planning/`](02-planning/) | Experimental plan, success criteria, no-mock enforcement |
| [`05-distillation/`](05-distillation/) | Distilled findings: gotchas, patterns, anti-patterns, decision records, recipes |
| [`06-skill-pack/`](06-skill-pack/) | Tutorial-style lessons, labs, and reference for building routers |
| [`07-evaluation/`](07-evaluation/) | Final report, known limitations, quality-gate verdicts, future work |
| [`04-logs/`](04-logs/) | Raw command/decision/error/evidence ledgers from the live runs |

---

## Limitations

Stated plainly, because the point is for you to weigh them:

- **Exact-answer math only.** All 56 tasks are integer-answer number theory / combinatorics. These conclusions describe that regime; they need **not** hold for coding, open-ended reasoning, or agentic work — the domain multi-agent orchestration is actually pitched for. This is a fair test of orchestration on hard *exact* problems, not of orchestration in general.
- **Small n, single run.** Each `(model, task)` was measured **once** at temperature 0; n = 56. One task = 1.8 points, so accuracy differences within ~1–2 tasks (e.g. GPT-5.5 0.821 vs gpt-5-nano 0.804) are **within noise** — read same-accuracy models as tied. No confidence intervals or repeated seeds.
- **Reproducibility gap.** The grader is "last integer in the response"; the raw response *text* was not retained, only the extracted integer, the correctness flag, cost, and latency. Post-hoc extraction audits aren't possible from the matrix alone (a future run should save raw text + `finish_reason`).
- **Latency is high-variance** and provider-dependent (slow "thinking" models stream for minutes) — treat it as directional, not an SLA.

### Independent audit

The methodology was independently reviewed, read-only, by **OpenAI Codex (GPT-5)** with no view of the author's reasoning. Its findings were folded in before publishing: it caught a missing-price bug that miscounted one model as wrong, a token-budget asymmetry that truncated some models (an earlier 6k cap cost GLM-4.7-flash 31 answers — now a uniform 16k budget, re-measured), and the conflation of operational failures (timeouts/rate-limits) with capability failures (re-measured). The within-noise framing and the limitations above are partly its doing.

---

## License

[MIT](LICENSE). Code and data are provided as-is, for research and verification.
