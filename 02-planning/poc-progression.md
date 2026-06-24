# POC Progression

**Target**: Model Routing (cost-vs-quality model selection)
**Degree**: `01-llm-model-routing`
**Build order**: L0 → L1 → L2 → L2b → L3a → L3b → L3c → L4 → L5 → X1 → X2 → X3 → X4 → X5 → L-capstone.

All POCs are red → green → regression against **real** provider APIs (OpenAI, Anthropic, xAI;
OpenRouter only if its key appears). No mocks at the model-API boundary. Each green POC records
real token counts, computed USD cost, and provider responses in `04-logs/live-evidence-ledger.md`.
A POC with no live evidence is **not green** — it is "claimed green, unverified". Every quality/cost
figure below is a **plan/intent**, not a result; values are "TBD — measured live in <POC>".

Standard live preamble for every POC (load creds, import harness):
```bash
set -a; . .agent-university/secrets.local.env; set +a
```
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
from providers import chat, embed   # plus tasks, metrics, router_base, cache as needed
```

---

## L0 — Smoke + harness + baselines

**Concept introduced**: All three providers reachable live; the shared harness works end-to-end;
the two anchor baselines — **always-cheap** (`FixedModel("gpt-4o-mini")`) and **always-strong**
(`FixedModel("gpt-4.1")`) — run over the coding/qa/math suites and produce a real cost-quality
table. Validates the easy/hard split empirically (cheap wins easy, loses some hard).
**Prior concepts reused**: none (baseline).
**Live service touched**: OpenAI `/chat/completions` + `/embeddings`; Anthropic `/v1/messages`;
xAI `/v1/chat/completions`.
**Credentials required**: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `XAI_API_KEY`.
**Real resources**: one live call per provider for the smoke; `run_suite()` over all three suites
for each of the two baselines (≈ 2 × 36 live calls, cached).

**TDD intent**:
- **RED**: a test asserts (a) `chat(m, ...)` returns non-empty `text` and `prompt_tokens>0` for one
  model of each provider; (b) `usd>0` and matches `usd_for(model, pt, billed_ct)`; (c) the two
  baseline `RunResult`s have `n == len(suite)` and `accuracy` in `[0,1]`; (d) always-strong accuracy
  ≥ always-cheap accuracy on the mixed-hard split (the gap that makes routing worthwhile). Run before
  wiring → fails.
- **GREEN**: run the smoke; run both baselines over the suites via `run_suite`; emit
  `metrics.format_table([cheap.row(), strong.row()])`; record real numbers.
- **REGRESSION**: assert the **xAI ticks→USD conversion** live — capture `cost_in_usd_ticks` for one
  grok-4.3 call and compare `ticks × factor` to the uniform `usd_for` estimate; record whether the
  harness factor (`1e-9`) or the xAI-docs factor (`1e-10`, 10^10 ticks/USD) is correct, and reconcile.

**Expected evidence**: one live response per provider (text + token counts); per-model `usd`;
baseline cost-quality table (always-cheap vs always-strong: accuracy, total_usd, usd_per_correct,
mean_latency) — values TBD, measured live in L0; the ticks-conversion finding.
**Blocked if**: any of the three provider keys missing/invalid. (xAI optional for the core baseline
table; if xAI is down, the OpenAI+Anthropic baselines still stand and the ticks check is deferred to
a `surprises.md` note.)

---

## L1 — Heuristic router

**Concept introduced**: A deterministic `SingleModelRouter` subclass whose `choose(item)` uses
hand-written features (prompt length, code/math keyword presence, difficulty cues) to send each item
to cheap-vs-strong. No model call to decide; pure rule logic. Lands **between** the two baselines on
the Pareto plot.
**Prior concepts reused**: harness `chat`/`run_suite`/`metrics`; baselines from L0 as anchors.
**Live service touched**: OpenAI `/chat/completions` (the routed answer calls).
**Credentials required**: `OPENAI_API_KEY` (Anthropic/xAI only if the rule routes to them).
**Real resources**: `run_suite(heuristic, mixed_suite)` — one live answer call per item (~24).

**TDD intent**:
- **RED**: test asserts the heuristic router's `RunResult` is **not dominated** by random on the same
  suite (accuracy ≥ random AND cost ≤ always-strong) and routes a non-trivial fraction to each tier
  (`0 < pct_cheap < 1`). Run before implementing → fails (router routes everything one way).
- **GREEN**: implement the feature rules; run live; compare its `row()` to the L0 baselines and a
  random baseline; place it on the frontier.
- **REGRESSION**: assert monotonicity — tightening the "send to strong" rule (lower length/keyword
  threshold) does not *decrease* accuracy while *increasing* cost (a sane knob). Record 2–3 threshold
  points.

**Expected evidence**: per-item routing decisions + grades; heuristic `row()` vs cheap/strong/random;
`pct_cheap`; frontier placement — TBD, measured live in L1.
**Blocked if**: OpenAI key missing.

---

## L2 — Embedding-kNN router (RouteLLM similarity flavor)

**Concept introduced**: Build a labeled routing set by running **both** cheap and strong on a small
training split and grading each (real runs); embed each training prompt with
`text-embedding-3-small`; at decision time embed the query, take k nearest training neighbors, and
route to cheap if the neighbors' "cheap was good enough" vote passes a threshold. Threshold = the
cost/quality knob. (RouteLLM SW-ranking / similarity-weighted flavor — research-supported framing.)
**Prior concepts reused**: harness `embed`; labeled-run pattern; baselines/random from L0–L1.
**Live service touched**: OpenAI `/embeddings` (train + query) and `/chat/completions` (label runs +
routed answers); Anthropic/xAI if those are in the cheap/strong pair.
**Credentials required**: `OPENAI_API_KEY`.
**Real resources**: 2 live answers per training item for labels (~2 × 16) + embeddings + routed
answers on held-out (~12). All cached so re-runs are free.

**TDD intent**:
- **RED**: test asserts (a) the labeled set has both classes present (some items where cheap suffices,
  some where it does not — else routing is moot); (b) on a held-out split the kNN router's accuracy ≥
  random's at strictly lower cost than always-strong. Run before building labels → fails.
- **GREEN**: generate labels via real runs; cache embeddings; implement kNN `choose`; sweep `k` and
  threshold; pick a point that dominates random; record the frontier points.
- **REGRESSION**: assert the threshold is a real knob — three threshold values trace a monotone
  cost↑/cheap↓ curve; assert embedding cost is tiny but nonzero (`usd>0` for `text-embedding-3-small`).

**Expected evidence**: labeled routing set (item → cheap-good bool, real grades); embedding `usd`;
kNN `RunResult` vs baselines at ≥3 threshold points — TBD, measured live in L2.
**Blocked if**: OpenAI key missing (embeddings + labels both need it).

---

## L2b — Classifier router (RouteLLM / Hybrid-LLM, threshold sweep)

**Concept introduced**: Train a small **logistic-regression** classifier (numpy only, no sklearn) on
embedding features predicting P(cheap model is good enough). Sweep the decision threshold to trace a
full Pareto curve (Hybrid-LLM "predicted quality gap" framing). Train labels come from **real** runs
(reuse L2's labeled set); evaluate live on a held-out split.
**Prior concepts reused**: L2 labeled set + embeddings; baselines/random/oracle anchors.
**Live service touched**: OpenAI `/embeddings` + `/chat/completions` (held-out routed answers);
Anthropic/xAI if in the pair.
**Credentials required**: `OPENAI_API_KEY`.
**Real resources**: reuse cached labels/embeddings; live routed answers on held-out (~12) per
threshold point evaluated.

**TDD intent**:
- **RED**: test asserts (a) the numpy logistic-regression fit converges (training loss decreases over
  iterations) and its train accuracy > 0.5 (beats coin flip on the labeled set); (b) sweeping the
  threshold from 0→1 yields a **monotone** cost-vs-cheap-fraction curve; (c) at least one threshold
  point dominates random on held-out. Run before training → fails.
- **GREEN**: featurize embeddings, fit logistic regression, sweep threshold, run held-out live at each
  point, emit a Pareto-curve table.
- **REGRESSION**: hold out a fixed split and assert the curve is reproducible from the cache (same
  numbers on re-run); assert no threshold collapses to always-cheap or always-strong silently (guard
  against routing collapse — `0 < pct_cheap < 1` for interior thresholds).

**Expected evidence**: training-loss trace; threshold-sweep table (threshold → accuracy, total_usd,
pct_cheap) on held-out; dominates-random point — TBD, measured live in L2b.
**Blocked if**: OpenAI key missing.

---

## L3a — FrugalGPT cascade (cheap → mid → strong + verification gate)

**Concept introduced**: A cascade that calls the **cheap** model first, scores its answer with a
verification gate (LLM-judge confidence or self-scored confidence), and escalates to **mid** then
**strong** only when the gate is not satisfied. Measure cost reduction at matched accuracy vs
always-strong. (FrugalGPT — cited claim up to 98% cost cut is **NOT reproduced**; we report our own
small-suite result, win or loss.)
**Prior concepts reused**: harness `chat`; `judge.py` for the gate; baselines.
**Live service touched**: OpenAI `/chat/completions` (cheap/mid/strong answers + judge);
Anthropic/xAI if in the cascade.
**Credentials required**: `OPENAI_API_KEY` (+ judge model = `gpt-4.1`).
**Real resources**: per item, 1 cheap call + (gate) + possibly mid + strong + judge calls. Worst case
~4 calls/item over ~12 items; cached.

**TDD intent**:
- **RED**: test asserts (a) easy items terminate at the cheap tier (no escalation — `models == [cheap]`)
  and hard items escalate (`strong in models`); (b) cascade accuracy ≥ always-cheap accuracy and
  cascade total_usd < always-strong total_usd on the suite. Run before building the gate → fails.
- **GREEN**: implement the cascade router overriding `answer()`; tune the gate threshold so cheap
  terminates when correct; run live; compare to baselines.
- **REGRESSION**: sweep the gate threshold (2–3 points) and assert the expected trade — stricter gate
  → more escalation → higher cost, accuracy non-decreasing; record the cost-at-matched-accuracy point.

**Expected evidence**: per-item escalation trace (which tiers were called); cascade accuracy +
total_usd vs always-cheap/always-strong; cost reduction at matched accuracy (or honest "no reduction")
— TBD, measured live in L3a.
**Blocked if**: OpenAI key missing.

---

## L3b — Harness routing for a multi-step coding agent (opencode-style)

**Concept introduced**: A multi-step coding agent (plan → edit → fix loop) where **each step's
model** is chosen by step difficulty/role — cheap for plan/summarize, strong for the hard edit/fix —
mirroring opencode/oh-my-opencode per-agent model assignment. Compare **all-strong harness** vs
**routed harness** on coding tasks; the produced code is run against the hidden unit tests.
**Prior concepts reused**: harness `chat`; `tasks.code_grader` (subprocess unit-test execution);
baselines.
**Live service touched**: OpenAI `/chat/completions` (multiple steps per task); Anthropic/xAI optional.
**Credentials required**: `OPENAI_API_KEY`.
**Real resources**: per coding task, 2–4 step calls × two harness configs over ~8 coding tasks; cached.

**TDD intent**:
- **RED**: test asserts (a) the routed harness uses a cheap model on ≥1 step and a strong model on ≥1
  step per task (`pct_cheap` strictly between 0 and 1 at the step level); (b) routed-harness pass rate
  ≥ all-cheap-harness pass rate, at total_usd < all-strong-harness. Run before building the loop → fails.
- **GREEN**: implement the step loop with per-step model selection; run both configs live; grade final
  code via `code_grader`; compare pass rate + cost.
- **REGRESSION**: assert latency compounding is visible — record mean_latency for all-strong vs routed;
  document the cascade-latency-in-a-loop gotcha from the research (coding is harder to route).

**Expected evidence**: per-task step-by-step model trace; routed vs all-strong vs all-cheap pass rate +
total_usd + mean_latency on coding tasks — TBD, measured live in L3b.
**Blocked if**: OpenAI key missing; subprocess code execution unavailable.

---

## L3c — OpenAI-compatible gateway integration (transparent client)

**Concept introduced**: Wrap the router behind an **OpenAI-compatible `/chat/completions` request
shape** so an existing client (raw OpenAI SDK / a thin OpenAI-style client / LangChain-style call)
uses the router transparently — the client thinks it is calling one model; the router picks the real
backend per request. Prove a real client-shaped call routes and returns a valid completion object.
**Prior concepts reused**: L1/L2b router decisions; harness `chat`.
**Live service touched**: OpenAI `/chat/completions` (the backend the router selects); the gateway
adapter is in-process here (L4 makes it a live HTTP server).
**Credentials required**: `OPENAI_API_KEY`.
**Real resources**: a handful of client-shaped routed calls over mixed items (~6).

**TDD intent**:
- **RED**: test asserts an OpenAI-shaped request `{"model":"router-auto","messages":[...]}` returns an
  OpenAI-shaped response object with `choices[0].message.content` non-empty and `usage` token fields
  present, and that the served backend (recorded in a side-channel field) varies by input difficulty.
  Run before the adapter exists → fails.
- **GREEN**: implement the request→router→`chat`→OpenAI-shaped-response adapter; call it like an
  OpenAI client; assert shape conformance and routing.
- **REGRESSION**: assert an unknown router alias falls back to a safe default model (no crash) and the
  response still conforms to the OpenAI shape; record the served model per request.

**Expected evidence**: OpenAI-shaped response objects; per-request served backend; routing variance by
difficulty — TBD, measured live in L3c.
**Blocked if**: OpenAI key missing.

---

## L4 — Routing gateway runtime (live local HTTP server + cost ledger)

**Concept introduced**: Run the router as a **live local HTTP gateway** (Python stdlib
`http.server`); `curl` it (or `urllib` from a separate process); each request makes a real routing
decision, calls the real backend, and **persists a per-request cost ledger** row (model, tokens, usd,
decision, latency). This is the "runtime" evidence — routing observed over the wire, not just in a
unit test.
**Prior concepts reused**: L3c adapter; harness `chat`; ledger format from observability-strategy.
**Live service touched**: the local HTTP server (in-process boundary) **forwarding to** real OpenAI
`/chat/completions`; the client→server hop is local, the server→model hop is the real service boundary.
**Credentials required**: `OPENAI_API_KEY` (server-side).
**Real resources**: server process + a few `curl`/`urllib` client requests, each triggering one real
backend call (~5).

**TDD intent**:
- **RED**: test starts the server in a subprocess/thread, sends a real HTTP `POST /v1/chat/completions`
  from a separate client, and asserts (a) HTTP 200 + OpenAI-shaped body with non-empty content; (b) a
  ledger file gained a row with `usd>0`, the chosen model, and a routing decision. Run before the
  server exists → fails (connection refused).
- **GREEN**: implement the stdlib HTTP handler that routes + calls the backend + appends the ledger
  row; start it; make the live client call; assert the body and the ledger.
- **REGRESSION**: send 3 requests of differing difficulty and assert the ledger shows ≥2 distinct
  models chosen and a running cost total; assert the ledger persists across requests.

**Expected evidence**: HTTP request/response transcript; ledger rows (model, tokens, usd, decision,
latency) for ≥3 requests; distinct-model proof — TBD, measured live in L4.
**Blocked if**: OpenAI key missing; local socket binding blocked in the sandbox (fall back to a
loopback port; record any sandbox limitation in `surprises.md`).

---

## L5 — Failure modes + observability

**Concept introduced**: Trigger **≥3 safe live failures** and prove graceful handling: (1) invalid
model slug → caught error / fallback; (2) provider timeout or 429/rate-limit → backoff + fallback
chain to a working model (harness already retries 429/5xx with backoff); (3) **silent misroute**
(cheap model confidently wrong, FM-1) caught by the verifier → escalation; (4) **cost-budget guard**
trips (per-run USD cap; the harness/POC enforces a hard cap, default $0.10/run). Sanitized
routing/cost observability throughout.
**Prior concepts reused**: cascade gate (L3a) for misroute detection; ledger (L4); harness retry path.
**Live service touched**: OpenAI `/chat/completions` (real 4xx from an invalid slug; real success on
fallback); a deliberately tiny `max_tokens`/timeout to provoke a real edge.
**Credentials required**: `OPENAI_API_KEY`.
**Real resources**: a few deliberately-failing + recovering live calls (~6); one budget-trip run.

**TDD intent**:
- **RED**: test asserts (a) calling an invalid model id raises `ProviderError` with the real HTTP 4xx
  body captured (not a mock); (b) a fallback chain `[bad_model, good_model]` returns a valid answer
  from the **good** model; (c) the verifier flags a known cheap-misroute item and escalation produces
  the correct answer; (d) a run exceeding the budget cap stops before the next call and reports the cap
  trip. Run before guards exist → fails.
- **GREEN**: implement the fallback chain, the misroute→escalate path, and the pre-call budget guard;
  trigger each failure live; capture the real error bodies and recovery.
- **REGRESSION**: assert error bodies are **sanitized** in logs (no key, no full payload); assert the
  budget guard is a hard stop (no call after the cap is reached); document fallback-storm mitigation
  (backoff+jitter, cooldown) as research-supported, not load-tested here.

**Expected evidence**: real 4xx error body (sanitized); fallback-recovery transcript; misroute→escalate
trace; budget-trip log line; observability rows — TBD, measured live in L5.
**Blocked if**: OpenAI key missing. (We do not need to *cause* a real provider outage — an invalid
slug + a tight timeout + a forced bad-model-first chain give real, safe failures.)

---

## X1 — Mixture-of-Agents (cheap-ensemble vs single SOTA)

**Concept introduced**: N **cheap** models (from `ENSEMBLE_CHEAP`, different families) each propose an
answer; an aggregator (`judge.aggregate_moa`, mid model) synthesizes one final answer. Compare the
cheap ensemble's accuracy + cost vs a single **strong** model on a suite. (Mixture-of-Agents, Wang et
al. — cited 65.1% AlpacaEval is **NOT reproduced**; headline reports the REAL measured outcome,
**whether or not cheap wins**.)
**Prior concepts reused**: harness `chat`; `judge.aggregate_moa`; baselines.
**Live service touched**: OpenAI + Anthropic `/chat/completions` (3 proposers + aggregator).
**Credentials required**: `OPENAI_API_KEY` + `ANTHROPIC_API_KEY` (ensemble spans families).
**Real resources**: per item, 3 proposer calls + 1 aggregator call vs 1 strong call, over ~12 items;
cached.

**TDD intent**:
- **RED**: test asserts the MoA router returns a non-empty synthesized answer and that its
  `RunResult` is recorded alongside the single-strong baseline for the same items (both `n` equal).
  Run before the ensemble exists → fails.
- **GREEN**: implement the proposer→aggregator flow; run live; emit a table: MoA accuracy + total_usd
  vs single-strong accuracy + total_usd.
- **REGRESSION**: assert the outcome is reported **honestly** — if MoA costs more for equal-or-lower
  accuracy, that is the recorded result (no spin); add a 2-layer MoA-Lite variant only if budget allows
  and record its delta.

**Expected evidence**: per-item proposals + synthesized answer; MoA vs single-strong accuracy +
total_usd + mean_latency; honest win/loss verdict — TBD, measured live in X1.
**Blocked if**: OpenAI or Anthropic key missing (cross-family ensemble). Can degrade to an all-OpenAI
cheap ensemble and note the reduced error-decorrelation in `surprises.md`.

---

## X2 — Self-consistency vote (sample-k cheap vs single strong)

**Concept introduced**: Sample a **cheap** model k times at temperature>0 (distinct `nonce` per sample
so the cache keeps them separate), take the majority/most-consistent answer on math/reasoning, compare
cost + accuracy to a single **strong** call. (Self-Consistency, Wang et al.; "More Agents Is All You
Need", Li et al. — cited +17.9pp GSM8K is **NOT reproduced**; we report our small-suite numbers.)
**Prior concepts reused**: harness `chat` with `nonce` sampling; `tasks.numeric_grader`; baselines.
**Live service touched**: OpenAI `/chat/completions` (k cheap samples + 1 strong).
**Credentials required**: `OPENAI_API_KEY`.
**Real resources**: per math item, k (e.g. 5) cheap samples + 1 strong call, over ~12 math items; cached
per nonce.

**TDD intent**:
- **RED**: test asserts (a) k samples are drawn with distinct nonces (k cache entries, not 1) and a
  majority vote is computed; (b) the self-consistency router's accuracy ≥ single-cheap-call accuracy on
  math. Run before the voter exists → fails.
- **GREEN**: implement sample-k + majority vote over `numeric_grader`-comparable answers; run live;
  compare accuracy + total_usd to single-cheap and single-strong.
- **REGRESSION**: sweep k ∈ {1,3,5} and assert accuracy is non-decreasing and cost increases linearly;
  record the k where cheap-sampled meets/beats single-strong accuracy (if any) and at what cost.

**Expected evidence**: per-item sample set + vote; accuracy/cost vs k; comparison to single-strong —
TBD, measured live in X2.
**Blocked if**: OpenAI key missing.

---

## X3 — Multi-agent debate (cheap debaters vs single strong)

**Concept introduced**: 2–3 **cheap** models independently answer, then read each other's answers and
revise over 1–2 rounds; a judge/aggregator decides the final answer. Compare to a single **strong**
model. (Du et al., multi-agent debate — cited reasoning/factuality gains are **NOT reproduced**;
report the REAL measured outcome.)
**Prior concepts reused**: harness `chat`; `judge.pick_best`/`aggregate_moa`; baselines.
**Live service touched**: OpenAI + Anthropic `/chat/completions` (debaters × rounds + judge).
**Credentials required**: `OPENAI_API_KEY` + `ANTHROPIC_API_KEY`.
**Real resources**: per item, (debaters × rounds) calls + judge vs 1 strong, over ~10 items; this is
the most call-heavy ensemble — keep rounds ≤2 and items ≤10; cached.

**TDD intent**:
- **RED**: test asserts (a) debate produces a transcript with ≥2 rounds where at least one agent's
  round-2 answer differs from its round-1 (revision actually happened); (b) the debate router's
  `RunResult` is recorded vs single-strong for the same items. Run before debate exists → fails.
- **GREEN**: implement the round loop + final judge; run live; emit debate vs single-strong accuracy +
  total_usd + mean_latency.
- **REGRESSION**: assert cost honesty — debate is expected to be the **most expensive** ensemble; if it
  does not beat single-strong accuracy, that is recorded plainly; cap rounds/items to stay under budget.

**Expected evidence**: debate transcripts (revision visible); debate vs single-strong accuracy + cost +
latency; honest verdict — TBD, measured live in X3.
**Blocked if**: OpenAI or Anthropic key missing. Degrade to all-OpenAI debaters and note correlation.

---

## X4 — Verification cascade (AutoMix-style self-verify + escalate)

**Concept introduced**: Cheap model **generates**, then the cheap model **self-verifies** its own
answer (few-shot "is this answer correct? confidence"), and we **escalate to strong only on low
verifier confidence**; sweep the confidence threshold. (AutoMix, Madaan et al.; the POMDP
meta-verifier is **cited, NOT reproduced** — we implement the simpler confidence-threshold variant and
note the gap. Cited >50% cost cut is NOT reproduced.)
**Prior concepts reused**: cascade pattern (L3a) but with **self**-verification (no separate judge for
the gate); baselines.
**Live service touched**: OpenAI `/chat/completions` (generate + self-verify + escalate).
**Credentials required**: `OPENAI_API_KEY`.
**Real resources**: per item, 1 cheap generate + 1 cheap verify + (conditional) 1 strong, over ~12
items; cached.

**TDD intent**:
- **RED**: test asserts (a) self-verification returns a parseable confidence and low-confidence items
  escalate (`strong in models`) while high-confidence items do not; (b) at some threshold the cascade's
  total_usd < always-strong with accuracy ≥ always-cheap. Run before the verifier exists → fails.
- **GREEN**: implement generate→self-verify→conditional-escalate; sweep the confidence threshold; run
  live; emit the threshold-sweep table.
- **REGRESSION**: document self-verification **miscalibration** (cheap models over-trust their own wrong
  answers — the exact failure AutoMix's POMDP corrects); show ≥1 item where self-verify said "confident"
  but was wrong; note this as the reason the cited POMDP exists. Honest about whether escalation actually
  saved cost.

**Expected evidence**: per-item generate/verify/escalate trace + confidence; threshold-sweep cost-quality
table; ≥1 documented miscalibration case — TBD, measured live in X4.
**Blocked if**: OpenAI key missing.

---

## X5 — Router benchmark Pareto (all routers + oracle; the empirical heart)

**Concept introduced**: A RouterBench-style aggregate run: execute **every** router over the **shared**
suite and emit one cost-vs-quality **Pareto frontier** table + markdown report. Routers: always-cheap,
always-strong, **random**, **ORACLE (upper bound)**, heuristic (L1), kNN (L2), classifier (L2b),
cascade (L3a), MoA (X1), self-consistency (X2), and (budget permitting) debate (X3) / AutoMix (X4). The
**oracle** = cheapest model that is actually correct per item, computed **offline after all runs
complete** (unrealizable in production — reported as a ceiling only). This is the empirical heart of the
degree and is **coordinator-run** (serial, one shared cache).
**Prior concepts reused**: every prior router; `metrics.pareto_front` + `format_table`; the cache.
**Live service touched**: all providers used by the included routers.
**Credentials required**: `OPENAI_API_KEY` (+ `ANTHROPIC_API_KEY` for cross-family ensembles/oracle).
**Real resources**: all routers × shared suite, **heavily cached** (overlapping (model,item) pairs paid
once). Budget-bounded; debate/AutoMix included only if the running total stays under the run cap.

**TDD intent**:
- **RED**: test asserts (a) the result table has one row per included router with `n` equal across rows;
  (b) **oracle accuracy ≥ every other router's accuracy** and oracle cost ≤ always-strong cost (oracle
  is the ceiling); (c) at least one **non-trivial router strictly dominates random** (≥ accuracy at ≤
  cost, one strict). Run before the aggregate exists → fails.
- **GREEN**: run all routers via `run_suite` over the shared suite with one shared cache; build the
  oracle offline from per-item per-model correctness; compute `pareto_front`; write
  `pareto-report.md` with the full table + which routers are on the frontier.
- **REGRESSION**: assert reproducibility from the cache (re-run → identical accuracy/cost numbers);
  assert no router is silently equal to a baseline (routing-collapse guard); flag any router that
  **fails** to beat a baseline (reported honestly, not hidden).

**Expected evidence**: full router × {accuracy, total_usd, usd_per_correct, mean_latency, pct_cheap}
table; oracle ceiling row; Pareto-frontier subset; dominates-random proof; honest list of any router
that lost — TBD, measured live in X5.
**Blocked if**: OpenAI key missing. Ensemble rows degrade gracefully if Anthropic is unavailable; the
core frontier (baselines + heuristic + kNN + classifier + cascade + oracle) needs only OpenAI.

---

## L-capstone — Adaptive routing gateway

**Concept introduced**: Combine the proven pieces into ONE adaptive gateway: **classifier prediction**
(L2b) picks an initial tier; a **cascade with verification** (L3a/X4) escalates on low confidence; an
**ensemble fallback** (X1/X2) handles hard queries flagged by the classifier; a **cost-budget guard**
(L5) caps per-request and per-run spend; **full observability** (L4 ledger) records every decision;
served behind the **OpenAI-compatible HTTP gateway** (L3c/L4) and **benchmarked** (X5) to show, with
real numbers, where it sits on the Pareto frontier vs the naive baselines. **Coordinator-run.**
**Prior concepts reused**: L2b classifier, L3a/X4 cascade+verify, X1/X2 ensemble, L5 budget guard +
failure handling, L3c/L4 gateway + ledger, X5 benchmark methodology.
**Live service touched**: all providers via the live gateway → real `/chat/completions`.
**Credentials required**: `OPENAI_API_KEY` (+ `ANTHROPIC_API_KEY` for the ensemble-fallback path).
**Real resources**: the gateway serving the shared suite end-to-end + a fault-injection request +
benchmark placement; cached.

**TDD intent**:
- **RED**: test asserts (a) `POST /v1/chat/completions` to the live gateway returns a valid OpenAI-shaped
  body for an easy item routed cheap and a hard item routed strong/ensemble (decision recorded in the
  ledger); (b) an injected bad-first-model fallback still returns a valid answer; (c) the budget guard
  trips on a forced over-budget run; (d) the gateway's benchmark row **dominates random** and is plotted
  vs the baselines. Run before the gateway exists → fails.
- **GREEN**: assemble the components behind the gateway; run the shared suite through it; inject the
  fault; trip the budget; produce its Pareto row vs the frontier.
- **REGRESSION**: assert end-to-end reproducibility from the cache; assert the ledger captures every
  request's model + tokens + usd + decision; assert the honest verdict — where exactly the adaptive
  gateway sits (it need not beat oracle; it must beat random and report its position truthfully).

**Expected evidence**: live gateway transcript (easy→cheap, hard→strong/ensemble); fallback-recovery;
budget-trip; ledger; capstone Pareto row + frontier placement vs baselines — TBD, measured live in
capstone.
**Blocked if**: OpenAI key missing. Ensemble-fallback path degrades to cascade-only if Anthropic is
unavailable; recorded honestly.

---

## Cross-cutting evidence rule

Every passing live POC must record, in `04-logs/live-evidence-ledger.md`: the model(s) called, real
prompt/completion token counts, the uniformly-computed USD cost, the routing decision, and (where
applicable) the grade. A POC with no real token/cost numbers and no executed-code or provider-response
evidence is **not green**. Local helper tests (numpy math, schema builders) are labeled `Invalid for
service evidence` and never substitute for a live claim.
