"""S5b — the decisive frontier test: on the tasks a single GPT-5.5 call FAILS, does orchestration
recover them? This is the one regime where Fugu's 12-30x cost is supposed to be justified.

On the 11 GPT-5.5 failures (10 nonlinear modular recurrences + 1 big inclusion-exclusion), run:
  - single GPT-5.5 (baseline: 0/11 by construction)
  - Fugu-Ultra (the real multi-agent conductor)
  - a diverse STRONG ensemble (DeepSeek-R1-0528 + Gemini-2.5-Pro + GPT-5.5), majority vote on the integer
Grade with the deterministic gold. Report recoveries + cost.

Run: set -a; . .agent-university/secrets.local.env; set +a; python3 run_frontier_failures.py
"""
import json
import os
import re
import sys
from collections import Counter

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)
sys.path.insert(0, os.path.dirname(__file__))

from cache import Cache  # noqa: E402
import superhard as S  # noqa: E402
import tasks as T  # noqa: E402

HERE = os.path.dirname(__file__)
CACHE = Cache(os.path.join(HERE, ".cache.json"))
ENSEMBLE = ["openrouter/deepseek/deepseek-r1-0528", "openrouter/google/gemini-2.5-pro", "gpt-5.5"]


def call(model, prompt, mt=8000, timeout=300):
    try:
        return CACHE.chat(model, [{"role": "user", "content": prompt}], max_tokens=mt, temperature=0.0, timeout=timeout)
    except Exception as e:
        print(f"    [warn] {model}: {str(e)[:50]}", flush=True)
        return {"text": "", "usd": 0.0, "latency_ms": 0}


def last_int(t):
    n = re.findall(r"-?\d+", (t or "").replace(",", ""))
    return int(n[-1]) if n else None


def main():
    items = {it["id"]: it for it in S.gen(seed=7)}
    fails = [r["id"] for r in json.load(open(os.path.join(HERE, "superhard_gpt55.json"))) if not r["gpt55_ok"]]
    print(f"== frontier test on {len(fails)} GPT-5.5 failures: {fails} ==\n", flush=True)

    res = {"gpt-5.5-solo": {"ok": 0, "usd": 0.0}, "fugu-ultra": {"ok": 0, "usd": 0.0},
           "ensemble-vote": {"ok": 0, "usd": 0.0}}
    per = []
    for fid in fails:
        it = items[fid]; gold = it["gold"]; row = {"id": fid, "gold": gold}
        # gpt-5.5 solo (cached from the sweep) — by construction wrong, but record cost + answer
        g = call("gpt-5.5", it["prompt"]); row["gpt55"] = last_int(g["text"]); res["gpt-5.5-solo"]["usd"] += g["usd"]
        res["gpt-5.5-solo"]["ok"] += (last_int(g["text"]) == gold)
        # fugu-ultra
        fu = call("fugu-ultra", it["prompt"]); fok = it["grade"](fu["text"])
        row["fugu_ultra"] = (last_int(fu["text"]), bool(fok)); res["fugu-ultra"]["ok"] += bool(fok); res["fugu-ultra"]["usd"] += fu["usd"]
        # diverse strong ensemble: majority vote on the integer answer
        votes = []; ecost = 0.0
        for m in ENSEMBLE:
            r = call(m, it["prompt"]); votes.append(last_int(r["text"])); ecost += r["usd"]
        tally = Counter(v for v in votes if v is not None)
        winner = tally.most_common(1)[0][0] if tally else None
        eok = (winner == gold)
        row["ensemble"] = {"votes": votes, "winner": winner, "ok": eok}
        res["ensemble-vote"]["ok"] += eok; res["ensemble-vote"]["usd"] += ecost
        per.append(row)
        CACHE.save()
        print(f"  {fid}: gold={gold} | gpt5.5={row['gpt55']} | fugu-ultra={row['fugu_ultra']} | "
              f"ensemble={votes}->{winner} {'OK' if eok else 'x'}", flush=True)

    n = len(fails)
    print(f"\n== RECOVERY on {n} GPT-5.5 failures ==")
    for k in ["gpt-5.5-solo", "fugu-ultra", "ensemble-vote"]:
        print(f"  {k:16} recovered {res[k]['ok']}/{n}  cost ${res[k]['usd']:.4f} (${res[k]['usd']/n:.4f}/task)")
    json.dump({"failures": fails, "results": res, "per_task": per},
              open(os.path.join(HERE, "frontier_failures.json"), "w"), indent=1)
    print("wrote frontier_failures.json | cache:", CACHE.stats())


if __name__ == "__main__":
    main()
