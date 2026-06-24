"""X6 — Does a frontier reasoning model (GPT-5.5) change the routing story?

The base degree used gpt-4.1 as "strong" (0.978; one item, m8, beat BOTH cheap and strong).
This experiment runs GPT-5.5 and GPT-5.4 over the SAME 45-task suite, live, to answer:
  - Does a stronger model crack the hard-math tail (and the unsolvable m8)?
  - What does it cost vs gpt-4.1 (it is a reasoning model at $5/$30 per 1M)?
  - How does a stronger TOP tier change the oracle ceiling and the routing opportunity?

Run: set -a; . .agent-university/secrets.local.env; set +a; python3 run_x6.py
"""
import json
import os
import sys

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

import tasks  # noqa: E402
from cache import Cache  # noqa: E402

HERE = os.path.dirname(__file__)
CACHE = Cache(os.path.join(HERE, ".cache.json"))
MATRIX = {r["id"]: r for r in json.load(open(os.path.join(HARNESS, ".cache", "labelset_export.json")))}
HARD_MATH = ["m8", "m9", "m10", "m12", "m13", "m14", "m15"]  # m11 was easy; m8 = neither-solved baseline


def run_model(model):
    rec = {"per_item": {}, "usd": 0.0, "lat": [], "out_tok": 0}
    for it in tasks.ALL:
        # reasoning models need a generous budget (hidden reasoning + answer/code)
        mt = 8000 if it["discipline"] == "coding" else 3000
        r = CACHE.chat(model, [{"role": "user", "content": it["prompt"]}], max_tokens=mt)
        ok = bool(it["grade"](r["text"]))
        rec["per_item"][it["id"]] = ok
        rec["usd"] += r["usd"]
        rec["lat"].append(r.get("latency_ms", 0))
        rec["out_tok"] += r.get("billed_completion_tokens", r.get("completion_tokens", 0))
    return rec


def acc(per_item, ids=None):
    ids = ids or [it["id"] for it in tasks.ALL]
    return sum(per_item[i] for i in ids) / len(ids)


def disc_acc(per_item, disc):
    ids = [it["id"] for it in tasks.ALL if it["discipline"] == disc]
    return sum(per_item[i] for i in ids) / len(ids)


def main():
    n = len(tasks.ALL)
    # Baselines from the committed live outcome matrix
    cheap = {i: MATRIX[i]["cheap_correct"] for i in MATRIX}
    strong = {i: MATRIX[i]["strong_correct"] for i in MATRIX}
    cheap_usd = sum(MATRIX[i]["cheap_usd"] for i in MATRIX)
    strong_usd = sum(MATRIX[i]["strong_usd"] for i in MATRIX)

    print("== running frontier models live over 45 tasks (cached after first run) ==")
    results = {}
    for m in ["gpt-5.4", "gpt-5.5"]:
        print(f"  {m} ...", flush=True)
        results[m] = run_model(m)
    CACHE.save()

    rows = [
        ("gpt-4o-mini (cheap)", acc(cheap), cheap_usd, None),
        ("gpt-4.1 (prev strong)", acc(strong), strong_usd, None),
    ]
    for m in ["gpt-5.4", "gpt-5.5"]:
        r = results[m]
        rows.append((m, acc(r["per_item"]), r["usd"], sum(r["lat"]) // n))

    print("\n| model | accuracy | hard-math(7) | coding | cost(45) | vs gpt-4.1 cost | mean latency |")
    print("|---|---|---|---|---|---|---|")
    for name, a, usd, lat in rows:
        if name.startswith("gpt-5"):
            r = results[name]
            hm = sum(r["per_item"][i] for i in HARD_MATH) / len(HARD_MATH)
            cod = disc_acc(r["per_item"], "coding")
            print(f"| {name} | {a:.3f} | {hm:.3f} | {cod:.3f} | ${usd:.5f} | {usd/strong_usd:.1f}x | {lat}ms |")
        else:
            if name.startswith("gpt-4o-mini"):
                hm = sum(cheap[i] for i in HARD_MATH) / len(HARD_MATH)
            else:
                hm = sum(strong[i] for i in HARD_MATH) / len(HARD_MATH)
            print(f"| {name} | {a:.3f} | {hm:.3f} | 1.000 | ${usd:.5f} | {usd/strong_usd:.1f}x | — |")

    # m8 — the item neither cheap nor gpt-4.1 solved
    print(f"\nm8 (neither cheap nor gpt-4.1 solved, gold=14):")
    print(f"  gpt-4o-mini={cheap['m8']}  gpt-4.1={strong['m8']}  "
          f"gpt-5.4={results['gpt-5.4']['per_item']['m8']}  gpt-5.5={results['gpt-5.5']['per_item']['m8']}")

    # New oracle ceilings
    def oracle(top_correct, top_usd_map):
        cost = 0.0; nc = 0
        for i in MATRIX:
            if cheap[i]:
                cost += MATRIX[i]["cheap_usd"]; nc += 1
            elif strong[i]:
                cost += MATRIX[i]["strong_usd"]; nc += 1
            elif top_correct.get(i):
                cost += top_usd_map[i]; nc += 1
            else:
                cost += MATRIX[i]["cheap_usd"]  # unsolvable -> cheapest
        return nc / len(MATRIX), cost

    # per-item gpt-5.5 cost for oracle accounting (approx: total/45 not used; use actual per-item)
    g55 = results["gpt-5.5"]
    # recompute per-item usd for gpt-5.5 from cache for oracle (re-call cached, no spend)
    g55_usd = {}
    for it in tasks.ALL:
        mt = 8000 if it["discipline"] == "coding" else 3000
        rr = CACHE.chat("gpt-5.5", [{"role": "user", "content": it["prompt"]}], max_tokens=mt)
        g55_usd[it["id"]] = rr["usd"]
    base_oracle_acc = sum(1 for i in MATRIX if cheap[i] or strong[i]) / len(MATRIX)
    base_oracle_cost = sum((MATRIX[i]["cheap_usd"] if cheap[i] else (MATRIX[i]["strong_usd"] if strong[i] else MATRIX[i]["cheap_usd"])) for i in MATRIX)
    o3_acc, o3_cost = oracle(g55["per_item"], g55_usd)
    print(f"\nOracle ceilings (cheapest-correct):")
    print(f"  2-tier {{cheap, gpt-4.1}}:          acc={base_oracle_acc:.3f}  ${base_oracle_cost:.5f}")
    print(f"  3-tier {{cheap, gpt-4.1, gpt-5.5}}:  acc={o3_acc:.3f}  ${o3_cost:.5f}")

    json.dump({
        "models": {m: {"acc": acc(results[m]["per_item"]),
                       "hard_math": sum(results[m]["per_item"][i] for i in HARD_MATH) / len(HARD_MATH),
                       "coding": disc_acc(results[m]["per_item"], "coding"),
                       "usd": round(results[m]["usd"], 5),
                       "x_vs_gpt41": round(results[m]["usd"] / strong_usd, 2),
                       "mean_latency_ms": sum(results[m]["lat"]) // n,
                       "out_tokens": results[m]["out_tok"],
                       "m8": results[m]["per_item"]["m8"]} for m in ["gpt-5.4", "gpt-5.5"]},
        "baselines": {"cheap": {"acc": acc(cheap), "usd": round(cheap_usd, 5)},
                      "gpt-4.1": {"acc": acc(strong), "usd": round(strong_usd, 5)}},
        "oracle_2tier": {"acc": round(base_oracle_acc, 3), "usd": round(base_oracle_cost, 5)},
        "oracle_3tier_with_gpt55": {"acc": round(o3_acc, 3), "usd": round(o3_cost, 5)},
    }, open(os.path.join(HERE, "x6_summary.json"), "w"), indent=2)
    print("\nwrote x6_summary.json | cache:", CACHE.stats())


if __name__ == "__main__":
    main()
