"""S3 (live) — REAL Sakana Fugu vs GPT-5.5, head-to-head on identical tasks.

Subscription now active. We run BOTH Fugu models (fugu = Mini, fugu-ultra = the multi-agent
conductor) over the same 21 authored hard tasks that GPT-5.5 solved 21/21 in S0, with the same
deterministic graders. Question: does Fugu's orchestration beat / match a single frontier call, and
at what real cost? Fugu bills ALL tokens including orchestration ($5/$30 per 1M) — the harness folds
orchestration tokens into the billed cost, so this is the true price of the multi-agent machinery.

Run: set -a; . .agent-university/secrets.local.env; set +a; python3 run_fugu.py
"""
import json
import os
import sys

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
S0 = os.path.join(os.path.dirname(__file__), "..", "..", "S0-hard-suite", "source")
sys.path.insert(0, HARNESS)
sys.path.insert(0, S0)

from cache import Cache  # noqa: E402
import build_hard_suite as hs  # noqa: E402

HERE = os.path.dirname(__file__)
CACHE = Cache(os.path.join(HERE, ".cache.json"))
MODELS = ["gpt-5.5", "fugu", "fugu-ultra"]   # gpt-5.5 reference (re-priced here) + the two Fugu models


def main():
    hs.validate()
    items = hs.build_items()
    agg = {m: {"score": 0.0, "usd": 0.0, "lat": 0, "orch": 0, "total_tok": 0, "n": 0} for m in MODELS}
    rows = []
    for it in items:
        mt = 8000 if it["discipline"] == "coding" else 2048
        row = {"id": it["id"], "disc": it["discipline"]}
        for m in MODELS:
            try:
                r = CACHE.chat(m, [{"role": "user", "content": it["prompt"]}], max_tokens=mt,
                               temperature=0.0, timeout=300)  # fugu-ultra conductor can exceed 120s
            except Exception as e:
                print(f"  [warn] {m} {it['id']} failed: {str(e)[:60]}", flush=True)
                r = {"text": "", "usd": 0.0, "latency_ms": 0, "total_tokens": 0, "raw_usage": {}}
            sc = float(it["grade"](r["text"]))
            ru = r.get("raw_usage", {})
            orch = ((ru.get("prompt_tokens_details") or {}).get("orchestration_input_tokens", 0) or 0) + \
                   ((ru.get("completion_tokens_details") or {}).get("orchestration_output_tokens", 0) or 0)
            agg[m]["score"] += sc; agg[m]["usd"] += r["usd"]; agg[m]["lat"] += r.get("latency_ms", 0)
            agg[m]["orch"] += orch; agg[m]["total_tok"] += r.get("total_tokens", 0); agg[m]["n"] += 1
            row[m] = round(sc, 2)
        rows.append(row)
        CACHE.save()
        print(f"  {it['id']:5} {it['discipline']:7} " + "  ".join(f"{m}={row[m]}" for m in MODELS), flush=True)

    n = len(items)
    print("\n== REAL Fugu vs GPT-5.5 on 21 authored hard tasks (same graders) ==")
    print(f"  {'model':12} {'accuracy':>9} {'total$':>9} {'$/task':>9} {'mean_lat':>9} {'orch_tok/task':>14}")
    for m in MODELS:
        a = agg[m]
        print(f"  {m:12} {a['score']/n:>9.3f} {a['usd']:>9.4f} {a['usd']/n:>9.5f} "
              f"{a['lat']//n:>8}ms {a['orch']//n:>14}")
    # cost multiple vs gpt-5.5
    base = agg["gpt-5.5"]["usd"] / n
    print(f"\n  fugu-ultra costs {(agg['fugu-ultra']['usd']/n)/base:.1f}x a single gpt-5.5 call per task "
          f"(same accuracy region); fugu(mini) {(agg['fugu']['usd']/n)/base:.1f}x.")
    json.dump({"n": n, "rows": rows, "agg": {m: {k: agg[m][k] for k in agg[m]} for m in MODELS}},
              open(os.path.join(HERE, "fugu_results.json"), "w"), indent=1)
    print("wrote fugu_results.json | cache:", CACHE.stats())


if __name__ == "__main__":
    main()
