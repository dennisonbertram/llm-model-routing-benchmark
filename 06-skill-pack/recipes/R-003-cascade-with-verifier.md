# Recipe R-003: Cascade with Independent Verifier

Live verified (L3a; L3b; 2026-06-21). Cheap-first cascade with a structural verifier.

Back to [index](../index.md).

---

## When to use

- You have a structural verification signal: code test execution, numeric extraction,
  or a trained judge — NOT self-reported confidence.
- Cheap model handles most traffic correctly; escalation is rare.
- The verifier call is cheaper than the strong model call.

## When NOT to use

- Your only verification option is asking the cheap model to rate its own confidence.
  This fails when the cheap model is overconfident-and-wrong (L3a: acc=0.844 at all thresholds).
- Cheap model is already 100% accurate on the workload (L3b: 0 escalations on coding —
  the cascade just adds overhead).

---

## Live results

Live verified (L3b; 2026-06-21): routed harness (cheap-first, escalate-on-test-failure)
on 18 coding tasks: acc=1.000, $0.00148, 0 escalations. Identical to all-cheap cost.

Live verified (L3a; 2026-06-21): coding verifier (YES/NO judge): 18/18 coding, 1
unnecessary escalation, 0 false accepts.

---

## Code: code-execution verifier (opencode-style)

```python
"""
opencode-style cascade: cheap model first, run tests, escalate to strong on failure.
Live verified: acc=1.000, $0.00148 on 18 coding tasks, 0 escalations. (L3b; 2026-06-21)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
from providers import chat
from cache import Cache

CHEAP_MODEL  = "gpt-4o-mini"
STRONG_MODEL = "gpt-4.1"
MAX_REPAIRS  = 2


def run_tests(code: str, grade_fn) -> bool:
    """Execute produced code against the task's grade function. Returns True if passes."""
    return bool(grade_fn(code))


def repair_prompt(task_prompt: str, failing_code: str) -> str:
    return (
        f"The following Python code was written to solve this task:\n"
        f"TASK: {task_prompt}\n"
        f"FAILING CODE:\n```python\n{failing_code}\n```\n"
        f"The code failed the hidden unit tests. Please write a corrected version.\n"
        f"Return only a python code block."
    )


def cascade_route(item: dict, cache: Cache = None) -> dict:
    """
    item: {id, prompt, grade(answer)->bool}
    Returns {answer, model, escalated, total_usd}
    """
    call = cache.chat if cache else chat

    # Step 1: cheap model
    r1 = call(CHEAP_MODEL, [{"role": "user", "content": item["prompt"]}],
              max_tokens=512, temperature=0.0)
    answer = r1["text"]
    total_usd = r1["usd"]

    if run_tests(answer, item["grade"]):
        return {"answer": answer, "model": CHEAP_MODEL, "escalated": False, "total_usd": total_usd}

    # Step 2: escalate to strong with repair prompt
    for attempt in range(MAX_REPAIRS):
        repair = repair_prompt(item["prompt"], answer)
        r2 = call(STRONG_MODEL, [{"role": "user", "content": repair}],
                  max_tokens=512, temperature=0.0)
        answer = r2["text"]
        total_usd += r2["usd"]
        if run_tests(answer, item["grade"]):
            return {"answer": answer, "model": STRONG_MODEL, "escalated": True, "total_usd": total_usd}

    return {"answer": answer, "model": STRONG_MODEL, "escalated": True, "total_usd": total_usd}
```

---

## Code: self-confidence gate (ILLUSTRATIVE — confirmed non-discriminative for hard math)

```python
"""
Self-confidence gate — FOR ILLUSTRATION ONLY.
CONFIRMED FAILURE on hard-math workload: gpt-4o-mini returns conf=0.9 for ALL six
wrong hard-math answers at every threshold (0.1–0.9). This gate is non-discriminative
for the items that most need escalation. (L3a; 2026-06-21)
"""

CONFIDENCE_PROMPT = (
    "Rate your confidence in your previous answer on a scale 0.0 to 1.0. "
    "Reply with only a number between 0.0 and 1.0."
)


def confidence_gate(answer: str, context: list, model: str, cache=None, threshold: float = 0.5) -> bool:
    """
    Returns True if the answer should be ACCEPTED (no escalation needed).
    WARNING: this fails on overconfident-and-wrong cheap models.
    """
    call = cache.chat if cache else chat
    probe = context + [
        {"role": "assistant", "content": answer},
        {"role": "user", "content": CONFIDENCE_PROMPT},
    ]
    r = call(model, probe, max_tokens=8, temperature=0.0)
    try:
        conf = float(r["text"].strip())
    except ValueError:
        conf = 0.0
    return conf >= threshold
```

---

## Key rule

> The verifier must be more reliable than the generator. Self-confidence fails when the
> cheap model is overconfident-and-wrong. Use code test execution, a trained classifier,
> or a second independent judge model.

## Sources

- `03-pocs/L3a-frugalgpt-cascade/source/run_l3a.py`
- `03-pocs/L3b-harness-routing-coding-agent/source/run_l3b.py`
