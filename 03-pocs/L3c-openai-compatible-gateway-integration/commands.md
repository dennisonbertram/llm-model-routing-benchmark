# Commands — L3c OpenAI-Compatible Gateway Integration

## Prerequisites

Load credentials (required for live tests):
```bash
set -a; . .agent-university/secrets.local.env; set +a
```

## Run the behavioral tests

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/L3c-openai-compatible-gateway-integration/source
python3 test_l3c.py
# Expected: Ran 10 tests in ~9s — OK
```

## Run the full integration script

```bash
cd model-routing/degrees/01-llm-model-routing/03-pocs/L3c-openai-compatible-gateway-integration/source
python3 run_l3c.py
# Starts gateway, runs wire tests, tries openai SDK, writes l3c_evidence.json
```

## Reproduce RED output (no keys)

```bash
env -i HOME="$HOME" PATH="$PATH" python3 test_l3c.py
# Expected: 4 offline heuristic tests pass, 6 live wire tests ERROR with HTTP 502
```

## Start gateway as a standalone server

```bash
# Start (will block):
python3 -c "
import os, sys
sys.path.insert(0, '$(pwd)/../../../harness')
from gateway import run_server
s = run_server()
s.serve_forever()
"

# In another terminal, call it:
curl -s http://127.0.0.1:8770/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer x' \
  -d '{"model":"auto","messages":[{"role":"user","content":"What is the capital of France?"}]}'
```

## Use with openai Python SDK

```python
import openai
client = openai.OpenAI(base_url="http://127.0.0.1:8770/v1", api_key="not-needed")
resp = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "What is 2+2?"}]
)
print(resp.model)           # gpt-4o-mini (actually served)
print(resp.choices[0].message.content)
```

## Use with Vercel AI SDK (TypeScript)

```typescript
import { createOpenAI } from "@ai-sdk/openai";
import { generateText } from "ai";

const router = createOpenAI({ baseURL: "http://127.0.0.1:8770/v1", apiKey: "x" });
const { text } = await generateText({
    model: router("auto"),
    prompt: "What is the capital of France?",
});
```

## Use with LangChain

```python
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="auto", base_url="http://127.0.0.1:8770/v1", api_key="x")
result = llm.invoke("What is the capital of France?")
```
