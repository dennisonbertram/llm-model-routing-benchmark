"""L4 behavioral tests — routing gateway runtime.

Label: Live behavioral test.

RED (before keys / server): ProviderError or connection refused.
GREEN (with keys + gateway running): all assertions pass against the real live gateway.

Tests:
  1. Gateway starts and /v1/health returns {"status": "ok"}
  2. An "auto" request with a simple prompt routes to CHEAP_DEFAULT and returns valid text
  3. An "auto" request with a hard-math keyword routes to STRONG_DEFAULT
  4. A forced-model request uses the specified model regardless of content
  5. Cost ledger is written and each line has required fields with sane values
"""
import json
import os
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
HARNESS = os.path.join(HERE, "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

from config import CHEAP_DEFAULT, STRONG_DEFAULT  # noqa: E402

PORT = 8767  # different port from the demo to avoid conflicts
BASE = f"http://127.0.0.1:{PORT}"
LEDGER = os.path.join(HERE, "cost-ledger-test.jsonl")
GW_PROC = None


def _post(path, body):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(f"{BASE}{path}", data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get(path):
    with urllib.request.urlopen(f"{BASE}{path}", timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def setUpModule():
    global GW_PROC
    if os.path.exists(LEDGER):
        os.remove(LEDGER)
    env = os.environ.copy()
    GW_PROC = subprocess.Popen(
        [sys.executable, os.path.join(HERE, "gateway.py"), "--port", str(PORT)],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    # Wait for ready
    for _ in range(20):
        try:
            _get("/v1/health")
            return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("Gateway did not start in time")


def tearDownModule():
    if GW_PROC:
        GW_PROC.terminate()
        GW_PROC.wait(timeout=5)
    if os.path.exists(LEDGER):
        os.remove(LEDGER)


class L4GatewayTests(unittest.TestCase):
    def test_01_health(self):
        """Gateway health endpoint returns status ok."""
        r = _get("/v1/health")
        self.assertEqual(r["status"], "ok")

    def test_02_auto_simple_routes_cheap(self):
        """Auto-routing of a simple factual question picks the cheap model."""
        r = _post("/v1/chat/completions", {
            "model": "auto",
            "messages": [{"role": "user", "content": "What is the capital of France?"}],
            "max_tokens": 64,
        })
        self.assertEqual(r["object"], "chat.completion")
        self.assertTrue(r["choices"][0]["message"]["content"].strip(),
                        "response text must not be empty")
        self.assertEqual(r["model"], CHEAP_DEFAULT,
                         f"simple question should route to cheap ({CHEAP_DEFAULT}), got {r['model']}")
        routing = r.get("x_routing", {})
        self.assertEqual(routing.get("chosen_model"), CHEAP_DEFAULT)
        self.assertGreater(routing.get("usd", 0), 0)
        self.assertGreater(routing.get("latency_ms", 0), 0)

    def test_03_auto_hard_math_routes_strong(self):
        """Auto-routing of a combinatorics question picks the strong model."""
        r = _post("/v1/chat/completions", {
            "model": "auto",
            "messages": [{"role": "user", "content": "How many ways can you select a combination of 3 items from 10 distinct items?"}],
            "max_tokens": 128,
        })
        self.assertEqual(r["object"], "chat.completion")
        self.assertEqual(r["model"], STRONG_DEFAULT,
                         f"combinatorics question should route to strong ({STRONG_DEFAULT}), got {r['model']}")
        routing = r.get("x_routing", {})
        self.assertTrue(routing.get("decision", "").startswith("keyword:"),
                        f"decision should reference the matched keyword, got: {routing.get('decision')}")

    def test_04_forced_model_bypasses_routing(self):
        """A forced model= request ignores routing and uses the specified model."""
        r = _post("/v1/chat/completions", {
            "model": CHEAP_DEFAULT,
            "messages": [{"role": "user", "content": "Say hello."}],
            "max_tokens": 32,
        })
        self.assertEqual(r["model"], CHEAP_DEFAULT)
        routing = r.get("x_routing", {})
        self.assertEqual(routing.get("decision"), "forced",
                         "forced model should show decision='forced'")

    def test_05_ledger_written(self):
        """The main ledger file has entries with required fields."""
        main_ledger = os.path.join(HERE, "cost-ledger.jsonl")
        self.assertTrue(os.path.exists(main_ledger),
                        "cost-ledger.jsonl must exist after requests to the gateway")
        with open(main_ledger, encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
        self.assertGreater(len(lines), 0, "ledger must have at least one entry")
        required = {"ts", "decision", "chosen_model", "prompt_tokens",
                    "completion_tokens", "usd", "latency_ms"}
        for line in lines:
            missing = required - set(line.keys())
            self.assertFalse(missing, f"ledger entry missing fields: {missing}")
            self.assertGreater(line["usd"], 0, "ledger usd must be positive")
            self.assertGreater(line["latency_ms"], 0, "ledger latency_ms must be positive")


if __name__ == "__main__":
    unittest.main(verbosity=2)
