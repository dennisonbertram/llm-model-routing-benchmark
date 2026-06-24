"""L3c live behavioral tests — OpenAI-compatible gateway.

RED  (no API keys): ProviderError raised when gateway tries to call upstream.
GREEN (keys loaded): all assertions pass against real upstream models.

Run:
  # RED (no keys loaded):
  env -i HOME=$HOME python3 test_l3c.py

  # GREEN:
  set -a; . .agent-university/secrets.local.env; set +a
  cd source && python3 test_l3c.py
"""
import json
import os
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

import config  # noqa: E402
from gateway import run_server, heuristic_route  # noqa: E402

GATEWAY_PORT = 8766  # Different port from run_l3c to avoid conflict
GATEWAY_URL = f"http://127.0.0.1:{GATEWAY_PORT}/v1/chat/completions"


def _post(messages, model="auto", max_tokens=256):
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.0}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        GATEWAY_URL, data=data,
        headers={"Content-Type": "application/json", "Authorization": "Bearer x"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


class GatewayServer:
    """Context manager: starts gateway in a background thread, stops it on exit."""
    def __init__(self):
        self.server = None

    def __enter__(self):
        self.server = run_server("127.0.0.1", GATEWAY_PORT)
        ready = threading.Event()

        def serve():
            ready.set()
            self.server.serve_forever()

        t = threading.Thread(target=serve, daemon=True)
        t.start()
        ready.wait(timeout=5)
        return self

    def __exit__(self, *_):
        if self.server:
            self.server.shutdown()


class TestGatewayHeuristic(unittest.TestCase):
    """Offline heuristic routing logic — no API calls needed."""

    def test_cheap_route_factual(self):
        got = heuristic_route([{"role": "user", "content": "What is the capital of France?"}])
        self.assertEqual(got, config.CHEAP_DEFAULT,
                         f"short factual should route cheap, got {got!r}")

    def test_cheap_route_coding(self):
        got = heuristic_route([{"role": "user",
                                 "content": "def fibonacci(n): write a python function"}])
        self.assertEqual(got, config.CHEAP_DEFAULT,
                         f"simple coding should route cheap, got {got!r}")

    def test_strong_route_combinatorics(self):
        got = heuristic_route([{"role": "user",
                                 "content": "In how many ways can 8 books be arranged "
                                            "with permutation constraints?"}])
        self.assertEqual(got, config.STRONG_DEFAULT,
                         f"combinatorics should route strong, got {got!r}")

    def test_strong_route_proof(self):
        got = heuristic_route([{"role": "user",
                                 "content": "Prove that for all n the sum 1+2+...+n = n(n+1)/2 "
                                            "using induction."}])
        self.assertEqual(got, config.STRONG_DEFAULT,
                         f"proof should route strong, got {got!r}")


class TestGatewayWire(unittest.TestCase):
    """Live wire-format tests — require API keys. Label: Live behavioral test."""

    @classmethod
    def setUpClass(cls):
        cls._gw = GatewayServer()
        cls._gw.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._gw.__exit__(None, None, None)

    def test_openai_response_shape(self):
        """Gateway returns proper OpenAI-shaped response for an 'auto' request."""
        r = _post([{"role": "user", "content": "Reply with exactly: WIRE_OK"}],
                  model="auto", max_tokens=32)
        # shape assertions
        self.assertIn("choices", r)
        self.assertIn("model", r)
        self.assertIn("usage", r)
        self.assertIn("id", r)
        self.assertEqual(r["object"], "chat.completion")
        content = r["choices"][0]["message"]["content"]
        self.assertTrue(content.strip(), "empty content from gateway")
        usage = r["usage"]
        self.assertIn("prompt_tokens", usage)
        self.assertIn("completion_tokens", usage)
        self.assertIn("total_tokens", usage)
        self.assertGreater(usage["prompt_tokens"], 0)

    def test_cheap_route_live(self):
        """Short factual prompt is routed to cheap model and returns real answer."""
        r = _post([{"role": "user", "content": "What is the capital of France?"}])
        self.assertEqual(r["model"], config.CHEAP_DEFAULT,
                         f"expected cheap model {config.CHEAP_DEFAULT!r}, got {r['model']!r}")
        content = r["choices"][0]["message"]["content"].lower()
        self.assertIn("paris", content, f"expected Paris in answer, got {content!r}")

    def test_strong_route_live(self):
        """Combinatorics prompt is routed to strong model and returns non-empty answer."""
        r = _post([{"role": "user", "content":
                    "In how many ways can 8 distinct books be arranged on a shelf "
                    "so that 3 specific books are always together? Show work."}], max_tokens=512)
        self.assertEqual(r["model"], config.STRONG_DEFAULT,
                         f"expected strong model {config.STRONG_DEFAULT!r}, got {r['model']!r}")
        content = r["choices"][0]["message"]["content"]
        self.assertTrue(len(content) > 20, f"too-short answer: {content!r}")

    def test_explicit_model_passthrough(self):
        """When client specifies an explicit model, gateway honours it without routing."""
        r = _post([{"role": "user", "content": "Reply with exactly: PASSTHROUGH_OK"}],
                  model="gpt-4.1-nano", max_tokens=16)
        self.assertEqual(r["model"], "gpt-4.1-nano",
                         f"passthrough failed, served {r['model']!r}")

    def test_model_field_is_actual_not_auto(self):
        """The response model field is the actually-served model, never 'auto'."""
        r = _post([{"role": "user", "content": "ping"}], model="auto", max_tokens=8)
        self.assertNotEqual(r["model"], "auto",
                            "model field should be the actual served model, not 'auto'")

    def test_routing_metadata_present(self):
        """x_routing extension field is present with cost + latency data."""
        r = _post([{"role": "user", "content": "What is 2+2?"}], model="auto", max_tokens=16)
        self.assertIn("x_routing", r)
        xr = r["x_routing"]
        self.assertGreater(xr.get("usd", 0), 0, "x_routing.usd should be positive")
        self.assertGreater(xr.get("latency_ms", 0), 0, "x_routing.latency_ms should be positive")


if __name__ == "__main__":
    unittest.main(verbosity=2)
