# L-Capstone — Adaptive Routing Gateway

**Evidence: Live verified (2026-06-21).** Status: Complete with live evidence.

The degree's combined system: one deployable, OpenAI-compatible **adaptive routing gateway** that
folds in every prior POC and lands near the oracle ceiling on the realizable Pareto frontier — with
real cost and quality measured live.

## What it combines (maps back to the ladder)

| Capability | From | In the capstone |
|---|---|---|
| Predictive routing (logistic classifier over embeddings) | L2b / X5 (the proven winner) | primary decision: P(cheap correct) ≥ threshold ⇒ cheap, else strong |
| Verification escalation (cheap self-check → escalate) | L3a / X4 | optional `verify_escalate` safety net |
| Cost-budget guard | L5 | per-session USD cap forces cheap once exceeded |
| Provider fallback chain | L5 | bad/erroring primary → fallback model |
| OpenAI-compatible runtime + ledger | L4 / L3c | `POST /v1/chat/completions`, `{model:"auto"}`, decision/cost ledger |
| Cost-vs-quality benchmark | X5 / L0 | 5-fold CV, scored on the live outcome matrix |

## Honest benchmark — 5-fold CV over 45 tasks (no leakage), live-measured

| Router | accuracy | cost | pct routed cheap |
|---|---|---|---|
| always-cheap | 0.844 | $0.00166 | 100% |
| always-strong | 0.978 | $0.02148 | 0% |
| oracle (ceiling, unrealizable) | 0.978 | $0.00214 | — |
| adaptive(thr=0.7) | 0.956 | $0.00227 | 82% |
| **adaptive(thr=0.8)** | **0.978** | **$0.00257** | 71% |
| adaptive(thr=0.9) | 0.978 | $0.00275 | 64% |

> **Live verified: the adaptive gateway matches always-strong accuracy (0.978) at $0.00257 — 8.4×
> cheaper than always-strong, only 1.20× the unrealizable oracle cost.** It keeps ~71% of traffic
> on the cheap model and routes the hard-math tail to the strong model.

## Live behaviors (real calls, see `green-output.txt`)

- **OpenAI-compatible HTTP gateway** (`gateway_server.py`, curled live):
  - `auto` + "capital of France" → `p_cheap=0.97` → **gpt-4o-mini** → "Paris."
  - `auto` + "ways to arrange BALLOON" → `p_cheap=0.38` → **gpt-4.1** → "1260" (correct)
  - `model:"gpt-4o-mini"` (forced, drop-in client) → honored
  - every request appended to `gateway-ledger.jsonl` (decision, model, tokens, USD, latency)
- **Budget guard**: with a $0.00025 cap, requests 1–4 route to gpt-4.1, then the guard forces
  gpt-4o-mini on requests 5–6 (`decision=budget_guard(spent=$0.0003>=cap)`).
- **Provider fallback**: a deliberately bad strong slug → the gateway falls back to gpt-4o-mini
  and still returns an answer (`fallback_from=yes`).

## Run it

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd source
python3 run_capstone.py                 # CV benchmark + live budget-guard + fallback demos
python3 gateway_server.py 8137 &         # OpenAI-compatible runtime
curl -s -X POST localhost:8137/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"auto","messages":[{"role":"user","content":"What is 2+2? Just the number."}]}'
```

RED (`red-output.txt`): keys unset → `ProviderError` (live-access blocker).
