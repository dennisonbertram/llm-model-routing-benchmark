"""L3a — FrugalGPT-style cascade: cheap → verification gate → strong.

FrugalGPT (Chen/Zaharia/Zou, 2023): call the cheap model first; a verification gate decides
whether to accept the cheap answer or escalate to the strong model.

Verification strategies by discipline:
  - math / qa:  ask cheap model to SELF-RATE confidence 0.0–1.0 for its own answer;
                escalate when confidence < threshold.
  - coding:    ask cheap verifier "is this code correct? Reply YES or NO." (cheap LLM judge);
               escalate when verifier says NO.

We sweep the confidence threshold (0.1 … 0.9) to trace the cost-quality trade-off.
Results are compared against:
  - always-cheap (baseline from labelset_export.json — no extra bills)
  - always-strong (same source)
  - oracle (same source)

IMPORTANT: All cascade logic makes FRESH LIVE API CALLS (confidence-rating + verifier calls).
Cheap-model answers reuse the harness labelset cache to avoid re-billing the primary answers.
"""
import json
import os
import re
import sys

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

import config  # noqa: E402
import tasks   # noqa: E402
from cache import Cache  # noqa: E402
from providers import chat  # noqa: E402
from router_base import _budget  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
LABELSET = os.path.join(HARNESS, ".cache", "labelset_export.json")
# Own cache for cascade verification calls — never touches harness/.cache/labelset.json
CASCADE_CACHE = Cache(os.path.join(HERE, ".cache.json"))

CHEAP = config.CHEAP_DEFAULT    # gpt-4o-mini
STRONG = config.STRONG_DEFAULT  # gpt-4.1


# ── load the pre-measured labelset (RouterBench methodology) ────────────────────────────────────
def load_labelset():
    with open(LABELSET) as f:
        rows = json.load(f)
    # index by id for easy lookup
    return {r["id"]: r for r in rows}


# ── build a task-id → item lookup from the live tasks list ──────────────────────────────────────
def load_tasks():
    return {it["id"]: it for it in tasks.ALL}


# ── harness labelset cache: reuse cheap+strong primary answers ───────────────────────────────────
def load_labelset_cache():
    """Load the harness labelset.json so we can replay cheap answers without re-billing."""
    label_cache_path = os.path.join(HARNESS, ".cache", "labelset.json")
    cache = Cache(label_cache_path)
    return cache


# ── confidence-based gate (math + qa) ───────────────────────────────────────────────────────────
CONF_PROMPT = """You just answered a question. Rate your confidence that your answer is correct.
Reply with ONLY a number between 0.0 and 1.0. No other text.

Question: {question}
Your answer: {answer}"""


def get_confidence(question: str, answer: str) -> tuple[float, float]:
    """Ask cheap model to self-rate confidence. Returns (confidence_0_to_1, usd)."""
    prompt = CONF_PROMPT.format(question=question, answer=answer)
    r = CASCADE_CACHE.chat(CHEAP, [{"role": "user", "content": prompt}],
                           max_tokens=16, temperature=0.0)
    txt = r["text"].strip()
    # parse float from response
    m = re.search(r"[0-9]*\.?[0-9]+", txt)
    conf = float(m.group()) if m else 0.5
    conf = max(0.0, min(1.0, conf))
    return conf, r["usd"]


# ── coding verifier gate ─────────────────────────────────────────────────────────────────────────
VERIFIER_PROMPT = """Review the following Python function. Does it correctly implement the
task described in the docstring / problem statement? Reply with ONLY 'YES' or 'NO'.

PROBLEM:
{question}

CODE:
{code}"""


def verify_code(question: str, code: str) -> tuple[bool, float]:
    """Ask cheap model to verify code correctness. Returns (accepted, usd)."""
    prompt = VERIFIER_PROMPT.format(question=question, code=code)
    r = CASCADE_CACHE.chat(CHEAP, [{"role": "user", "content": prompt}],
                           max_tokens=8, temperature=0.0)
    txt = r["text"].strip().upper()
    accepted = txt.startswith("YES")
    return accepted, r["usd"]


# ── cascade logic ────────────────────────────────────────────────────────────────────────────────
def run_cascade(labelset: dict, tasks_map: dict, threshold: float) -> dict:
    """
    Run the cascade over all 45 items at a given confidence threshold.

    For math/qa: get cheap answer (from labelset cache), ask for confidence,
                 escalate if confidence < threshold.
    For coding:  get cheap answer (from labelset cache), run verifier,
                 escalate if verifier says NO.

    Returns metrics dict: accuracy, total_usd, escalation_rate, n_escalated, per_item.
    """
    label_cache = load_labelset_cache()
    per_item = []
    total_correct = 0
    total_usd = 0.0
    n_escalated = 0

    for task_id, item in sorted(tasks_map.items()):
        lb = labelset[task_id]
        discipline = item["discipline"]

        # Step 1: get cheap answer (reuse harness cache — no re-bill)
        cheap_r = label_cache.chat(CHEAP, [{"role": "user", "content": item["prompt"]}],
                                   max_tokens=_budget(item))
        cheap_answer = cheap_r["text"]
        cheap_usd = cheap_r["usd"]

        gate_usd = 0.0
        escalated = False
        final_answer = cheap_answer
        final_model = CHEAP

        if discipline == "coding":
            # Verification gate: cheap LLM judge
            accepted, gate_usd = verify_code(item["prompt"], cheap_answer)
            if not accepted:
                escalated = True
        else:
            # Confidence gate: self-rating
            conf, gate_usd = get_confidence(item["prompt"], cheap_answer)
            if conf < threshold:
                escalated = True

        strong_usd = 0.0
        if escalated:
            # Make a FRESH LIVE CALL to strong model (NOT from cache to prove it's live)
            strong_r = CASCADE_CACHE.chat(STRONG, [{"role": "user", "content": item["prompt"]}],
                                          max_tokens=_budget(item))
            final_answer = strong_r["text"]
            strong_usd = strong_r["usd"]
            final_model = STRONG
            n_escalated += 1

        correct = bool(item["grade"](final_answer))
        item_usd = cheap_usd + gate_usd + strong_usd
        total_correct += correct
        total_usd += item_usd

        per_item.append({
            "id": task_id,
            "discipline": discipline,
            "difficulty": item["difficulty"],
            "escalated": escalated,
            "final_model": final_model,
            "correct": correct,
            "usd": item_usd,
            "gate_usd": gate_usd,
            "strong_usd": strong_usd,
        })

    label_cache.save()
    CASCADE_CACHE.save()

    n = len(per_item)
    return {
        "threshold": threshold,
        "accuracy": total_correct / n,
        "total_usd": total_usd,
        "n": n,
        "n_escalated": n_escalated,
        "escalation_rate": n_escalated / n,
        "per_item": per_item,
    }


# ── baselines from labelset (no re-bill) ────────────────────────────────────────────────────────
def compute_baselines(labelset: dict) -> dict:
    rows = list(labelset.values())
    n = len(rows)

    cheap_acc = sum(r["cheap_correct"] for r in rows) / n
    cheap_cost = sum(r["cheap_usd"] for r in rows)

    strong_acc = sum(r["strong_correct"] for r in rows) / n
    strong_cost = sum(r["strong_usd"] for r in rows)

    oracle_acc = sum(1 for r in rows if r["cheap_correct"] or r["strong_correct"]) / n
    oracle_cost = sum(
        r["cheap_usd"] if r["cheap_correct"] else r["strong_usd"]
        for r in rows
    )

    return {
        "always_cheap": {"accuracy": cheap_acc, "total_usd": cheap_cost},
        "always_strong": {"accuracy": strong_acc, "total_usd": strong_cost},
        "oracle": {"accuracy": oracle_acc, "total_usd": oracle_cost},
    }


# ── main ─────────────────────────────────────────────────────────────────────────────────────────
def main():
    print("== L3a FrugalGPT Cascade ==")
    print(f"Cheap model : {CHEAP}")
    print(f"Strong model: {STRONG}")
    print()

    labelset = load_labelset()
    tasks_map = load_tasks()

    # Sanity-check: labelset matches tasks list
    assert set(labelset.keys()) == set(tasks_map.keys()), "labelset / tasks mismatch"

    baselines = compute_baselines(labelset)
    always_cheap = baselines["always_cheap"]
    always_strong = baselines["always_strong"]
    oracle = baselines["oracle"]

    print("== Baselines (from labelset, no re-bill) ==")
    print(f"  always-cheap  ({CHEAP}): acc={always_cheap['accuracy']:.3f}  "
          f"${always_cheap['total_usd']:.5f}")
    print(f"  always-strong ({STRONG}): acc={always_strong['accuracy']:.3f}  "
          f"${always_strong['total_usd']:.5f}  "
          f"({always_strong['total_usd']/always_cheap['total_usd']:.1f}x cheap)")
    print(f"  oracle                   : acc={oracle['accuracy']:.3f}  "
          f"${oracle['total_usd']:.5f}")
    print()

    # Coding threshold is fixed (NO = escalate, YES = accept) — threshold param ignored for coding
    # Sweep thresholds for math/qa gate
    thresholds = [0.1, 0.3, 0.5, 0.7, 0.9]

    print("== Cascade sweep (live calls for gate + escalated strong) ==")
    print(f"  (coding items use verifier gate regardless of threshold)")
    print()

    all_results = []
    for thr in thresholds:
        print(f"  Running threshold={thr:.1f} ...")
        result = run_cascade(labelset, tasks_map, thr)
        all_results.append(result)
        pct_strong = always_strong["total_usd"]
        cost_pct = result["total_usd"] / pct_strong * 100
        acc_delta = result["accuracy"] - always_cheap["accuracy"]
        print(f"    acc={result['accuracy']:.3f} (Δ{acc_delta:+.3f} vs cheap)  "
              f"cost=${result['total_usd']:.5f} ({cost_pct:.0f}% of strong)  "
              f"escalation={result['escalation_rate']*100:.0f}%")

    print()
    print("== Results table ==")
    print(f"| strategy             | acc   | cost ($)  | esc-rate | cost-vs-strong |")
    print(f"| -------------------- | ----- | --------- | -------- | -------------- |")
    print(f"| always-cheap         | {always_cheap['accuracy']:.3f} | "
          f"{always_cheap['total_usd']:.5f} | -        | "
          f"{always_cheap['total_usd']/always_strong['total_usd']*100:.0f}%            |")
    for r in all_results:
        pct = r["total_usd"] / always_strong["total_usd"] * 100
        print(f"| cascade thr={r['threshold']:.1f}     | {r['accuracy']:.3f} | "
              f"{r['total_usd']:.5f} | "
              f"{r['escalation_rate']*100:.0f}%      | {pct:.0f}%             |")
    print(f"| always-strong        | {always_strong['accuracy']:.3f} | "
          f"{always_strong['total_usd']:.5f} | 100%     | 100%           |")
    print(f"| oracle               | {oracle['accuracy']:.3f} | "
          f"{oracle['total_usd']:.5f} | (n/a)    | "
          f"{oracle['total_usd']/always_strong['total_usd']*100:.0f}%            |")

    # Find best cascade (highest accuracy, then lowest cost)
    best = max(all_results, key=lambda r: (r["accuracy"], -r["total_usd"]))
    print()
    print(f"== Best cascade (thr={best['threshold']:.1f}) ==")
    print(f"  accuracy:        {best['accuracy']:.3f}")
    print(f"  cost:            ${best['total_usd']:.5f}")
    pct_of_strong = best["total_usd"] / always_strong["total_usd"] * 100
    savings_vs_strong = (1 - best["total_usd"] / always_strong["total_usd"]) * 100
    print(f"  cost vs strong:  {pct_of_strong:.0f}% of always-strong  "
          f"({savings_vs_strong:.0f}% savings)")
    print(f"  escalation rate: {best['escalation_rate']*100:.0f}%")
    print()

    # Verifier error analysis (false accepts — cheap wrong but cascade accepted)
    print("== Verifier / gate error analysis ==")
    best_items = best["per_item"]
    false_accepts = [it for it in best_items if not it["escalated"] and not it["correct"]]
    correct_escalations = [it for it in best_items if it["escalated"] and it["correct"]]
    wrong_escalations = [it for it in best_items if it["escalated"] and not it["correct"]]
    print(f"  False accepts (gate said OK, cheap was wrong): {len(false_accepts)}")
    for it in false_accepts:
        print(f"    - {it['id']} ({it['discipline']}/{it['difficulty']})")
    print(f"  Correct escalations (escalated, strong got it right): {len(correct_escalations)}")
    print(f"  Wrong escalations (escalated, strong also wrong): {len(wrong_escalations)}")

    # Discipline breakdown for best threshold
    print()
    print("== Per-discipline breakdown (best threshold) ==")
    disc_stats = {}
    for it in best_items:
        d = it["discipline"]
        disc_stats.setdefault(d, {"n": 0, "correct": 0, "escalated": 0, "usd": 0.0})
        disc_stats[d]["n"] += 1
        disc_stats[d]["correct"] += int(it["correct"])
        disc_stats[d]["escalated"] += int(it["escalated"])
        disc_stats[d]["usd"] += it["usd"]
    for d, s in sorted(disc_stats.items()):
        print(f"  {d:8}: acc={s['correct']}/{s['n']}={s['correct']/s['n']:.2f}  "
              f"esc={s['escalated']}/{s['n']}  cost=${s['usd']:.5f}")

    # Save summary
    summary = {
        "baselines": baselines,
        "cascade_results": [
            {k: v for k, v in r.items() if k != "per_item"}
            for r in all_results
        ],
        "best_threshold": best["threshold"],
        "best_accuracy": best["accuracy"],
        "best_cost": best["total_usd"],
        "best_escalation_rate": best["escalation_rate"],
        "false_accept_count": len(false_accepts),
        "false_accept_ids": [it["id"] for it in false_accepts],
        "cache_stats": CASCADE_CACHE.stats(),
        "cheap_model": CHEAP,
        "strong_model": STRONG,
    }
    out_path = os.path.join(HERE, "l3a_summary.json")
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nwrote {out_path}")
    print("== done ==")


if __name__ == "__main__":
    main()
