"""S5g — group models by COST TIER, then benchmark within-tier ensembles (test the user's hypothesis).

Hypothesis: the near-frontier ensemble lost partly because Gemini-3.5-Flash inflated COST while
weaker members diluted ACCURACY. So: tier the 9 cheap models by $/task and evaluate cost-matched
ensembles. Build the full 9-model per-task outcome matrix (6 fast cheap measured live here; the 3
near-frontier answers reused from nearfrontier_results.json), then evaluate ALL 1/2/3-model votes
OFFLINE with cost = sum of members' avg $/task. Same 56 super-hard tasks.

Run: set -a; . .agent-university/secrets.local.env; set +a; python3 tier_sweep.py
"""
import json
import os
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from itertools import combinations

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS); sys.path.insert(0, os.path.dirname(__file__))
from providers import chat as live_chat  # noqa: E402
import superhard as S  # noqa: E402

HERE = os.path.dirname(__file__)
FAST6 = [  # (name, full id) measured live here
    ("deepseek-v4-flash", "openrouter/deepseek/deepseek-v4-flash"),
    ("llama-3.3-70b", "openrouter/meta-llama/llama-3.3-70b-instruct"),
    ("gemma-4-31b", "openrouter/google/gemma-4-31b-it"),
    ("mistral-small", "openrouter/mistralai/mistral-small-2603"),
    ("deepseek-v3.1", "openrouter/deepseek/deepseek-chat-v3.1"),
    ("qwen-2.5-72b", "openrouter/qwen/qwen-2.5-72b-instruct"),
]
NF = ["glm-5.2", "deepseek-v4-pro", "gemini-3.5-flash"]  # reused from nearfrontier_results.json
# solo avg $/task (measured: cheap_sweep_results.json + nearfrontier_results.json)
COST = {"deepseek-v4-flash": 0.00046, "llama-3.3-70b": 0.00025, "gemma-4-31b": 0.00018,
        "mistral-small": 0.00103, "deepseek-v3.1": 0.00165, "qwen-2.5-72b": 0.00002,
        "glm-5.2": 0.00551, "deepseek-v4-pro": 0.00212, "gemini-3.5-flash": 0.02608}
GPT_COST = 0.0299


def last_int(t):
    n = re.findall(r"-?\d+", (t or "").replace(",", "")); return int(n[-1]) if n else None


def main():
    items = S.gen(seed=7)[:56]; gold = {it["id"]: it["gold"] for it in items}
    nf = json.load(open(os.path.join(HERE, "nearfrontier_results.json")))["per_task"]
    ANS = {m: {} for m in [n for n, _ in FAST6] + NF}      # ANS[model][task] = int
    for m in NF:
        for tid in nf:
            ANS[m][tid] = nf[tid][m]
    gpt = {tid: nf[tid]["gpt5.5"] for tid in nf}

    # measure the 6 fast cheap models live (parallel)
    def one(name, full, it):
        try:
            r = live_chat(full, [{"role": "user", "content": it["prompt"]}], max_tokens=4000, temperature=0.0, timeout=30, retries=0)
            return name, it["id"], last_int(r["text"])
        except Exception:
            return name, it["id"], None
    jobs = [(n, f, it) for n, f in FAST6 for it in items]
    with ThreadPoolExecutor(max_workers=12) as ex:
        for fu in [ex.submit(one, n, f, it) for n, f, it in jobs]:
            n, tid, a = fu.result(); ANS[n][tid] = a
    print("measured 6 fast cheap models", flush=True)

    models = [n for n, _ in FAST6] + NF
    def solo_acc(m): return sum(1 for it in items if ANS[m][it["id"]] == gold[it["id"]]) / len(items)
    def ens_eval(members):
        ok = 0
        for it in items:
            votes = [ANS[m][it["id"]] for m in members]
            tally = Counter(v for v in votes if v is not None)
            ok += (tally.most_common(1)[0][0] if tally else None) == gold[it["id"]]
        cost = sum(COST[m] for m in members)
        return ok / len(items), cost

    # cost tiers
    TIERS = {"T1 ultra (<$0.0005)": [m for m in models if COST[m] < 0.0005],
             "T2 cheap ($0.0005-0.003)": [m for m in models if 0.0005 <= COST[m] < 0.003],
             "T3 mid ($0.003-0.03)": [m for m in models if COST[m] >= 0.003]}

    print(f"\nGPT-5.5 reference: acc={solo_ref():.3f} ${GPT_COST:.4f}/task" if False else
          f"\nGPT-5.5 reference: acc={sum(1 for it in items if gpt[it['id']]==gold[it['id']])/len(items):.3f}  ${GPT_COST:.4f}/task")
    print("\n== solo accuracies by cost tier ==")
    for tname, ms in TIERS.items():
        print(f"  {tname}")
        for m in sorted(ms, key=lambda m: COST[m]):
            print(f"    {m:20} acc={solo_acc(m):.3f}  ${COST[m]:.5f}/task")

    print("\n== WITHIN-TIER (cost-matched) ensembles: does voting beat the tier's best single? ==")
    for tname, ms in TIERS.items():
        if len(ms) < 2:
            continue
        best_single = max((solo_acc(m), m) for m in ms)
        combos = [list(c) for k in (3, len(ms)) for c in combinations(ms, k) if 2 <= k <= len(ms)]
        seen = set(); uniq = []
        for c in combos:
            key = tuple(sorted(c))
            if key not in seen: seen.add(key); uniq.append(c)
        best_ens = max((ens_eval(c)[0], c) for c in uniq) if uniq else (0, [])
        print(f"  {tname}: best single = {best_single[0]:.3f} ({best_single[1]}); "
              f"best cost-matched ensemble = {best_ens[0]:.3f} ({'+'.join(best_ens[1])})")
        for c in uniq:
            a, cst = ens_eval(c); print(f"      {a:.3f}  ${cst:.5f}/task  {'+'.join(c)}")

    # overall cost-accuracy frontier across all singles + 2/3 combos
    cand = [[m] for m in models] + [list(c) for c in combinations(models, 2)] + [list(c) for c in combinations(models, 3)]
    rows = [{"members": c, "acc": ens_eval(c)[0], "cost": ens_eval(c)[1]} for c in cand]
    def dom(r): return any(s is not r and s["acc"] >= r["acc"] and s["cost"] <= r["cost"] and (s["acc"] > r["acc"] or s["cost"] < r["cost"]) for s in rows)
    front = sorted([r for r in rows if not dom(r)], key=lambda r: r["cost"])
    print("\n== overall cost-accuracy Pareto frontier (singles + 2/3 votes) ==")
    for r in front:
        print(f"  acc={r['acc']:.3f}  ${r['cost']:.5f}/task  {'+'.join(r['members'])}")
    g_acc = sum(1 for it in items if gpt[it["id"]] == gold[it["id"]]) / len(items)
    beats = [r for r in rows if r["acc"] >= g_acc]
    if beats:
        ch = min(beats, key=lambda r: r["cost"])
        print(f"\n  cheapest config >= GPT-5.5 ({g_acc:.3f}): {ch['acc']:.3f} @ ${ch['cost']:.5f}/task "
              f"({GPT_COST/ch['cost']:.1f}x cheaper) = {'+'.join(ch['members'])}")
    json.dump({"solo": {m: {"acc": solo_acc(m), "cost": COST[m]} for m in models},
               "gpt5.5": {"acc": g_acc, "cost": GPT_COST}, "frontier": [{"members": r["members"], "acc": r["acc"], "cost": r["cost"]} for r in front]},
              open(os.path.join(HERE, "tier_sweep_results.json"), "w"), indent=1)
    print("wrote tier_sweep_results.json")


def solo_ref():
    return 0.0


if __name__ == "__main__":
    main()
