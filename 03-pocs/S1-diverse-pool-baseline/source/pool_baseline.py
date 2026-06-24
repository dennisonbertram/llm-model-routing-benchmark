"""S1 — diverse-pool solo baselines on the HARD suite (the headroom + complementarity check).

GPT-5.5 saturates every authored deterministic task (S0: 21/21), so it cannot host an orchestration
experiment. Sakana's own ARC-AGI-2 setup used a DIVERSE, individually-NON-saturating pool
(o4-mini + Gemini-2.5-Pro + DeepSeek-R1). We replicate that condition: a diverse cross-architecture
pool via OpenRouter, measured solo on the hard suite, to confirm (a) none saturate and (b) they
COMPLEMENT each other (oracle-over-pool > best-single) — the precondition for Multi-LLM AB-MCTS.

Reuses the S0 candidate items (math golds computed; coding fraction-graded; trap QA). gpt-5.5 stays
as the reference ceiling (the routing alternative), NOT a pool member.

Run: set -a; . .agent-university/secrets.local.env; set +a; python3 pool_baseline.py
"""
import json
import os
import sys

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
S0 = os.path.join(os.path.dirname(__file__), "..", "..", "S0-hard-suite", "source")
sys.path.insert(0, HARNESS)
sys.path.insert(0, S0)

from cache import Cache  # noqa: E402
import build_hard_suite as hs  # noqa: E402  (reuse the authored + validated items)

HERE = os.path.dirname(__file__)
CACHE = Cache(os.path.join(HERE, ".cache.json"))

POOL = [
    "openrouter/deepseek/deepseek-chat-v3.1",
    "openrouter/qwen/qwen-2.5-72b-instruct",
    "openrouter/meta-llama/llama-3.3-70b-instruct",
    "openrouter/mistralai/mistral-medium-3-5",
    "openrouter/google/gemini-2.5-flash-lite-preview-09-2025",
]
SHORT = {m: m.split("/")[-1][:22] for m in POOL}


def main():
    hs.validate()
    items = hs.build_items()
    # scores[item_id][model] = float in [0,1]
    scores = {it["id"]: {} for it in items}
    cost = {m: 0.0 for m in POOL}
    for it in items:
        mt = 8000 if it["discipline"] == "coding" else 2048
        for m in POOL:
            r = CACHE.chat(m, [{"role": "user", "content": it["prompt"]}], max_tokens=mt)
            s = float(it["grade"](r["text"]))
            scores[it["id"]][m] = s
            cost[m] += r["usd"]
        CACHE.save()  # incremental: crash-safe + lets a re-run resume from cache
        print(f"  done {it['id']:5} ({it['discipline']})", flush=True)

    ids = [it["id"] for it in items]
    disc = {it["id"]: it["discipline"] for it in items}
    n = len(ids)

    def acc(m):
        return sum(scores[i][m] for i in ids) / n

    print("== diverse pool solo on the HARD suite (21 items; coding scored as pass-fraction) ==")
    for m in POOL:
        cod = [scores[i][m] for i in ids if disc[i] == "coding"]
        mat = [scores[i][m] for i in ids if disc[i] == "math"]
        qa = [scores[i][m] for i in ids if disc[i] == "qa"]
        print(f"  {SHORT[m]:24} all={acc(m):.3f}  coding={sum(cod)/len(cod):.3f}  "
              f"math={sum(mat)/len(mat):.3f}  qa={sum(qa)/len(qa):.3f}  ${cost[m]:.4f}")

    best_single = max(acc(m) for m in POOL)
    best_model = max(POOL, key=acc)
    oracle = sum(max(scores[i][m] for m in POOL) for i in ids) / n
    print(f"\n  best single model : {SHORT[best_model]} = {best_single:.3f}")
    print(f"  ORACLE over pool  : {oracle:.3f}  (max per item across the pool)")
    print(f"  complementarity headroom (oracle - best_single): {oracle - best_single:+.3f}")

    # which items does the best single FAIL but some other pool model gets? (the AB-MCTS opportunity)
    opp = []
    for i in ids:
        if scores[i][best_model] < 1.0 and max(scores[i][m] for m in POOL) > scores[i][best_model]:
            winners = [SHORT[m] for m in POOL if scores[i][m] == max(scores[i][mm] for mm in POOL)]
            opp.append((i, disc[i], round(scores[i][best_model], 2), round(max(scores[i][m] for m in POOL), 2), winners))
    print(f"\n  items where another model beats the best-single ({len(opp)}):")
    for i, d, bs, mx, w in opp:
        print(f"    {i:5} {d:7} best-single={bs} pool-max={mx} via {w}")

    json.dump({"scores": scores, "pool": POOL, "best_model": best_model, "best_single": best_single,
               "oracle": oracle, "cost": cost}, open(os.path.join(HERE, "pool_baseline.json"), "w"), indent=1)
    print("\nwrote pool_baseline.json | cache:", CACHE.stats())


if __name__ == "__main__":
    main()
