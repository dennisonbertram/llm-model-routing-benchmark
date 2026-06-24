"""Capstone — the Adaptive Routing Gateway.

Combines every prior POC into one deployable component:
  - L2b predictive routing: a logistic classifier over embeddings predicts P(cheap is correct);
    a threshold is the cost-quality knob (the X5-proven winner).
  - L3a/X4 verification escalation: optional cheap self-check escalates a low-confidence answer.
  - L5 reliability: a per-session cost-budget guard + a provider fallback chain.
  - L4/L3c runtime: served behind an OpenAI-compatible /v1/chat/completions interface.
  - Observability: a structured decision/cost ledger per request.

No mocks: every answer is a real provider call. Trains on the L0 live-measured outcome matrix.
"""
import hashlib
import json
import os
import re
import sys
import time

import numpy as np

HARNESS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "harness")
sys.path.insert(0, HARNESS)

import config  # noqa: E402
from providers import chat, embed, ProviderError  # noqa: E402

_EMB = os.path.join(os.path.dirname(__file__), ".emb_cache.json")


def _embed_cached(texts):
    store = json.load(open(_EMB)) if os.path.exists(_EMB) else {}
    out, todo, idx = [None] * len(texts), [], []
    for i, t in enumerate(texts):
        k = hashlib.sha256(("text-embedding-3-small\n" + t).encode()).hexdigest()
        if k in store:
            out[i] = store[k]
        else:
            todo.append(t); idx.append((i, k))
    if todo:
        vecs, _ = embed(todo)
        for (i, k), v in zip(idx, vecs):
            out[i] = v; store[k] = v
        json.dump(store, open(_EMB, "w"))
    return out


def _train_logreg(X, y, iters=500, lr=0.5, l2=1e-3):
    import warnings
    warnings.filterwarnings("ignore", message=".*matmul.*", category=RuntimeWarning)
    np.seterr(all="ignore")
    n, d = X.shape
    w, b = np.zeros(d), 0.0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(X @ w + b)))
        w -= lr * (X.T @ (p - y) / n + l2 * w)
        b -= lr * float(np.mean(p - y))
    return w, b


class AdaptiveRouter:
    def __init__(self, cheap=None, strong=None, threshold=0.6, budget_usd=None,
                 fallback=None, verify_escalate=False):
        self.cheap = cheap or config.CHEAP_DEFAULT
        self.strong = strong or config.STRONG_DEFAULT
        self.threshold = threshold          # route cheap when P(cheap correct) >= threshold
        self.budget_usd = budget_usd        # per-session cap; None = unlimited
        self.fallback = fallback or "gpt-4o-mini"
        self.verify_escalate = verify_escalate
        self.spent = 0.0
        self.ledger = []
        self._fit()

    def _fit(self):
        matrix = json.load(open(os.path.join(HARNESS, ".cache", "labelset_export.json")))
        X = np.array(_embed_cached([r["prompt"] for r in matrix]))
        y = np.array([float(r["cheap_correct"]) for r in matrix])
        self.w, self.b = _train_logreg(X, y)

    def p_cheap_ok(self, prompt):
        x = np.array(_embed_cached([prompt])[0])
        return float(1 / (1 + np.exp(-(x @ self.w + self.b))))

    def decide(self, prompt):
        p = self.p_cheap_ok(prompt)
        # Budget guard: if we're over budget, force the cheap model regardless of prediction.
        if self.budget_usd is not None and self.spent >= self.budget_usd:
            return self.cheap, f"budget_guard(spent=${self.spent:.4f}>=cap)", p
        model = self.cheap if p >= self.threshold else self.strong
        return model, f"classifier(p_cheap={p:.2f},thr={self.threshold})", p

    def _call(self, model, prompt):
        """Live call with a single fallback on provider error."""
        try:
            return chat(model, [{"role": "user", "content": prompt}], max_tokens=512), model, None
        except ProviderError as e:
            r = chat(self.fallback, [{"role": "user", "content": prompt}], max_tokens=512)
            return r, self.fallback, str(e)[:160]

    def answer(self, prompt):
        t0 = time.time()
        model, reason, p = self.decide(prompt)
        r, served, err = self._call(model, prompt)
        usd = r["usd"]
        # Optional verification escalation: a cheap yes/no self-check; escalate once on "no".
        escalated = False
        if self.verify_escalate and served == self.cheap:
            chk = chat(self.cheap, [{"role": "user", "content":
                       f"Question:\n{prompt}\n\nProposed answer:\n{r['text']}\n\n"
                       f"Is the proposed answer correct? Reply only YES or NO."}], max_tokens=4)
            usd += chk["usd"]
            if chk["text"].strip().upper().startswith("NO") and (self.budget_usd is None or self.spent + usd < self.budget_usd):
                r2, served2, _ = self._call(self.strong, prompt)
                usd += r2["usd"]; r = r2; served = served2; escalated = True
                reason += "+verify_escalate"
        self.spent += usd
        entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "decision": reason,
                 "served_model": served, "usd": round(usd, 6), "latency_ms": int((time.time() - t0) * 1000),
                 "fallback_from": err, "escalated": escalated, "total_spent": round(self.spent, 6)}
        self.ledger.append(entry)
        return {"text": r["text"], "served_model": served, "usd": usd, "decision": reason, "entry": entry}
