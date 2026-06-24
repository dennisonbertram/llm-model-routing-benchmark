"""X1 behavioral tests. Label: Live behavioral test.

RED (no keys / harness): ImportError or ProviderError.
GREEN (with keys + harness): all assertions pass against real APIs.

Tests assert the core MoA invariants:
  1. MoA makes real API calls to N proposers + 1 aggregator.
  2. MoA costs more than a single cheap model call per item.
  3. The aggregated answer is non-empty and graded correctly (at least on easy items).
"""
import os
import sys
import unittest

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

import config
import tasks
from cache import Cache
import judge
from router_base import FixedModel, _budget

HERE = os.path.dirname(__file__)
CACHE_PATH = os.path.join(HERE, ".cache.json")


class X1Tests(unittest.TestCase):

    def test_moa_aggregator_returns_text(self):
        """aggregate_moa makes a real call and returns non-empty text."""
        cache = Cache(CACHE_PATH)
        question = "What is 2 + 2? Reply with just the number."
        proposals = ["4", "four", "The answer is 4"]
        result = judge.aggregate_moa(question, proposals, model=config.MID_DEFAULT, cache=cache)
        self.assertIn("text", result)
        self.assertTrue(result["text"].strip(), "aggregator returned empty text")
        self.assertGreater(result["usd"], 0.0, "aggregator cost not measured")
        cache.save()

    def test_moa_costs_more_than_single_cheap(self):
        """MoA (3 proposals + 1 agg) costs more than a single cheap call."""
        cache = Cache(CACHE_PATH)

        # Get a sample easy math item
        item = next(t for t in tasks.ALL if t["id"] == "m1")

        # Single cheap call cost
        cheap_r = cache.chat(config.CHEAP_DEFAULT,
                              [{"role": "user", "content": item["prompt"]}],
                              max_tokens=_budget(item))
        single_cheap_usd = cheap_r["usd"]

        # MoA cost: 3 proposals + 1 aggregator
        proposals = []
        moa_usd = 0.0
        for model in config.ENSEMBLE_CHEAP:
            r = cache.chat(model, [{"role": "user", "content": item["prompt"]}],
                           max_tokens=_budget(item))
            proposals.append(r["text"])
            moa_usd += r["usd"]

        agg_r = judge.aggregate_moa(item["prompt"], proposals, model=config.MID_DEFAULT,
                                     cache=cache)
        moa_usd += agg_r["usd"]

        self.assertGreater(moa_usd, single_cheap_usd * 1.5,
                           f"MoA ${moa_usd:.2e} should be much more than single cheap ${single_cheap_usd:.2e}")
        cache.save()

    def test_moa_grades_easy_item_correctly(self):
        """MoA should get simple factual questions right (e.g. m1: 17+25=42)."""
        cache = Cache(CACHE_PATH)

        item = next(t for t in tasks.ALL if t["id"] == "m1")  # 17+25=42

        proposals = []
        for model in config.ENSEMBLE_CHEAP:
            r = cache.chat(model, [{"role": "user", "content": item["prompt"]}],
                           max_tokens=_budget(item))
            proposals.append(r["text"])

        agg_r = judge.aggregate_moa(item["prompt"], proposals, model=config.MID_DEFAULT,
                                     cache=cache)
        correct = bool(item["grade"](agg_r["text"]))
        self.assertTrue(correct, f"MoA got easy item m1 wrong: {agg_r['text']!r}")
        cache.save()


if __name__ == "__main__":
    unittest.main(verbosity=2)
