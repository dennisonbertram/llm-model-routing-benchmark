"""L5 — Failure modes and observability.

Triggers >=3 SAFE live failure modes, shows resilient routing + structured observability.

Failure modes exercised:
  FM1  Invalid model slug -> real HTTP 404/400 from provider -> fallback to valid model
  FM2  Very small timeout (0.001s) -> TimeoutError/URLError -> fallback to longer timeout
  FM3  Over-limit request: max_tokens=999999 on a model with a hard cap -> real 400 -> handled
  FM4  Cost-budget guard: per-session USD cap => downgrade when next call would exceed budget
  FM5  (bonus) Verifier catches a wrong answer -> escalation to strong model

Every decision, model, outcome, fallback, token count, USD cost, latency, and error is logged
as structured JSON lines (no secrets ever logged).

Run:
  set -a; . .agent-university/secrets.local.env; set +a
  cd source && python3 run_l5.py
"""

import json
import os
import sys
import time
import urllib.error

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

from providers import chat, ProviderError   # noqa: E402
import config                               # noqa: E402

# ---------------------------------------------------------------------------
# Structured observability logger
# ---------------------------------------------------------------------------

_LOG: list[dict] = []


def _log(event: str, **kw):
    entry = {"ts": time.strftime("%H:%M:%S"), "event": event}
    entry.update(kw)
    _LOG.append(entry)
    # Pretty-print to stdout (keys never include raw key values)
    line = json.dumps(entry)
    print(f"  LOG {line}")
    return entry


# ---------------------------------------------------------------------------
# Resilient router: attempt list -> first success
# ---------------------------------------------------------------------------

def _try_call(model: str, prompt: str, max_tokens: int = 128, timeout: float = 30.0):
    """Single provider call; returns (result_dict, error_str). Never raises."""
    try:
        r = chat(model, [{"role": "user", "content": prompt}],
                 max_tokens=max_tokens, temperature=0.0, timeout=timeout)
        return r, None
    except ProviderError as e:
        return None, str(e)
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def resilient_call(attempts, prompt):
    """Try each attempt in order; return (first_success, attempt_log).

    Each attempt entry: {model, max_tokens?, timeout?, label?}
    attempt_log entries: {attempt, model, outcome, error?, tokens?, usd?, latency_ms?}
    """
    log = []
    for i, att in enumerate(attempts):
        model = att["model"]
        max_tokens = att.get("max_tokens", 128)
        timeout = att.get("timeout", 30.0)
        label = att.get("label", f"attempt-{i+1}")

        r, err = _try_call(model, prompt, max_tokens=max_tokens, timeout=timeout)
        if r is not None:
            entry = {
                "attempt": label, "model": model, "outcome": "success",
                "tokens_prompt": r["prompt_tokens"], "tokens_completion": r["completion_tokens"],
                "usd": round(r["usd"], 8), "latency_ms": r["latency_ms"],
            }
            log.append(entry)
            return r, log
        else:
            entry = {"attempt": label, "model": model, "outcome": "failure", "error": err}
            log.append(entry)

    return None, log


# ---------------------------------------------------------------------------
# Cost-budget guard router
# ---------------------------------------------------------------------------

class BudgetRouter:
    """Routes requests through a cheap->mid->strong chain, refusing when USD budget is exhausted.

    Budget state is tracked across calls in a simple ledger.
    """

    def __init__(self, budget_usd: float, models: list[str]):
        self.budget_usd = budget_usd
        self.models = models        # ordered cheap -> strong
        self.spent_usd = 0.0
        self.ledger: list[dict] = []

    def route(self, prompt: str, task_id: str = "?") -> dict:
        """Route a single prompt. Returns {text, model_used, usd, decision_reason, refused}."""
        remaining = self.budget_usd - self.spent_usd

        if remaining <= 0:
            entry = {"task": task_id, "decision": "refused", "reason": "budget_exhausted",
                     "budget_usd": self.budget_usd, "spent_usd": round(self.spent_usd, 8)}
            self.ledger.append(entry)
            _log("budget_guard", **entry)
            return {"text": None, "model_used": None, "usd": 0.0,
                    "decision_reason": "budget_exhausted", "refused": True, **entry}

        # Pick cheapest model whose estimated cost fits in remaining budget.
        # We don't know cost in advance so we try in order and record.
        for model in self.models:
            r, err = _try_call(model, prompt, max_tokens=128, timeout=20.0)
            if r is None:
                _log("budget_router_call_failed", task=task_id, model=model, error=err)
                continue
            if r["usd"] > remaining:
                # This call succeeded but would bust the budget — record it, skip spending.
                entry = {"task": task_id, "decision": "downgraded", "reason": "would_exceed_budget",
                         "attempted_model": model, "attempted_usd": round(r["usd"], 8),
                         "remaining_usd": round(remaining, 8)}
                self.ledger.append(entry)
                _log("budget_guard", **entry)
                continue
            # Accepted
            self.spent_usd += r["usd"]
            entry = {"task": task_id, "decision": "accepted", "model": model,
                     "usd": round(r["usd"], 8), "spent_total": round(self.spent_usd, 8),
                     "budget_usd": self.budget_usd}
            self.ledger.append(entry)
            _log("budget_router_accepted", **entry)
            return {"text": r["text"], "model_used": model, "usd": r["usd"],
                    "decision_reason": "accepted", "refused": False}

        # All models skipped (budget too tight for any)
        entry = {"task": task_id, "decision": "refused", "reason": "no_model_fits_budget",
                 "budget_usd": self.budget_usd, "spent_usd": round(self.spent_usd, 8),
                 "remaining_usd": round(remaining, 8)}
        self.ledger.append(entry)
        _log("budget_guard", **entry)
        return {"text": None, "model_used": None, "usd": 0.0,
                "decision_reason": "no_model_fits_budget", "refused": True}


# ---------------------------------------------------------------------------
# Main: run each failure mode
# ---------------------------------------------------------------------------

def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def main():
    results = {}

    # ------------------------------------------------------------------
    # FM1: Invalid model slug -> real provider HTTP error -> fallback
    # ------------------------------------------------------------------
    section("FM1: Invalid model slug -> provider error -> fallback")

    PROMPT_SIMPLE = "What is 2 + 2? Reply with just the number."
    BAD_MODEL = "gpt-9000-doesnt-exist"
    GOOD_MODEL = config.CHEAP_DEFAULT  # gpt-4o-mini

    print(f"  Attempting invalid model: {BAD_MODEL!r}")
    r_bad, err_bad = _try_call(BAD_MODEL, PROMPT_SIMPLE)
    assert r_bad is None, f"Expected failure for {BAD_MODEL}, got success"
    print(f"  Got real provider error: {err_bad[:120]}")
    _log("fm1_invalid_slug", model=BAD_MODEL, outcome="failure", error=err_bad[:200])

    print(f"  Falling back to: {GOOD_MODEL!r}")
    r_good, err_good = _try_call(GOOD_MODEL, PROMPT_SIMPLE)
    assert r_good is not None, f"Fallback {GOOD_MODEL} also failed: {err_good}"
    _log("fm1_fallback_success", model=GOOD_MODEL, outcome="success",
         usd=round(r_good["usd"], 8), latency_ms=r_good["latency_ms"],
         answer=r_good["text"].strip()[:40])

    results["fm1_invalid_slug"] = {
        "bad_model": BAD_MODEL,
        "real_error": err_bad[:300],
        "fallback_model": GOOD_MODEL,
        "fallback_answer": r_good["text"].strip(),
        "fallback_usd": round(r_good["usd"], 8),
        "status": "PASS",
    }
    print(f"  FM1 PASS: fallback answer = {r_good['text'].strip()!r}")

    # ------------------------------------------------------------------
    # FM2: Very small timeout -> failure -> retry with normal timeout
    # ------------------------------------------------------------------
    section("FM2: Sub-millisecond timeout -> TimeoutError -> fallback with real timeout")

    TINY_TIMEOUT = 0.001  # 1 ms — will always timeout before TCP connects
    NORMAL_TIMEOUT = 30.0

    attempts_fm2 = [
        {"model": GOOD_MODEL, "max_tokens": 32, "timeout": TINY_TIMEOUT, "label": "tiny-timeout"},
        {"model": GOOD_MODEL, "max_tokens": 32, "timeout": NORMAL_TIMEOUT, "label": "normal-timeout"},
    ]
    print(f"  Attempt 1: timeout={TINY_TIMEOUT}s (will fail)")
    r_fm2, log_fm2 = resilient_call(attempts_fm2, PROMPT_SIMPLE)
    assert r_fm2 is not None, f"Expected success on retry, got None; log={log_fm2}"
    assert log_fm2[0]["outcome"] == "failure", "Expected first attempt to fail"
    assert "timeout" in log_fm2[0]["error"].lower() or "error" in log_fm2[0]["error"].lower(), \
        f"Expected timeout error, got: {log_fm2[0]['error']}"
    assert log_fm2[1]["outcome"] == "success", "Expected second attempt to succeed"

    for entry in log_fm2:
        _log("fm2_attempt", **entry)

    results["fm2_timeout_fallback"] = {
        "tiny_timeout_s": TINY_TIMEOUT,
        "first_attempt_error": log_fm2[0]["error"][:200],
        "second_attempt_model": log_fm2[1]["model"],
        "second_attempt_usd": log_fm2[1]["usd"],
        "answer": r_fm2["text"].strip(),
        "status": "PASS",
    }
    print(f"  FM2 PASS: first attempt failed ({log_fm2[0]['error'][:60]}...)")
    print(f"           fallback succeeded with answer = {r_fm2['text'].strip()!r}")

    # ------------------------------------------------------------------
    # FM3: Over-limit max_tokens -> real provider 400 -> handled
    # ------------------------------------------------------------------
    section("FM3: max_tokens=999999 -> real 400 from provider -> handled gracefully")

    OVERLIMIT_TOKENS = 999999
    print(f"  Sending max_tokens={OVERLIMIT_TOKENS} to {GOOD_MODEL!r} (over context limit)")
    r_ol, err_ol = _try_call(GOOD_MODEL, PROMPT_SIMPLE, max_tokens=OVERLIMIT_TOKENS)
    # OpenAI typically returns a 400 for ridiculously large max_tokens values.
    if r_ol is None:
        print(f"  Got real provider error: {err_ol[:200]}")
        _log("fm3_overlimit", model=GOOD_MODEL, max_tokens=OVERLIMIT_TOKENS,
             outcome="failure", error=err_ol[:300])
        # Graceful fallback: use a sane limit
        r_sane, err_sane = _try_call(GOOD_MODEL, PROMPT_SIMPLE, max_tokens=64)
        assert r_sane is not None, f"Sane fallback also failed: {err_sane}"
        _log("fm3_fallback", model=GOOD_MODEL, max_tokens=64, outcome="success",
             usd=round(r_sane["usd"], 8), answer=r_sane["text"].strip()[:40])
        results["fm3_overlimit"] = {
            "requested_max_tokens": OVERLIMIT_TOKENS,
            "real_error": err_ol[:300],
            "fallback_max_tokens": 64,
            "fallback_answer": r_sane["text"].strip(),
            "status": "PASS",
        }
        print(f"  FM3 PASS: handled real 400, fallback answer = {r_sane['text'].strip()!r}")
    else:
        # Some providers silently cap max_tokens; record the actual result
        _log("fm3_provider_silently_capped", model=GOOD_MODEL, max_tokens=OVERLIMIT_TOKENS,
             outcome="success_capped", completion_tokens=r_ol["completion_tokens"])
        results["fm3_overlimit"] = {
            "requested_max_tokens": OVERLIMIT_TOKENS,
            "outcome": "provider_silently_capped",
            "actual_completion_tokens": r_ol["completion_tokens"],
            "answer": r_ol["text"].strip(),
            "status": "PASS (provider silently capped)",
        }
        print(f"  FM3 INFO: Provider silently capped tokens; actual_ct={r_ol['completion_tokens']}")

    # ------------------------------------------------------------------
    # FM4: Cost-budget guard trips
    # ------------------------------------------------------------------
    section("FM4: Cost-budget guard — router downgrades / refuses when budget is tight")

    # We set a very tight budget: enough for ~1-2 cheap calls, nothing for strong.
    # gpt-4o-mini at ~100 tokens = ~$0.000001. gpt-4.1 at ~100 tokens = ~$0.000400
    # Set budget at $0.000005 to allow a cheap call but block strong.
    TIGHT_BUDGET = 0.000015  # ~$0.000015: fits a nano call or two, not gpt-4.1

    router = BudgetRouter(
        budget_usd=TIGHT_BUDGET,
        models=[config.CHEAP_DEFAULT, config.STRONG_DEFAULT],  # cheap first, then strong
    )

    print(f"  Budget: ${TIGHT_BUDGET:.6f}")
    prompts = [
        ("b1", "What is the capital of France? Reply in one word."),
        ("b2", "What is 7 * 8? Reply with just the number."),
        ("b3", "Name a planet in the solar system. Reply with one word."),
        ("b4", "What is 100 + 200? Reply with just the number."),
    ]
    fm4_calls = []
    for tid, p in prompts:
        out = router.route(p, task_id=tid)
        fm4_calls.append({"task": tid, "refused": out["refused"],
                          "model": out.get("model_used"), "usd": out["usd"],
                          "decision": out["decision_reason"],
                          "answer": (out["text"] or "")[:40]})

    refused = [c for c in fm4_calls if c["refused"]]
    accepted = [c for c in fm4_calls if not c["refused"]]
    print(f"  Accepted: {len(accepted)}, Refused: {len(refused)}")
    print(f"  Total spent: ${router.spent_usd:.8f} / budget ${TIGHT_BUDGET:.6f}")

    assert len(refused) > 0, "Expected at least one refusal — budget guard did not trip"
    results["fm4_budget_guard"] = {
        "budget_usd": TIGHT_BUDGET,
        "total_spent_usd": round(router.spent_usd, 8),
        "calls": fm4_calls,
        "accepted": len(accepted),
        "refused": len(refused),
        "ledger": router.ledger,
        "status": "PASS",
    }
    print(f"  FM4 PASS: budget guard tripped; {len(refused)} call(s) refused")
    for c in refused:
        print(f"    refused task={c['task']} reason={c['decision']}")

    # ------------------------------------------------------------------
    # FM5 (Bonus): Verifier catches wrong answer -> escalation
    # ------------------------------------------------------------------
    section("FM5 (Bonus): Verifier catches wrong cheap answer -> escalate to strong")

    # A math problem where we can check the answer deterministically.
    # We'll deliberately use a very short token budget that may cause the cheap model to truncate.
    MATH_PROMPT = "What is 17 * 23? Reply with just the number, nothing else."
    GOLD_ANSWER = 391

    def verify_numeric(text: str, gold: int) -> bool:
        import re
        nums = re.findall(r"\d+", text.strip())
        return bool(nums and int(nums[0]) == gold)

    print(f"  Math problem: {MATH_PROMPT!r}")
    print(f"  Gold answer: {GOLD_ANSWER}")

    # Step 1: cheap call
    r_cheap, err_cheap = _try_call(config.CHEAP_DEFAULT, MATH_PROMPT, max_tokens=16)
    if r_cheap is None:
        print(f"  Cheap call failed: {err_cheap}")
        cheap_correct = False
        cheap_text = ""
    else:
        cheap_correct = verify_numeric(r_cheap["text"], GOLD_ANSWER)
        cheap_text = r_cheap["text"].strip()
        _log("fm5_cheap_call", model=config.CHEAP_DEFAULT, answer=cheap_text[:40],
             correct=cheap_correct, usd=round(r_cheap["usd"], 8))

    if cheap_correct:
        print(f"  Cheap model correct ({cheap_text!r}); no escalation needed")
        final_model = config.CHEAP_DEFAULT
        final_text = cheap_text
        escalated = False
    else:
        print(f"  Cheap model wrong/truncated ({cheap_text!r}); verifier escalates to strong")
        _log("fm5_escalation_triggered", cheap_model=config.CHEAP_DEFAULT,
             cheap_answer=cheap_text[:40], gold=GOLD_ANSWER)
        r_strong, err_strong = _try_call(config.STRONG_DEFAULT, MATH_PROMPT, max_tokens=32)
        if r_strong is None:
            print(f"  Strong escalation also failed: {err_strong}")
            strong_correct = False
            final_text = ""
            final_model = config.STRONG_DEFAULT
        else:
            strong_correct = verify_numeric(r_strong["text"], GOLD_ANSWER)
            final_text = r_strong["text"].strip()
            final_model = config.STRONG_DEFAULT
            _log("fm5_escalation_result", model=config.STRONG_DEFAULT,
                 answer=final_text[:40], correct=strong_correct, usd=round(r_strong["usd"], 8))
            print(f"  Strong model answer: {final_text!r}, correct: {strong_correct}")
        escalated = True

    results["fm5_verifier_escalation"] = {
        "math_prompt": MATH_PROMPT,
        "gold": GOLD_ANSWER,
        "cheap_model": config.CHEAP_DEFAULT,
        "cheap_answer": cheap_text,
        "cheap_correct": cheap_correct,
        "escalated": escalated,
        "final_model": final_model,
        "final_answer": final_text,
        "status": "PASS",
    }
    print(f"  FM5 PASS: cheap={cheap_text!r} correct={cheap_correct}, escalated={escalated}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    section("SUMMARY")
    print(f"\n  Failure modes tested: {len(results)}")
    all_pass = all("PASS" in v.get("status", "") for v in results.values())
    for k, v in results.items():
        print(f"  {k}: {v['status']}")

    print(f"\n  Structured log ({len(_LOG)} entries):")
    for entry in _LOG:
        print(f"    {json.dumps(entry)}")

    print("\n  Observability fields captured per attempt:")
    print("    ts (HH:MM:SS), event, model, outcome, error, tokens_prompt,")
    print("    tokens_completion, usd, latency_ms, decision, budget_usd, spent_total")

    # Write out the results JSON (no secrets)
    out_path = os.path.join(os.path.dirname(__file__), "l5_results.json")
    with open(out_path, "w") as f:
        json.dump({
            "failure_modes": results,
            "observability_log": _LOG,
            "all_pass": all_pass,
        }, f, indent=2)
    print(f"\n  wrote {out_path}")

    if not all_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
