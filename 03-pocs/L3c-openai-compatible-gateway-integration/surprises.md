# Surprises — L3c OpenAI-Compatible Gateway Integration

## 1. openai SDK was available and worked without any package install

The `openai` Python package was already importable in this workspace. The `base_url` override
pattern worked exactly as documented — no other changes were needed. The SDK transparently sent
its standard request shape to the gateway and parsed the response without any issues.

This confirms the wire-compat claim is not theoretical: a real SDK client exercised the full path
in the live run.

## 2. The gateway server's `model` field is the key user-visible contract

The most important detail of the integration is that the `model` field in the response must be the
**actually-served** model, not `"auto"`. If a gateway returned `"auto"` in the model field, clients
like the openai SDK's `.model` attribute and LangChain's logging would show meaningless metadata.
The gateway sets `"model": routed_model` in the response, so clients always see the real backend.

## 3. Port reuse between test run and run script

The first run of `run_l3c.py` failed with `OSError: [Errno 48] Address already in use` because
the test suite (`test_l3c.py`) had used port 8765 and the OS hadn't released it yet. Used port
8770 for the run script and port 8766 for the test suite to avoid the collision. This is a
commonplace socket lifecycle issue: the OS TIME_WAIT state can hold a port for up to 2 minutes
after a server process exits.

## 4. The `x_routing` extension field is silently ignored by standard clients

The gateway adds `"x_routing": {"routed_model": ..., "latency_ms": ..., "usd": ...}` to the
response. The openai Python SDK, Vercel AI SDK, and LangChain all ignore unknown top-level fields
in the response JSON. This makes it safe to add routing observability metadata without breaking
any client, while still exposing it to clients that know to look for it (e.g., a custom logging
middleware).

## 5. Explicit model passthrough needed no special routing bypass

When the client sends `model:"gpt-4.1-nano"`, the gateway simply checks `if requested_model == "auto"`
and falls through to call the harness directly with the client's choice. No special passthrough
mechanism was needed — the routing gate is entirely conditional on the sentinel model name `"auto"`.
