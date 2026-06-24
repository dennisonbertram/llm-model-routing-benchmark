# Recipe R-004: Adaptive Routing Gateway

Live verified (capstone; 2026-06-21/22). The full production-pattern gateway: logistic
classifier + budget guard + provider fallback + OpenAI-compatible HTTP server.

Back to [index](../index.md).

---

## What it combines

Live verified (capstone):
- Logistic classifier prediction (P(cheap correct) ≥ threshold → cheap, else strong)
- Cost-budget guard (cap forces cheap after session limit is exceeded)
- Provider fallback (bad or erroring primary → fallback model)
- OpenAI-compatible `POST /v1/chat/completions` with `model:"auto"`
- Append-only JSONL cost ledger per request

---

## Live results

Live verified. 5-fold CV over 45 tasks (2026-06-21):

| Router | accuracy | cost | pct_cheap |
|--------|----------|------|-----------|
| adaptive(thr=0.8) | **0.978** | **$0.00257** | **71%** |
| always-strong | 0.978 | $0.02148 | 0% |
| always-cheap | 0.844 | $0.00166 | 100% |
| oracle (unrealizable) | 0.978 | $0.00214 | — |

adaptive(thr=0.8): 8.4x cheaper than always-strong; 1.20x the oracle cost.

---

## Adaptive router core

```python
"""
AdaptiveRouter: logistic classifier + budget guard + provider fallback.
Live verified: thr=0.8 → acc=0.978, $0.00257, 71% cheap traffic. (capstone; 2026-06-21)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "harness"))
from providers import chat, embed
import math, json

CHEAP_MODEL  = "gpt-4o-mini"
STRONG_MODEL = "gpt-4.1"
EMBED_MODEL  = "text-embedding-3-small"


def sigmoid(z):
    return 1.0 / (1.0 + math.exp(-max(-500, min(500, z))))

def l2_norm(v):
    n = math.sqrt(sum(x*x for x in v)) or 1.0
    return [x/n for x in v]

def dot(a, b):
    return sum(ai*bi for ai, bi in zip(a, b))


class AdaptiveRouter:
    def __init__(self, threshold: float = 0.80, budget_usd: float = None,
                 strong_fallback: str = None):
        self.threshold = threshold
        self.budget_usd = budget_usd       # None = no cap
        self.spent_usd  = 0.0
        self.fallback   = strong_fallback  # used if strong fails
        self.w = None  # trained weights

    def load_weights(self, path: str):
        """Load serialized weight vector from a JSON file."""
        with open(path) as f:
            self.w = json.load(f)

    # ── Routing decision ───────────────────────────────────────────────────

    def _predict(self, prompt: str) -> float:
        """P(cheap_correct) for a prompt. Requires trained weights."""
        vecs, _ = embed([prompt], model=EMBED_MODEL)
        x = l2_norm(vecs[0])
        return sigmoid(dot(self.w, x))

    def decide(self, prompt: str, force_model: str = None) -> tuple[str, str]:
        """
        Returns (chosen_model, decision_string).
        decision_string is human-readable and logged verbatim.
        """
        if force_model and force_model != "auto":
            return force_model, "forced"

        # Budget guard takes priority
        if self.budget_usd is not None and self.spent_usd >= self.budget_usd:
            return CHEAP_MODEL, f"budget_guard(spent=${self.spent_usd:.4f}>=cap)"

        p = self._predict(prompt)
        model = CHEAP_MODEL if p >= self.threshold else STRONG_MODEL
        return model, f"classifier(p_cheap={p:.2f},thr={self.threshold})"

    # ── Answer (decide + call + record) ───────────────────────────────────

    def answer(self, prompt: str, force_model: str = None,
               max_tokens: int = 512) -> dict:
        """
        Returns {text, served_model, decision, usd, entry}.
        Falls back to CHEAP_MODEL if the primary model errors.
        """
        model, decision = self.decide(prompt, force_model)
        fallback_from = None

        try:
            r = chat(model, [{"role": "user", "content": prompt}], max_tokens=max_tokens)
            text = r["text"]
            usd  = r["usd"]
        except Exception as e:
            # Provider fallback
            fallback_from = model
            fb = self.fallback or CHEAP_MODEL
            r  = chat(fb, [{"role": "user", "content": prompt}], max_tokens=max_tokens)
            text = r["text"]
            usd  = r["usd"]
            model = fb

        self.spent_usd += usd
        entry = {
            "decision": decision,
            "served_model": model,
            "usd": round(usd, 6),
            "fallback_from": fallback_from,
        }
        return {"text": text, "served_model": model, "decision": decision,
                "usd": usd, "entry": entry}
```

---

## OpenAI-compatible HTTP gateway

```python
"""
Gateway server — exposes POST /v1/chat/completions with {model:"auto",...}.
Live verified: 3 live curls + ledger persisted (capstone; 2026-06-22).
"""
import json, os, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
# from adaptive_router import AdaptiveRouter  # the class above

LEDGER = "gateway-ledger.jsonl"


class RoutingHandler(BaseHTTPRequestHandler):
    router: "AdaptiveRouter" = None   # set at startup

    def log_message(self, *a):
        pass   # suppress default access log; use structured ledger

    def do_POST(self):
        if self.path.rstrip("/") != "/v1/chat/completions":
            self.send_response(404); self.end_headers(); return

        body  = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        msgs  = body.get("messages", [])
        prompt = next((m["content"] for m in reversed(msgs) if m.get("role") == "user"), "")
        force  = body.get("model")

        out = self.router.answer(prompt, force_model=force,
                                 max_tokens=body.get("max_tokens", 512))

        # Append to ledger
        with open(LEDGER, "a") as f:
            f.write(json.dumps(out["entry"]) + "\n")

        resp = {
            "id":     "amr-gw",
            "object": "chat.completion",
            "model":  out["served_model"],   # ACTUALLY-served model (never "auto")
            "choices": [{"index": 0,
                          "message": {"role": "assistant", "content": out["text"]},
                          "finish_reason": "stop"}],
            "usage": {"estimated_usd": round(out["usd"], 6)},
            "x_routing_decision": out["decision"],
        }
        data = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def start(port: int = 8137, router=None):
    RoutingHandler.router = router
    open(LEDGER, "w").close()   # fresh ledger each start
    print(f"adaptive routing gateway on :{port}", flush=True)
    HTTPServer(("127.0.0.1", port), RoutingHandler).serve_forever()
```

---

## Start and curl

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd model-routing/degrees/01-llm-model-routing/03-pocs/L-capstone-adaptive-routing-gateway/source
python3 gateway_server.py 8137 &

# Easy QA — expect cheap route (live-verified)
curl -s -X POST localhost:8137/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"auto","messages":[{"role":"user","content":"What is the capital of France?"}]}'
# Response: model=gpt-4o-mini, x_routing_decision=classifier(p_cheap=0.97,thr=0.6), answer=Paris.

# Hard math — expect strong route (live-verified)
curl -s -X POST localhost:8137/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"auto","messages":[{"role":"user","content":"How many ways can you arrange BALLOON?"}]}'
# Response: model=gpt-4.1, x_routing_decision=classifier(p_cheap=0.38,thr=0.6), answer=1260

kill %1
```

## Source

`03-pocs/L-capstone-adaptive-routing-gateway/source/`
- `adaptive_router.py` — the AdaptiveRouter class
- `gateway_server.py` — the HTTP server
- `run_capstone.py` — CV benchmark + live budget-guard + fallback smoke
