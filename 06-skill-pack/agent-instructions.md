# Agent Instructions — LLM Model Routing

Live verified. Operating brief for a coding agent building a model router. Every claim
is grounded in live-verified or explicitly labeled research-supported evidence from 15
POCs run 2026-06-21/22. When evidence is research-supported only, that is stated.

Back to [index](index.md).

---

## Read these first

Before writing any code:

1. **[reference/model-pool.md](reference/model-pool.md)** — which models are verified live,
   their pricing, and provider-specific wire-format differences.
2. **[reference/harness-api.md](reference/harness-api.md)** — the shared harness API.
   Import `chat`, `embed`, `run_suite` from `harness/`. Do NOT reimplement providers.
3. **[reference/pareto-numbers.md](reference/pareto-numbers.md)** — the definitive live-measured
   Pareto table. Every accuracy and cost claim you make must trace back here or to a committed
   POC evidence file.
4. **[troubleshooting/empty-response-reasoning-model.md](troubleshooting/empty-response-reasoning-model.md)** — read before calling any gpt-5 / o-series model.

---

## The first router to build: logistic classifier

Live verified (L2b; X5). This is the correct starting point — not a heuristic, not an ensemble.

**Why:** The logistic classifier at thr=0.9 on the full suite (X5) achieved acc=0.978,
$0.00291 — matching always-strong accuracy at 7.4x lower cost. No other realizable strategy
comes close to this ratio. The heuristic router at thr=0.40 achieved only acc=0.956 at
$0.00902. MoA cost $0.10159 and was less accurate than strong.

**Build order:**
1. Measure your baseline (run both models on your suite; record per-item correctness).
2. Embed all prompts via `embed(texts, model="text-embedding-3-small")` (~$3e-05 for 45 prompts).
3. Use the labeled outcome matrix to define `y = 1` where cheap is correct, `0` otherwise.
4. Train logistic regression on embedding features (gradient descent, L2 regularization).
5. Sweep threshold from 0.7 to 0.95 to find your operating point.
6. Report the Pareto table honestly: include always-cheap, always-strong, oracle (labeled
   unrealizable), and your router.

Recipe: [recipes/R-002-logistic-classifier-router.md](recipes/R-002-logistic-classifier-router.md)

---

## The benchmark to run

Live verified (X5; L0). Before claiming any router "works", run this benchmark:

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd model-routing/degrees/01-llm-model-routing/03-pocs/X5-router-benchmark-pareto/source
python3 benchmark.py
```

Check your router against the full-suite baseline numbers in [reference/pareto-numbers.md](reference/pareto-numbers.md).
A router that doesn't beat random-50% (acc=0.909, $0.01177) is not useful.

---

## What to verify before calling it done

Live verified (L5; capstone).

- [ ] The gateway returns a valid `model` field — the actually-served model, never `"auto"`.
- [ ] The cost ledger appends one JSON line per request with ts, decision, served_model, usd, latency_ms.
- [ ] An invalid model slug triggers a 4xx and the fallback chain recovers (not a crash).
- [ ] A sub-second timeout triggers a retry with normal timeout (not a crash).
- [ ] The budget guard refuses requests after the cap is exceeded (tested with a small synthetic cap).
- [ ] No API key value appears in any log line (structural observability test).
- [ ] `p_cheap` is reported in the routing decision string so decisions are auditable.

---

## What NOT to mock

The harness spec (`.context/model-routing-spec.md`) is explicit: **No mocks/stubs as proof
of behavior. Real model APIs only.** Local helper tests can use a fixture but must be labeled
"Invalid for service evidence."

Concretely: do not mock `chat()`, `embed()`, or `run_suite()` in evidence-bearing tests.
If keys are absent, the test must fail with `ProviderError` — that is the RED state.
The GREEN state requires live API calls.

Every number you report must come from a live run or from the committed labelset cache
(reuse `Cache` to avoid re-billing — the harness cache is on-disk at `harness/.cache/`).

---

## The negatives to remember (first-class lessons, not footnotes)

Live verified (X1; X2; X3; L3a).

**1. Cheap-model ensembles did NOT beat one strong model on this suite.**
- MoA (3 cheap + aggregator): acc=0.956, $0.10159. Single strong: acc=0.978, $0.02148.
  MoA is 4.64x more expensive AND less accurate. (X1)
- Self-consistency @5 on math: 9/15 vs 14/15 single strong. Sampling a weak model more
  times does not manufacture the reasoning it lacks. (X2)
- Debate (3 models, 1 round): 0.957 == strong accuracy, but 3.84x its cost. Dominated. (X3)
- Conclusion: on a hard-reasoning-tail workload, ensembles are the wrong tool.

**2. FrugalGPT self-confidence gating fails when the cheap model is overconfident-and-wrong.**
- gpt-4o-mini returned confidence=0.9 for ALL six hard-math answers it got wrong.
- Every threshold from 0.1 to 0.9 produced identical results: acc=0.844, $0.00391.
- Fix: use an independent structural verifier (code test execution, a second model, a
  trained binary classifier) — not self-reported confidence. (L3a)

**3. Canonical coding tasks are memorized and saturate even the cheapest model.**
- gpt-4.1-nano and gpt-4o-mini both solve all 18 coding tasks at temp=0.
- The coding suite does NOT discriminate model strength; the hard gap is in multi-step
  combinatorics and algebra math. (L0; L3b)
- Implication: if your workload is predominantly coding, you may not need strong-model
  routing at all. Measure first.

**4. Oracle is an unrealizable ceiling — never report it as a router result.**
- The oracle peeks at per-item correctness (which model got it right), which is
  unknown at inference time. It is the theoretical ceiling, not a deployable strategy. (L0; X5)
- Report it separately, labeled "unrealizable ceiling," when plotting the Pareto frontier.

---

## DO list

Live verified (L4; L5; capstone).

**Confirm credentials without printing the value:**
```bash
[ -n "$OPENAI_API_KEY" ] && echo SET || echo UNSET
```

**Apply REASONING_FLOOR before calling gpt-5 / o-series:**
```python
REASONING_FLOOR = 2048
def safe_max_tokens(model: str, requested: int) -> int:
    if any(s in model for s in ("o1", "o3", "o4", "gpt-5", "grok")):
        return max(requested, REASONING_FLOOR)
    return requested
```
Source: [troubleshooting/empty-response-reasoning-model.md](troubleshooting/empty-response-reasoning-model.md),
[`../05-distillation/gotchas/G-001-reasoning-model-empty-content-small-budget.md`](../05-distillation/gotchas/G-001-reasoning-model-empty-content-small-budget.md)

**Use `max_completion_tokens` (not `max_tokens`) for gpt-5 / o-series:**
```python
if is_reasoning_model(model):
    payload["max_completion_tokens"] = safe_max_tokens(model, requested)
else:
    payload["max_tokens"] = requested
```

**Do NOT pass `temperature` to gpt-5 / o-series** — they reject it with HTTP 400.

**For grok-4.x: trust `native_cost_usd`, not tokens × price:**
Grok hides reasoning tokens from `completion_tokens` but bills them. Uniform
tokens × price undercounts. The provider field `cost_in_usd_ticks / 1e10` gives
the billed amount, but still diverges ~1.5x from token × price due to cached tokens.
Source: [troubleshooting/cost-accounting-grok.md](troubleshooting/cost-accounting-grok.md)

**Suppress numpy 2.0 matmul warnings on macOS:**
```python
import warnings; warnings.filterwarnings("ignore", ".*divide by zero.*", RuntimeWarning)
```
Use `np.dot` instead of `@` for matrix multiply on normalized float64 arrays.

**Report the Pareto table with all routers, including the negatives:**
```
always-cheap        acc=0.844  $0.00166
...
MoA                 acc=0.956  $0.10159   <- DOMINATED (expensive + less accurate)
...
logistic(thr=0.9)   acc=0.978  $0.00291   <- best realizable
oracle (UNREALIZABLE ceiling)  acc=0.978  $0.00214
always-strong       acc=0.978  $0.02148
```

---

## DON'T list

Live verified.

| Do not | Why |
|--------|-----|
| Claim an ensemble beats a strong model without measuring it | MoA, debate, and self-consistency all cost more and were less accurate here (X1, X2, X3) |
| Use self-reported confidence as the escalation gate | gpt-4o-mini returns 0.9 confidence on wrong answers (L3a) |
| Call an unrealizable oracle "a router" | Oracle peeks at per-item correctness — it's the ceiling, not a deployable strategy (L0; X5) |
| Re-call models already in the labelset cache | Use `Cache` to replay; saves money and keeps results reproducible |
| Floor cheap-model accuracy below never-routing (always-cheap) and call it a win | A cascade that costs 2.4x cheap AND has the same accuracy is a loss (L3a) |
| Assume "cheaper model = strictly worse per item" | Cheap accuracy is non-monotonic: gpt-4o-mini sometimes beats gpt-4.1-nano on individual items (L0) |
| Report only the best threshold | Always report the full threshold sweep so the operator can choose their operating point |
| Set `max_tokens` < 512 for a reasoning model | Budget starvation returns blank content with HTTP 200 (G-001) |
| Skip the cost ledger | You cannot audit budget spend or routing decisions without it |

---

## Canonical adaptive gateway pattern

Live verified (capstone). Copy and adapt from
[recipes/R-004-adaptive-gateway.md](recipes/R-004-adaptive-gateway.md) or directly from:

```
03-pocs/L-capstone-adaptive-routing-gateway/source/
  adaptive_router.py   # logistic classifier + budget guard + fallback
  gateway_server.py    # stdlib http.server OpenAI-compatible endpoint
  run_capstone.py      # CV benchmark + live smoke tests
```

The gateway at thr=0.8 on the 45-task CV: acc=0.978, $0.00257, ~71% cheap traffic,
8.4x cheaper than always-strong. Source: `03-pocs/L-capstone-adaptive-routing-gateway/evidence.md`.

---

## Evidence scope

**Live-verified in this degree (all POCs, 2026-06-21/22):**

| Capability | POC | Headline |
|-----------|-----|---------|
| 3-provider live access (OpenAI, Anthropic, xAI) | L0 | All respond; harness measures tokens + cost |
| Baseline cost-quality gap | L0 | cheap: 0.844/$0.00166; strong: 0.978/$0.02148; oracle: 0.978/$0.00214 |
| Heuristic routing | L1 | thr=0.40: acc=0.956, $0.00902 |
| Embedding kNN routing | L2 | k=7, thr=0.7: acc=0.955, 88% cost reduction |
| Logistic classifier routing | L2b | thr=0.80 test set: oracle accuracy, 6.3x cheaper |
| FrugalGPT self-confidence failure | L3a | acc=0.844 at all thresholds; gate is non-discriminative |
| Coding verifier success | L3a | 18/18 coding, 1 escalation, 0 false accepts |
| opencode escalation loop | L3b | acc=1.000, $0.00148, 0 escalations on coding |
| OpenAI-compatible gateway | L3c | base_url override; 10/10 live tests |
| HTTP gateway runtime + ledger | L4 | 3 live curls, persisted JSONL ledger |
| 5 live failure modes + recovery | L5 | 9/9 behavioral tests green |
| MoA negative finding | X1 | acc=0.956, $0.100 — 4.64x more than strong |
| Self-consistency negative finding | X2 | 9/15 math @5 vs 14/15 single strong |
| Debate negative finding | X3 | 0.957 == strong, 3.84x cost — dominated |
| AutoMix positive (with caveats) | X4 | 0.978 acc, 71.6% savings; but 2.85x oracle |
| Full Pareto benchmark | X5 | Logistic(thr=0.9) = strong acc, 7.4x cheaper |
| Adaptive gateway CV + live smoke | capstone | thr=0.8: acc=0.978, $0.00257, 8.4x cheaper |
| Frontier tier (GPT-5.5) + 3-tier router | X6 | gpt-5.5=1.000 but 5.6x cost; 3-tier router=1.000 @ 30x cheaper than always-gpt-5.5 |

**Orchestration rule (Live verified, S2/S3):** multi-agent orchestration (Mixture-of-Agents, AB-MCTS
tree search, or a hosted conductor like Sakana Fugu) is a COST/LATENCY MULTIPLIER, not a free accuracy
win. Live: real `fugu-ultra` matched gpt-5.5 accuracy at 12.2× cost + 5.6× latency (~7,700 orchestration
tokens/task); fugu-mini was less accurate at 4× cost; AB-MCTS over cheap models plateaued at best-single,
never reaching the frontier (correlated errors). Route to the right single model; reserve orchestration
for the genuine frontier (no single model solves it) WITH a reliable verifier and uncorrelated models. See G-017.

**Frontier-model rule (Live verified, X6):** if a stronger/newer model is available, ADD it as a top
tier reached only for the hard tail — do not default to it. GPT-5.5 hit 100% but cost 5.6x gpt-4.1
and ~2.75 s/call; a 3-tier router captured that 100% for 1/30th the always-frontier cost. And
measure first: gpt-5.4 did NOT beat gpt-4.1 yet cost 1.8x more (G-016). See recipe R-011.

**Research-supported but not live-verified in this degree:**
- Specific accuracy numbers from RouteLLM, FrugalGPT, RouterBench, AutoMix papers (the papers
  used different workloads, model pools, and eval sets from this degree)
- Production throughput / SLA / multi-region routing beyond a local http.server
- OpenRouter backend (key not present in this workspace)
