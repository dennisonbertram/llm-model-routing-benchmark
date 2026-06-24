"""Debug script: inspect actual samples and voting behavior on a subset."""
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
from router_base import _budget  # noqa: E402


def extract_numeric_answer(text):
    """Extract the last integer from text."""
    nums = re.findall(r"-?\d+", text.replace(",", ""))
    return int(nums[-1]) if nums else None


MATH = [t for t in tasks.ALL if t["discipline"] == "math"]
HARD_MATH_IDS = {"m8", "m9", "m10", "m12", "m13", "m14", "m15"}

# Focus on one hard example: m9 (divisible by 3 or 5)
m9 = next(t for t in MATH if t["id"] == "m9")

print(f"Item: {m9['id']} (hard math)")
print(f"Prompt: {m9['prompt']}")
print(f"Gold answer: {m9['gold']}")
print()

cache = Cache(os.path.join(HARNESS, ".cache", "labelset.json"))

from providers import chat

# Sample 5 times at temperature 0.7
print("Sampling gpt-4o-mini 5 times at temperature 0.7:")
for i in range(5):
    nonce = f"debug-m9-sample-{i}"
    r = cache.chat(
        "gpt-4o-mini",
        [{"role": "user", "content": m9["prompt"]}],
        max_tokens=_budget(m9),
        temperature=0.7,
        nonce=nonce
    )
    answer = extract_numeric_answer(r["text"])
    print(f"  Sample {i}: text={r['text']!r:50} -> numeric={answer}")

cache.save()

# Also sample a couple more items
print("\nItem: m12 (hard math)")
m12 = next(t for t in MATH if t["id"] == "m12")
print(f"Prompt: {m12['prompt']}")
print(f"Gold answer: {m12['gold']}")
for i in range(3):
    nonce = f"debug-m12-sample-{i}"
    r = cache.chat(
        "gpt-4o-mini",
        [{"role": "user", "content": m12["prompt"]}],
        max_tokens=_budget(m12),
        temperature=0.7,
        nonce=nonce
    )
    answer = extract_numeric_answer(r["text"])
    print(f"  Sample {i}: text={r['text']!r:50} -> numeric={answer}")

cache.save()
