# G-012: Gateway health endpoint passes without credentials — a canary request is needed to confirm backend auth

**Category**: gotcha
**Severity**: medium
**Evidence tier**: Live verified
**Source POC**: L4-routing-gateway-runtime

## What

Live verified. In the L4 routing gateway, `GET /v1/health` returned HTTP 200 with no API key set. The gateway process started, bound to the port, and served health checks before touching any provider credential. The HTTP 502 error only appeared when a real model call was attempted inside a `POST /v1/chat/completions` handler.

In the live run, a missing `OPENAI_API_KEY` caused HTTP 502 on the first chat completion request — but all prior health probes succeeded.

## Why it matters

Container orchestrators (Kubernetes, Railway, Fly.io) use `GET /health` or `GET /v1/health` as readiness probes. If the gateway only checks the HTTP listener (not the actual provider connection), the container will be marked `Ready` before credentials are injected, and live traffic will fail with 502s until the secret is available.

An automated deployment pipeline that waits for the health check to pass before sending traffic will deliver broken requests if backend credentials are not validated in the health check.

## Root cause

The routing gateway's health endpoint is intentionally lightweight — it checks that the server is listening and has a loaded router model. It does not make a test call to any provider, because doing so would add latency, cost, and a provider dependency to every liveness probe cycle.

## Fix

Use a two-tier readiness check in production deployments:

1. **Liveness probe** (`/v1/health`): lightweight, no provider call — confirms the process is alive and the HTTP listener is bound.
2. **Startup canary** (one-time, run by the deployment script after health passes): send a real `POST /v1/chat/completions` with a trivial prompt and assert the response is HTTP 200 with non-empty content. This confirms API credentials are valid and the provider backend is reachable.

Example deploy script pattern:
```bash
# Wait for the process to be healthy
until curl -sf http://localhost:8080/v1/health; do sleep 1; done

# Canary: confirm credentials work
RESP=$(curl -sf -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"auto","messages":[{"role":"user","content":"ping"}]}')
echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['choices'][0]['message']['content'], 'canary failed'"
echo "Canary passed."
```

## Regression note

Add an integration test that starts the gateway with a deliberately invalid API key, calls `/v1/health`, and asserts that the health check passes (HTTP 200) while a subsequent `/v1/chat/completions` call fails (HTTP 502 or 401). This documents the intentional separation between liveness and credential readiness.

## Evidence

- Source: `03-pocs/L4-routing-gateway-runtime/surprises.md`, item 1: "The gateway process starts, binds to the port, and successfully serves `GET /v1/health` without touching any API key. The 502 error only appears when a real model call is attempted inside a `POST /v1/chat/completions` handler. This means container readiness probes (which typically call `/v1/health`) would pass before credentials are injected — a live deployment needs a separate 'canary' request test, not just a health-check ping, to confirm the backend credentials are valid." (Live verified)
- Source: results-digest.md, L4: "RED = HTTP 502 missing key." (Live verified)
