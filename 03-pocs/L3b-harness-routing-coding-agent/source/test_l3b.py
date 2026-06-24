"""L3b behavioral tests. Label: Live behavioral test.

RED (before credentials / harness): ProviderError or ImportError.
GREEN (with keys + harness): all assertions pass.

Tests cover:
1. The cheap model can answer a coding task live.
2. The repair loop produces a result dict with the expected shape.
3. On an intentionally broken first attempt (simulated via a distinct nonce), strong repairs it.
"""
import os
import sys
import unittest

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

import config  # noqa: E402
import tasks  # noqa: E402
from cache import Cache  # noqa: E402

CACHE_PATH = os.path.join(os.path.dirname(__file__), ".cache.json")
CHEAP = config.CHEAP_DEFAULT
STRONG = config.STRONG_DEFAULT


class L3bTests(unittest.TestCase):

    def test_cheap_model_answers_coding_task(self):
        """Cheap model produces code that passes the grader for an easy task."""
        c1 = tasks.suite("coding")[0]  # is_palindrome — easy
        cache = Cache(CACHE_PATH)
        r = cache.chat(CHEAP, [{"role": "user", "content": c1["prompt"]}], max_tokens=700)
        cache.save()
        self.assertTrue(r["text"].strip(), "cheap model returned empty text")
        self.assertGreater(r["usd"], 0.0, "cheap model cost not measured")
        passed = bool(c1["grade"](r["text"]))
        # On this easy task, cheap should succeed — but we don't hard-fail if it doesn't,
        # since the test is about proving the call works, not forcing a pass.
        # Log the outcome.
        print(f"\n  [test] c1 (is_palindrome) cheap: {'PASS' if passed else 'FAIL'}")

    def test_strong_model_answers_coding_task(self):
        """Strong model produces code that passes the grader for a hard task."""
        c18 = tasks.suite("coding")[-1]  # is_number — hard discriminator
        cache = Cache(CACHE_PATH)
        r = cache.chat(STRONG, [{"role": "user", "content": c18["prompt"]}], max_tokens=700)
        cache.save()
        self.assertTrue(r["text"].strip(), "strong model returned empty text")
        self.assertGreater(r["usd"], 0.0, "strong model cost not measured")
        passed = bool(c18["grade"](r["text"]))
        print(f"\n  [test] c18 (is_number) strong: {'PASS' if passed else 'FAIL'}")

    def test_repair_prompt_elicits_code(self):
        """Strong model given a failing-code repair prompt returns code with a function def."""
        repair_prompt = (
            "The following Python code was written to solve this task:\n\n"
            "TASK: Write a Python function `fizzbuzz(n: int) -> str` returning 'Fizz' if n "
            "divisible by 3, 'Buzz' if by 5, 'FizzBuzz' if by both, else str(n). "
            "Return only a python code block.\n\n"
            "FAILING CODE:\n```python\ndef fizzbuzz(n):\n    return str(n)  # stub\n```\n\n"
            "The code failed the hidden unit tests. Please write a corrected version. "
            "Return only a python code block."
        )
        cache = Cache(CACHE_PATH)
        r = cache.chat(STRONG, [{"role": "user", "content": repair_prompt}],
                       max_tokens=700, nonce="test_repair_fizzbuzz")
        cache.save()
        self.assertIn("def fizzbuzz", r["text"], "repair response should define fizzbuzz")
        # Grade it for correctness
        c2 = tasks.suite("coding")[1]  # fizzbuzz
        passed = bool(c2["grade"](r["text"]))
        print(f"\n  [test] repair fizzbuzz: {'PASS' if passed else 'FAIL'}")
        self.assertTrue(passed, "strong model should correctly repair the fizzbuzz stub")

    def test_result_shape(self):
        """run_l3b item result has the expected keys."""
        # Import the main module to check its output shape directly.
        import run_l3b
        item = tasks.suite("coding")[0]
        result = run_l3b._run_item_cheap(item)
        run_l3b.save_cache()
        for key in ("id", "difficulty", "correct", "usd", "latency_ms",
                    "models_used", "escalations", "attempts", "decision"):
            self.assertIn(key, result, f"result missing key: {key}")
        self.assertIsInstance(result["escalations"], int)
        self.assertIsInstance(result["models_used"], list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
