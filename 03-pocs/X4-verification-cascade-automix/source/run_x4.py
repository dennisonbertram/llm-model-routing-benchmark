"""X4 — AutoMix-style verification cascade.

STRATEGY:
  1. gpt-4o-mini (cheap) answers the question.
  2. gpt-4o-mini self-verifies by taking k=3 independent "Is this answer correct? Answer ONLY yes or no."
     samples at temperature=0.8. The fraction of 'yes' responses is the cheap model's confidence.
  3. If confidence >= threshold T, accept the cheap answer. Otherwise escalate to gpt-4.1 (strong).
  4. Sweep T in {0.0, 0.33, 0.67, 1.0} to trace the cost-quality curve.

The cheap-model confidence is the *verifier signal* — we measure its calibration separately:
  - When the verifier says low-confidence, was the cheap answer really wrong?

COST ACCOUNTING:
  - We use the labelset_export.json (RouterBench methodology) to skip re-billing cheap/strong
    ANSWER calls for items already in the cache.
  - Verifier calls (k=3 per item per threshold) ARE new live calls — these are the novel behavior
    this POC measures. We do make real live API calls for these.
  - A small live confirmation (a single real item through the full cascade) is performed and
    recorded at the start.

Oracle (from L0): acc 0.978, $0.00214.
Baselines (from L0): cheap 0.844 / $0.00166; strong 0.978 / $0.02148.
"""
import json
import os
import sys

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

import config
import tasks
from cache import Cache
from providers import chat
from router_base import _budget

HERE = os.path.dirname(__file__)
OWN_CACHE_PATH = os.path.join(HERE, ".cache.json")
LABELSET_PATH = os.path.join(HARNESS, ".cache", "labelset_export.json")

# Verifier prompt template — asks the cheap model to self-verify its own answer.
# We deliberately do NOT tell it the correct answer; it must judge from first principles.
VERIFY_SYS = (
    "You are a careful answer validator. You will be shown a question and an answer. "
    "Your only job is to assess if the answer is correct. "
    "Reply with exactly ONE word: 'yes' if the answer is correct, 'no' if it is wrong or uncertain."
)


def verifier_confidence(item, cheap_answer, cache, k=3):
    """Run k verifier samples on (item, cheap_answer). Return fraction of 'yes' responses.

    Each sample is an independent call at temperature=0.8 with a distinct nonce so the cache
    stores all k separately and never collapses them.
    """
    verify_prompt = (
        f"QUESTION:\n{item['prompt']}\n\n"
        f"PROPOSED ANSWER:\n{cheap_answer}\n\n"
        "Is this answer correct? Reply with exactly ONE word: yes or no."
    )
    msgs = [{"role": "user", "content": verify_prompt}]
    votes = []
    total_usd = 0.0
    for i in range(k):
        r = cache.chat(
            config.CHEAP_DEFAULT,
            msgs,
            max_tokens=8,
            temperature=0.8,
            system=VERIFY_SYS,
            nonce=f"x4_verify_{item['id']}_{i}",
        )
        raw = r["text"].strip().lower()
        # Accept 'yes' if the response starts with 'yes'; treat anything else as 'no'
        votes.append(1 if raw.startswith("yes") else 0)
        total_usd += r["usd"]
    return sum(votes) / len(votes), total_usd, votes


def run_automix_from_labels(labelset, thresholds, verifier_cache, k=3, verbose=False):
    """Simulate the AutoMix cascade using the pre-measured label matrix + fresh verifier calls.

    For every item:
      - cheap_answer text is not stored in labelset (only correctness + cost). We load the cheap
        model's actual cached answer from the harness labelset.json (the Cache object).
      - If cheap answer is not in own cache, fall back to fetching it live (will be cached).
      - Run the verifier k times to get confidence (live calls, own cache).
      - For each threshold T: use cheap if confidence >= T else use strong (from labelset).
    """
    harness_cache = Cache(os.path.join(HARNESS, ".cache", "labelset.json"))

    # Step 1: For each item, get the cheap model's actual answer text + run verifier
    per_item = {}
    for row in labelset:
        item = next((t for t in tasks.ALL if t["id"] == row["id"]), None)
        if item is None:
            continue
        # Get cheap answer text (from harness cache — no new billing)
        r_cheap = harness_cache.chat(
            config.CHEAP_DEFAULT,
            [{"role": "user", "content": item["prompt"]}],
            max_tokens=_budget(item),
        )
        cheap_text = r_cheap["text"]

        # Run verifier (live calls, own cache — these are the new charges)
        conf, v_usd, votes = verifier_confidence(item, cheap_text, verifier_cache, k=k)

        per_item[row["id"]] = {
            "cheap_correct": row["cheap_correct"],
            "strong_correct": row["strong_correct"],
            "cheap_usd": row["cheap_usd"],
            "strong_usd": row["strong_usd"],
            "verifier_conf": conf,
            "verifier_votes": votes,
            "verifier_usd": v_usd,
            "discipline": row["discipline"],
            "difficulty": row["difficulty"],
        }
        if verbose:
            flag = "OK " if row["cheap_correct"] else "XX "
            print(f"  [{row['id']:>4}|{row['difficulty']:<4}] conf={conf:.2f} ({votes}) "
                  f"{flag} cheap_correct={row['cheap_correct']}")

    verifier_cache.save()

    # Step 2: For each threshold, simulate the cascade decision
    results = {}
    for T in thresholds:
        nc = cost = escalations = 0
        for iid, d in per_item.items():
            escalate = d["verifier_conf"] < T
            if escalate:
                # Use strong answer
                correct = d["strong_correct"]
                answer_usd = d["strong_usd"]
                escalations += 1
            else:
                # Accept cheap answer
                correct = d["cheap_correct"]
                answer_usd = d["cheap_usd"]
            # Verifier cost always paid (k calls per item)
            total_usd = answer_usd + d["verifier_usd"]
            nc += correct
            cost += total_usd
        n = len(per_item)
        results[T] = {
            "threshold": T,
            "accuracy": round(nc / n, 4),
            "total_usd": round(cost, 6),
            "escalation_rate": round(escalations / n, 3),
            "n": n,
        }
    return results, per_item


def calibration_stats(per_item):
    """Measure verifier calibration: for each confidence bucket, what fraction of cheap answers
    were actually correct? A well-calibrated verifier has low-confidence when cheap is wrong."""
    buckets = {
        "low (0.0-0.33)": [],
        "mid (0.34-0.66)": [],
        "high (0.67-1.0)": [],
    }
    for d in per_item.values():
        c = d["verifier_conf"]
        correct = d["cheap_correct"]
        if c <= 0.33:
            buckets["low (0.0-0.33)"].append(correct)
        elif c <= 0.66:
            buckets["mid (0.34-0.66)"].append(correct)
        else:
            buckets["high (0.67-1.0)"].append(correct)

    stats = {}
    for name, vals in buckets.items():
        if vals:
            stats[name] = {
                "n": len(vals),
                "cheap_correct_rate": round(sum(vals) / len(vals), 3),
            }
        else:
            stats[name] = {"n": 0, "cheap_correct_rate": None}
    return stats


def live_confirmation(verifier_cache):
    """Run a single real item through the full cascade and record the trace as live evidence."""
    # Use m9: cheap fails, strong passes — a good demonstration of escalation
    item = next(t for t in tasks.ALL if t["id"] == "m9")
    print("\n== live confirmation: item m9 ==")
    print(f"  prompt: {item['prompt'][:80]}")

    # Step 1: cheap answer (will be served from harness cache — no new billing)
    harness_cache = Cache(os.path.join(HARNESS, ".cache", "labelset.json"))
    r_cheap = harness_cache.chat(
        config.CHEAP_DEFAULT,
        [{"role": "user", "content": item["prompt"]}],
        max_tokens=_budget(item),
    )
    print(f"  cheap answer: {r_cheap['text']!r}  (cached={r_cheap.get('cached', False)})")
    print(f"  cheap correct: {bool(item['grade'](r_cheap['text']))}")

    # Step 2: verifier (LIVE calls)
    conf, v_usd, votes = verifier_confidence(item, r_cheap["text"], verifier_cache, k=3)
    verifier_cache.save()
    print(f"  verifier votes: {votes}  confidence={conf:.2f}  verifier_usd=${v_usd:.2e}")

    # Step 3: cascade decision at T=0.67
    T = 0.67
    escalate = conf < T
    print(f"  threshold={T}: escalate={escalate}")
    if escalate:
        r_strong = chat(
            config.STRONG_DEFAULT,
            [{"role": "user", "content": item["prompt"]}],
            max_tokens=_budget(item),
        )
        print(f"  strong answer: {r_strong['text']!r}  cost=${r_strong['usd']:.2e}")
        print(f"  strong correct: {bool(item['grade'](r_strong['text']))}")
    return conf, v_usd, votes


def main():
    print("== X4 — AutoMix Verification Cascade ==\n")

    # Load labelset export (no re-billing)
    with open(LABELSET_PATH) as f:
        labelset = json.load(f)

    verifier_cache = Cache(OWN_CACHE_PATH)

    # Live confirmation first
    conf, v_usd, votes = live_confirmation(verifier_cache)

    # Full sweep
    THRESHOLDS = [0.0, 0.34, 0.67, 1.0]
    print("\n== running verifier on all 45 items (k=3 samples each) ==")
    results, per_item = run_automix_from_labels(
        labelset, THRESHOLDS, verifier_cache, k=3, verbose=True
    )

    print("\n== calibration ==")
    cal = calibration_stats(per_item)
    for bucket, s in cal.items():
        print(f"  {bucket}: n={s['n']}, cheap_correct_rate={s['cheap_correct_rate']}")

    print("\n== threshold sweep (cost-quality curve) ==")
    print(f"  {'threshold':<12} {'accuracy':<10} {'total_usd':<12} {'esc_rate':<10}")
    print(f"  {'-'*10:<12} {'-'*8:<10} {'-'*10:<12} {'-'*8:<10}")
    # Baselines (from L0 — no verifier overhead)
    print(f"  {'(baseline)':>12}")
    print(f"  always-cheap                0.8444     $0.001660    0.000")
    print(f"  always-strong               0.9778     $0.021480    1.000")
    print(f"  oracle                      0.9778     $0.002140    0.133")
    for T, r in results.items():
        print(f"  T={T:<10.2f} {r['accuracy']:<10.4f} ${r['total_usd']:<11.6f} {r['escalation_rate']:<10.3f}")

    # Cheapest-cost AutoMix (T=0 = never escalate = just cheap + verifier overhead)
    # Most useful = T=0.67 (verify then escalate only uncertain ones)
    best = max(results.values(), key=lambda r: r["accuracy"] / max(r["total_usd"], 1e-9))
    print(f"\n  best accuracy/cost ratio: T={best['threshold']}, acc={best['accuracy']}, usd=${best['total_usd']:.6f}")

    # Compare T=0.67 vs baselines
    t67 = results[0.67]
    cheap_usd = 0.001660
    cheap_acc = 0.8444
    strong_usd = 0.021480
    strong_acc = 0.9778
    oracle_usd = 0.002140
    print(f"\n== summary at T=0.67 ==")
    print(f"  acc:   {t67['accuracy']:.4f}  (cheap={cheap_acc}, strong={strong_acc}, oracle={strong_acc})")
    print(f"  cost:  ${t67['total_usd']:.6f} vs cheap ${cheap_usd:.6f} / strong ${strong_usd:.6f} / oracle ${oracle_usd:.6f}")
    print(f"  escalation rate: {t67['escalation_rate']:.1%}")
    cost_vs_strong_pct = t67["total_usd"] / strong_usd * 100
    print(f"  cost is {cost_vs_strong_pct:.1f}% of always-strong")

    # Save results for evidence
    summary = {
        "thresholds": results,
        "calibration": cal,
        "per_item_sample": {k: {kk: vv for kk, vv in v.items() if kk != "verifier_votes"}
                            for k, v in list(per_item.items())[:5]},
        "baselines": {
            "always_cheap": {"acc": cheap_acc, "usd": cheap_usd},
            "always_strong": {"acc": strong_acc, "usd": strong_usd},
            "oracle": {"acc": strong_acc, "usd": oracle_usd},
        },
        "live_confirmation": {
            "item": "m9",
            "verifier_conf": conf,
            "verifier_votes": votes,
            "verifier_usd": round(v_usd, 8),
        },
        "k_verifier": 3,
    }
    out_path = os.path.join(HERE, "x4_summary.json")
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nwrote {out_path}")
    print("cache stats:", verifier_cache.stats())


if __name__ == "__main__":
    main()
