"""L3c — OpenAI-compatible gateway integration — live run script.

Starts the gateway in-process (no subprocess needed — the handler logic is called directly
via a socketless in-process transport) then drives it with raw HTTP calls over localhost,
proving the full wire path: client -> OpenAI-shaped POST -> gateway router -> real upstream
model -> OpenAI-shaped response.

Also drives the gateway with the openai Python package if it is importable.

Run:
  set -a; . .agent-university/secrets.local.env; set +a
  cd source && python3 run_l3c.py
"""
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

import config  # noqa: E402
from gateway import run_server, heuristic_route  # noqa: E402

GATEWAY_PORT = 8770
GATEWAY_URL = f"http://127.0.0.1:{GATEWAY_PORT}/v1/chat/completions"




# ── helpers ─────────────────────────────────────────────────────────────────

def raw_post(messages, model="auto", max_tokens=256, temperature=0.0):
    """Send a raw POST to the gateway using urllib (same wire path as any OpenAI client)."""
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        GATEWAY_URL,
        data=data,
        headers={"Content-Type": "application/json", "Authorization": "Bearer not-needed"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ── test cases ───────────────────────────────────────────────────────────────

ROUTING_CASES = [
    # (label, messages, expected_route)
    ("cheap — factual/short",
     [{"role": "user", "content": "What is the capital of France?"}],
     config.CHEAP_DEFAULT),

    ("cheap — coding task",
     [{"role": "user", "content": "Write a Python function that reverses a string."}],
     config.CHEAP_DEFAULT),

    ("strong — combinatorics",
     [{"role": "user", "content":
       "In how many ways can you arrange 8 distinct books on a shelf such that "
       "3 specific books are always together? Show work."}],
     config.STRONG_DEFAULT),

    ("strong — proof/reasoning",
     [{"role": "user", "content":
       "Prove that for all n >= 1, the sum 1+2+...+n = n(n+1)/2 using induction."}],
     config.STRONG_DEFAULT),

    ("auto passthrough — explicit gpt-4o-mini",
     [{"role": "user", "content": "What is 2+2?"}],
     config.CHEAP_DEFAULT),  # model="gpt-4o-mini" explicit
]


def run_unit_routing():
    """Test heuristic_route() offline (no API call) — validates routing logic."""
    section("Unit: heuristic_route() offline checks")
    passed = 0
    failed = 0
    for label, msgs, expected in ROUTING_CASES[:4]:
        got = heuristic_route(msgs)
        ok = got == expected
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  [{status}] {label}")
        print(f"         expected={expected!r}  got={got!r}")
    return passed, failed


def run_wire_tests(server_ready):
    """Drive the live gateway via raw HTTP — the same wire path as openai-python."""
    server_ready.wait(timeout=5)
    section("Wire: raw urllib POST -> gateway -> real model")

    results = []

    # Case 1: simple factual question → should route to cheap
    print("\n[1] cheap routing — capital of France")
    r = raw_post([{"role": "user", "content": "What is the capital of France?"}])
    print(f"  model served   : {r['model']}")
    print(f"  content        : {r['choices'][0]['message']['content']!r}")
    print(f"  usage          : {r['usage']}")
    print(f"  routing meta   : {r.get('x_routing')}")
    assert r["choices"][0]["message"]["content"].strip(), "empty content"
    assert r["model"] == config.CHEAP_DEFAULT, f"expected cheap, got {r['model']}"
    results.append(("cheap route", True, r))

    # Case 2: hard math → should route to strong
    print("\n[2] strong routing — combinatorics")
    r2 = raw_post([{"role": "user", "content":
                    "In how many ways can 8 distinct books be arranged on a shelf "
                    "so that 3 specific books are always together?"}], max_tokens=512)
    print(f"  model served   : {r2['model']}")
    print(f"  content (first 200): {r2['choices'][0]['message']['content'][:200]!r}")
    print(f"  usage          : {r2['usage']}")
    print(f"  routing meta   : {r2.get('x_routing')}")
    assert r2["model"] == config.STRONG_DEFAULT, f"expected strong, got {r2['model']}"
    results.append(("strong route", True, r2))

    # Case 3: explicit model passthrough — client says gpt-4.1-nano, gateway honours it
    print("\n[3] explicit model passthrough — gpt-4.1-nano (bypass router)")
    r3 = raw_post([{"role": "user", "content": "Reply with exactly: GATEWAY_OK"}],
                  model="gpt-4.1-nano", max_tokens=16)
    print(f"  model served   : {r3['model']}")
    print(f"  content        : {r3['choices'][0]['message']['content']!r}")
    assert r3["model"] == "gpt-4.1-nano", f"passthrough failed, got {r3['model']}"
    results.append(("passthrough", True, r3))

    return results


def try_openai_sdk(server_ready):
    """Try using the openai Python package pointed at the gateway. Return (used, result_str)."""
    server_ready.wait(timeout=5)
    section("openai SDK integration (base_url override)")
    try:
        import openai  # noqa: F401
    except ImportError:
        print("  openai package not importable — using raw urllib equivalent (see above)")
        print("  One-line override (if installed): openai.OpenAI(base_url='http://127.0.0.1:8765/v1', api_key='x')")
        return False, "not importable"

    import openai
    client = openai.OpenAI(
        base_url=f"http://127.0.0.1:{GATEWAY_PORT}/v1",
        api_key="not-needed",  # gateway doesn't check client-side key; uses server env vars
    )
    completion = client.chat.completions.create(
        model="auto",
        messages=[{"role": "user", "content": "What is the capital of France?"}],
        max_tokens=64,
    )
    content = completion.choices[0].message.content
    model_served = completion.model
    tokens = completion.usage
    print(f"  model served   : {model_served}")
    print(f"  content        : {content!r}")
    print(f"  usage          : prompt={tokens.prompt_tokens} completion={tokens.completion_tokens}")
    assert content.strip(), "empty response via openai SDK"
    return True, f"model={model_served} content={content!r}"


def main():
    # Step 0: unit routing checks (no network)
    passed, failed = run_unit_routing()
    print(f"\nUnit routing: {passed} passed, {failed} failed")

    # Step 1: start the gateway server in a background thread
    server = run_server("127.0.0.1", GATEWAY_PORT)
    server_ready = threading.Event()

    def serve():
        server_ready.set()
        server.serve_forever()

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    server_ready.wait(timeout=5)
    print(f"\nGateway started on port {GATEWAY_PORT}")

    try:
        # Step 2: wire tests
        wire_results = run_wire_tests(server_ready)

        # Step 3: openai SDK (if installed)
        sdk_used, sdk_result = try_openai_sdk(server_ready)

        # Step 4: summary
        section("Summary")
        all_pass = all(ok for _, ok, _ in wire_results)
        route_table = []
        for label, ok, r in wire_results:
            route_table.append({
                "test": label,
                "model_served": r["model"],
                "content_excerpt": r["choices"][0]["message"]["content"][:80],
                "usage": r["usage"],
                "usd": r.get("x_routing", {}).get("usd"),
                "latency_ms": r.get("x_routing", {}).get("latency_ms"),
            })

        for row in route_table:
            print(f"  {row['test']:30} model={row['model_served']:18} "
                  f"${row['usd']:.2e}  {row['latency_ms']}ms")

        print(f"\n  openai SDK used: {sdk_used}  result: {sdk_result}")
        print(f"\n  Wire compat: {'ALL PASS' if all_pass else 'SOME FAILURES'}")

        # Write evidence JSON
        evidence = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "gateway_port": GATEWAY_PORT,
            "cheap_model": config.CHEAP_DEFAULT,
            "strong_model": config.STRONG_DEFAULT,
            "wire_tests": route_table,
            "openai_sdk_used": sdk_used,
            "openai_sdk_result": sdk_result,
            "unit_routing_passed": passed,
            "unit_routing_failed": failed,
        }
        out_path = os.path.join(os.path.dirname(__file__), "l3c_evidence.json")
        with open(out_path, "w") as f:
            json.dump(evidence, f, indent=2)
        print(f"\nWrote evidence to {out_path}")

    finally:
        server.shutdown()
        print("Gateway stopped.")


if __name__ == "__main__":
    main()
