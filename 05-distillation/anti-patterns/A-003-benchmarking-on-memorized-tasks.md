# A-003: Benchmarking on Memorized Tasks — Using Canonical LeetCode/Algorithm Problems to Measure Routing Gain

**Category**: anti-pattern
**Severity**: high — produces a saturated benchmark with no discriminating signal
**Evidence tier**: Live verified
**Source POCs**: L0-smoke-and-harness, L3b-harness-routing-coding-agent

---

## What the anti-pattern looks like

Live verified. Building a routing benchmark from canonical LeetCode-style problems or
well-known algorithm tasks (two-sum, FizzBuzz, binary search, min-window-substring,
edit-distance, LIS, coin change, regex matching) and expecting to see a measurable
accuracy gap between cheap and strong models that a router can exploit.

Measured result in this degree (L0, L3b, 18 coding tasks, 2026-06-21):

| Model | Coding accuracy (18 tasks) |
|---|---|
| `gpt-4o-mini` (cheap) | 18/18 (100%) |
| `gpt-4.1` (strong) | 18/18 (100%) |
| `gpt-4.1-nano` (cheapest) | 18/18 (100%) |

All three models, including the cheapest available, solved every coding task including
the "hard" ones (c8–c18: sliding window, LIS, coin change, regex matching). The routing
gain from routing coding tasks to strong: $0 saved, 0pp accuracy improvement.

L3b confirmed: the opencode-style cheap-first harness triggered 0 escalations across 18
coding tasks. The repair mechanism is real and tested, but it was never needed.

---

## Root cause

Canonical algorithm problems are memorized by modern LLMs. The training corpus for
models from gpt-4o-mini onward contains thousands of solutions to every standard
LeetCode problem. The models retrieve memorized solutions rather than solving from first
principles. This means even the cheapest models produce correct code, making the suite
unable to discriminate model capability.

The routable gap in this degree was entirely in hard **multi-step mathematical reasoning**
(combinatorics, counting, algebra with non-obvious constraints — items m9, m10, m12,
m13, m14, m15). These are not in the standard LeetCode corpus and require genuine
on-the-fly reasoning chains. `gpt-4o-mini` scored 8/15 on math; `gpt-4.1` scored 14/15.
That 6-task gap is where every routing gain in this degree came from.

---

## How to detect a saturated benchmark

Before finalizing a task suite:

1. Run always-cheap and always-strong. If cheap accuracy ≥ 95% on a discipline, that
   discipline is saturated for routing purposes.
2. Measure the oracle gap: `oracle_cost = Σ min(cheap_cost_i, strong_cost_i) where correct`.
   If `oracle_cost ≈ always_cheap_cost`, cheap already solves everything and there is no
   gain to capture.
3. Count how many tasks have `cheap_correct=False AND strong_correct=True`. This is the
   "routeable tail" — the set of tasks where strong adds value. In this degree: 6/45 = 13%.
   If this number is 0–2, routing is not worth building.

---

## Fix

**Live verified** (L0; L3b)

Build tasks that require genuine on-the-fly reasoning, not memorized solutions:

- **Math with novel constraints**: combinatorics ("how many 4-digit numbers where each
  digit differs from the next by exactly 2?"), counting with modular arithmetic, nested
  constraints. Avoid textbook examples.
- **Multi-step word problems**: require decomposing into sub-problems before computing.
- **Spec-edge-case coding**: not the standard algorithm, but a variant with a precise
  constraint the cheap model has not seen before (e.g., the `is_number` task that tripped
  cheap in L0 — parsing a complex floating-point/scientific-notation spec).
- **Domain knowledge under ambiguity**: questions where the cheap model's knowledge cutoff
  or limited depth causes failures that strong corrects.

If you find cheap accuracy ≥ 95% on your suite, your benchmark is measuring retrieval
quality, not reasoning quality. Replace the saturated tasks.

---

## Evidence

- L0 README.md: "Canonical coding problems are saturated even for the cheapest model. `gpt-4.1-nano` solves all 18 coding tasks — including regex matching, min-window-substring, edit-distance — so they do not discriminate model strength." (Live verified)
- L3b README.md: "`gpt-4o-mini` at temperature=0 achieves 100% on all 18 coding tasks — including every 'hard' problem (c8–c18: sliding window, LIS, coin change, regex matching, etc.). Routed harness costs exactly the same as all-cheap. 0 escalations." (Live verified)
- results-digest.md, Gotcha 4: "Canonical LeetCode/algorithm coding tasks are MEMORIZED and saturate even gpt-4.1-nano → they don't discriminate model strength; the routable gap was multi-step combinatorics MATH." (Live verified)
- L0 README.md: "The real gap is in hard reasoning math." (Live verified)
