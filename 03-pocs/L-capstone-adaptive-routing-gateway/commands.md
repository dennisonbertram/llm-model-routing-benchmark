# Commands

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd source

# (1) honest CV benchmark + (2) live budget-guard + fallback demos
python3 run_capstone.py                       # -> green-output.txt

# (3) OpenAI-compatible runtime
python3 gateway_server.py 8137 & SRV=$!; sleep 3
curl -s -X POST http://127.0.0.1:8137/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"auto","messages":[{"role":"user","content":"In how many ways can BALLOON be arranged? Just the number."}]}'
cat gateway-ledger.jsonl
kill $SRV
```
RED: run with keys unset -> ProviderError (red-output.txt).
