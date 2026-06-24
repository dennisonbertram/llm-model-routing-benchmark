"""S5e — how cheap can a model ensemble get and still rival GPT-5.5?

RouterBench-style: measure each cheap model ONCE on all 56 super-hard tasks (live, cached) -> an
outcome matrix -> then evaluate EVERY 1/3/5/7-model majority-vote ensemble OFFLINE (no new calls).
Report the cost-accuracy Pareto frontier, the cheapest ensemble that matches GPT-5.5's accuracy, and
the free-tier floor (models with a $0 OpenRouter tier). Same deterministic golds as the rest of S5.

Run: set -a; . .agent-university/secrets.local.env; set +a; python3 cheap_sweep.py
"""
import json
import os
import re
import sys
from collections import Counter
from itertools import combinations

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)
sys.path.insert(0, os.path.dirname(__file__))

from concurrent.futures import ThreadPoolExecutor  # noqa: E402
from cache import Cache  # noqa: E402
from providers import chat as live_chat  # noqa: E402
import superhard as S  # noqa: E402

HERE = os.path.dirname(__file__)
CACHE = Cache(os.path.join(HERE, ".cache.json"))

# cheap pool (paid ids; FREE flags those with a $0 OpenRouter tier -> deployable at $0, same model)
# Fast non-reasoning cheap models (answer in 1-5s, no timeouts). GLM-4.7-flash dropped: it reasons
# and times out on every recurrence, dominating wall-clock; DeepSeek-V4-flash ($0.09) is the cheap floor.
POOL = [
    ("deepseek-v4-flash","openrouter/deepseek/deepseek-v4-flash",        False),
    ("llama-3.3-70b",   "openrouter/meta-llama/llama-3.3-70b-instruct",  True),
    ("gemma-4-31b",     "openrouter/google/gemma-4-31b-it",              True),
    ("mistral-small",   "openrouter/mistralai/mistral-small-2603",       False),
    ("deepseek-v3.1",   "openrouter/deepseek/deepseek-chat-v3.1",        False),
    ("qwen-2.5-72b",    "openrouter/qwen/qwen-2.5-72b-instruct",         False),
]
NAME = {short: full for short, full, _ in POOL}
FREE = {short for short, _, f in POOL if f}


def last_int(t):
    n = re.findall(r"-?\d+", (t or "").replace(",", ""))
    return int(n[-1]) if n else None


def call(full, prompt):
    try:
        return CACHE.chat(full, [{"role": "user", "content": prompt}], max_tokens=4000, temperature=0.0, timeout=60)
    except Exception as e:
        print(f"    [warn] {full}: {str(e)[:45]}", flush=True)
        return {"text": "", "usd": 0.0}


def main():
    items = S.gen(seed=7)[:56]
    gold = {it["id"]: it["gold"] for it in items}
    # ---- 1. measure each cheap model once, PARALLEL across all (model,task) pairs (fast-fail 30s) ----
    M = {short: {} for short, _, _ in POOL}   # M[short][task_id] = (int_answer, usd)

    def one(short, full, it):
        try:
            r = live_chat(full, [{"role": "user", "content": it["prompt"]}], max_tokens=4000,
                          temperature=0.0, timeout=25, retries=0)
            return short, it["id"], last_int(r["text"]), r["usd"]
        except Exception:
            return short, it["id"], None, 0.0

    jobs = [(short, full, it) for short, full, _ in POOL for it in items]
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = [ex.submit(one, s, f, it) for s, f, it in jobs]
        for k, fu in enumerate(futs):
            short, tid, ans, usd = fu.result()
            M[short][tid] = (ans, usd)
            if (k + 1) % 56 == 0:
                print(f"  ...{k+1}/{len(jobs)} calls done", flush=True)
    for short, _, _ in POOL:
        acc = sum(1 for it in items if M[short][it["id"]][0] == gold[it["id"]]) / len(items)
        cost = sum(M[short][it["id"]][1] for it in items)
        print(f"  solo {short:18} {acc:.3f}  ${cost/len(items):.5f}/task", flush=True)
    # gpt-5.5 reference (cached from the sweep)
    g = {}
    for it in items:
        r = CACHE.chat("gpt-5.5", [{"role": "user", "content": it["prompt"]}], max_tokens=8000, temperature=0.0, timeout=240)
        g[it["id"]] = (last_int(r["text"]), r["usd"])
    CACHE.save()
    g_acc = sum(1 for it in items if g[it["id"]][0] == gold[it["id"]]) / len(items)
    g_cost = sum(g[it["id"]][1] for it in items) / len(items)

    # ---- 2. evaluate ensembles OFFLINE over the matrix ----
    def evaluate(members):
        ok = cost = 0.0
        for it in items:
            tid = it["id"]
            votes = [M[m][tid][0] for m in members]
            cost += sum(M[m][tid][1] for m in members)
            tally = Counter(v for v in votes if v is not None)
            winner = tally.most_common(1)[0][0] if tally else None
            ok += (winner == gold[tid])
        n = len(items)
        free = all(m in FREE for m in members)
        return {"members": members, "acc": ok / n, "usd_task": cost / n, "free": free}

    shorts = [s for s, _, _ in POOL]
    cand = [[s] for s in shorts]
    cand += [list(c) for c in combinations(shorts, 3)]
    cand += [list(c) for c in combinations(shorts, 5)]
    cand += [shorts]
    rows = [evaluate(c) for c in cand]

    # cost-accuracy Pareto frontier (max acc, min cost)
    def dominated(r, rows):
        return any(s is not r and s["acc"] >= r["acc"] and s["usd_task"] <= r["usd_task"]
                   and (s["acc"] > r["acc"] or s["usd_task"] < r["usd_task"]) for s in rows)
    front = sorted([r for r in rows if not dominated(r, rows)], key=lambda r: r["usd_task"])

    print(f"\n== reference: GPT-5.5 single call: acc={g_acc:.3f}  ${g_cost:.4f}/task ==")
    print("\n== cheap-ensemble cost-accuracy Pareto frontier ==")
    print(f"  {'acc':>5} {'$/task':>9} {'free?':>5}  members")
    for r in front:
        print(f"  {r['acc']:>5.3f} {r['usd_task']:>9.5f} {'FREE' if r['free'] else '':>5}  {'+'.join(r['members'])}")

    best_acc = max(r["acc"] for r in rows)
    cheapest_at_best = min((r for r in rows if r["acc"] == best_acc), key=lambda r: r["usd_task"])
    match_g = [r for r in rows if r["acc"] >= g_acc]
    cheapest_match = min(match_g, key=lambda r: r["usd_task"]) if match_g else None
    free_rows = [r for r in rows if r["free"]]
    best_free = max(free_rows, key=lambda r: r["acc"]) if free_rows else None

    print(f"\n  best cheap-ensemble accuracy: {best_acc:.3f} at ${cheapest_at_best['usd_task']:.5f}/task  ({'+'.join(cheapest_at_best['members'])})")
    if cheapest_match:
        print(f"  cheapest ensemble >= GPT-5.5 ({g_acc:.3f}): {cheapest_match['acc']:.3f} @ ${cheapest_match['usd_task']:.5f}/task "
              f"= {g_cost/cheapest_match['usd_task']:.1f}x cheaper than GPT-5.5 ({'+'.join(cheapest_match['members'])})")
    else:
        print(f"  NO cheap ensemble reached GPT-5.5's {g_acc:.3f}. (best was {best_acc:.3f})")
    if best_free:
        print(f"  FREE-tier floor: best $0 ensemble = {best_free['acc']:.3f} acc ({'+'.join(best_free['members'])})")
    json.dump({"gpt5.5": {"acc": g_acc, "usd_task": g_cost}, "solo": {s: {"acc": sum(1 for it in items if M[s][it['id']][0]==gold[it['id']])/len(items), "usd_task": sum(M[s][it['id']][1] for it in items)/len(items)} for s in shorts},
               "frontier": [{"members": r["members"], "acc": r["acc"], "usd_task": r["usd_task"], "free": r["free"]} for r in front],
               "all": [{"members": r["members"], "acc": r["acc"], "usd_task": r["usd_task"], "free": r["free"]} for r in rows]},
              open(os.path.join(HERE, "cheap_sweep_results.json"), "w"), indent=1)
    print("wrote cheap_sweep_results.json | cache:", CACHE.stats())


if __name__ == "__main__":
    main()
