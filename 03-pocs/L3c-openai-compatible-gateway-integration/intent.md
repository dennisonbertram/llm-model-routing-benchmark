# Intent — L3c OpenAI-Compatible Gateway Integration

## Goal

Show that a routing layer can be surfaced behind the **OpenAI chat completions wire format**,
so that any existing OpenAI client — the official Python SDK, the Vercel AI SDK, LangChain,
or a raw HTTP client — can use a router without code changes beyond a `base_url` override.

This is the **deployment integration seam** for a router: it turns a routing strategy (L1
heuristic, L2 embedding-kNN, or L3a cascade) into a service that production clients can
consume without knowing anything about how routing decisions are made.

## What we build

A minimal Python stdlib HTTP server (`gateway.py`) that:

1. Accepts a standard `POST /v1/chat/completions` request with `{model:"auto", messages:[...]}`
2. Applies a heuristic router to select `gpt-4o-mini` (cheap) or `gpt-4.1` (strong) from the
   prompt text alone (no oracle features)
3. Calls the upstream model via the frozen harness `providers.chat()`
4. Returns a valid OpenAI `chat.completion` JSON object with real token counts and actual model id

## What it proves

- The router's routing logic can be hidden behind a standard interface
- The `model` field in the response reflects the **actually served** model (never `"auto"`)
- The `openai` Python package `base_url` override works with this server unchanged
- The wire format matches what OpenAI sends: `choices[0].message.content`, `usage`, `id`, `object`
- Explicit model passthrough (client says `model:"gpt-4.1-nano"`) is honoured

## What it does NOT prove

- Production-grade reliability or concurrency (this is a demo-grade stdlib server)
- That the heuristic router achieves good accuracy-vs-cost on the benchmark suite (that is L1's claim)
- That the gateway scales beyond a single-threaded request handler

Those claims are made by other POCs; L3c's narrow scope is the **integration seam**.
