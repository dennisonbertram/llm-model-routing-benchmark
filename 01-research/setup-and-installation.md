# Setup and Installation

**Target**: Model Routing (LLM selection + cost efficiency for AI agents)
**Degree**: 01-llm-model-routing
**Gathered**: 2026-06-21
**Sources**: harness source code in `harness/providers.py` + `harness/pricing.py` (live-built by coordinator); spec at `.context/model-routing-spec.md`; provider docs fetched via WebFetch.

Evidence label: **Research supported but not live verified** (this file describes setup; POC READMEs carry the Live verified label once runs complete).

---

## Prerequisites

### Python version

Python 3.9+. No virtualenv or `pip install` is required for any POC in this degree. The harness uses only:

- Python stdlib: `json`, `os`, `time`, `urllib.request`, `urllib.error`, `subprocess`, `sys`
- `numpy` 2.0.2 — already present in the workspace

Confirm:

```bash
python3 --version          # must be >= 3.9
python3 -c "import numpy; print(numpy.__version__)"  # should print 2.0.2
```

If numpy is missing:

```bash
pip install "numpy<3"
```

No other packages are needed. The harness deliberately avoids sklearn, scipy, and any paid ML library so POC workers can run without environment setup friction.

---

## Credential setup

API keys live in `.agent-university/secrets.local.env` (gitignored — never commit this file or echo its values). Load them into the current shell before running any POC:

```bash
set -a; . /Users/dennison/conductor/workspaces/agent-university/nashville/.agent-university/secrets.local.env; set +a
```

Verify each key is present without printing its value:

```bash
[ -n "$OPENAI_API_KEY" ]      && echo "OPENAI_API_KEY SET"     || echo "MISSING"
[ -n "$ANTHROPIC_API_KEY" ]   && echo "ANTHROPIC_API_KEY SET"  || echo "MISSING"
[ -n "$XAI_API_KEY" ]         && echo "XAI_API_KEY SET"        || echo "MISSING"
[ -n "$OPENROUTER_API_KEY" ]  && echo "OPENROUTER_API_KEY SET" || echo "MISSING (optional)"
```

`OPENROUTER_API_KEY` is optional — see `configuration-and-env-vars.md`. All other three are required for the L0 smoke POC.

---

## Harness layout

```
model-routing/degrees/01-llm-model-routing/
├── harness/                  ← coordinator-owned; POC workers READ only
│   ├── providers.py          ← chat(), embed(), ProviderError
│   ├── pricing.py            ← PRICES table, usd_for()
│   ├── judge.py              ← (to be built) judge_correct(), exact_match, numeric_match
│   ├── tasks.py              ← (to be built) task suite dicts
│   ├── metrics.py            ← (to be built) accumulator, Pareto row emitter
│   └── router_base.py        ← (to be built) Router base class, run_suite()
├── 01-research/              ← this directory
├── 02-planning/
├── 03-pocs/
│   ├── L0-smoke-and-harness/
│   ├── L1-heuristic-router/
│   └── ...
├── 04-logs/
├── 05-distillation/
├── 06-skill-pack/
├── 07-evaluation/
└── README.md
```

**Coordinator owns `harness/`**: POC worker agents must not modify harness files. If a POC needs a harness change, it must be requested via the coordinator.

---

## Importing the harness from a POC

Every POC lives under `03-pocs/<dir>/source/`. The canonical import block is:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
from providers import chat, embed
from pricing import PRICES, usd_for
from router_base import Router, run_suite
from tasks import CODING_SUITE, QA_SUITE, MATH_SUITE
from metrics import accumulate, pareto_row
```

The relative path `../..` from `source/` reaches `03-pocs/` then again to reach `harness/` — verify the exact depth for your POC directory. If in doubt, use an absolute path built from `__file__`.

---

## Running a POC

```bash
# 1. Load secrets
set -a; . /path/to/.agent-university/secrets.local.env; set +a

# 2. Run the POC entry point
python3 /path/to/model-routing/degrees/01-llm-model-routing/03-pocs/<poc-dir>/source/run.py
```

Output goes to stdout. POCs must write `green-output.txt` (passing run) or `red-output.txt` (failing/partial run) in `source/` as evidence.

---

## What the harness modules do

| Module | Key exports | Purpose |
|---|---|---|
| `providers.py` | `chat(model, messages, **opts)`, `embed(texts)`, `ProviderError` | All live API calls. Returns normalized dict. |
| `pricing.py` | `PRICES`, `usd_for(model, pt, ct)` | USD cost from token counts. Price table seeded 2026-06-21. |
| `judge.py` | `judge_correct(task, answer)`, `exact_match`, `numeric_match` | Answer grading. Strong model for open-ended; rules for closed. |
| `tasks.py` | `CODING_SUITE`, `QA_SUITE`, `MATH_SUITE`, `MIXED_HARD`, `MIXED_EASY` | Small task suites (~12 items each). Real prompts, no licensed data. |
| `metrics.py` | `accumulate(results)`, `pareto_row(name, acc, usd, lat)` | Aggregation and Pareto frontier output. |
| `router_base.py` | `Router`, `run_suite(router, suite)` | Base class + live evaluation loop. |

---

## Harness contract (providers.py)

`chat()` always returns:

```python
{
    "model":             str,     # model id as called
    "provider":          str,     # "openai" | "anthropic" | "xai" | "openrouter"
    "text":              str,     # response text
    "prompt_tokens":     int,
    "completion_tokens": int,
    "total_tokens":      int,
    "latency_ms":        int,     # wall-clock ms for the HTTP round trip
    "usd":               float,   # cost in USD, computed from PRICES table
    "finish_reason":     str,     # "stop" | "length" | "tool_calls" | ...
    "raw_usage":         dict,    # provider's raw usage object (for evidence)
    "native_cost_usd":   float|None,  # xAI ticks→USD; None for other providers
}
```

`embed()` returns `(vectors: list[list[float]], usd: float)`.

`ProviderError` is raised on all provider errors (HTTP 4xx/5xx, network timeout) after exhausting retries. Callers must handle it to implement cascade / fallback logic.

---

## Cost discipline

Keep each live run small and cheap:
- Task suites have ≤ ~20 items each — do not expand them without coordinator approval.
- Use cheap models (gpt-4.1-nano, claude-haiku-4-5) for routing signal; strong models (gpt-4o, claude-opus-4-8) only for judge and baseline comparison.
- Target total spend per POC run < $0.10 USD.
- If a run exceeds $0.50, stop and report; do not loop indefinitely.

See `local-development.md` for the full run discipline and `security-model.md` for the cost-budget guard pattern.

---

## Sources

- Harness source: `model-routing/degrees/01-llm-model-routing/harness/providers.py` (coordinator-built, 2026-06-21)
- Harness source: `model-routing/degrees/01-llm-model-routing/harness/pricing.py` (coordinator-built, 2026-06-21)
- Spec: `.context/model-routing-spec.md`
- Python 3.9 stdlib: https://docs.python.org/3.9/library/urllib.request.html
- numpy 2.0 release: https://numpy.org/doc/stable/release/2.0.0-notes.html
