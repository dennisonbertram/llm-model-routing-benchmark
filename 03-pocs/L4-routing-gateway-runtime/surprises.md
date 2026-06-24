# Surprises

## 1. Gateway health passes even with no credentials

The gateway process starts, binds to the port, and successfully serves `GET /v1/health`
without touching any API key. The 502 error only appears when a real model call is
attempted inside a `POST /v1/chat/completions` handler. This means container readiness
probes (which typically call `/v1/health`) would pass before credentials are injected —
a live deployment needs a separate "canary" request test, not just a health-check ping,
to confirm the backend credentials are valid.

## 2. Python 3.9 rejects f-string expressions containing quote-matched dict lookups

The shell-embedded Python ledger display used f-strings of the form
`f"  {'ts':24}  {'decision':20}  ..."` which Python 3.9 rejects with `SyntaxError:
f-string: expecting '}'`. Python 3.12 handles this but 3.9 (the system Python on macOS
14) does not. Had to switch to `.format()` — a portability footgun when writing quick
inline Python in shell scripts.

## 3. Port reuse from a prior incomplete run causes the gateway to fail silently in the background

When the prior demo run's gateway was still alive (from a previous test run that wasn't
killed), starting a second gateway on the same port produced `OSError: [Errno 48] Address
already in use`. Because the gateway runs in the background and its stderr is suppressed,
the script detected this as the old server still being ready (it was) and proceeded with
curl requests hitting the old process. The demo output looked identical to a clean run.
The fix: always kill any prior server on the port before starting a new one, or use a
unique port per invocation.

## 4. The keyword set matters more than expected

"How many ways can you arrange 5 items..." contained the word "combinatorics" in the
prompt because we included it explicitly. The routing matched on that word. If we had
phrased the question as "How many permutations of 5 from 8?" without the word
"combinatorics", the prompt would have matched "permutation" instead (which is also in
the keyword set). The heuristic is brittle: users who ask genuinely complex math questions
in plain language ("I have 8 marbles, 5 red and 3 blue, how many distinct color
sequences...") may get routed cheap. This is the motivation for the embedding-kNN (L2)
and classifier (L2b) routers.

## 5. The x_routing field reveals the chosen model — not always desirable

The `x_routing` field in the response exposes `chosen_model`, `decision`, and `usd`.
In a production setting, cost metadata may be sensitive (reveals provider choice,
pricing, routing logic). A production gateway would strip this field from client responses
and log it only to an internal audit trail.
