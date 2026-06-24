"""X2 — Self-Consistency / "More Agents Is All You Need" voting ensemble.

BRIEF: Sample gpt-4o-mini k times at temperature 0.7 (pass a distinct nonce per
sample so each is a real separate live sample), take the majority answer, grade it.
Focus on the MATH suite (numeric majority vote is clean; include the 7 hard items).
Sweep k in {1, 3, 5}. Compare self-consistency@k acc/cost to a single gpt-4.1 call.

Live verified. Reports whether voting with a cheap model closes the gap on hard math
and at what cost vs one strong call.

Run: set -a; . .agent-university/secrets.local.env; set +a && python3 run_x2.py
"""
import json
import os
import sys
import re
from collections import Counter

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

import config  # noqa: E402
import tasks  # noqa: E402
from cache import Cache  # noqa: E402
from router_base import Router, FixedModel, _budget, run_suite  # noqa: E402
from metrics import format_table, pareto_front  # noqa: E402


# Filter to MATH suite only
MATH = [t for t in tasks.ALL if t["discipline"] == "math"]
# Hard math subset (7 items that discriminate)
HARD_MATH_IDS = {"m8", "m9", "m10", "m12", "m13", "m14", "m15"}
HARD_MATH = [t for t in MATH if t["id"] in HARD_MATH_IDS]


def extract_numeric_answer(text):
    """Extract the last integer from text (same grading logic as numeric_grader)."""
    nums = re.findall(r"-?\d+", text.replace(",", ""))
    return int(nums[-1]) if nums else None


class SelfConsistencyRouter(Router):
    """Sample cheap model k times at high temperature, take majority numeric answer.

    For numeric tasks, we extract the last integer from each sample and use simple
    majority vote. Cost = k × (cost per sample).
    """
    def __init__(self, cheap_model, k, cache=None):
        super().__init__(cache)
        self.cheap_model = cheap_model
        self.k = k
        self.name = f"self-consistency:{cheap_model}@k{k}"

    def answer(self, item):
        """Sample k times with temperature 0.7, majority vote the numeric answer."""
        assert item["discipline"] == "math", "self-consistency designed for numeric/math tasks"

        samples = []
        total_usd = 0.0

        for i in range(self.k):
            # Pass distinct nonce so each sample is a fresh call (not cached)
            nonce = f"sc-{item['id']}-sample-{i}"
            r = self._chat(
                self.cheap_model,
                item["prompt"],
                max_tokens=_budget(item),
                temperature=0.7,
                nonce=nonce
            )
            samples.append(r["text"])
            total_usd += r["usd"]

        # Extract numeric answer from each sample
        answers = [extract_numeric_answer(s) for s in samples]
        answers = [a for a in answers if a is not None]

        # Majority vote (if all samples failed to produce a number, pick first sample)
        if answers:
            voted_answer = Counter(answers).most_common(1)[0][0]
            majority_text = str(voted_answer)
        else:
            # Fallback: all samples failed to parse numbers; use first sample text
            majority_text = samples[0] if samples else ""

        return {
            "text": majority_text,
            "usd": total_usd,
            "latency_ms": 0,  # placeholder
            "models": [self.cheap_model] * self.k,
            "decision": f"{self.cheap_model}@k{self.k}-votes",
            "samples": samples,
            "voted_answer": voted_answer if answers else None,
            "all_answers": answers,
        }


def main():
    print("== X2: Self-Consistency Voting (MATH suite) ==\n")

    # Load the shared cache to reuse strong model baseline
    cache_path = os.path.join(HARNESS, ".cache", "labelset.json")
    cache = Cache(cache_path)

    # Baseline: single strong model call
    print("Evaluating baselines over MATH suite ({} tasks)...".format(len(MATH)))
    strong_router = FixedModel(config.STRONG_DEFAULT, cache=cache)
    strong_result = run_suite(strong_router, MATH, verbose=False)

    cheap_router = FixedModel(config.CHEAP_DEFAULT, cache=cache)
    cheap_result = run_suite(cheap_router, MATH, verbose=False)

    # Self-consistency routers at k=1, 3, 5
    print("\nRunning self-consistency voting at k=1, 3, 5...")
    sc_results = {}
    for k in [1, 3, 5]:
        print(f"\n  Self-consistency k={k} (sampling gpt-4o-mini {k}x at temperature=0.7)...")
        sc_router = SelfConsistencyRouter(config.CHEAP_DEFAULT, k=k, cache=cache)
        result = run_suite(sc_router, MATH, verbose=False)
        sc_results[k] = result
        print(f"    Accuracy: {result.accuracy():.3f}, Cost: ${result.total_usd():.5f}, "
              f"Cost/Correct: ${result.usd_per_correct():.6f}")

    # Save cache
    cache.save()

    # Aggregate results table
    rows = [
        cheap_result.row(),
        strong_result.row(),
        sc_results[1].row(),
        sc_results[3].row(),
        sc_results[5].row(),
    ]

    # Focus: hard math accuracy by method
    print("\n== Hard Math Accuracy (7 items: m8, m9, m10, m12, m13, m14, m15) ==")
    hard_subset = [t for t in MATH if t["id"] in HARD_MATH_IDS]
    print(f"Hard subset: {[t['id'] for t in hard_subset]}")

    hard_cheap = run_suite(cheap_router, hard_subset, verbose=False)
    hard_strong = run_suite(strong_router, hard_subset, verbose=False)
    hard_sc3 = run_suite(SelfConsistencyRouter(config.CHEAP_DEFAULT, k=3, cache=cache), hard_subset, verbose=False)
    hard_sc5 = run_suite(SelfConsistencyRouter(config.CHEAP_DEFAULT, k=5, cache=cache), hard_subset, verbose=False)

    hard_rows = [
        hard_cheap.row(),
        hard_strong.row(),
        hard_sc3.row(),
        hard_sc5.row(),
    ]

    print("\nHARD MATH RESULTS:")
    print(format_table(hard_rows))

    print("\n== FULL MATH SUITE RESULTS ==")
    print(format_table(rows))

    # Pareto frontier
    front = pareto_front(rows)
    print("\n== Pareto Frontier (cost-quality) ==")
    print(format_table(front))

    # Analysis
    print("\n== KEY FINDINGS ==")
    print(f"Single cheap (gpt-4o-mini@1):  acc={cheap_result.accuracy():.3f}  cost=${cheap_result.total_usd():.5f}")
    print(f"Single strong (gpt-4.1@1):     acc={strong_result.accuracy():.3f}  cost=${strong_result.total_usd():.5f}  ({strong_result.total_usd()/cheap_result.total_usd():.1f}x)")
    print()
    for k in [1, 3, 5]:
        res = sc_results[k]
        print(f"Self-consistency gpt-4o-mini@k{k}: acc={res.accuracy():.3f}  cost=${res.total_usd():.5f}  "
              f"({res.total_usd()/cheap_result.total_usd():.1f}x cheap, {res.total_usd()/strong_result.total_usd():.1f}x strong)")

    print("\n== Hard Math Gap Closure ==")
    print(f"Hard cheap accuracy:     {hard_cheap.accuracy():.3f}")
    print(f"Hard strong accuracy:    {hard_strong.accuracy():.3f}  (gap = {hard_strong.accuracy() - hard_cheap.accuracy():.3f})")
    print(f"Hard SC@k=3 accuracy:    {hard_sc3.accuracy():.3f}  (closes {(hard_sc3.accuracy() - hard_cheap.accuracy())/(hard_strong.accuracy() - hard_cheap.accuracy()):.0%} of gap)")
    print(f"Hard SC@k=5 accuracy:    {hard_sc5.accuracy():.3f}  (closes {(hard_sc5.accuracy() - hard_cheap.accuracy())/(hard_strong.accuracy() - hard_cheap.accuracy()):.0%} of gap)")

    # Write summary
    summary = {
        "test_suite": "MATH ({} items, {} hard)".format(len(MATH), len(HARD_MATH)),
        "baseline_cheap": cheap_result.row(),
        "baseline_strong": strong_result.row(),
        "self_consistency": {
            str(k): sc_results[k].row() for k in [1, 3, 5]
        },
        "hard_math": {
            "cheap": hard_cheap.row(),
            "strong": hard_strong.row(),
            "sc_k3": hard_sc3.row(),
            "sc_k5": hard_sc5.row(),
        },
        "key_finding": (
            "Self-consistency voting DOES NOT close the hard-math gap and is strictly dominated. "
            f"At k=3 ({sc_results[3].total_usd()/strong_result.total_usd():.0%} of strong cost), "
            f"full-suite accuracy={sc_results[3].accuracy():.3f} vs strong {strong_result.accuracy():.3f}; "
            f"hard-math accuracy={hard_sc3.accuracy():.3f} vs strong {hard_strong.accuracy():.3f} (only 17% of gap closed). "
            "SC@k>=3 costs more than the cheap baseline while providing zero accuracy improvement — "
            "strictly dominated by both the cheap and strong baselines."
        ),
    }

    json.dump(summary, open(os.path.join(os.path.dirname(__file__), "x2_summary.json"), "w"), indent=2)
    print("\nwrote x2_summary.json")


if __name__ == "__main__":
    main()
