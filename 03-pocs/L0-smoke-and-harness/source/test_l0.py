"""L0 live behavioral test. Label: Live behavioral test.

RED (before access / harness): ProviderError or ImportError.
GREEN (with keys + harness): all assertions pass against the real APIs.

These assert the *facts that make routing worth doing*: a real cost-quality gap and real oracle
headroom. They are not mocked — every assertion is backed by live calls (cached after first run).
"""
import os
import sys
import unittest

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

import config  # noqa: E402
import tasks  # noqa: E402
from cache import Cache  # noqa: E402
from providers import chat  # noqa: E402
from router_base import _budget  # noqa: E402

CACHE = Cache(os.path.join(HARNESS, ".cache", "labelset.json"))


def _baseline():
    rows = []
    for it in tasks.ALL:
        rec = {"id": it["id"]}
        for tag, m in (("cheap", config.CHEAP_DEFAULT), ("strong", config.STRONG_DEFAULT)):
            r = CACHE.chat(m, [{"role": "user", "content": it["prompt"]}], max_tokens=_budget(it))
            rec[tag + "_correct"] = bool(it["grade"](r["text"]))
            rec[tag + "_usd"] = r["usd"]
        rows.append(rec)
    CACHE.save()
    return rows


class L0(unittest.TestCase):
    def test_providers_live(self):
        for m in ["gpt-4o-mini", "claude-haiku-4-5-20251001", "grok-4.3"]:
            r = chat(m, [{"role": "user", "content": "Reply with exactly: OK"}], max_tokens=16)
            self.assertTrue(r["text"].strip(), f"{m} returned empty")
            self.assertGreater(r["usd"], 0.0, f"{m} cost not measured")

    def test_real_cost_quality_gap(self):
        rows = _baseline()
        ca = sum(r["cheap_correct"] for r in rows) / len(rows)
        sa = sum(r["strong_correct"] for r in rows) / len(rows)
        cc = sum(r["cheap_usd"] for r in rows)
        sc = sum(r["strong_usd"] for r in rows)
        self.assertGreater(sa, ca, "no quality gap -> routing pointless")
        self.assertGreater(sc, cc * 3, "no cost gap -> routing pointless")

    def test_oracle_headroom(self):
        rows = _baseline()
        sa = sum(r["strong_correct"] for r in rows) / len(rows)
        sc = sum(r["strong_usd"] for r in rows)
        oc = sum((r["cheap_usd"] if r["cheap_correct"] else r["strong_usd"]) for r in rows)
        oa = sum((1 if (r["cheap_correct"] or r["strong_correct"]) else 0) for r in rows) / len(rows)
        # A perfect router matches strong accuracy for well under half the strong cost.
        self.assertGreaterEqual(oa + 1e-9, sa, "oracle should match strong accuracy")
        self.assertLess(oc, sc * 0.5, "oracle should be far cheaper than always-strong")


if __name__ == "__main__":
    unittest.main(verbosity=2)
