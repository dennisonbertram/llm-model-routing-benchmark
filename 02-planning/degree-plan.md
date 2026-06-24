# Degree Plan

**Target**: Model Routing (cost-vs-quality model selection for LLMs, agent harnesses, and multi-model systems)
**Degree**: `01-llm-model-routing`
**Category**: `inference-optimization`
**Audience**: autonomous LLM coding agents.
**Today**: 2026-06-21.

## Goal

Produce live, test-driven, evidence-backed proof that an autonomous coding agent can pick the
**best model for a job** and extract **more quality per dollar** — across the full routing
discipline. The degree covers rule/heuristic routing, predictive routing (embedding-kNN,
trained classifiers in the RouteLLM / Hybrid-LLM family), LLM cascades with verification
(FrugalGPT, AutoMix), opencode-style harness routing (pick a model per agent step / difficulty),
ensembles where **cheap models used together may beat a single SOTA model** (Mixture-of-Agents,
self-consistency / sample-and-vote, multi-agent debate), routing as a deployed
OpenAI-compatible gateway, and benchmarking routers on a **cost-vs-quality Pareto frontier**
(RouterBench-style). Coding is the primary discipline; QA/knowledge and math/reasoning are also
covered.

Every quality and cost number in any green POC must come from a real, executed live API call
captured in this repo. Where a number is only knowable after the live run, the plan writes
"TBD — measured live in <POC>". Paper claims (RouteLLM ~85% cost cut on MT-Bench, FrugalGPT up to
98%, AutoMix >50%, MoA 65.1% AlpacaEval, Self-Consistency +17.9pp GSM8K) are carried as **cited,
research-supported, NOT reproduced here** unless and until our own live run reproduces a directional
result on our own small suite. We do not assume our suite will match the papers.

## Progression principle

Prove the simplest primitive first (providers reachable + baselines), then layer routing
intelligence in order of sophistication, then ensembles, then aggregate everything on one
Pareto frontier, then ship the combined adaptive gateway. Each level is a TDD POC against real
provider APIs: **red** (behavior/contract test fails) → **green** (smallest live implementation)
→ **regression** (keep + extend). No mocks at the model-API boundary. Every green POC records real
token/cost numbers and provider responses in `04-logs/live-evidence-ledger.md`; a POC with no
live evidence is not green.

## Shared substrate

A coordinator-built, **live-verified** Python harness (`harness/`, stdlib + numpy only) underpins
every POC. POC workers import it and never re-implement provider plumbing:

- `providers.chat(model, messages, ...)` → `{text, prompt_tokens, completion_tokens,
  billed_completion_tokens, latency_ms, usd, finish_reason, raw_usage, native_cost_usd}`, provider
  auto-detected from the model id (OpenAI / Anthropic / xAI / OpenRouter). `providers.embed(texts)`
  for `text-embedding-3-small`.
- `pricing.PRICES` + `usd_for(model, pt, ct)` — **uniform** cost = Σ tokens × unit price for all
  providers (apples-to-apples). Seeded list prices reconciled against
  `01-research/pricing-quotas-limits.md` (dated, sourced). xAI also returns `cost_in_usd_ticks`
  (recorded in raw evidence; **the ticks→USD factor must be verified live in L0** — harness uses
  `1e-9` but xAI docs state 10^10 ticks/USD = `1e-10`; this discrepancy is an explicit L0 task).
- `judge.py` — LLM-judge / aggregator helpers for ensemble fusion (`aggregate_moa`, `pick_best`).
  Closed-task correctness is always the deterministic grader, never the judge.
- `tasks.py` — coding / qa / math suites, each item `{id, discipline, difficulty, prompt,
  grade(answer)->bool, gold}`. Graders are deterministic (numeric match / normalized QA / unit-test
  execution in a subprocess).
- `metrics.py` — `RunResult` (accuracy, total_usd, usd_per_correct, mean_latency, pct_cheap,
  by_difficulty) + `pareto_front()` + `format_table()`.
- `router_base.py` — `Router.answer(item)`, `SingleModelRouter.choose(item)`, `FixedModel`,
  and `run_suite(router, items, cache)` (live execution + deterministic grading).
- `cache.py` — on-disk response cache keyed on (model, messages, system, temperature, max_tokens,
  nonce) so re-running the **same** deterministic pair does not re-bill or wobble accuracy; pass a
  per-sample `nonce` for temperature>0 sampling. First run of a pair is the billed event.

## Model pool tiers (from `harness/config.py`, all live-verified 2026-06-21)

| Tier | Models | Role |
|---|---|---|
| CHEAP | `gpt-4.1-nano`, `gpt-4o-mini`, `claude-haiku-4-5-20251001` | low-cost workers; routing target |
| MID | `gpt-4.1-mini`, `gpt-4o`, `claude-sonnet-4-5-20250929` | cascade middle; MoA aggregator |
| STRONG | `gpt-4.1`, `claude-opus-4-8` | strong, non-reasoning, reliable |
| FRONTIER_REASONING | `gpt-5-mini`, `gpt-5` | reasoning (help math; higher cost/latency) |
| CROSS_PROVIDER | `grok-4.3` | optional; reasons by default; reconcile cost |

Canonical "cheap vs strong" headline pair: `CHEAP_DEFAULT=gpt-4o-mini` vs `STRONG_DEFAULT=gpt-4.1`
(both OpenAI, clean per-token cost, no hidden reasoning tokens → unambiguous cost-quality gap).
`JUDGE_MODEL=gpt-4.1`. `ENSEMBLE_CHEAP=[gpt-4o-mini, gpt-4.1-mini, claude-haiku-4-5-20251001]`
(different families → less-correlated errors).

OpenRouter is **optional**: `OPENROUTER_API_KEY` is not on disk in this workspace. POCs must not
depend on it. If it appears, an OpenRouter backend unlocks open models + native per-generation
cost (`GET /generation`); this is an enhancement, never a blocker.

## Task suites (small but REAL — ≤ ~20 items each so runs are fast/cheap)

- **coding** (primary): ~12 self-contained Python problems with hidden unit tests, authored here
  (not a licensed dataset); grader runs the tests in a subprocess.
- **qa**: ~12 factual/closed questions with gold short answers; deterministic normalized match.
- **math**: ~12 arithmetic/word problems with exact numeric gold.
- **mixed-easy / mixed-hard** splits drive the routing demos: some items genuinely need a strong
  model, some a cheap one suffices. The easy/hard split is **validated empirically in L0**, not
  assumed.

## Measurement approach

Each router is evaluated by `run_suite()` over a suite, producing a `RunResult`. We report, per
router: accuracy, total_usd, usd_per_correct, mean_latency, %routed-cheap. The four canonical
baselines — **always-cheap, always-strong, random, ORACLE** (cheapest model that is actually
correct per item, computed offline after all runs; an unrealizable ceiling) — anchor the frontier.
A "good router" must (1) dominate random, (2) approach oracle, (3) be monotone under a threshold
sweep. The empirical heart is **X5**, which runs every router over the shared suite and emits the
cost-vs-quality Pareto frontier table; the **capstone** then shows where the combined adaptive
gateway sits on that frontier with real numbers. All target numbers are TBD until measured live.

## Levels (detail in `poc-progression.md`)

- **L0** — smoke + harness + baselines (always-cheap vs always-strong)
- **L1** — heuristic router (deterministic features)
- **L2** — embedding-kNN router (RouteLLM similarity flavor)
- **L2b** — classifier router (logistic regression on embeddings; threshold sweep)
- **L3a** — FrugalGPT cascade (cheap→mid→strong + verification gate)
- **L3b** — harness routing for a multi-step coding agent (opencode-style)
- **L3c** — OpenAI-compatible gateway integration (transparent client)
- **L4** — routing gateway runtime (live local HTTP server + cost ledger)
- **L5** — failure modes + observability (≥3 safe live failures + fallback)
- **X1** — Mixture-of-Agents (cheap-ensemble vs single SOTA)
- **X2** — self-consistency vote (sample-k cheap vs single strong)
- **X3** — multi-agent debate (cheap debaters vs single strong)
- **X4** — verification cascade (AutoMix-style self-verify + escalate)
- **X5** — router benchmark Pareto (all routers + oracle; the empirical heart)
- **L-capstone** — adaptive routing gateway (classifier + cascade + ensemble fallback + budget
  guard + observability, served OpenAI-compatible, benchmarked)

## Deliverables

- `03-pocs/<level>/` — `README.md` (indexed, evidence `Live verified`), `intent.md`, `evidence.md`,
  `commands.md`, `surprises.md`, `status.md`, `source/` (code + `red-output.txt` + `green-output.txt`).
- `04-logs/*` — live-evidence ledger, error log, command log, decisions, access blockers, test results.
- `05-distillation/` — gotchas, recipes, patterns, anti-patterns, decision records (evidence-labeled
  per section so the indexer classifies them as `Live verified`).
- `06-skill-pack/agent-instructions.md` + `quickstart.md` — operational entry point for future agents.
- `07-evaluation/final-report.md` — what was proven live, the honest Pareto story, what stayed blocked.

## Definition of done

Every POC green with live evidence (real provider responses + token/cost numbers + executed code
tests) recorded in the ledger; an honest cost-quality Pareto frontier where at least one router
**measurably dominates random**, with the cheap-ensemble outcome reported truthfully (win OR loss);
zero fabricated numbers; the degree indexed and searchable via `/v1/search` + MCP build-tools.
Commit is a separate step; deploy (merge to main → Railway) is gated.
