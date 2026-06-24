# Live Test Strategy

All tests run against the **real** provider APIs (OpenAI, Anthropic, xAI; OpenRouter only if its key
appears). No mocks at the model-API boundary for any claim about routing, cost, or quality. The shared
harness is the only allowed indirection — and the harness itself was live-verified by the coordinator
before any POC worker ran.

## Test framework

- Plain Python `unittest` / `node --test`-style assertions are not used; POCs use **`python -m
  unittest`** (or a `if __name__ == "__main__"` runner that exits non-zero on failure) so they run with
  **stdlib only** (no pytest install in the Conductor workspace).
- Each POC lives in `03-pocs/<level>/source/`. The live test is `source/test_live.py` (or the POC's main
  runnable), and the captured runs are `source/red-output.txt` + `source/green-output.txt`.
- The test file starts with a credentials guard that **skips (not fails)** when keys are absent:
  ```python
  import os, unittest
  REQUIRED = ["OPENAI_API_KEY"]  # plus ANTHROPIC_API_KEY / XAI_API_KEY per POC
  missing = [k for k in REQUIRED if not os.environ.get(k)]

  @unittest.skipIf(missing, f"missing creds: {missing}")
  class LiveTest(unittest.TestCase): ...
  ```
- Load creds first: `set -a; . .agent-university/secrets.local.env; set +a`.

## Service boundary rule

The provider HTTP endpoints (`api.openai.com`, `api.anthropic.com`, `api.x.ai`) are the service
boundary. Any test that claims a routing decision, cost figure, accuracy, or escalation behavior must
exercise the real endpoint through `harness/providers.chat` / `embed`. `responses`, `httpretty`,
`respx`, `unittest.mock` over urllib, or any other HTTP interceptor is **forbidden** at that boundary.
Internal helpers (the numpy logistic-regression fit, the Pareto math, the heuristic feature extractor,
the OpenAI-shape adapter formatting, ledger writers) may be unit-tested without live calls — but those
tests are labeled `Invalid for service evidence` and never back a routing/cost claim.

## Task suites (graders)

From `harness/tasks.py`, each item is `{id, discipline, difficulty, prompt, grade(answer)->bool, gold}`:

- **coding** (primary, ~12): `code_grader(tests, func_required)` extracts the model's code block and
  runs it + hidden unit tests in a subprocess; pass iff exit 0. Real execution, not a string match.
- **math** (~12): `numeric_grader(gold)` — last integer in the answer must equal the exact gold.
- **qa** (~12): `qa_grader(acceptable)` — normalized (lowercased, punctuation-stripped) containment of a
  gold short answer.

Graders are **deterministic** so the benchmark is reproducible without LLM-judge noise. The LLM judge
(`judge.py`) is used **only** for the ensemble fusion/ranking step (MoA aggregate, debate pick-best),
never as the final correctness signal for closed tasks.

## Oracle

The oracle is computed **offline, after all suite runs complete** (X5): for each item, the cheapest
model that is **actually correct**; if no model is correct, the cheapest model. Oracle accuracy is the
upper bound and oracle cost ≤ always-strong cost. It is **unrealizable in production** (knowing
correctness requires solving the query) and is reported as a **ceiling only**, never as an achievable
router. The X5 RED test asserts oracle accuracy ≥ every other router's accuracy.

## Held-out splits

L2 / L2b train labels on one split and evaluate routing on a **held-out** split (no item is both a
training neighbor/label and an evaluation item). The split is fixed (seeded) and recorded so the curve
is reproducible from the cache. This prevents the classifier from "memorizing" its own training items.

## Pareto evaluation

Each router → `RunResult` → `row()` (accuracy, total_usd, usd_per_correct, mean_latency). `metrics.
pareto_front(rows)` returns the non-dominated subset (≥ accuracy AND ≤ cost, one strict). A "good
router" must dominate **random** and be monotone under a threshold sweep; the frontier is anchored by
always-cheap, always-strong, random, and oracle. The capstone is placed on this same frontier.

## Keeping runs small and cheap

- Suites are ≤ ~12 items each; prompts are short.
- Closed tasks use `temperature=0` (deterministic, cacheable); self-consistency uses `temperature>0`
  with a distinct `nonce` per sample so the cache keeps each sample separate.
- **`harness/cache.py`** stores every unique (model, messages, system, temperature, max_tokens, nonce)
  result on disk: the **first** run of a pair is the billed event; re-runs and overlapping
  (model,item) pairs across routers (especially in X5) are free and produce identical numbers. The
  benchmark reports cost as if each unique pair were paid once.
- A **per-run USD budget guard** (default $0.10/run; L5 + capstone) does a pre-call check and hard-stops
  before exceeding the cap. Ensemble-heavy POCs (X3 debate, X4) cap rounds/items to stay under budget.
- Reasoning models (`gpt-5*`, `grok-4.3`) are used sparingly (math/hard items) because they spend hidden
  reasoning tokens (the harness floors their `max_tokens` to `REASONING_FLOOR=2048` so they answer).

## Evidence recording

After each green run, the POC appends to `04-logs/live-evidence-ledger.md`: model(s) called, real
prompt/completion token counts, uniform USD, routing decision, grade. `green-output.txt` captures the
full passing run; `red-output.txt` captures the prior failing run. A run with no real token/cost numbers
is not evidence.

## How each POC proves live behavior (one line each)

- **L0** — real responses from all 3 providers + a live baseline cost-quality table.
- **L1** — live routed answers; heuristic row sits between the live baselines, beats random.
- **L2 / L2b** — labels + embeddings + held-out routing are all live; threshold sweep is a real curve.
- **L3a / X4** — live escalation traces; cost-at-matched-accuracy measured against live always-strong.
- **L3b** — produced code executed against real unit tests; routed vs all-strong pass rate is live.
- **L3c / L4** — a real client-shaped / HTTP request routes to a real backend; ledger rows are live.
- **L5** — real 4xx bodies, real fallback recovery, a real budget trip.
- **X1 / X2 / X3** — live proposers/samples/debaters + aggregator vs a live single-strong call.
- **X5** — every router run live over the shared suite; oracle computed from real per-model correctness.
- **capstone** — the live gateway serves the suite end-to-end; its frontier position is measured live.
