# POC Intent

POC level: L0 — live access and smoke
POC name: Live smoke + baseline measurement harness
Concept introduced: the routing measurement model (model pool, deterministic graders, uniform
  cost accounting) + the oracle/baseline framing that quantifies routing headroom.
Prior concepts reused: none (foundation).
Live service boundary exercised: real chat + embeddings calls to OpenAI, Anthropic, xAI.
Real resources required: funded OPENAI_API_KEY, ANTHROPIC_API_KEY, XAI_API_KEY.
Expected learning: how much quality-per-dollar routing can possibly recover (the oracle ceiling),
  and where the cheap/strong gap actually lives.
What this POC must prove: providers are live; the harness measures real acc/cost/latency; a real
  cost-quality gap and oracle headroom exist.
What would count as cheating: mocking provider responses; hardcoding accuracy/cost; computing the
  oracle from anything but real per-task correctness.
Why cheating would destroy the learning: the entire degree's premise (routing saves money at
  matched quality) is only credible if the baseline gap is measured against real models.
