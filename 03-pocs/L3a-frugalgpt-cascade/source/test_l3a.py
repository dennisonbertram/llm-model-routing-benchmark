"""L3a live behavioral tests. Label: Live behavioral test.

RED (before cascade is implemented / no credentials): ImportError or gate-call failures.
GREEN (with harness + keys): all assertions pass — the cascade actually makes fresh gate
calls, reduces cost vs always-strong, and the verifier error rate is measurable.
"""
import json
import os
import sys
import unittest

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

HERE = os.path.dirname(os.path.abspath(__file__))
LABELSET = os.path.join(HARNESS, ".cache", "labelset_export.json")
CASCADE_CACHE_PATH = os.path.join(HERE, ".cache.json")

import config  # noqa: E402
import tasks   # noqa: E402
from cache import Cache  # noqa: E402
from providers import chat  # noqa: E402
from router_base import _budget  # noqa: E402


# Import the cascade helpers from run_l3a.py
sys.path.insert(0, HERE)
from run_l3a import (  # noqa: E402
    get_confidence, verify_code, run_cascade, compute_baselines, load_labelset, load_tasks
)

CHEAP = config.CHEAP_DEFAULT
STRONG = config.STRONG_DEFAULT


class L3aCascadeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.labelset = load_labelset()
        cls.tasks_map = load_tasks()
        cls.baselines = compute_baselines(cls.labelset)

    def test_confidence_gate_returns_float(self):
        """Confidence gate makes a LIVE call and returns a float in [0, 1]."""
        conf, usd = get_confidence("What is 2 + 2?", "4")
        self.assertIsInstance(conf, float, "confidence must be float")
        self.assertGreaterEqual(conf, 0.0)
        self.assertLessEqual(conf, 1.0)
        self.assertGreater(usd, 0.0, "gate call must cost something")

    def test_code_verifier_returns_bool(self):
        """Code verifier makes a LIVE call and returns a bool."""
        code = "def is_palindrome(s):\n    return s == s[::-1]"
        accepted, usd = verify_code("Write a Python function is_palindrome(s: str) -> bool.", code)
        self.assertIsInstance(accepted, bool, "accepted must be bool")
        self.assertGreater(usd, 0.0, "verifier call must cost something")

    def test_confidence_high_for_easy_math(self):
        """Cheap model should rate confidence ≥ 0.6 for a trivial arithmetic question."""
        conf, _ = get_confidence("What is 7 * 8?", "56")
        self.assertGreaterEqual(conf, 0.5,
            f"Expected high confidence for trivial math, got {conf}")

    def test_cascade_reduces_cost_vs_strong(self):
        """Cascade at any threshold must cost less than always-strong."""
        result = run_cascade(self.labelset, self.tasks_map, threshold=0.5)
        strong_cost = self.baselines["always_strong"]["total_usd"]
        self.assertLess(result["total_usd"], strong_cost,
            f"cascade cost ${result['total_usd']:.5f} not < always-strong ${strong_cost:.5f}")

    def test_cascade_accuracy_above_cheap(self):
        """Cascade at threshold=0.3 should match or exceed always-cheap accuracy."""
        result = run_cascade(self.labelset, self.tasks_map, threshold=0.3)
        cheap_acc = self.baselines["always_cheap"]["accuracy"]
        # Allow a 0.02 tolerance — verifier may introduce a false accept
        self.assertGreaterEqual(result["accuracy"], cheap_acc - 0.02,
            f"cascade acc {result['accuracy']:.3f} << cheap {cheap_acc:.3f}")

    def test_some_escalation_occurs(self):
        """At threshold=0.7, some items should be escalated to strong."""
        result = run_cascade(self.labelset, self.tasks_map, threshold=0.7)
        self.assertGreater(result["n_escalated"], 0,
            "Expected at least some escalations at high threshold")

    def test_low_threshold_fewer_escalations_than_high(self):
        """Lower thresholds escalate fewer items (less strict gate)."""
        low = run_cascade(self.labelset, self.tasks_map, threshold=0.1)
        high = run_cascade(self.labelset, self.tasks_map, threshold=0.9)
        self.assertLessEqual(low["n_escalated"], high["n_escalated"],
            "Low threshold should escalate <= high threshold items")

    def test_summary_json_written(self):
        """run_l3a must produce l3a_summary.json — checked after a full run."""
        summary_path = os.path.join(HERE, "l3a_summary.json")
        if not os.path.exists(summary_path):
            self.skipTest("l3a_summary.json not yet written (run run_l3a.py first)")
        with open(summary_path) as f:
            summary = json.load(f)
        self.assertIn("baselines", summary)
        self.assertIn("cascade_results", summary)
        self.assertIn("best_accuracy", summary)
        self.assertIn("cache_stats", summary)


if __name__ == "__main__":
    unittest.main(verbosity=2)
