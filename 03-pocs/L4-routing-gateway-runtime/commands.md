# Commands

## Prerequisites

```bash
# Load credentials (required for any live model call)
set -a; . .agent-university/secrets.local.env; set +a
```

## Run the full demo (start server, 3 curl requests, show ledger, stop)

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/L4-routing-gateway-runtime/source
bash run_l4.sh
```

## Run the behavioral tests

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/L4-routing-gateway-runtime/source
python3 -m unittest test_l4 -v
```

## Start the gateway manually and exercise it

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/L4-routing-gateway-runtime/source
python3 gateway.py --port 8765 &
GW_PID=$!

# Health check
curl -s http://127.0.0.1:8765/v1/health | python3 -m json.tool

# Auto request (simple — routes cheap)
curl -s -X POST http://127.0.0.1:8765/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"auto","messages":[{"role":"user","content":"What is the boiling point of water?"}],"max_tokens":64}' \
  | python3 -m json.tool

# Auto request (hard math — routes strong)
curl -s -X POST http://127.0.0.1:8765/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"auto","messages":[{"role":"user","content":"Use induction to prove that 1+2+...+n = n(n+1)/2."}],"max_tokens":256}' \
  | python3 -m json.tool

# Forced model
curl -s -X POST http://127.0.0.1:8765/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4.1","messages":[{"role":"user","content":"Summarize quantum entanglement in one sentence."}],"max_tokens":64}' \
  | python3 -m json.tool

# Show ledger
cat cost-ledger.jsonl | python3 -m json.tool

# Stop
kill $GW_PID
```

## Inspect the ledger from a prior run

```bash
# Pretty-print all entries
cat model-routing/degrees/01-llm-model-routing/03-pocs/L4-routing-gateway-runtime/source/cost-ledger.jsonl | python3 -c "
import sys, json
total = 0
for line in sys.stdin:
    if line.strip():
        e = json.loads(line)
        print(f\"{e['ts']}  {e['decision']:<22}  {e['chosen_model']:<15}  \${e['usd']:.6f}  {e['latency_ms']}ms\")
        total += e['usd']
print(f'Total: \${total:.6f}')
"
```
