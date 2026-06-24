# G-013: Stale gateway process on the same port silently hijacks a new gateway start

**Category**: gotcha
**Severity**: medium
**Evidence tier**: Live verified
**Source POC**: L4-routing-gateway-runtime, L3c-openai-compatible-gateway-integration

## What

Live verified in two separate POCs. When a prior gateway process was still running on the same port (from an incomplete test run that wasn't killed), starting a second gateway produced `OSError: [Errno 48] Address already in use`. Because the new gateway ran in the background with stderr suppressed, the script detected the old server as still ready and continued sending curl requests to the old process. The demo output looked identical to a clean run — but requests were served by the old gateway, not the new one.

In L3c, a similar collision occurred between the test suite (port 8765) and the run script (port 8765). The fix was to use separate ports: 8766 for tests, 8770 for the run script. The OS TIME_WAIT state can hold a port for up to 2 minutes after a server process exits.

## Why it matters

A routing gateway that silently starts against a stale process will serve requests with the old router version, old credentials, and old configuration — while the deployment script reports success. This is a correctness failure that looks like a success.

## Root cause

The OS TIME_WAIT socket state holds a port bound for up to 2 minutes after a process exits. If a new server tries to bind before the socket clears, it gets `EADDRINUSE`. If the new server runs in the background (with `&`) and fails to bind, it exits immediately — but the health check script finds the old server still responding on that port and declares success.

## Fix

Always kill any prior server process on the target port before starting a new one:

```bash
# Kill any process on port 8080
lsof -ti :8080 | xargs kill -9 2>/dev/null || true
sleep 0.5   # allow OS to release the socket

# Start new gateway
python3 gateway.py --port 8080 &
GATEWAY_PID=$!

# Verify it is the NEW process that is responding
until curl -sf http://localhost:8080/v1/health; do sleep 0.5; done
echo "Gateway PID $GATEWAY_PID is ready"
```

Use `SO_REUSEADDR` in the server socket initialization to reduce TIME_WAIT impact:

```python
import socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(("127.0.0.1", port))
```

Use distinct ports for test runs and demo/production runs to avoid collisions between concurrent processes.

## Regression note

In CI, assert that the gateway PID returned by the start command matches the process actually serving health checks. A simple `curl -s .../v1/health | python3 -c "import sys,json; print(json.load(sys.stdin)['pid'])"` field in the health response can confirm this.

## Evidence

- Source: `03-pocs/L4-routing-gateway-runtime/surprises.md`, item 3: "When the prior demo run's gateway was still alive, starting a second gateway on the same port produced `OSError: [Errno 48] Address already in use`. Because the gateway runs in the background and its stderr is suppressed, the script detected this as the old server still being ready (it was) and proceeded with curl requests hitting the old process." (Live verified)
- Source: `03-pocs/L3c-openai-compatible-gateway-integration/surprises.md`, item 3: "The first run of `run_l3c.py` failed with `OSError: [Errno 48] Address already in use` because the test suite had used port 8765 and the OS hadn't released it yet. Used port 8770 for the run script and port 8766 for the test suite to avoid the collision." (Live verified)
