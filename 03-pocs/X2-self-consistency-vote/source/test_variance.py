"""Test if gpt-4o-mini produces variance at temperature 0.7 on a hard math item.

This is the honest test: do we get diverse answers or all the same wrong answer?
"""
import os
import sys
import re
from collections import Counter

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

import config  # noqa: E402
import tasks  # noqa: E402
from cache import Cache  # noqa: E402
from router_base import _budget  # noqa: E402
from providers import chat


def extract_numeric_answer(text):
    """Extract the last integer from text."""
    nums = re.findall(r"-?\d+", text.replace(",", ""))
    return int(nums[-1]) if nums else None


# Use a local cache just for this test (not the shared labelset)
cache = Cache(os.path.join(os.path.dirname(__file__), ".cache_variance.json"))

MATH = [t for t in tasks.ALL if t["discipline"] == "math"]
HARD_MATH_IDS = {"m8", "m9", "m10", "m12", "m13", "m14", "m15"}

# Test on two hard items
test_items = [t for t in MATH if t["id"] in ["m9", "m13"]]

for item in test_items:
    print(f"\n{item['id']}: {item['prompt']}")
    print(f"Gold: {item['gold']}")
    print("Samples at temperature 0.7:")

    answers = []
    for i in range(5):
        # Use nocache=True to force fresh API calls
        r = chat(
            "gpt-4o-mini",
            [{"role": "user", "content": item["prompt"]}],
            max_tokens=_budget(item),
            temperature=0.7,
        )
        answer = extract_numeric_answer(r["text"])
        answers.append(answer)
        print(f"  Sample {i}: {r['text']!r:40} -> {answer}  (cost ${r['usd']:.2e})")

    vote = Counter(answers).most_common(1)[0][0] if answers else None
    print(f"Majority vote: {vote}, Correct: {vote == item['gold']}")
