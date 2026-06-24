"""OpenAI-compatible HTTP gateway in front of the AdaptiveRouter (stdlib http.server).

POST /v1/chat/completions  with  {"model": "auto"|<id>, "messages": [...]}  ->  OpenAI-shaped JSON
whose `model` field reports the ACTUALLY-served model. Each request appends a line to
gateway-ledger.jsonl. Start: python3 gateway_server.py [port]
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(__file__))
from adaptive_router import AdaptiveRouter  # noqa: E402

ROUTER = AdaptiveRouter(threshold=0.6, budget_usd=None)
LEDGER = os.path.join(os.path.dirname(__file__), "gateway-ledger.jsonl")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # quiet

    def do_POST(self):
        if self.path.rstrip("/") != "/v1/chat/completions":
            self.send_response(404); self.end_headers(); return
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        msgs = body.get("messages", [])
        prompt = next((m["content"] for m in reversed(msgs) if m.get("role") == "user"), "")
        forced = body.get("model")
        if forced and forced != "auto":
            from providers import chat
            r = chat(forced, [{"role": "user", "content": prompt}], max_tokens=512)
            served, decision, usd = forced, "forced", r["usd"]
            text = r["text"]
            entry = {"decision": "forced", "served_model": served, "usd": round(usd, 6)}
        else:
            out = ROUTER.answer(prompt)
            served, decision, usd, text, entry = out["served_model"], out["decision"], out["usd"], out["text"], out["entry"]
        with open(LEDGER, "a") as f:
            f.write(json.dumps(entry) + "\n")
        resp = {"id": "amr-gw", "object": "chat.completion", "model": served,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": text},
                             "finish_reason": "stop"}],
                "usage": {"estimated_usd": round(usd, 6)}, "x_routing_decision": decision}
        data = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
    open(LEDGER, "w").close()  # fresh ledger
    print(f"adaptive routing gateway on :{port}", flush=True)
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
