# R-005: opencode-Style Harness Routing (Escalate-on-Failure)

**Category**: recipe
**Evidence tier**: Live verified (POC L3b)
**Source POC**: L3b-harness-routing-coding-agent

## Live verified

An opencode-style coding harness that starts with the cheap model and escalates to the strong
model only when the cheap model's output fails unit tests:

- All-cheap (`gpt-4o-mini`): **acc 1.000, $0.00148**
- All-strong (`gpt-4.1`): **acc 1.000, $0.01967** (13.25× more)
- **Routed (cheap-first, escalate-on-failure): acc 1.000, $0.00148 — 13.25× cheaper than
  all-strong** with identical accuracy (L3b)

On the 18 coding tasks: zero escalations were triggered. `gpt-4o-mini` at temperature=0
solved all 18, including hard tasks (sliding window, LIS, coin change, regex matching).
This is a real measurement. The escalation path is proven correct via a synthetic test
(deliberate broken stub → strong model repairs and passes tests). (L3b)

**Key insight**: Canonical LeetCode-style coding problems are **memorized** and saturate
even the cheapest models. The hard tail that needs escalation is in math (m9–m15), not
coding. Discipline matters more than difficulty label. (L0, L3b)

## The loop

```
1. Cheap model writes code
2. Run unit tests (subprocess)
3. Tests pass → accept (cost = 1 cheap call)
4. Tests fail → escalate to strong with repair prompt
   Strong sees: task + failing code (not the hidden test oracles)
   Up to MAX_REPAIRS=2 attempts before accepting last result
```

## Snippet (copy-paste-ready)

```python
import subprocess, textwrap, tempfile, os

def run_code_tests(code: str, test_code: str) -> tuple[bool, str]:
    """Execute code + test_code in a subprocess. Returns (passed, output)."""
    combined = f"{code}\n\n{test_code}"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(combined)
        path = f.name
    try:
        result = subprocess.run(
            ["python3", path],
            capture_output=True, text=True, timeout=10
        )
        passed = result.returncode == 0
        return passed, (result.stdout + result.stderr)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    finally:
        os.unlink(path)

def extract_code_block(text: str) -> str:
    """Pull first ```python ... ``` block, or fall back to raw text."""
    import re
    m = re.search(r"```python\s*(.*?)```", text, re.DOTALL)
    return m.group(1).strip() if m else text.strip()

def harness_route_coding(
    task_prompt: str,
    test_code:   str,          # hidden unit tests to run
    cheap_model:  str = "gpt-4o-mini",
    strong_model: str = "gpt-4.1",
    max_repairs:  int = 2,
    cache=None,
) -> dict:
    """
    opencode-style escalate-on-failure for coding tasks.
    Returns {answer, model_used, escalations, passed, usd}
    """
    call = cache.chat if cache else chat
    total_usd  = 0.0
    escalations = 0

    # Step 1: cheap model attempts the task
    cheap_result = call(cheap_model,
        [{"role": "user", "content": task_prompt}],
        max_tokens=700, temperature=0.0)
    total_usd += cheap_result.usd
    code = extract_code_block(cheap_result.text)

    # Step 2: run tests
    passed, test_out = run_code_tests(code, test_code)
    if passed:
        return {"answer": code, "model_used": cheap_model,
                "escalations": 0, "passed": True, "usd": total_usd}

    # Step 3: escalate to strong for up to max_repairs attempts
    repair_prompt_template = textwrap.dedent("""\
        The following Python code was written to solve this task:
        TASK: {task}
        FAILING CODE:
        ```python
        {code}
        ```
        The code failed the hidden unit tests. Please write a corrected version.
        Return only a python code block.""")

    for attempt in range(max_repairs):
        escalations += 1
        rp = repair_prompt_template.format(task=task_prompt, code=code)
        strong_result = call(strong_model,
            [{"role": "user", "content": rp}],
            max_tokens=700, temperature=0.0)
        total_usd += strong_result.usd
        code = extract_code_block(strong_result.text)
        passed, test_out = run_code_tests(code, test_code)
        if passed:
            break

    return {
        "answer":      code,
        "model_used":  strong_model if escalations > 0 else cheap_model,
        "escalations": escalations,
        "passed":      passed,
        "usd":         total_usd,
    }
```

## When escalation fires (and when it does not)

Live verified findings (L3b):

- **Coding (all 18 tasks)**: zero escalations. LeetCode-style problems are saturated at the
  cheap tier. The strong model is never needed.
- **Hard math (m9–m15 from L0)**: cheap fails; this discipline benefits from predictive
  routing (R-001) not from a repair loop (there is no "test suite" to run math answers against).
- **Escalation path works**: a deliberately broken fizzbuzz stub was fed to the repair loop;
  the strong model repaired it and passed all unit tests (L3b test_repair_prompt_elicits_code).

Scenarios where escalation would fire in production:
- Tight token budget forces the cheap model to truncate its code
- Edge-case-heavy specs where the cheap model's solution misses a corner case
- Non-LeetCode coding tasks (novel algorithmic problems not in training corpora)

## Cost structure

| Strategy    | Accuracy | Cost (18 coding tasks) | vs all-strong |
|-------------|----------|------------------------|---------------|
| all-cheap   | 1.000    | $0.00148               | 7.5%          |
| all-strong  | 1.000    | $0.01967               | 100%          |
| **routed**  | **1.000** | **$0.00148**          | **7.5%**      |

Cost per task: cheap ~$2e-5 (easy) to ~$2e-4 (hard long solutions). Strong ~10–15× more per
output token on complex solutions. (L3b)

## Evidence

- L3b-harness-routing-coding-agent/README.md — full three-harness table, repair loop details
- results-digest.md lines 36–37 — authoritative numbers
