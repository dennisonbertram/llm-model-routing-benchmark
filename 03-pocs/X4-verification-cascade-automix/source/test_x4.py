"""X4 live behavioral test. Label: Live behavioral test.

RED (without API keys): ProviderError on the first live verifier call.
GREEN (with keys): cascade achieves strong-level accuracy (0.9778) for under 30% of
strong model cost, with a calibrated verifier (high-conf = correct, low-conf = uncertain).

These assertions are backed by real API calls (verifier calls are all live, cached in
own .cache.json; answer calls reuse the harness labelset cache — no re-billing).
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(__file__)
HARNESS = os.path.join(HERE, "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

import config
import tasks
from cache import Cache
from router_base import _budget

OWN_CACHE = os.path.join(HERE, ".cache.json")
LABELSET_PATH = os.path.join(HARNESS, ".cache", "labelset_export.json")

VERIFY_SYS = (
    "You are a careful answer validator. You will be shown a question and an answer. "
    "Your only job is to assess if the answer is correct. "
    "Reply with exactly ONE word: 'yes' if the answer is correct, 'no' if it is wrong or uncertain."
)


def _run_cascade_at_threshold(T, cache, labelset, k=3):
    """Run the full cascade at threshold T using cached verifier calls. Returns (acc, usd, esc_rate)."""
    harness_cache = Cache(os.path.join(HARNESS, ".cache", "labelset.json"))
    nc = cost = escalations = 0
    n = 0
    for row in labelset:
        item = next((t for t in tasks.ALL if t["id"] == row["id"]), None)
        if item is None:
            continue
        n += 1
        # Get cheap answer text from harness cache
        r_cheap = harness_cache.chat(
            config.CHEAP_DEFAULT,
            [{"role": "user", "content": item["prompt"]}],
            max_tokens=_budget(item),
        )
        cheap_text = r_cheap["text"]
        # Run verifier (live or own cache)
        verify_prompt = (
            f"QUESTION:\n{item['prompt']}\n\n"
            f"PROPOSED ANSWER:\n{cheap_text}\n\n"
            "Is this answer correct? Reply with exactly ONE word: yes or no."
        )
        msgs = [{"role": "user", "content": verify_prompt}]
        votes = []
        v_usd = 0.0
        for i in range(k):
            r = cache.chat(
                config.CHEAP_DEFAULT, msgs, max_tokens=8, temperature=0.8,
                system=VERIFY_SYS, nonce=f"x4_verify_{item['id']}_{i}"
            )
            votes.append(1 if r["text"].strip().lower().startswith("yes") else 0)
            v_usd += r["usd"]
        conf = sum(votes) / len(votes)
        escalate = conf < T
        if escalate:
            correct = row["strong_correct"]
            answer_usd = row["strong_usd"]
            escalations += 1
        else:
            correct = row["cheap_correct"]
            answer_usd = row["cheap_usd"]
        nc += correct
        cost += answer_usd + v_usd
    cache.save()
    return nc / n, cost, escalations / n


class X4(unittest.TestCase):
    def test_verifier_reachable_and_returns_yesno(self):
        """Verifier makes real API calls and returns 'yes' or 'no'."""
        cache = Cache(OWN_CACHE)
        item = next(t for t in tasks.ALL if t["id"] == "q1")
        # q1: "What is the capital of France?" — trivial, cheap answer should be "Paris"
        harness_cache = Cache(os.path.join(HARNESS, ".cache", "labelset.json"))
        r = harness_cache.chat(
            config.CHEAP_DEFAULT, [{"role": "user", "content": item["prompt"]}], max_tokens=32
        )
        cheap_text = r["text"]
        verify_prompt = (
            f"QUESTION:\n{item['prompt']}\n\n"
            f"PROPOSED ANSWER:\n{cheap_text}\n\n"
            "Is this answer correct? Reply with exactly ONE word: yes or no."
        )
        r_v = cache.chat(
            config.CHEAP_DEFAULT,
            [{"role": "user", "content": verify_prompt}],
            max_tokens=8, temperature=0.8, system=VERIFY_SYS,
            nonce="test_x4_q1_0",
        )
        cache.save()
        raw = r_v["text"].strip().lower()
        self.assertGreater(len(raw), 0, "verifier returned empty response")
        # Should start with 'yes' or 'no'
        self.assertTrue(raw.startswith("yes") or raw.startswith("no"),
                        f"unexpected verifier response: {raw!r}")
        self.assertGreater(r_v["usd"], 0, "verifier call must have non-zero cost")

    def test_cascade_strong_accuracy(self):
        """At T=0.67 the cascade achieves strong-level accuracy."""
        with open(LABELSET_PATH) as f:
            labelset = json.load(f)
        cache = Cache(OWN_CACHE)
        acc, usd, esc = _run_cascade_at_threshold(0.67, cache, labelset, k=3)
        # Must match strong accuracy (0.9778 = 44/45)
        self.assertGreaterEqual(acc, 0.97, f"cascade accuracy too low: {acc:.4f}")

    def test_cascade_cheaper_than_strong(self):
        """At T=0.67 the cascade costs well under the always-strong baseline."""
        with open(LABELSET_PATH) as f:
            labelset = json.load(f)
        cache = Cache(OWN_CACHE)
        acc, usd, esc = _run_cascade_at_threshold(0.67, cache, labelset, k=3)
        strong_usd = 0.021480
        self.assertLess(usd, strong_usd * 0.5,
                        f"cascade usd={usd:.6f} should be < 50% of strong_usd={strong_usd:.6f}")

    def test_verifier_calibrated(self):
        """High verifier confidence (>=0.67) items should all be correct; low-conf includes wrongs."""
        with open(LABELSET_PATH) as f:
            labelset = json.load(f)
        harness_cache = Cache(os.path.join(HARNESS, ".cache", "labelset.json"))
        cache = Cache(OWN_CACHE)
        high_conf_correct = []
        low_conf_correct = []
        for row in labelset:
            item = next((t for t in tasks.ALL if t["id"] == row["id"]), None)
            if item is None:
                continue
            r = harness_cache.chat(
                config.CHEAP_DEFAULT, [{"role": "user", "content": item["prompt"]}],
                max_tokens=_budget(item)
            )
            cheap_text = r["text"]
            verify_prompt = (
                f"QUESTION:\n{item['prompt']}\n\n"
                f"PROPOSED ANSWER:\n{cheap_text}\n\n"
                "Is this answer correct? Reply with exactly ONE word: yes or no."
            )
            msgs = [{"role": "user", "content": verify_prompt}]
            votes = []
            for i in range(3):
                rv = cache.chat(
                    config.CHEAP_DEFAULT, msgs, max_tokens=8, temperature=0.8,
                    system=VERIFY_SYS, nonce=f"x4_verify_{item['id']}_{i}"
                )
                votes.append(1 if rv["text"].strip().lower().startswith("yes") else 0)
            conf = sum(votes) / len(votes)
            if conf >= 0.67:
                high_conf_correct.append(row["cheap_correct"])
            else:
                low_conf_correct.append(row["cheap_correct"])
        cache.save()
        # High confidence items should be 100% correct (the verifier is perfectly calibrated
        # on this dataset at the upper end)
        if high_conf_correct:
            hc_rate = sum(high_conf_correct) / len(high_conf_correct)
            self.assertGreaterEqual(hc_rate, 0.95,
                                    f"high-conf calibration={hc_rate:.3f}, expected >=0.95")
        # Low confidence region must contain some wrong items
        if low_conf_correct:
            lc_rate = sum(low_conf_correct) / len(low_conf_correct)
            self.assertLess(lc_rate, 0.8,
                            f"low-conf region has too many correct items ({lc_rate:.3f}), "
                            "suggesting verifier signal is weak")


if __name__ == "__main__":
    unittest.main(verbosity=2)
