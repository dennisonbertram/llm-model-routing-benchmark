# Integration Playbook — LLM Model Routing

Live verified. Covers: wiring an existing OpenAI SDK client to the routing gateway,
cross-provider API surface differences, and embedding the router in an agent harness.

---

## 1. Drop-in gateway integration via `base_url` override

**Live verified** (L3c; L4; capstone)

Any client that talks to the OpenAI API can be redirected to the routing gateway by
setting `base_url`. The client code does not change:

```python
from openai import OpenAI

# Before: direct to OpenAI
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# After: route through the local gateway
client = OpenAI(
    api_key="not-used-by-gateway",  # gateway ignores this; uses its own keys
    base_url="http://localhost:8137/v1",
)

# The call is identical; routing is transparent to the caller
response = client.chat.completions.create(
    model="auto",           # "auto" triggers routing; or pass a specific model to force it
    messages=[{"role": "user", "content": "..."}],
    max_tokens=512,
)
```

L3c proved this integration live: 10/10 tests passed against the real gateway with
a real OpenAI SDK client. The SDK's response parsing works on gateway-returned JSON
because the gateway returns valid OpenAI-shaped JSON.

---

## 2. Using `model="auto"` vs. forcing a specific model

**Live verified** (L4; capstone)

- `model="auto"` — activates the router's decision logic (classifier, heuristic, etc.)
- `model="gpt-4o-mini"` or any specific slug — bypasses routing; `x_routing.decision`
  is set to `"forced"`. Use for debugging or when the caller has domain knowledge that
  the router does not.

Forced routing is proved live in L4: a `model="gpt-4o-mini"` explicit request with
prompt "Say hello briefly." was honored with `decision="forced"`, $0.0000029, 608ms.

---

## 3. Cross-provider API surface — what must be handled per provider

**Live verified** (L0)

| Provider | Base URL | Auth header | Cost field | Special notes |
|---|---|---|---|---|
| OpenAI | `https://api.openai.com/v1` | `Authorization: Bearer $OPENAI_API_KEY` | None in response — compute client-side | o-series: `max_completion_tokens`, no `temperature` |
| Anthropic | `https://api.anthropic.com/v1/messages` | `x-api-key: $ANTHROPIC_API_KEY` + `anthropic-version: 2023-06-01` | None — compute client-side | Response text at `content[0].text`; requires `max_tokens` |
| xAI | `https://api.x.ai/v1` (OpenAI-compatible) | `Authorization: Bearer $XAI_API_KEY` | `cost_in_usd_ticks` in usage | `ticks / 1e10` = USD; grok always spends reasoning tokens |

The harness `providers.py` handles all three with a unified `chat(model, messages, ...)
-> {text, prompt_tokens, completion_tokens, latency_ms, usd, native_cost_usd}` interface.
Import it rather than re-implementing provider detection:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
from providers import chat, embed
```

---

## 4. Embedding the router in an agent harness (opencode-style)

**Live verified** (L3b; capstone)

For a multi-step coding agent, integrate routing at the step level:

```python
# opencode-style harness routing (L3b pattern)
def run_task_with_routing(task, max_repairs=2):
    # Step 1: always try cheap first
    cheap_result = chat(CHEAP_DEFAULT, [{"role": "user", "content": task["prompt"]}])
    
    # Step 2: run tests
    if task["grade"](cheap_result.text):
        return cheap_result  # cheap succeeded, done
    
    # Step 3: escalate to strong with repair prompt
    for attempt in range(max_repairs):
        repair_prompt = f"""The following Python code was written to solve this task:
TASK: {task['prompt']}
FAILING CODE:
```python
{cheap_result.text}
```
The code failed unit tests. Please write a corrected version. Return only a python code block."""
        
        strong_result = chat(STRONG_DEFAULT, [{"role": "user", "content": repair_prompt}])
        if task["grade"](strong_result.text):
            return strong_result
    
    return strong_result  # return last attempt even if wrong
```

This pattern produced 0 escalations on 18 coding tasks (cheap saturates on coding),
but the escalation path is real and tested (L3b synthetic repair test).

For non-coding steps (planning, analysis, summarization), use the classifier router
to decide up-front rather than the escalate-on-failure pattern — these steps do not
have deterministic pass/fail signals.

---

## 5. Integrating the classifier router into a new project

**Live verified** (L2b; capstone)

Minimum steps to use the classifier from the capstone in a new project:

```python
# 1. Load the serialized classifier (train once, reuse)
import json, numpy as np

with open("classifier_weights.json") as f:
    weights = json.load(f)
# weights: {"w": [...], "b": float}

# 2. For each incoming prompt, embed and predict
from providers import embed

def route(prompt: str, threshold: float = 0.8) -> str:
    vec, _cost = embed([prompt])
    vec = np.array(vec[0])
    vec = vec / np.linalg.norm(vec)  # L2-normalize
    logit = float(np.dot(vec, weights["w"]) + weights["b"])
    p_cheap = 1 / (1 + np.exp(-logit))  # sigmoid
    return CHEAP_DEFAULT if p_cheap >= threshold else STRONG_DEFAULT

# 3. Call the chosen model
model = route(user_prompt)
result = chat(model, [{"role": "user", "content": user_prompt}])
```

The classifier weights are small (1536 floats + 1 bias) and can be serialized as JSON.
Re-embedding each query costs ~$3.8e-07 per call (1 prompt × ~100 tokens × $0.02/1M).
At 100k queries/day, embedding cost is ~$0.038/day.

---

## 6. What to NOT reuse across deployments

**Live verified** (L0; L2b)

The outcome matrix and classifier trained in this degree are specific to:
- The task suite (45 items: 15 math, 12 QA, 18 coding)
- The model pool (`gpt-4o-mini` vs `gpt-4.1`)
- The embedding model (`text-embedding-3-small`)
- The pricing at the time of measurement (2026-06-21)

Reusing the trained weights for a different task distribution, different model pool,
or different embedding model will produce wrong routing decisions. The classifier
learned signal from this specific distribution of prompts and labels.

For a new project:
1. Collect an outcome matrix on your own task sample (minimum 50–100 items, with at
   least 10–20 where cheap fails).
2. Embed your prompts with the same embedding model you plan to use in production.
3. Train a new classifier on your labels.
4. Evaluate with CV; confirm the Pareto curve matches your accuracy/cost SLA.

---

## Evidence

- L3c README.md: "10/10 live tests pass; openai SDK base_url override works end-to-end." (Live verified)
- L4 README.md: forced routing live: `model="gpt-4o-mini"` → `decision="forced"`. (Live verified)
- L0 README.md: provider table and wire-format notes. (Live verified)
- L3b README.md: full harness repair loop with repair prompt format. (Live verified)
- Capstone README.md: `auto` + simple prompt → cheap; `auto` + combinatorics → strong. (Live verified)
