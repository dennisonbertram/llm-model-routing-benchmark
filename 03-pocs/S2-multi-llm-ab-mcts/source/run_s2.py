"""S2 — Multi-LLM AB-MCTS over a diverse pool on the HARD coding slice (the faithful Sakana test).

Question: does adaptive multi-model tree search (AB-MCTS) over a diverse, individually-non-saturating
pool beat the best single model AND simple repeated sampling at matched budget — on verifiable coding,
where a code-runner is a reliable node evaluator (the condition the paper says is required)?

NO LEAKAGE: each coding task's asserts are split into PUBLIC (search/verifier signal) and HIDDEN
(final eval). The search and the refine feedback only ever see PUBLIC tests; we report HIDDEN
pass-fraction. gpt-5.5-solo is the reference ceiling (the routing alternative), not a pool member.

Run: set -a; . .agent-university/secrets.local.env; set +a; python3 run_s2.py
"""
import json
import os
import sys

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
S0 = os.path.join(os.path.dirname(__file__), "..", "..", "S0-hard-suite", "source")
sys.path.insert(0, HARNESS)
sys.path.insert(0, S0)

import tasks  # noqa: E402
from cache import Cache  # noqa: E402
import build_hard_suite as hs  # noqa: E402
from abmcts import ab_mcts_multi  # noqa: E402

HERE = os.path.dirname(__file__)
CACHE = Cache(os.path.join(HERE, ".cache.json"))

# 3 diverse architectures (DeepSeek / Alibaba-Qwen / Google), all fast+reliable via OpenRouter.
POOL = [
    "openrouter/deepseek/deepseek-chat-v3.1",
    "openrouter/qwen/qwen-2.5-72b-instruct",
    "openrouter/google/gemini-2.5-flash-lite-preview-09-2025",
]
SHORT = {m: m.split("/")[-1][:18] for m in POOL}
REF = "gpt-5.5"
BUDGETS = [1, 8]  # budget 16 over slow OpenRouter calls hung; 1+8 already show the plateau conclusively
GEN_TOK = 4000
TIMEOUT = 40


def safe_chat(model, prompt, nonce=None, mt=GEN_TOK, temperature=0.0):
    """Tolerant cached call: a stalled/failed provider returns empty text (score 0) instead of
    hanging or crashing the whole run. Cache makes re-runs resume."""
    try:
        return CACHE.chat(model, [{"role": "user", "content": prompt}], max_tokens=mt,
                          temperature=temperature, nonce=nonce, timeout=TIMEOUT)
    except Exception as e:
        print(f"    [warn] {model} failed: {str(e)[:70]}", flush=True)
        return {"text": "", "usd": 0.0}


def split_tests(tlist):
    """~60% public (search signal) / 40% hidden (eval). Deterministic split."""
    k = max(1, int(round(len(tlist) * 0.6)))
    return tlist[:k], tlist[k:]


def coding_items():
    out = []
    for cid, fn, prompt, tlist, ref in hs.CODE:
        pub, hid = split_tests(tlist)
        out.append({"id": cid, "fn": fn, "prompt": prompt,
                    "pub_grade": tasks.code_grader_frac(pub, func_required=fn),
                    "hid_grade": tasks.code_grader_frac(hid, func_required=fn),
                    "n_pub": len(pub), "n_hid": len(hid)})
    return out


def gen_call(prompt, model, nonce):
    r = safe_chat(model, prompt, nonce=nonce, temperature=0.7)
    return r["text"], r["usd"]


def refine_call(prompt, parent_code, model, nonce):
    rp = (f"{prompt}\n\nA previous attempt:\n```python\n{tasks.extract_code(parent_code)}\n```\n"
          f"Some tests still fail. Produce a corrected, complete solution as a single python code block.")
    r = safe_chat(model, rp, nonce=nonce, temperature=0.7)
    return r["text"], r["usd"]


def main():
    hs.validate()
    items = coding_items()
    print(f"== S2: {len(items)} hard coding tasks; pool={[SHORT[m] for m in POOL]} ==")
    print(f"   public/hidden test split per item: {[(it['id'], it['n_pub'], it['n_hid']) for it in items]}\n")

    # reference: gpt-5.5 solo (1 attempt, temp 0) -> hidden frac
    ref_hidden = []
    ref_cost = 0.0
    for it in items:
        r = safe_chat(REF, it["prompt"], temperature=0.0)
        ref_hidden.append(it["hid_grade"](r["text"]))
        ref_cost += r["usd"]
    CACHE.save()
    print(f"reference gpt-5.5 solo: hidden mean={sum(ref_hidden)/len(items):.3f}  ${ref_cost:.4f}\n", flush=True)

    results = {}  # method -> {hidden_mean, solved, cost}
    # best single pool model, solo (temp 0)
    for m in POOL:
        hid = []
        c = 0.0
        for it in items:
            r = safe_chat(m, it["prompt"], temperature=0.0)
            hid.append(it["hid_grade"](r["text"]))
            c += r["usd"]
        results[f"solo:{SHORT[m]}"] = {"hidden": sum(hid) / len(items),
                                       "solved": sum(1 for h in hid if h == 1.0), "cost": c, "calls": len(items)}
        CACHE.save()
        print(f"  solo done {SHORT[m]}: hidden={results[f'solo:{SHORT[m]}']['hidden']:.3f}", flush=True)
    best_solo = max((k for k in results if k.startswith("solo:")), key=lambda k: results[k]["hidden"])
    print("solo baselines (hidden):")
    for k in sorted([k for k in results if k.startswith("solo:")], key=lambda k: -results[k]["hidden"]):
        print(f"  {k:28} hidden={results[k]['hidden']:.3f}  solved={results[k]['solved']}/{len(items)}  ${results[k]['cost']:.4f}")
    print(f"  best single = {best_solo}\n")

    # budget sweep: repeated-sampling (best solo model) vs Multi-LLM AB-MCTS
    best_model = next(m for m in POOL if SHORT[m] == best_solo.split("solo:")[1])
    for B in BUDGETS:
        # repeated sampling with the best single model: B fresh temp-0.7 samples, pick best by PUBLIC, report HIDDEN
        rs_hid = []
        rs_cost = 0.0
        for it in items:
            cands = []
            for j in range(B):
                t, c = gen_call(it["prompt"], best_model, nonce=f"rs-{B}-{j}")
                rs_cost += c
                cands.append((it["pub_grade"](t), it["hid_grade"](t)))
            cands.sort(key=lambda x: -x[0])  # pick best by public
            rs_hid.append(cands[0][1])
        results[f"repeated@{B}:{best_solo.split(':')[1]}"] = {
            "hidden": sum(rs_hid) / len(items), "solved": sum(1 for h in rs_hid if h == 1.0),
            "cost": rs_cost, "calls": B * len(items)}

        # Multi-LLM AB-MCTS at budget B
        ab_hid = []
        ab_cost = 0.0
        pulls_tot = {m: 0 for m in POOL}
        for it in items:
            step = {"n": 0}

            def gfn(model, _it=it, _step=step):
                _step["n"] += 1
                return gen_call(_it["prompt"], model, nonce=f"ab-{B}-g{_step['n']}")

            def rfn(parent_text, model, _it=it, _step=step):
                _step["n"] += 1
                return refine_call(_it["prompt"], parent_text, model, nonce=f"ab-{B}-r{_step['n']}")

            out = ab_mcts_multi(POOL, gfn, rfn, it["pub_grade"], budget=B, seed=0)
            ab_cost += out["cost"]
            ab_hid.append(it["hid_grade"](out["best"].text))
            for m, p in out["pulls"].items():
                pulls_tot[m] += p
        results[f"ab-mcts@{B}"] = {"hidden": sum(ab_hid) / len(items),
                                   "solved": sum(1 for h in ab_hid if h == 1.0), "cost": ab_cost,
                                   "calls": sum(pulls_tot.values()), "pulls": {SHORT[m]: pulls_tot[m] for m in POOL}}
        CACHE.save()
        print(f"  budget {B} done: repeated hidden={results[f'repeated@{B}:'+best_solo.split(':')[1]]['hidden']:.3f} "
              f"ab-mcts hidden={results[f'ab-mcts@{B}']['hidden']:.3f}", flush=True)
    CACHE.save()

    print("== budget sweep (HIDDEN pass-fraction; solved = hidden==1.0) ==")
    print(f"  {'method':28} {'hidden':>7} {'solved':>8} {'calls':>6} {'cost':>9}")
    print(f"  {'gpt-5.5 solo (ref ceiling)':28} {sum(ref_hidden)/len(items):>7.3f} "
          f"{sum(1 for h in ref_hidden if h==1.0):>5}/{len(items)} {len(items):>6} {ref_cost:>9.4f}")
    print(f"  {best_solo+' (best single)':28} {results[best_solo]['hidden']:>7.3f} "
          f"{results[best_solo]['solved']:>5}/{len(items)} {results[best_solo]['calls']:>6} {results[best_solo]['cost']:>9.4f}")
    for B in BUDGETS:
        for tag in (f"repeated@{B}:{best_solo.split(':')[1]}", f"ab-mcts@{B}"):
            r = results[tag]
            print(f"  {tag:28} {r['hidden']:>7.3f} {r['solved']:>5}/{len(items)} {r['calls']:>6} {r['cost']:>9.4f}")
        ab = results[f"ab-mcts@{B}"]
        print(f"      ab-mcts@{B} per-arm pulls: {ab['pulls']}")

    json.dump({"items": [it["id"] for it in items], "pool": POOL, "best_solo": best_solo,
               "ref_gpt55_hidden": sum(ref_hidden) / len(items), "results": results},
              open(os.path.join(HERE, "s2_results.json"), "w"), indent=1)
    print("\nwrote s2_results.json | cache:", CACHE.stats())


if __name__ == "__main__":
    main()
