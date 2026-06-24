"""L0 — live smoke + baseline harness.

Proves: (1) OpenAI, Anthropic, and xAI are reachable live; (2) the measurement harness produces
real accuracy/cost/latency over the 45-item suite; (3) the cost-quality GAP and the ORACLE
headroom that motivate routing are real (not assumed).

Run:  set -a; . .agent-university/secrets.local.env; set +a ; python3 run_l0.py
"""
import json
import os
import sys

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

import config  # noqa: E402
import tasks  # noqa: E402
from cache import Cache  # noqa: E402
from providers import chat  # noqa: E402
from router_base import _budget  # noqa: E402


def main():
    print("== provider liveness ==")
    for m in ["gpt-4o-mini", "claude-haiku-4-5-20251001", "grok-4.3"]:
        r = chat(m, [{"role": "user", "content": "Reply with exactly: OK"}], max_tokens=16)
        print(f"  {m:30} -> {r['text']!r:8} {r['latency_ms']}ms  ${r['usd']:.2e}")

    cache = Cache(os.path.join(HARNESS, ".cache", "labelset.json"))
    CHEAP, STRONG = config.CHEAP_DEFAULT, config.STRONG_DEFAULT

    rows = []
    for it in tasks.ALL:
        rec = {"id": it["id"], "discipline": it["discipline"], "difficulty": it["difficulty"]}
        for tag, m in (("cheap", CHEAP), ("strong", STRONG)):
            r = cache.chat(m, [{"role": "user", "content": it["prompt"]}], max_tokens=_budget(it))
            rec[tag + "_correct"] = bool(it["grade"](r["text"]))
            rec[tag + "_usd"] = r["usd"]
        rows.append(rec)
    cache.save()

    def agg(pick):
        nc = cost = 0.0
        for r in rows:
            c = pick(r)
            nc += r[c + "_correct"]
            cost += r[c + "_usd"]
        return nc / len(rows), cost

    ac, acost = agg(lambda r: "cheap")
    asr, ascost = agg(lambda r: "strong")
    orc, ocost = agg(lambda r: "cheap" if r["cheap_correct"] else ("strong" if r["strong_correct"] else "cheap"))

    need_strong = [r["id"] for r in rows if not r["cheap_correct"] and r["strong_correct"]]
    both_wrong = [r["id"] for r in rows if not r["cheap_correct"] and not r["strong_correct"]]

    print("\n== baseline over 45 tasks ==")
    print(f"  always-cheap  ({CHEAP:11}): acc={ac:.3f}  cost=${acost:.5f}")
    print(f"  always-strong ({STRONG:11}): acc={asr:.3f}  cost=${ascost:.5f}  ({ascost/acost:.1f}x cheap)")
    print(f"  ORACLE (cheapest-correct)   : acc={orc:.3f}  cost=${ocost:.5f}  "
          f"({ocost/ascost*100:.0f}% of strong cost at strong-level accuracy)")
    print(f"\n  items only strong solves ({len(need_strong)}): {need_strong}")
    print(f"  items neither solves ({len(both_wrong)}): {both_wrong}")
    print(f"  cheap is enough for {sum(r['cheap_correct'] for r in rows)}/{len(rows)} tasks")

    summary = {
        "always_cheap": {"acc": round(ac, 4), "usd": round(acost, 6)},
        "always_strong": {"acc": round(asr, 4), "usd": round(ascost, 6)},
        "oracle": {"acc": round(orc, 4), "usd": round(ocost, 6)},
        "need_strong": need_strong, "both_wrong": both_wrong,
        "cheap_enough": sum(r["cheap_correct"] for r in rows), "n": len(rows),
        "cheap_model": CHEAP, "strong_model": STRONG,
    }
    json.dump(summary, open(os.path.join(os.path.dirname(__file__), "l0_summary.json"), "w"), indent=2)
    print("\nwrote l0_summary.json")


if __name__ == "__main__":
    main()
