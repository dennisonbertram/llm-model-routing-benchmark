"""S5d — CHEAP-only ensemble (no frontier model) vs GPT-5.5 vs Fugu-Ultra, on all 56 super-hard tasks.

Fixes the rigged comparison: the earlier ensemble included GPT-5.5, so "ensemble vs GPT-5.5" was
circular. This ensemble is THREE genuinely cheap models from three vendors, NONE of them frontier:
  Gemma-4-31b (Google, $0.12/$0.35) + DeepSeek-V4-flash ($0.09/$0.18) + GLM-5.2 (Z-AI, $0.98/$3.08).
Majority vote on the integer answer. Question the user actually wants: can a cheap ensemble match the
expensive single frontier call (GPT-5.5) — and at what cost? Same 56 tasks, same deterministic golds.

Run: set -a; . .agent-university/secrets.local.env; set +a; python3 run_cheap_ensemble.py
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

HERE = os.path.dirname(__file__)
CACHE = Cache(os.path.join(HERE, ".cache.json"))
CHEAP3 = ["openrouter/google/gemma-4-31b-it", "openrouter/deepseek/deepseek-v4-flash", "openrouter/z-ai/glm-5.2"]
SHORT = {m: m.split("/")[-1] for m in CHEAP3}


def last_int(t):
    n = re.findall(r"-?\d+", (t or "").replace(",", ""))
    return int(n[-1]) if n else None


def call(model, prompt, timeout=60):  # cheap models that can't do recurrences in 60s fail them anyway
    try:
        return CACHE.chat(model, [{"role": "user", "content": prompt}], max_tokens=4000, temperature=0.0, timeout=timeout)
    except Exception as e:
        print(f"    [warn] {model}: {str(e)[:50]}", flush=True)
        return {"text": "", "usd": 0.0, "latency_ms": 0}


def main():
    items = S.gen(seed=7)[:56]
    solo = {m: {"ok": 0, "usd": 0.0} for m in CHEAP3}
    ens = {"ok": 0, "usd": 0.0, "lat": 0}
    gpt = {"ok": 0, "usd": 0.0}
    per = []
    for it in items:
        gold = it["gold"]
        g = call("gpt-5.5", it["prompt"], timeout=240)
        gpt["ok"] += (last_int(g["text"]) == gold); gpt["usd"] += g["usd"]
        votes, ecost, elat = [], 0.0, 0
        for m in CHEAP3:
            r = call(m, it["prompt"])
            ans = last_int(r["text"]); votes.append(ans)
            solo[m]["ok"] += (ans == gold); solo[m]["usd"] += r["usd"]
            ecost += r["usd"]; elat += r.get("latency_ms", 0)
        tally = Counter(v for v in votes if v is not None)
        winner = tally.most_common(1)[0][0] if tally else None
        ok = (winner == gold)
        ens["ok"] += ok; ens["usd"] += ecost; ens["lat"] += elat
        per.append({"id": it["id"], "gold": gold, "gpt5.5": last_int(g["text"]), "votes": votes, "winner": winner, "ok": ok})
        CACHE.save()
        print(f"  {it['id']}: gold={gold} | gpt5.5={'OK' if last_int(g['text'])==gold else 'x'} | "
              f"cheap-ens {votes}->{winner} {'OK' if ok else 'x'}", flush=True)

    n = len(items)
    print(f"\n== CHEAP-only ensemble vs GPT-5.5 on all {n} super-hard tasks ==")
    print(f"  {'system':34} {'accuracy':>12} {'$/task':>9} {'total$':>9}")
    print(f"  {'GPT-5.5 (single frontier call)':34} {gpt['ok']}/{n}={gpt['ok']/n:>5.3f} {gpt['usd']/n:>9.4f} {gpt['usd']:>9.4f}")
    for m in CHEAP3:
        print(f"  {'  solo '+SHORT[m]:34} {solo[m]['ok']}/{n}={solo[m]['ok']/n:>5.3f} {solo[m]['usd']/n:>9.5f} {solo[m]['usd']:>9.4f}")
    print(f"  {'CHEAP ENSEMBLE (3 cheap, vote)':34} {ens['ok']}/{n}={ens['ok']/n:>5.3f} {ens['usd']/n:>9.4f} {ens['usd']:>9.4f}")
    ratio = gpt['usd'] / ens['usd'] if ens['usd'] else 0
    print(f"\n  cheap ensemble is {ratio:.1f}x {'cheaper' if ratio>1 else 'MORE EXPENSIVE'} than always-GPT-5.5; "
          f"accuracy {ens['ok']/n:.3f} vs GPT-5.5 {gpt['ok']/n:.3f}")
    json.dump({"n": n, "gpt": gpt, "solo": {SHORT[m]: solo[m] for m in CHEAP3}, "ensemble": ens, "per_task": per},
              open(os.path.join(HERE, "cheap_ensemble_results.json"), "w"), indent=1)
    print("wrote cheap_ensemble_results.json | cache:", CACHE.stats())


if __name__ == "__main__":
    main()
