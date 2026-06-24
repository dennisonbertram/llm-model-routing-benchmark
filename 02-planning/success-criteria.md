# Success Criteria

A POC is "green" only when its criteria are met with **live evidence** (a passing run + real
prompt/completion token counts + uniformly-computed USD + the routing decision + the grade, recorded in
`04-logs/live-evidence-ledger.md`). No mock substitutes for a model-API claim. Every number is a
**measured** value; unmeasured values are written "TBD — measured live in <POC>", never invented.

## L0 — Smoke + harness + baselines

- [ ] A live `chat()` call to one model of **each** provider (OpenAI, Anthropic, xAI) returns non-empty
      `text` with `prompt_tokens > 0`.
- [ ] `usd > 0` for each call and equals `usd_for(model, prompt_tokens, billed_completion_tokens)`.
- [ ] Both baselines (always-cheap `gpt-4o-mini`, always-strong `gpt-4.1`) run over coding/qa/math via
      `run_suite`; a real cost-quality table is emitted (accuracy, total_usd, usd_per_correct, latency).
- [ ] always-strong accuracy ≥ always-cheap accuracy on the mixed-hard split (the routable gap exists).
- [ ] The xAI ticks→USD factor is checked against a real `cost_in_usd_ticks` and the correct factor recorded.

## L1 — Heuristic router

- [ ] The heuristic router runs live and routes a non-trivial fraction to each tier (`0 < pct_cheap < 1`).
- [ ] Its row is **not dominated by random** (≥ accuracy at ≤ cost).
- [ ] A 2–3 point threshold sweep shows a sane (monotone) cost↑/accuracy-non-decreasing knob.

## L2 — Embedding-kNN router

- [ ] A labeled routing set is built from **real** dual runs (both classes present).
- [ ] Embeddings cost `usd > 0` (real `text-embedding-3-small` calls).
- [ ] On a held-out split the kNN router beats random at lower cost than always-strong, at ≥1 threshold.

## L2b — Classifier router

- [ ] The numpy logistic-regression fit converges (loss decreases) and train accuracy > 0.5.
- [ ] A threshold sweep traces a **monotone** cost-vs-cheap-fraction curve on held-out (no silent collapse).
- [ ] At least one threshold point dominates random on held-out.

## L3a — FrugalGPT cascade

- [ ] Easy items terminate at the cheap tier; hard items escalate (`strong in models`).
- [ ] Cascade accuracy ≥ always-cheap and cascade total_usd < always-strong on the suite.
- [ ] The cost-at-matched-accuracy point (or an honest "no reduction") is recorded.

## L3b — Harness routing for a multi-step coding agent

- [ ] The routed harness uses ≥1 cheap and ≥1 strong step per task (step-level mix).
- [ ] Produced code is executed against real unit tests; routed pass rate ≥ all-cheap pass rate.
- [ ] Routed total_usd < all-strong total_usd; latency compounding is measured and documented.

## L3c — OpenAI-compatible gateway integration

- [ ] An OpenAI-shaped request returns an OpenAI-shaped response with non-empty `choices[0].message.content`
      and `usage` token fields.
- [ ] The served backend varies by input difficulty; an unknown alias falls back safely (no crash).

## L4 — Routing gateway runtime

- [ ] A real HTTP `POST /v1/chat/completions` from a separate client returns 200 + OpenAI-shaped body.
- [ ] A ledger file gains a row per request with `usd > 0`, the chosen model, and the routing decision.
- [ ] ≥3 requests of differing difficulty show ≥2 distinct models chosen and a running cost total.

## L5 — Failure modes + observability

- [ ] An invalid model slug raises `ProviderError` with the **real** HTTP 4xx body captured (sanitized).
- [ ] A fallback chain `[bad, good]` returns a valid answer from the good model.
- [ ] A verifier-caught misroute escalates and produces the correct answer.
- [ ] A forced over-budget run trips the cap and **stops before** the next call (hard stop).

## X1 — Mixture-of-Agents

- [ ] 3 cheap proposers + aggregator produce a non-empty synthesized answer; run alongside single-strong.
- [ ] MoA vs single-strong accuracy + total_usd + latency are reported **honestly** (win OR loss).

## X2 — Self-consistency vote

- [ ] k cheap samples are drawn with distinct nonces (k cache entries) and majority-voted.
- [ ] Self-consistency accuracy ≥ single-cheap-call accuracy on math; the k where it meets/beats
      single-strong (if any) and its cost are recorded.

## X3 — Multi-agent debate

- [ ] A ≥2-round transcript shows at least one agent revising between rounds.
- [ ] Debate vs single-strong accuracy + cost + latency reported honestly (expected most-expensive; loss is valid).

## X4 — Verification cascade (AutoMix-style)

- [ ] Self-verification returns a parseable confidence; low-confidence items escalate, high-confidence don't.
- [ ] At some threshold, total_usd < always-strong with accuracy ≥ always-cheap.
- [ ] ≥1 self-verification miscalibration case is documented (confident-but-wrong).

## X5 — Router benchmark Pareto (the empirical heart)

- [ ] Every included router has a row with equal `n`; the table reports accuracy/total_usd/usd_per_correct/
      latency/pct_cheap.
- [ ] **Oracle** accuracy ≥ every other router and oracle cost ≤ always-strong (ceiling holds).
- [ ] At least one non-trivial router **strictly dominates random**.
- [ ] Numbers reproduce from the cache; any router that fails to beat a baseline is listed honestly.

## L-capstone — Adaptive routing gateway

- [ ] Live gateway routes an easy item cheap and a hard item strong/ensemble (decision in the ledger).
- [ ] Injected bad-first-model recovers via fallback; valid OpenAI-shaped body returned.
- [ ] A forced over-budget run trips the cap before the next call.
- [ ] The capstone's X5 row **dominates random**, sits at/below oracle, and its frontier position is
      reported with real numbers (win or loss).

## Degree-level "done"

- [ ] L0–L5 + X1–X5 + capstone all green with live evidence in `04-logs/live-evidence-ledger.md`.
- [ ] An **honest Pareto frontier** (X5) where at least one router measurably dominates random, with the
      cheap-ensemble result reported truthfully (win OR loss) — no spin.
- [ ] **Zero fabricated numbers**: every quality/cost figure traces to a captured live call or a cited
      external source explicitly labeled as such; paper claims labeled `NOT reproduced here`.
- [ ] Red/green/regression captured per POC (`red-output.txt` / `green-output.txt`); commands in
      `04-logs/`.
- [ ] Gotchas/recipes/patterns distilled in `05-distillation/` (each rank-bearing section labeled `Live
      verified`); skill pack written in `06-skill-pack/`.
- [ ] Any blocked work labeled in `04-logs/access-blockers.md` (never mocked).
- [ ] The degree is **indexed and searchable** via `/v1/search` and the MCP build-tools.
