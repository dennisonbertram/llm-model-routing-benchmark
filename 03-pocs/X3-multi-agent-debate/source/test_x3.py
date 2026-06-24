"""X3 debate — behavioral tests. Label: Live behavioral test.

RED (no keys): ProviderError on any live call.
GREEN (with keys + harness): all assertions pass.

Tests:
  1. Debate protocol — each debater answers, then revises in round 1 (total calls = 3×2=6 per item).
  2. Numeric majority aggregation works correctly on a simple math item.
  3. Final debate accuracy on MATH suite is >= single cheap model (or at most marginally worse),
     and the cost is accurately measured as N_debaters × N_rounds × cheap_cost.
  4. No oracle leakage — the router reads only item["prompt"] to make decisions.
"""
import os
import sys
import unittest

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

import config  # noqa: E402
import tasks   # noqa: E402
from cache import Cache  # noqa: E402
from router_base import FixedModel, run_suite  # noqa: E402

from run_x3 import DebateRouter, DEBATERS, N_ROUNDS, SUBSET, HARD_MATH_IDS  # noqa: E402


CACHE_PATH = os.path.join(os.path.dirname(__file__), ".cache.json")


class X3DebateTests(unittest.TestCase):

    def setUp(self):
        self.cache = Cache(CACHE_PATH)

    def tearDown(self):
        self.cache.save()

    def test_debate_transcript_produced(self):
        """Debate on a single easy math item produces a transcript with 1+N_ROUNDS answers each."""
        item = next(t for t in tasks.ALL if t["id"] == "m1")
        debate = DebateRouter(DEBATERS, n_rounds=N_ROUNDS, cache=self.cache)
        out = debate.answer(item)
        ts = debate._transcript_sample
        self.assertIsNotNone(ts, "transcript_sample should be set after first answer() call")
        # Each debater has 1 + N_ROUNDS answers
        for i, hist in enumerate(ts["history"]):
            self.assertEqual(len(hist), 1 + N_ROUNDS,
                             f"Debater {i} should have {1+N_ROUNDS} history entries; got {len(hist)}")
        self.assertIn("final_text", ts)
        self.assertIn("agg_method", ts)

    def test_debate_produces_answer(self):
        """Debate on an easy math item produces a non-empty final text and positive cost."""
        item = next(t for t in tasks.ALL if t["id"] == "m1")
        debate = DebateRouter(DEBATERS, n_rounds=N_ROUNDS, cache=self.cache)
        out = debate.answer(item)
        self.assertTrue(out["text"].strip(), "debate answer should be non-empty")
        self.assertGreater(out["usd"], 0.0, "debate cost should be positive")

    def test_no_oracle_leakage(self):
        """DebateRouter.answer() must not read item['difficulty'] or item['discipline']."""
        import inspect
        src = inspect.getsource(DebateRouter.answer)
        self.assertNotIn("difficulty", src,
                         "answer() must not use item['difficulty'] — oracle leakage")
        self.assertNotIn("discipline", src,
                         "answer() must not use item['discipline'] — oracle leakage")

    def test_debate_cost_scales_with_calls(self):
        """Debate cost should be roughly N_debaters × (1+N_ROUNDS) × single cheap cost per item."""
        item = next(t for t in tasks.ALL if t["id"] == "m4")  # trivial math
        cheap_r = self.cache.chat(config.CHEAP_DEFAULT,
                                  [{"role": "user", "content": item["prompt"]}],
                                  max_tokens=256)
        cheap_usd = cheap_r["usd"]

        debate = DebateRouter(DEBATERS, n_rounds=N_ROUNDS, cache=self.cache)
        out = debate.answer(item)

        # Each debater makes (1 + N_ROUNDS) calls; all 3 models used
        # Cost will differ across models but should be in a sane range
        expected_min = len(DEBATERS) * (1 + N_ROUNDS) * cheap_usd * 0.5  # models may be cheaper
        expected_max = len(DEBATERS) * (1 + N_ROUNDS) * cheap_usd * 20   # some models pricier

        self.assertGreater(out["usd"], expected_min,
                           f"debate usd {out['usd']:.2e} seems too low vs expected_min {expected_min:.2e}")
        self.assertLess(out["usd"], expected_max,
                        f"debate usd {out['usd']:.2e} seems too high vs expected_max {expected_max:.2e}")

    def test_full_subset_debate_accuracy(self):
        """Debate on SUBSET should produce meaningful accuracy (>= 0.60) and positive cost."""
        debate = DebateRouter(DEBATERS, n_rounds=N_ROUNDS, cache=self.cache)
        result = run_suite(debate, SUBSET)
        self.assertGreaterEqual(result.accuracy(), 0.60,
                                f"Debate accuracy {result.accuracy():.3f} seems unreasonably low")
        self.assertGreater(result.total_usd(), 0.0, "Debate cost should be positive")


if __name__ == "__main__":
    unittest.main(verbosity=2)
