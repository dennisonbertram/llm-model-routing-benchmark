"""S5f — near-frontier CHEAP trio vs GPT-5.5 on all 56 super-hard tasks.

The real contenders just behind the frontier (all far cheaper than GPT-5.5's $5/$30):
  GLM-5.2 ($0.98/$3.08), DeepSeek-V4-pro ($0.43/$0.87), Gemini-3.5-Flash ($1.50/$9.00).
Measure each solo (PARALLEL across all model,task pairs), then the 3-way majority-vote ensemble.
Report accuracy + $/task vs a single GPT-5.5 call. Same deterministic golds.

Run: set -a; . .agent-university/secrets.local.env; set +a; python3 nearfrontier.py
"""
import json
import os
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)
sys.path.insert(0, os.path.dirname(__file__))
from cache import Cache  # noqa: E402
from providers import chat as live_chat  # noqa: E402
import superhard as S  # noqa: E402

HERE = os.path.dirname(__file__)
CACHE = Cache(os.path.join(HERE, ".cache.json"))
POOL = [
    ("glm-5.2",          "openrouter/z-ai/glm-5.2"),
    ("deepseek-v4-pro",  "openrouter/deepseek/deepseek-v4-pro"),
    ("gemini-3.5-flash", "openrouter/google/gemini-3.5-flash"),
]


def last_int(t):
    n = re.findall(r"-?\d+", (t or "").replace(",", ""))
    return int(n[-1]) if n else None


def main():
    items = S.gen(seed=7)[:56]
    gold = {it["id"]: it["gold"] for it in items}
    M = {s: {} for s, _ in POOL}

    def one(short, full, it):
        try:
            r = live_chat(full, [{"role": "user", "content": it["prompt"]}], max_tokens=4000,
                          temperature=0.0, timeout=120, retries=0)
            return short, it["id"], last_int(r["text"]), r["usd"]
        except Exception:
            return short, it["id"], None, 0.0

    jobs = [(s, f, it) for s, f in POOL for it in items]
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = [ex.submit(one, s, f, it) for s, f, it in jobs]
        for k, fu in enumerate(futs):
            s, tid, ans, usd = fu.result()
            M[s][tid] = (ans, usd)
            if (k + 1) % 28 == 0:
                print(f"  ...{k+1}/{len(jobs)} calls done", flush=True)

    # gpt-5.5 reference (cached)
    g = {}
    for it in items:
        r = CACHE.chat("gpt-5.5", [{"role": "user", "content": it["prompt"]}], max_tokens=8000, temperature=0.0, timeout=240)
        g[it["id"]] = (last_int(r["text"]), r["usd"])
    CACHE.save()

    n = len(items)
    def acc_cost(getans):
        ok = c = 0.0
        for it in items:
            a, u = getans(it["id"]); ok += (a == gold[it["id"]]); c += u
        return ok / n, c / n
    print(f"\n== near-frontier cheap trio vs GPT-5.5 on {n} super-hard tasks ==")
    print(f"  {'system':30} {'accuracy':>10} {'$/task':>9} {'vs GPT-5.5 cost':>16}")
    ga, gc = acc_cost(lambda t: g[t])
    print(f"  {'GPT-5.5 (single frontier call)':30} {ga:>10.3f} {gc:>9.4f} {'1x':>16}")
    solo = {}
    for s, _ in POOL:
        a, c = acc_cost(lambda t, s=s: M[s][t]); solo[s] = (a, c)
        print(f"  {'  solo '+s:30} {a:>10.3f} {c:>9.5f} {gc/c if c else 0:>15.1f}x")

    # 3-way majority vote ensemble
    def ens(t):
        votes = [M[s][t][0] for s, _ in POOL]
        cost = sum(M[s][t][1] for s, _ in POOL)
        tally = Counter(v for v in votes if v is not None)
        return (tally.most_common(1)[0][0] if tally else None), cost
    ea, ec = acc_cost(ens)
    print(f"  {'ENSEMBLE (3-way vote)':30} {ea:>10.3f} {ec:>9.4f} {gc/ec if ec else 0:>15.1f}x")
    best_solo = max(solo.values())[0]
    print(f"\n  best single of trio: {best_solo:.3f} | ensemble: {ea:.3f} | GPT-5.5: {ga:.3f}")
    print(f"  ensemble vs GPT-5.5: {'MATCHES/BEATS' if ea>=ga else f'{ga-ea:+.3f} below'} at {gc/ec if ec else 0:.1f}x lower cost")
    json.dump({"n": n, "gpt5.5": {"acc": ga, "usd_task": gc},
               "solo": {s: {"acc": solo[s][0], "usd_task": solo[s][1]} for s, _ in POOL},
               "ensemble": {"acc": ea, "usd_task": ec},
               "per_task": {it["id"]: {"gold": gold[it["id"]], "gpt5.5": g[it["id"]][0],
                                       **{s: M[s][it["id"]][0] for s, _ in POOL}} for it in items}},
              open(os.path.join(HERE, "nearfrontier_results.json"), "w"), indent=1)
    print("wrote nearfrontier_results.json | cache:", CACHE.stats())


if __name__ == "__main__":
    main()
