# POC Intent

POC level: L4 — routing gateway runtime
POC name: Local HTTP routing gateway with cost ledger
Concept introduced: routing as a deployed HTTP service; per-request cost tracking via JSONL
  ledger; OpenAI-compatible wire format as the integration surface for clients.
Prior concepts reused: heuristic routing logic from L1; harness providers.py for real API calls;
  OpenAI-shaped JSON from L3c.
Live service boundary exercised: real POST /v1/chat/completions calls to OpenAI API (gpt-4o-mini
  and gpt-4.1); local HTTP server process-boundary exercised from a separate curl client.
Real resources required: funded OPENAI_API_KEY.
Expected learning: how to interpose a routing layer as a transparent HTTP proxy; that routing
  decisions, chosen models, tokens, and USD cost can be persisted to a ledger without the client
  knowing or caring; that the OpenAI wire format is the lingua franca for heterogeneous routing.
What this POC must prove: a separate process (curl) can send an "auto" request to the gateway
  and receive a real model response with routing metadata; a forced-model request bypasses routing;
  every request appends a ledger line with real cost and latency.
What would count as cheating: mocking the backend API calls; returning fabricated tokens or cost;
  recording ledger entries without real calls.
Why cheating would destroy the learning: the value of the gateway pattern is that it works as a
  real process boundary — if backend calls are mocked, the process-boundary evidence is worthless.
