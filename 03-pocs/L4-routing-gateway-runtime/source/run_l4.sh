#!/usr/bin/env bash
# L4 — Runtime demo: start gateway, curl it, show ledger, stop it.
# Run from the repo root after loading credentials:
#   set -a; . .agent-university/secrets.local.env; set +a
#   bash model-routing/degrees/01-llm-model-routing/03-pocs/L4-routing-gateway-runtime/source/run_l4.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT=8765
GATEWAY_URL="http://127.0.0.1:${PORT}"
LEDGER="${SCRIPT_DIR}/cost-ledger.jsonl"

# Clean ledger from any prior run.
rm -f "${LEDGER}"

echo "=== L4 Routing Gateway Runtime Demo ==="
echo ""

# 1. Start the gateway in the background.
echo "[1/6] Starting gateway on port ${PORT}..."
python3 "${SCRIPT_DIR}/gateway.py" --port "${PORT}" &
GW_PID=$!
echo "      PID=${GW_PID}"

# Wait for the server to be ready (up to 10s).
for i in $(seq 1 20); do
    if curl -sf "${GATEWAY_URL}/v1/health" > /dev/null 2>&1; then
        echo "      Server ready."
        break
    fi
    sleep 0.5
    if [ $i -eq 20 ]; then
        echo "ERROR: server did not start within 10s" >&2
        kill "${GW_PID}" 2>/dev/null || true
        exit 1
    fi
done
echo ""

# 2. Health check.
echo "[2/6] Health check:"
curl -s "${GATEWAY_URL}/v1/health" | python3 -m json.tool
echo ""

# 3. Auto-routed request — simple factual question (should route to cheap).
echo "[3/6] AUTO request — simple factual question (expect cheap: gpt-4o-mini):"
curl -s -X POST "${GATEWAY_URL}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "auto",
        "messages": [{"role": "user", "content": "What is the capital of France?"}],
        "max_tokens": 64
    }' | python3 -m json.tool
echo ""

# 4. Auto-routed request — hard math question (should route to strong: gpt-4.1).
echo "[4/6] AUTO request — hard combinatorics question (expect strong: gpt-4.1):"
curl -s -X POST "${GATEWAY_URL}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "auto",
        "messages": [{"role": "user", "content": "How many ways can you arrange 5 items chosen from 8 distinct items using combinatorics?"}],
        "max_tokens": 128
    }' | python3 -m json.tool
echo ""

# 5. Forced-model request — explicitly request gpt-4o-mini.
echo "[5/6] FORCED request — model=gpt-4o-mini (no routing):"
curl -s -X POST "${GATEWAY_URL}/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "Say hello briefly."}],
        "max_tokens": 32
    }' | python3 -m json.tool
echo ""

# 6. Show ledger.
echo "[6/6] Cost ledger (all 3 requests):"
if [ -f "${LEDGER}" ]; then
    cat "${LEDGER}" | python3 -c "
import sys, json
lines = [json.loads(l) for l in sys.stdin if l.strip()]
hdr = '  {:<24}  {:<20}  {:<18}  {:>5}  {:>5}  {:>10}  {:>7}'
print(hdr.format('ts', 'decision', 'chosen_model', 'pt', 'ct', 'usd', 'ms'))
print('  ' + '-'*100)
row = '  {:<24}  {:<20}  {:<18}  {:>5}  {:>5}  {:>10}  {:>7}'
for l in lines:
    print(row.format(l['ts'], l['decision'], l['chosen_model'],
                     l['prompt_tokens'], l['completion_tokens'],
                     '\${:.6f}'.format(l['usd']), str(l['latency_ms'])+'ms'))
total_usd = sum(l['usd'] for l in lines)
print(row.format('', 'TOTAL', '', '', '', '\${:.6f}'.format(total_usd), ''))
"
else
    echo "  (no ledger file found)"
fi
echo ""

# Stop the gateway.
echo "Stopping gateway (PID=${GW_PID})..."
kill "${GW_PID}" 2>/dev/null || true
wait "${GW_PID}" 2>/dev/null || true
echo "Done."
