# Reference: Harness API

Live verified (L0; spec; 2026-06-21). The shared harness in `harness/` is frozen.
All POCs import from it. Do NOT reimport providers directly — use these interfaces.

Back to [index](../index.md).

---

## Import path (from inside a POC source/ file)

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
from providers import chat, embed
from cache import Cache
from router_base import Router, SingleModelRouter, run_suite
from metrics import format_table, pareto_front
from tasks import ALL as SUITE
import config
import judge
```

---

## providers.py

### chat()

```python
chat(model: str, messages: list, max_tokens: int = 512,
     temperature: float = 0.0, system: str = None) -> dict
```

Returns:
```python
{
    "text":                    str,    # response content
    "prompt_tokens":           int,
    "completion_tokens":       int,
    "billed_completion_tokens": int,   # may differ from completion_tokens for reasoning models
    "latency_ms":              float,
    "usd":                     float,  # computed from harness price table
    "finish_reason":           str,
    "native_cost_usd":         float,  # provider's native cost field (grok: ticks/1e10)
}
```

Provider auto-detected from model ID (openai / anthropic / xai). Raises `ProviderError`
on missing env var, HTTP 4xx/5xx, or network failure.

### embed()

```python
embed(texts: list[str], model: str = "text-embedding-3-small") -> tuple[list[list[float]], float]
```

Returns `(vectors, usd)`. Vectors are raw floats; L2-normalize before cosine similarity.

---

## cache.py

### Cache

```python
Cache(path: str)
```

On-disk JSON cache. Deduplicates by `(model, messages, max_tokens, temperature, nonce)`.
Warm cache hits return the stored result; no API call made, usd=0.

```python
cache = Cache("harness/.cache")
result = cache.chat(model, messages, max_tokens=256, temperature=0.0)
# For temperature>0 samples, pass a distinct nonce per sample:
result = cache.chat(model, messages, temperature=0.7, nonce=f"sc_sample_{i}")
```

---

## router_base.py

### Router (base class)

```python
class Router:
    def route(self, item: dict) -> str:
        raise NotImplementedError
```

### SingleModelRouter

```python
SingleModelRouter(model: str)
```

Always routes to the same model. Use for baselines.

### run_suite()

```python
run_suite(router: Router, items: list, cache: Cache = None) -> RunResult
```

Runs `router.route(item)` for each item, calls the model, grades the answer.
Returns `RunResult` with:

```python
result.accuracy()        -> float   # correct / total
result.total_usd()       -> float
result.usd_per_correct() -> float
result.mean_latency()    -> float   # ms
result.pct_cheap(models: list) -> float   # fraction routed to cheap models
result.by_difficulty()   -> dict    # per difficulty breakdown
result.row()             -> dict    # {label, accuracy, total_usd, usd_per_correct}
```

---

## tasks.py

### Task item structure

```python
{
    "id":         str,            # e.g. "m9", "c3", "q1"
    "discipline": str,            # "math" | "qa" | "coding"
    "difficulty": str,            # "easy" | "medium" | "hard"
    "prompt":     str,
    "grade":      Callable[[str], bool],   # grader function
    "gold":       str,            # gold answer (for display / judge)
}
```

### Suite

```python
from tasks import ALL            # all 45 items
from tasks import MATH, QA, CODING  # per-discipline slices
```

45 items: math m1–m15 (15 items), qa q1–q12 (12 items), coding c1–c18 (18 items).

---

## config.py

```python
config.CHEAP_DEFAULT   = "gpt-4o-mini"
config.STRONG_DEFAULT  = "gpt-4.1"
config.MID_DEFAULT     = "gpt-4o"
config.JUDGE_MODEL     = "gpt-4.1"
config.EMBED_MODEL     = "text-embedding-3-small"
config.ENSEMBLE_CHEAP  = ["gpt-4o-mini", "gpt-4.1-mini", "claude-haiku-4-5-20251001"]
config.REASONING_FLOOR = 2048
```

---

## metrics.py

```python
format_table(rows: list[dict]) -> str
```

Formats a list of `{label, accuracy, total_usd, usd_per_correct}` dicts into a Pareto table.

```python
pareto_front(rows: list[dict]) -> list[dict]
```

Returns only the non-dominated rows (higher accuracy OR lower cost for any given level of the other).

---

## judge.py

Aggregate ensemble proposals:
```python
judge.majority_vote(answers: list[str]) -> str
judge.aggregate_proposals(proposals: list[str], aggregator_model: str, cache: Cache) -> str
```

Grade open-ended answers:
```python
judge.judge_correct(task: dict, answer: str, model: str = None) -> bool
```

---

## Harness location

```
harness/
  providers.py
  pricing.py
  tasks.py
  cache.py
  config.py
  metrics.py
  router_base.py
  judge.py
  .cache/         # on-disk response cache (gitignored per repo, but included here)
    labelset.json # L0 per-item correctness matrix — reuse this, don't re-bill
```

Do NOT edit any file under `harness/`. It is frozen after L0. All changes go in your own POC source/.
