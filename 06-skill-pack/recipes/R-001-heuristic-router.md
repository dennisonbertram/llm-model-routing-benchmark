# Recipe R-001: Heuristic Router

Live verified (L1; 2026-06-21). Copy-paste starting point for a prompt-scoring
rule-based router. No embeddings, no training, no API calls to route.

Back to [index](../index.md).

---

## When to use

- No labeled data or embedding budget.
- Workload has strong structural text signals (math word problems vs. factual QA).
- Acceptable to accept ~4–5pp accuracy gap vs a trained classifier.

---

## Live results on 45-task suite

Live verified. thr=0.40: acc=0.956, $0.00902, 42% of strong cost. (L1)
See [reference/pareto-numbers.md](../reference/pareto-numbers.md) for full comparison.

---

## Code

```python
"""
Heuristic router — route prompts by text complexity score.
Live verified: thr=0.40 → acc=0.956, $0.00902 on 45-task suite (L1; 2026-06-21).
"""
import re

CHEAP_MODEL  = "gpt-4o-mini"
STRONG_MODEL = "gpt-4.1"

REASONING_CUES = [
    "how many", "in how many", "permutations", "combinations", "arrangements",
    "distinct", "divisible", "probability", "factorial", "consecutive",
    "proof", "derive", "integral", "recursion", "algorithm",
]

def complexity_score(prompt: str) -> float:
    """Score 0–1. Higher = more likely to need strong model."""
    words     = prompt.split()
    n_words   = len(words)
    n_digits  = sum(1 for c in prompt if c.isdigit())
    cue_count = sum(1 for cue in REASONING_CUES if cue in prompt.lower())
    clause_count = prompt.count(",") + prompt.count(";") + prompt.count(" and ")

    word_score  = min((n_words - 15) / 25.0, 1.0) if n_words > 15 else 0.0
    cue_score   = min(cue_count / 3.0, 1.0)
    clause_score = min(clause_count / 5.0, 1.0)
    digit_score = min((n_digits / max(len(prompt), 1)) * 5, 1.0)

    return (
        0.40 * word_score +
        0.35 * cue_score +
        0.15 * clause_score +
        0.10 * digit_score
    )


def route(prompt: str, threshold: float = 0.40) -> str:
    """Return the model ID to use for this prompt."""
    score = complexity_score(prompt)
    return STRONG_MODEL if score >= threshold else CHEAP_MODEL


# --- Threshold sweep (for calibration) ---

def threshold_sweep(items, threshold_range=(0.20, 0.70, 0.10)):
    """
    items: list of {prompt, grade(answer)->bool, gold} from harness tasks.py
    Prints a cost-vs-accuracy table. Re-uses the L0 labelset cache — no re-billing.
    """
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
    from cache import Cache
    from metrics import format_table

    cache = Cache(os.path.join(os.path.dirname(__file__), "..", "..", "harness", ".cache"))
    start, stop, step = threshold_range
    thresholds = [round(start + step * i, 2) for i in range(int((stop - start) / step) + 1)]

    rows = []
    for thr in thresholds:
        correct = total_usd = 0
        for item in items:
            model = route(item["prompt"], threshold=thr)
            result = cache.chat(model, [{"role": "user", "content": item["prompt"]}],
                                max_tokens=256, temperature=0.0)
            correct += int(item["grade"](result["text"]))
            total_usd += result["usd"]
        acc = correct / len(items)
        rows.append({"label": f"heuristic(thr={thr})", "accuracy": acc, "total_usd": total_usd})

    print(format_table(rows))


if __name__ == "__main__":
    # Quick smoke — no suite needed
    tests = [
        ("What is 2+2?", 0.40, CHEAP_MODEL),
        ("In how many ways can 6 people sit in a row of 6 chairs?", 0.40, STRONG_MODEL),
    ]
    for prompt, thr, expected in tests:
        got = route(prompt, threshold=thr)
        status = "OK" if got == expected else "FAIL"
        print(f"{status}  score={complexity_score(prompt):.3f}  routed={got}  expected={expected}")
```

---

## Notes

- Adjust `REASONING_CUES` for your workload's signal vocabulary.
- The 0.40/0.35/0.15/0.10 feature weights were tuned on this 45-task suite; re-tune for yours.
- Do NOT present the threshold-0.20 result as oracle-efficient — it routes 22 items to strong
  and costs $0.02002, close to always-strong.

## Source

`03-pocs/L1-heuristic-router/source/run_l1.py`
