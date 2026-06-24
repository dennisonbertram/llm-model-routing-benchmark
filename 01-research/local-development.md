# Local Development

**Target**: Model Routing — running POCs locally
**Degree**: 01-llm-model-routing
**Gathered**: 2026-06-21
**Sources**: Harness source `harness/providers.py`, `harness/pricing.py`; spec `.context/model-routing-spec.md`.

Evidence label: **Research supported but not live verified** (this file describes the workflow; Live verified evidence is in individual POC `evidence.md` files).

---

## Overview

Every POC in this degree runs locally with Python 3.9, no virtualenv, no pip installs beyond numpy. The harness calls real provider APIs — there are no mocks. A full suite run on the cheap-model tier costs well under $0.10 USD.

---

## Step-by-step: running a POC

### 1. Load secrets

```bash
set -a; . /Users/dennison/conductor/workspaces/agent-university/nashville/.agent-university/secrets.local.env; set +a
```

Verify without printing:

```bash
[ -n "$OPENAI_API_KEY" ] && echo "OK" || echo "MISSING: OPENAI_API_KEY"
[ -n "$ANTHROPIC_API_KEY" ] && echo "OK" || echo "MISSING: ANTHROPIC_API_KEY"
[ -n "$XAI_API_KEY" ] && echo "OK" || echo "MISSING: XAI_API_KEY"
```

### 2. Confirm numpy is importable

```bash
python3 -c "import numpy; print('numpy', numpy.__version__)"
```

### 3. Run the POC

```bash
python3 /Users/dennison/conductor/workspaces/agent-university/nashville/model-routing/degrees/01-llm-model-routing/03-pocs/<poc-dir>/source/run.py
```

Use absolute paths to avoid cwd ambiguity.

### 4. Capture output as evidence

A passing run must produce `green-output.txt` in `source/`:

```bash
python3 /path/to/run.py 2>&1 | tee source/green-output.txt
```

A failing or partial run produces `red-output.txt`. Both are required evidence artifacts.

---

## Harness import pattern

The canonical import from any `source/run.py`:

```python
import sys, os

# Reach harness/ from 03-pocs/<poc-dir>/source/
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "..", "harness")
sys.path.insert(0, HARNESS)

from providers import chat, embed, ProviderError
from pricing import PRICES, usd_for
```

Using `os.path.abspath(__file__)` makes the import path robust regardless of the working directory when `python3 run.py` is invoked.

---

## Keeping live runs small and cheap

### Task suite sizes

Task suites are capped at ~12–20 items each. Do not expand them without coordinator approval. The goal is to produce real routing signal while keeping per-POC cost under $0.10.

### Use cheap models for signal; strong models sparingly

During development, call cheap models (gpt-4.1-nano ~$0.0001 per typical call, claude-haiku-4-5 ~$0.0005 per call) for exploratory testing. Reserve strong models (claude-opus-4-8, gpt-5) for baselines and the LLM judge.

### Check cost before looping

Before running a full suite, estimate cost:

```python
# Rough estimate: N tasks × avg 200 tokens input + 100 tokens output
N = 12
pt_per_task = 200
ct_per_task = 100
from pricing import usd_for
est = N * usd_for("gpt-4.1-nano", pt_per_task, ct_per_task)
print(f"Estimated cost: ${est:.4f}")
```

If the estimate exceeds $0.05, run a 3-item smoke first.

### Hard cost cap pattern

Add a budget guard before any loop that calls `chat()`:

```python
BUDGET_USD = 0.10
total_usd = 0.0

for item in suite:
    if total_usd >= BUDGET_USD:
        print(f"[BUDGET GUARD] Reached ${BUDGET_USD:.2f} limit after {i} items. Stopping.")
        break
    result = chat(model, item["messages"])
    total_usd += result["usd"]
```

See `security-model.md` for the full cost-budget guard pattern.

---

## Iterating on a POC

1. Edit `source/run.py` (or the module it imports).
2. Re-run with `python3 source/run.py`.
3. When the run passes, capture `green-output.txt`.
4. Update `evidence.md` with new results — token counts, cost, accuracy numbers from the live run.
5. If a previously green run now fails, create a new `red-output.txt` and investigate before re-running.

**Do not overwrite `green-output.txt` with partial or failing output.** The green output is evidence.

---

## Debugging provider calls

### Print the raw response

```python
result = chat("gpt-4.1-nano", [{"role": "user", "content": "Hello"}])
import json; print(json.dumps(result["raw_usage"], indent=2))
```

`raw_usage` contains the provider's unmodified usage object. For xAI this includes `cost_in_usd_ticks`.

### Isolate a single provider

To test one provider without running the full suite:

```python
import sys, os
sys.path.insert(0, "/path/to/harness")
from providers import chat

# OpenAI smoke
r = chat("gpt-4.1-nano", [{"role": "user", "content": "Say 'ok' only."}], max_tokens=5)
print(r["text"], r["usd"])

# Anthropic smoke
r = chat("claude-haiku-4-5-20251001", [{"role": "user", "content": "Say 'ok' only."}], max_tokens=5)
print(r["text"], r["usd"])

# xAI smoke
r = chat("grok-4.3", [{"role": "user", "content": "Say 'ok' only."}], max_tokens=5)
print(r["text"], r["usd"], r["native_cost_usd"])
```

### ProviderError inspection

```python
from providers import chat, ProviderError
try:
    r = chat("gpt-4.1-nano", messages)
except ProviderError as e:
    print("Provider error:", str(e))
    # Includes provider name, HTTP status, and first 500 bytes of response body
```

---

## Harness modules not yet built (as of 2026-06-21)

The coordinator builds all harness modules before POC workers run. The modules still pending are listed in `setup-and-installation.md`. POC workers should check whether `judge.py`, `tasks.py`, `metrics.py`, and `router_base.py` exist before importing them.

```bash
ls /path/to/harness/
```

If a module is missing, block and notify the coordinator. Do not stub or mock it.

---

## Evidence artifact checklist (per POC)

After a successful run, verify all artifacts exist:

```
03-pocs/<poc-dir>/
├── README.md          ← rich, INDEXED; must include Live verified label
├── intent.md          ← what this POC proves
├── evidence.md        ← real numbers: token counts, cost, accuracy, latency
├── commands.md        ← exact commands to reproduce the run
├── surprises.md       ← unexpected findings
├── status.md          ← one of: green / partial / blocked / not-started
└── source/
    ├── run.py
    ├── green-output.txt   ← captured from a real passing run
    └── red-output.txt     ← captured from pre-fix run (if applicable)
```

---

## Sources

- Harness source: `harness/providers.py` (coordinator-built, 2026-06-21)
- Spec: `.context/model-routing-spec.md`
- Python docs (abspath): https://docs.python.org/3.9/library/os.path.html#os.path.abspath
