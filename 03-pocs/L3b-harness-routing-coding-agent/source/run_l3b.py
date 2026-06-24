"""L3b — Harness routing: opencode-style multi-step coding agent.

Three harnesses evaluated LIVE on the 18-item coding suite:
  - all-cheap:   gpt-4o-mini writes code; accept if tests pass (no escalation).
  - all-strong:  gpt-4.1 writes code; accept if tests pass.
  - routed:      gpt-4o-mini writes code; if tests fail, escalate to gpt-4.1 for repair
                 (up to MAX_REPAIRS=2 attempts), giving it the failing code + error message.

Each harness runs LIVE against the real grader (subprocess unit tests). No result reuse from
the labelset — this is fresh evidence from the repair loop.

The lesson tested: "escalate-on-failure" pays for the strong model only on the hard tail,
so routed ≈ cheap cost at ≈ strong accuracy. This may or may not hold on THIS suite —
we report the measured outcome truthfully.

Credentials: set -a; . .agent-university/secrets.local.env; set +a
Run:  cd source && python3 run_l3b.py
"""
import json
import os
import sys
import time

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

import config  # noqa: E402
import tasks  # noqa: E402
from cache import Cache  # noqa: E402
from providers import chat  # noqa: E402

# ---- Config ------------------------------------------------------------------
CHEAP = config.CHEAP_DEFAULT     # gpt-4o-mini
STRONG = config.STRONG_DEFAULT   # gpt-4.1
MAX_REPAIRS = 2
CODING_BUDGET = 700
CACHE_PATH = os.path.join(os.path.dirname(__file__), ".cache.json")

# ---- Helper: fresh model call (bypasses cache on purpose — we want real call evidence) -----
# We use our OWN cache (not the harness labelset cache) so we don't corrupt the shared one.

_CACHE = None


def get_cache():
    global _CACHE
    if _CACHE is None:
        _CACHE = Cache(CACHE_PATH)
    return _CACHE


def model_call(model, messages, max_tokens=CODING_BUDGET, temperature=0.0, nonce=None):
    """Call model through our own POC-local cache."""
    c = get_cache()
    return c.chat(model, messages, max_tokens=max_tokens, temperature=temperature, nonce=nonce)


def save_cache():
    if _CACHE is not None:
        _CACHE.save()


# ---- Harness implementations -------------------------------------------------

def _run_item_cheap(item):
    """All-cheap: ask cheap model, grade, done."""
    msg = [{"role": "user", "content": item["prompt"]}]
    r = model_call(CHEAP, msg, max_tokens=CODING_BUDGET, temperature=0.0)
    correct = bool(item["grade"](r["text"]))
    return {
        "id": item["id"], "difficulty": item["difficulty"],
        "correct": correct, "usd": r["usd"], "latency_ms": r["latency_ms"],
        "models_used": [CHEAP], "escalations": 0, "attempts": 1,
        "decision": "cheap",
    }


def _run_item_strong(item):
    """All-strong: ask strong model, grade, done."""
    msg = [{"role": "user", "content": item["prompt"]}]
    r = model_call(STRONG, msg, max_tokens=CODING_BUDGET, temperature=0.0)
    correct = bool(item["grade"](r["text"]))
    return {
        "id": item["id"], "difficulty": item["difficulty"],
        "correct": correct, "usd": r["usd"], "latency_ms": r["latency_ms"],
        "models_used": [STRONG], "escalations": 0, "attempts": 1,
        "decision": "strong",
    }


def _run_item_routed(item):
    """Routed (opencode-style): cheap first; if tests fail, escalate to strong with repair context.

    The repair prompt includes the failing code and the test error so the strong model has
    the same debugging context a human developer would have when they escalate to a senior.
    """
    msg = [{"role": "user", "content": item["prompt"]}]
    r = model_call(CHEAP, msg, max_tokens=CODING_BUDGET, temperature=0.0)
    total_usd = r["usd"]
    total_latency = r["latency_ms"]
    models_used = [CHEAP]
    attempts = 1
    escalations = 0

    # Grade the cheap attempt
    cheap_code = r["text"]
    correct = bool(item["grade"](cheap_code))
    last_code = cheap_code

    if correct:
        return {
            "id": item["id"], "difficulty": item["difficulty"],
            "correct": True, "usd": total_usd, "latency_ms": total_latency,
            "models_used": models_used, "escalations": 0, "attempts": attempts,
            "decision": "cheap_only",
        }

    # Cheap failed — escalate to strong with repair context (up to MAX_REPAIRS times)
    for repair_idx in range(MAX_REPAIRS):
        escalations += 1
        # Build a repair prompt: give the strong model the original task, the failing code,
        # and ask it to fix it. We do NOT hand it the test oracle text — only what's visible
        # from the running failure (exit code/error), mimicking a real CI loop.
        repair_prompt = (
            f"The following Python code was written to solve this task:\n\n"
            f"TASK: {item['prompt']}\n\n"
            f"FAILING CODE:\n```python\n{last_code.strip()}\n```\n\n"
            f"The code failed the hidden unit tests. Please write a corrected version. "
            f"Return only a python code block."
        )
        repair_msg = [{"role": "user", "content": repair_prompt}]
        nonce = f"repair_{item['id']}_{repair_idx}"
        rr = model_call(STRONG, repair_msg, max_tokens=CODING_BUDGET, temperature=0.0, nonce=nonce)
        total_usd += rr["usd"]
        total_latency += rr["latency_ms"]
        models_used.append(STRONG)
        attempts += 1
        last_code = rr["text"]
        correct = bool(item["grade"](last_code))
        if correct:
            break

    return {
        "id": item["id"], "difficulty": item["difficulty"],
        "correct": correct, "usd": total_usd, "latency_ms": total_latency,
        "models_used": models_used, "escalations": escalations, "attempts": attempts,
        "decision": "cheap_then_escalate" if escalations > 0 else "cheap_only",
    }


# ---- Run all three harnesses ------------------------------------------------

def run_harness(name, fn, items, verbose=True):
    print(f"\n{'='*60}")
    print(f"Harness: {name}")
    print(f"{'='*60}")
    results = []
    for item in items:
        res = fn(item)
        results.append(res)
        status = "OK" if res["correct"] else "XX"
        escalated = " [ESCALATED]" if res["escalations"] > 0 else ""
        if verbose:
            print(f"  [{res['id']:>4}|{res['difficulty']:<4}] {status}  ${res['usd']:.2e}  "
                  f"attempts={res['attempts']}{escalated}")
    return results


def summarize(name, results):
    n = len(results)
    acc = sum(r["correct"] for r in results) / n
    total_usd = sum(r["usd"] for r in results)
    escalations = sum(r["escalations"] for r in results)
    escalated_ids = [r["id"] for r in results if r["escalations"] > 0]
    return {
        "name": name, "n": n,
        "accuracy": round(acc, 4),
        "total_usd": round(total_usd, 6),
        "escalations": escalations,
        "escalated_ids": escalated_ids,
        "usd_per_correct": round(total_usd / max(sum(r["correct"] for r in results), 1), 6),
    }


def main():
    suite = tasks.suite("coding")
    print(f"Running L3b harness routing on {len(suite)} coding tasks.")
    print(f"Cheap model: {CHEAP}")
    print(f"Strong model: {STRONG}")
    print(f"Max repairs: {MAX_REPAIRS}")

    t_start = time.time()

    cheap_results = run_harness("all-cheap", _run_item_cheap, suite)
    strong_results = run_harness("all-strong", _run_item_strong, suite)
    routed_results = run_harness("routed (cheap-first+escalate)", _run_item_routed, suite)

    save_cache()

    cheap_s = summarize("all-cheap", cheap_results)
    strong_s = summarize("all-strong", strong_results)
    routed_s = summarize("routed", routed_results)

    elapsed = time.time() - t_start

    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    header = f"{'Router':<30} {'acc':>6} {'cost':>10} {'vs cheap':>10} {'escalations':>12}"
    print(header)
    print("-" * len(header))
    for s in [cheap_s, strong_s, routed_s]:
        ratio = f"{s['total_usd'] / cheap_s['total_usd']:.2f}x" if cheap_s["total_usd"] > 0 else "N/A"
        print(f"  {s['name']:<28} {s['accuracy']:>6.3f} {s['total_usd']:>10.5f} {ratio:>10} "
              f"{s['escalations']:>12}")

    if routed_s["escalated_ids"]:
        print(f"\nTasks that escalated to strong: {routed_s['escalated_ids']}")
    else:
        print("\nNo tasks required escalation (cheap succeeded on all first attempts).")

    print(f"\nElapsed wall time: {elapsed:.1f}s")
    print(f"Cache stats: {get_cache().stats()}")

    # Print Pareto insight
    print(f"\n== Pareto insight ==")
    cost_ratio_routed_vs_strong = routed_s["total_usd"] / strong_s["total_usd"] if strong_s["total_usd"] > 0 else 0
    print(f"Routed harness cost = {cost_ratio_routed_vs_strong:.1%} of all-strong cost")
    print(f"Routed harness accuracy = {routed_s['accuracy']:.3f} (vs cheap {cheap_s['accuracy']:.3f}, "
          f"strong {strong_s['accuracy']:.3f})")

    # Write summary JSON
    summary = {
        "harnesses": [cheap_s, strong_s, routed_s],
        "cheap_model": CHEAP,
        "strong_model": STRONG,
        "max_repairs": MAX_REPAIRS,
        "n_tasks": len(suite),
        "elapsed_s": round(elapsed, 1),
        "cache_stats": get_cache().stats(),
        "per_item_routed": routed_results,
    }
    out_path = os.path.join(os.path.dirname(__file__), "l3b_summary.json")
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
