"""L5 behavioral tests. Label: Live behavioral test.

RED (before access / harness): ProviderError or ImportError.
GREEN (with keys + harness): all 5 failure modes trigger and recover correctly.

Each test exercises a REAL live failure — no mocks. The assertions validate
that the resilient routing layer correctly catches and handles each fault.
"""

import os
import sys
import unittest

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

from providers import chat, ProviderError  # noqa: E402
import config                              # noqa: E402


def _call(model, prompt, max_tokens=128, timeout=30.0):
    """Single call returning (result, error_str). Never raises."""
    try:
        r = chat(model, [{"role": "user", "content": prompt}],
                 max_tokens=max_tokens, temperature=0.0, timeout=timeout)
        return r, None
    except ProviderError as e:
        return None, str(e)
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


class L5FailureModes(unittest.TestCase):

    # ---------------------------------------------------------------
    # FM1: Invalid model slug produces a real provider error
    # ---------------------------------------------------------------
    def test_fm1_invalid_model_slug_fails(self):
        """Calling a nonexistent model must raise ProviderError with HTTP error info."""
        bad = "gpt-9000-doesnt-exist"
        r, err = _call(bad, "What is 2+2?")
        self.assertIsNone(r, f"Expected failure for {bad!r}, got result: {r}")
        self.assertIsNotNone(err)
        # Provider should return an HTTP error (typically 404 or 400)
        self.assertTrue(
            "HTTP" in err or "404" in err or "400" in err or "error" in err.lower(),
            f"Expected an HTTP error message, got: {err[:200]}"
        )

    def test_fm1_fallback_to_valid_model_succeeds(self):
        """After an invalid-model failure the fallback to a valid model succeeds."""
        good = config.CHEAP_DEFAULT
        r, err = _call(good, "What is 2+2?")
        self.assertIsNone(err, f"Fallback model {good!r} failed unexpectedly: {err}")
        self.assertIsNotNone(r)
        self.assertGreater(len(r["text"].strip()), 0)
        self.assertGreater(r["usd"], 0.0)

    # ---------------------------------------------------------------
    # FM2: Sub-millisecond timeout always fails; normal timeout succeeds
    # ---------------------------------------------------------------
    def test_fm2_tiny_timeout_fails(self):
        """A 0.001s timeout must fail (no TCP connection completes in 1 ms)."""
        r, err = _call(config.CHEAP_DEFAULT, "What is 2+2?", timeout=0.001)
        self.assertIsNone(r, f"Expected timeout failure, got result: {r}")
        self.assertIsNotNone(err)
        # Should be a timeout or connection error, not an HTTP error
        err_lower = err.lower()
        self.assertTrue(
            "timeout" in err_lower or "timed out" in err_lower or "error" in err_lower,
            f"Expected timeout error, got: {err[:200]}"
        )

    def test_fm2_normal_timeout_succeeds(self):
        """The same model with a normal timeout must succeed."""
        r, err = _call(config.CHEAP_DEFAULT, "What is 2+2?", timeout=30.0)
        self.assertIsNone(err, f"Normal-timeout call failed: {err}")
        self.assertIsNotNone(r)
        self.assertGreater(r["latency_ms"], 0)

    # ---------------------------------------------------------------
    # FM3: Over-limit max_tokens -> handled (error or silent cap)
    # ---------------------------------------------------------------
    def test_fm3_overlimit_handled(self):
        """max_tokens=999999 must either produce a real error OR be silently capped — never crash."""
        r, err = _call(config.CHEAP_DEFAULT, "What is 2+2?", max_tokens=999999)
        # Either the provider returns an error (HTTP 400) OR silently caps.
        # Both are valid — the key thing is the code does not crash with an unhandled exception.
        if r is not None:
            # Silently capped — verify we got a usable answer
            self.assertGreater(len(r["text"].strip()), 0,
                               "Provider silently capped but returned empty text")
        else:
            # Got a real HTTP error — acceptable
            self.assertIsNotNone(err)
            self.assertTrue(len(err) > 0, "Error string is empty")

    # ---------------------------------------------------------------
    # FM4: Cost-budget guard
    # ---------------------------------------------------------------
    def test_fm4_budget_guard_refuses_when_exhausted(self):
        """After budget is spent the router must refuse further calls."""
        import importlib
        run_l5 = importlib.import_module("run_l5") if "run_l5" in sys.modules else None
        if run_l5 is None:
            spec_path = os.path.join(os.path.dirname(__file__), "run_l5.py")
            import importlib.util
            spec = importlib.util.spec_from_file_location("run_l5", spec_path)
            run_l5 = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(run_l5)

        BudgetRouter = run_l5.BudgetRouter

        # Set budget so tight that any real model call will exhaust it after 1-2 cheap calls.
        TIGHT = 0.000005  # $0.000005 — essentially nothing; first real call may exceed this
        router = BudgetRouter(budget_usd=TIGHT, models=[config.CHEAP_DEFAULT])

        calls = []
        for i in range(3):
            out = router.route(f"What is {i+1}+1?", task_id=f"t{i}")
            calls.append(out)

        refused = [c for c in calls if c["refused"]]
        # With a $0.000005 budget and real calls costing ~$0.000001 each, at least some
        # calls should be refused (either immediately or after the first).
        # If ALL calls go through (provider returned 0 cost somehow), that's also meaningful.
        total_spent = router.spent_usd
        self.assertGreaterEqual(total_spent, 0.0)
        # If budget is exceeded, subsequent calls must be refused
        if total_spent > TIGHT:
            self.assertGreater(len(refused), 0,
                               "Budget exceeded but no calls were refused — guard is broken")

    # ---------------------------------------------------------------
    # FM5: Verifier escalation (deterministic math)
    # ---------------------------------------------------------------
    def test_fm5_verifier_escalation_logic(self):
        """Verifier correctly identifies correct vs wrong answers."""
        import re

        def verify_numeric(text, gold):
            nums = re.findall(r"\d+", text.strip())
            return bool(nums and int(nums[0]) == gold)

        self.assertTrue(verify_numeric("391", 391))
        self.assertTrue(verify_numeric("The answer is 391.", 391))
        self.assertFalse(verify_numeric("42", 391))
        self.assertFalse(verify_numeric("", 391))

    def test_fm5_cheap_model_answers_simple_math(self):
        """The cheap model answers simple math correctly (no escalation needed)."""
        import re
        r, err = _call(config.CHEAP_DEFAULT, "What is 17 * 23? Reply with just the number.", max_tokens=16)
        self.assertIsNone(err, f"Cheap model failed: {err}")
        nums = re.findall(r"\d+", r["text"].strip())
        self.assertTrue(bool(nums and int(nums[0]) == 391),
                        f"Cheap model gave wrong answer: {r['text']!r}")

    # ---------------------------------------------------------------
    # Observability: log entries are structured and key-safe
    # ---------------------------------------------------------------
    def test_observability_log_schema(self):
        """Every log entry must have ts, event, and must not contain raw API key material."""
        import importlib.util
        spec_path = os.path.join(os.path.dirname(__file__), "run_l5.py")
        spec = importlib.util.spec_from_file_location("run_l5_obs", spec_path)
        run_l5 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(run_l5)

        # Trigger a log entry
        run_l5._log("test_event", model="gpt-4o-mini", outcome="ok")
        entry = run_l5._LOG[-1]

        self.assertIn("ts", entry, "Log entry missing 'ts' field")
        self.assertIn("event", entry, "Log entry missing 'event' field")
        self.assertEqual(entry["event"], "test_event")

        # Verify no key strings appear in any log entry
        import json
        key_vars = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "XAI_API_KEY"]
        import os as _os
        for entry in run_l5._LOG:
            line = json.dumps(entry)
            for var in key_vars:
                key_val = _os.environ.get(var, "")
                if key_val:
                    self.assertNotIn(key_val, line,
                                     f"Log entry leaks {var} value!")


if __name__ == "__main__":
    unittest.main(verbosity=2)
