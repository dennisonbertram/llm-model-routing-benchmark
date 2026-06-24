"""S5c — the STRAIGHT three-way comparison on ALL 56 super-hard tasks (no subsets, no jargon).

How good is each system, period? Same 56 tasks, same deterministic graders, same cost accounting:
  - GPT-5.5 (single call)
  - Fugu-Ultra (the real multi-agent conductor)
  - our diverse strong ensemble: DeepSeek-R1-0528 + Gemini-2.5-Pro + GPT-5.5, majority vote on the integer
Report each system's accuracy X/56, total cost, $/task, and mean latency. That's it.

Run: set -a; . .agent-university/secrets.local.env; set +a; python3 run_full56.py
"""
import json
import os
import re
import sys
import time
from collections import Counter

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)
sys.path.insert(0, os.path.dirname(__file__))

from cache import Cache  # noqa: E402
import superhard as S  # noqa: E402

HERE = os.path.dirname(__file__)
CACHE = Cache(os.path.join(HERE, ".cache.json"))
# Diverse strong ensemble across THREE vendors that actually answer (OpenAI + Anthropic + xAI).
# (The earlier OpenRouter reasoners DeepSeek-R1 / Gemini-2.5-Pro timed out so often the ensemble
#  degenerated to just GPT-5.5's vote — not a real ensemble. These three are responsive + diverse.)
ENSEMBLE = ["gpt-5.5", "claude-opus-4-8", "grok-4.3"]


def last_int(t):
    n = re.findall(r"-?\d+", (t or "").replace(",", ""))
    return int(n[-1]) if n else None


def call(model, prompt, timeout=240, retries=4, gap=0.0):
    try:
        r = CACHE.chat(model, [{"role": "user", "content": prompt}], max_tokens=8000,
                       temperature=0.0, timeout=timeout, retries=retries)
    except Exception as e:
        print(f"    [warn] {model}: {str(e)[:55]}", flush=True)
        r = {"text": "", "usd": 0.0, "latency_ms": 0}
    if gap:
        time.sleep(gap)
    return r


def main():
    items = S.gen(seed=7)[:56]
    agg = {"gpt-5.5": {"ok": 0, "usd": 0.0, "lat": 0}, "fugu-ultra": {"ok": 0, "usd": 0.0, "lat": 0},
           "ensemble": {"ok": 0, "usd": 0.0, "lat": 0}}
    per = []
    for it in items:
        gold = it["gold"]
        # gpt-5.5 (cached from the sweep)
        g = call("gpt-5.5", it["prompt"])
        g_ok = (last_int(g["text"]) == gold)
        agg["gpt-5.5"]["ok"] += g_ok; agg["gpt-5.5"]["usd"] += g["usd"]; agg["gpt-5.5"]["lat"] += g.get("latency_ms", 0)
        # fugu-ultra (gentle gap to dodge 429s)
        fu = call("fugu-ultra", it["prompt"], timeout=240, retries=4, gap=2.0)
        fu_ok = (last_int(fu["text"]) == gold)
        agg["fugu-ultra"]["ok"] += fu_ok; agg["fugu-ultra"]["usd"] += fu["usd"]; agg["fugu-ultra"]["lat"] += fu.get("latency_ms", 0)
        # diverse strong ensemble: majority vote
        votes, ecost, elat = [], 0.0, 0
        for m in ENSEMBLE:
            r = call(m, it["prompt"], timeout=120)
            votes.append(last_int(r["text"])); ecost += r["usd"]; elat += r.get("latency_ms", 0)
        tally = Counter(v for v in votes if v is not None)
        winner = tally.most_common(1)[0][0] if tally else None
        e_ok = (winner == gold)
        agg["ensemble"]["ok"] += e_ok; agg["ensemble"]["usd"] += ecost; agg["ensemble"]["lat"] += elat
        per.append({"id": it["id"], "gold": gold, "gpt5.5": (last_int(g["text"]), g_ok),
                    "fugu_ultra": (last_int(fu["text"]), fu_ok), "ensemble": (votes, winner, e_ok)})
        CACHE.save()
        print(f"  {it['id']}: gold={gold} | gpt5.5={'OK' if g_ok else 'x'} | "
              f"fugu-ultra={'OK' if fu_ok else 'x'} | ensemble={'OK' if e_ok else 'x'}", flush=True)

    n = len(items)
    print(f"\n== STRAIGHT three-way on ALL {n} super-hard tasks ==")
    print(f"  {'system':14} {'accuracy':>12} {'$/task':>9} {'mean_lat':>9}")
    for k in ["gpt-5.5", "fugu-ultra", "ensemble"]:
        a = agg[k]
        print(f"  {k:14} {a['ok']}/{n} = {a['ok']/n:>5.3f} {a['usd']/n:>9.4f} {int(a['lat']/n):>7}ms")
    json.dump({"n": n, "agg": agg, "per_task": per}, open(os.path.join(HERE, "full56_results.json"), "w"), indent=1)
    print("wrote full56_results.json | cache:", CACHE.stats())


if __name__ == "__main__":
    main()
