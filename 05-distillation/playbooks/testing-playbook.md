# Testing Playbook — LLM Model Routing

Live verified. This playbook covers: building a deterministic grader suite, collecting
the outcome matrix, cross-validation methodology, and the tests each POC must have.

---

## 1. Deterministic graders — no LLM judge for closed tasks

**Live verified** (L0; X5)

Use deterministic graders wherever the task has a ground-truth answer. The harness
`judge.py` implements three grader types:

```python
# tasks.py — each task item
{
    "id": "m9",
    "discipline": "math",
    "difficulty": "hard",
    "prompt": "Find the number of integers from 1 to 100 ...",
    "gold": "47",
    "grade": lambda answer: numeric_match(answer, 47, tolerance=0)
}
```

Grader types by discipline:
- **math**: `numeric_match(answer, gold, tolerance=0)` — strip non-numeric characters,
  parse as float, compare within tolerance. Exact match for integer answers.
- **QA/knowledge**: `normalized_match(answer, gold)` — lowercase, strip punctuation,
  compare; or short-answer LLM judge for multi-word answers.
- **coding**: execute the produced code against hidden unit tests in a subprocess;
  pass/fail is the grade. No LLM judge on code output.

Never use a prompted LLM judge for tasks with a numeric or exact-match gold answer —
the judge can hallucinate "correct" for wrong answers, and it adds cost per graded item.
LLM judge is appropriate for open-ended QA where normalization is not enough.

---

## 2. Building the outcome matrix

**Live verified** (L0)

The outcome matrix is the foundation of every router evaluation in this degree:

```python
# Pseudocode — run_l0.py builds this
outcome_matrix = {}
for item in tasks.ALL:
    cheap_result = cache.chat(CHEAP_DEFAULT, item["prompt"])
    strong_result = cache.chat(STRONG_DEFAULT, item["prompt"])
    outcome_matrix[item["id"]] = {
        "cheap_correct": item["grade"](cheap_result.text),
        "strong_correct": item["grade"](strong_result.text),
        "cheap_usd": cheap_result.usd,
        "strong_usd": strong_result.usd,
    }
```

The outcome matrix is cached at `harness/.cache/labelset.json`. All later POCs import it
rather than re-billing. After building the matrix, compute:
- always-cheap accuracy = `mean(cheap_correct)`
- always-strong accuracy = `mean(strong_correct)`
- oracle cost = `sum(min(cheap_usd_i, strong_usd_i) for i where strong_correct[i])`
- oracle accuracy = `mean(strong_correct)` (strong is always the strong-model answer)

In this degree: 6/45 items have `cheap_correct=False AND strong_correct=True` — these
are the 6 routing targets. 1 item (m8) has both=False — the oracle charges cheap for it.

---

## 3. Cross-validation methodology

**Live verified** (X5; capstone)

For predictive routers with a small labeled set (< 200 items), use 5-fold CV:

```python
# From X5 benchmark.py / capstone run_capstone.py
from sklearn_replacement import kfold_cv  # pure numpy implementation in harness

def cv_evaluate(router_class, items, n_folds=5, seed=42):
    folds = make_folds(items, n_folds, seed)
    results = []
    for fold_i, (train_items, test_items) in enumerate(folds):
        router = router_class.fit(train_items)
        fold_result = run_suite(router, test_items, cache)
        results.append(fold_result)
    return aggregate_cv_results(results)
```

Rules:
- Each item appears in exactly one test fold.
- The router is trained on the other k-1 folds.
- Never use `difficulty` or `discipline` labels as features — these are oracle leakage.
  Use only prompt text (via embedding) or prompt-level structural features.
- Report CV accuracy and CV cost as the canonical numbers. Single-split numbers can
  appear as supplementary context but must be labeled as "single split, held-out."

Why CV matters on small sets: a 45-item suite with a 30% test split (13 items) can show
1.000 accuracy by chance if the 6 hard items all land in the training set. CV distributes
them across folds and gives a stable estimate.

---

## 4. The RED/GREEN test pattern

**Live verified** (L0; L1; L2; L2b; L3a; L3b; L4; L5; X4)

Every POC must have both a RED and a GREEN captured run:

**RED test** — run with credentials unset (`OPENAI_API_KEY=""`):
- The expected failure is `ProviderError: Missing env var OPENAI_API_KEY`.
- Not a mock error — the live client code should fail because the key is absent.
- Captured in `source/red-output.txt`.

**GREEN test** — run with valid credentials:
- Live API calls succeed, graders produce real pass/fail, the results table matches the
  README claims.
- Captured in `source/green-output.txt`.

Each behavioral test class uses `setUpClass` to load credentials and fail fast with
`ProviderError` if missing:

```python
class TestL2Live(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.embed_result = embed(["test prompt"])  # raises ProviderError if no key
```

The RED/GREEN split ensures:
1. The live-access blocker is real (not masked by caching or mocks).
2. The GREEN run demonstrates actual behavior with real API calls.

---

## 5. Test coverage requirements per POC

**Live verified** (L0–L5; X1–X5; capstone)

Minimum behavioral tests for a routing POC:

| Test category | What to assert |
|---|---|
| live access | A real model call returns non-empty text and usd > 0 |
| routing correctness | At least 3 sample items are routed to the expected model |
| Pareto monotonicity | Sweeping threshold from low to high increases cost monotonically |
| oracle bound | Router cost ≥ oracle cost (router cannot cheat the oracle) |
| budget guard | Budget guard fires when cumulative cost exceeds the cap |
| observability | Ledger file written with all required fields; no API key in log |

For cascade POCs, also test:
- Verifier triggers escalation on a known-hard item
- Escalation produces a correct answer from the strong model
- Fallback fires when the primary provider returns an error

---

## 6. Regression tests

**Live verified** (L0 harness; L3b)

Add regression tests for critical harness behaviors:

```python
def test_reasoning_floor_applied():
    # Confirms REASONING_FLOOR=2048 is applied for o-series models
    payload = _build_payload("gpt-5-mini", [{"role": "user", "content": "hi"}], 16, 0.0)
    assert "temperature" not in payload  # must be omitted for o-series
    assert payload["max_completion_tokens"] >= 2048  # floor applied

def test_cheap_model_repair_path():
    # L3b: the repair prompt elicits a corrected solution from strong
    # This tests the repair mechanism even when cheap saturates on the full suite
    broken_code = "def fizzbuzz(n):\n    return 'broken'"
    result = repair_call(STRONG_DEFAULT, fizzbuzz_task, broken_code)
    assert fizzbuzz_grade(result.text) == True
```

The L3b repair test (the only one that proved the escalation path works) uses a
deliberately broken fizzbuzz stub to force escalation and verify the strong model
repairs it. This test is valid for service evidence; it exercises the real repair
code path with a real API call.

---

## Evidence

- L0 README.md: "Evidence: Live verified. Grade = deterministic (numeric/normalized QA/unit-test execution)." (Live verified)
- X5 README.md: "Predictive routers use 5-fold cross-validation so every task is held out exactly once (no leakage)." (Live verified)
- L2b README.md: "Train: 32 items (70% stratified split, seed=7)... Test: 13 items (30% held-out)." (Live verified)
- L3b README.md: "`test_repair_prompt_elicits_code` test (GREEN) confirms the strong model repairs a deliberately broken fizzbuzz stub." (Live verified)
- L5 README.md: "All 9 behavioral tests pass against live providers." (Live verified)
