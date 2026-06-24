"""S4 — Fugu vs our routers, head-to-head on the SAME 15 fresh tasks. Falsification-oriented.

Every system runs on the identical tasks with identical deterministic graders and identical cost
accounting (uniform token x price; Fugu cost includes its orchestration tokens). We then actively
try to FALSIFY the claim "our routing is cheaper than Fugu at matched accuracy":
  - is Fugu EVER cheaper than a single gpt-5.5 call, per task?
  - is Fugu EVER more accurate than gpt-5.5 / our router, per task?
  - do our routers actually MATCH the frontier/Fugu accuracy, or do they trade accuracy for cost?
  - what is the per-task cost-ratio DISTRIBUTION (min/median/max), so the headline isn't an average fluke?

Routers decide from the PROMPT ONLY (no leakage). The classifier is trained on the OLD 45-task suite
and applied to these NEW tasks (genuine generalization). "cheap"=gpt-4o-mini, "strong"=gpt-5.5.

Run: set -a; . .agent-university/secrets.local.env; set +a; python3 headtohead.py
"""
import hashlib
import json
import os
import re
import statistics
import sys

import warnings

import numpy as np

warnings.filterwarnings("ignore", message=".*matmul.*", category=RuntimeWarning)
np.seterr(all="ignore")  # benign macOS BLAS warnings on clean unit-norm embeddings

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)
sys.path.insert(0, os.path.dirname(__file__))

from cache import Cache  # noqa: E402
from providers import embed  # noqa: E402
import verify_tasks as VT  # noqa: E402

HERE = os.path.dirname(__file__)
CACHE = Cache(os.path.join(HERE, ".cache.json"))
OLD_LABELSET = os.path.join(HARNESS, ".cache", "labelset_export.json")
_EMB = os.path.join(HERE, ".emb_cache.json")

CHEAP, STRONG = "gpt-4o-mini", "gpt-5.5"
SYSTEMS = [CHEAP, STRONG, "fugu", "fugu-ultra"]
REASON_CUES = ["how many", "ways", "divisible", "remainder", "tile", "seat", "round table",
               "envelope", "binary", "prime", "power", "last digit", "distinct"]


def embed_cached(texts):
    store = json.load(open(_EMB)) if os.path.exists(_EMB) else {}
    out, todo, idx = [None] * len(texts), [], []
    for i, t in enumerate(texts):
        k = hashlib.sha256(("e3s\n" + t).encode()).hexdigest()
        if k in store: out[i] = store[k]
        else: todo.append(t); idx.append((i, k))
    if todo:
        vecs, _ = embed(todo)
        for (i, k), v in zip(idx, vecs): out[i] = v; store[k] = v
        json.dump(store, open(_EMB, "w"))
    return np.array(out)


def heuristic_decide(prompt):
    p = prompt.lower()
    score = sum(c in p for c in REASON_CUES) + (1 if len(re.findall(r"\d{3,}", p)) >= 1 else 0)
    return STRONG if score >= 2 else CHEAP


def train_classifier():
    rows = json.load(open(OLD_LABELSET))
    X = embed_cached([r["prompt"] for r in rows])
    y = np.array([float(r["cheap_correct"]) for r in rows])
    w, b = np.zeros(X.shape[1]), 0.0
    for _ in range(600):
        p = 1 / (1 + np.exp(-(X @ w + b)))
        w -= 0.5 * (X.T @ (p - y) / len(y) + 1e-3 * w); b -= 0.5 * float(np.mean(p - y))
    return w, b


def main():
    VT.validate()
    items = VT.ALL
    w, b = train_classifier()
    new_emb = {it["id"]: e for it, e in zip(items, embed_cached([it["prompt"] for it in items]))}

    def classifier_decide(it):
        pr = float(1 / (1 + np.exp(-(new_emb[it["id"]] @ w + b))))
        return CHEAP if pr >= 0.8 else STRONG

    # run every base system on every task
    rec = {m: {} for m in SYSTEMS}   # rec[model][id] = {ok, usd, lat}
    for it in items:
        mt = 8000 if it["discipline"] == "coding" else 2048
        for m in SYSTEMS:
            try:
                r = CACHE.chat(m, [{"role": "user", "content": it["prompt"]}], max_tokens=mt,
                               temperature=0.0, timeout=300)
            except Exception as e:
                print(f"  [warn] {m} {it['id']}: {str(e)[:50]}", flush=True)
                r = {"text": "", "usd": 0.0, "latency_ms": 0}
            rec[m][it["id"]] = {"ok": float(it["grade"](r["text"])), "usd": r["usd"], "lat": r.get("latency_ms", 0)}
        CACHE.save()
        print(f"  {it['id']:6} {it['discipline']:7} " +
              "  ".join(f"{m.split('/')[-1][:10]}={rec[m][it['id']]['ok']:.0f}" for m in SYSTEMS), flush=True)

    # routers reuse the base cheap/strong measured results per task (the model they CHOSE)
    def router_stats(decide):  # decide(item) -> model
        ok = usd = lat = 0.0
        chose = {CHEAP: 0, STRONG: 0}
        for it in items:
            m = decide(it)
            d = rec[m][it["id"]]; ok += d["ok"]; usd += d["usd"]; lat += d["lat"]; chose[m] += 1
        return {"acc": ok / len(items), "usd": usd, "lat": lat / len(items), "chose": chose}

    n = len(items)
    base = {m: {"acc": sum(rec[m][i["id"]]["ok"] for i in items) / n,
                "usd": sum(rec[m][i["id"]]["usd"] for i in items),
                "lat": sum(rec[m][i["id"]]["lat"] for i in items) / n} for m in SYSTEMS}
    heur = router_stats(lambda it: heuristic_decide(it["prompt"]))
    clf = router_stats(lambda it: classifier_decide(it))

    print("\n== HEAD-TO-HEAD on 15 identical tasks ==")
    print(f"  {'system':26} {'acc':>6} {'total$':>9} {'$/task':>9} {'mean_lat':>9}")
    table = [("always gpt-4o-mini (cheap)", base[CHEAP]),
             ("always gpt-5.5 (frontier)", base[STRONG]),
             ("fugu (mini)", base["fugu"]),
             ("fugu-ultra (conductor)", base["fugu-ultra"]),
             ("router: heuristic", heur),
             ("router: classifier(old-suite)", clf)]
    for name, s in table:
        print(f"  {name:26} {s['acc']:>6.3f} {s['usd']:>9.4f} {s['usd']/n:>9.5f} {int(s['lat']):>7}ms")

    print("\n== FALSIFICATION CHECKS ==")
    # 1) per-task: fugu-ultra ever cheaper than gpt-5.5?
    cheaper = [i["id"] for i in items if rec["fugu-ultra"][i["id"]]["usd"] < rec[STRONG][i["id"]]["usd"]]
    print(f"  tasks where fugu-ultra is cheaper than one gpt-5.5 call: {len(cheaper)}/{n} {cheaper}")
    # 2) fugu-ultra ever MORE accurate than gpt-5.5?
    fugu_wins = [i["id"] for i in items if rec["fugu-ultra"][i["id"]]["ok"] > rec[STRONG][i["id"]]["ok"]]
    gpt_wins = [i["id"] for i in items if rec[STRONG][i["id"]]["ok"] > rec["fugu-ultra"][i["id"]]["ok"]]
    print(f"  tasks where fugu-ultra MORE accurate than gpt-5.5: {len(fugu_wins)} {fugu_wins}")
    print(f"  tasks where gpt-5.5 MORE accurate than fugu-ultra: {len(gpt_wins)} {gpt_wins}")
    # 3) do routers match frontier accuracy?
    print(f"  frontier acc={base[STRONG]['acc']:.3f} | heuristic-router acc={heur['acc']:.3f} (chose {heur['chose']}) | "
          f"classifier-router acc={clf['acc']:.3f} (chose {clf['chose']})")
    # 4) per-task cost-ratio distribution fugu-ultra / gpt-5.5 and / classifier-router
    ratios_g = [rec["fugu-ultra"][i["id"]]["usd"] / rec[STRONG][i["id"]]["usd"] for i in items if rec[STRONG][i["id"]]["usd"] > 0]
    print(f"  fugu-ultra / gpt-5.5 cost ratio per task: min={min(ratios_g):.1f}x median={statistics.median(ratios_g):.1f}x max={max(ratios_g):.1f}x")
    # router per-task cost (chosen model) vs fugu-ultra
    clf_task_usd = [rec[classifier_decide(i)][i["id"]]["usd"] for i in items]
    ratios_r = [rec["fugu-ultra"][i["id"]]["usd"] / u for i, u in zip(items, clf_task_usd) if u > 0]
    print(f"  fugu-ultra / classifier-router cost ratio per task: min={min(ratios_r):.0f}x median={statistics.median(ratios_r):.0f}x max={max(ratios_r):.0f}x")

    out = {"n": n, "base": base, "heuristic": heur, "classifier": clf,
           "falsification": {"fugu_cheaper_than_gpt5_tasks": cheaper, "fugu_more_accurate_tasks": fugu_wins,
                             "gpt5_more_accurate_tasks": gpt_wins,
                             "fugu_vs_gpt5_ratio": {"min": min(ratios_g), "median": statistics.median(ratios_g), "max": max(ratios_g)},
                             "fugu_vs_router_ratio": {"min": min(ratios_r), "median": statistics.median(ratios_r), "max": max(ratios_r)}},
           "per_task": {i["id"]: {m: rec[m][i["id"]] for m in SYSTEMS} for i in items}}
    json.dump(out, open(os.path.join(HERE, "headtohead_results.json"), "w"), indent=1)
    print("\nwrote headtohead_results.json | cache:", CACHE.stats())


if __name__ == "__main__":
    main()
