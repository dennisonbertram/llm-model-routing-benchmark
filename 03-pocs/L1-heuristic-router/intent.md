# POC Intent

POC level: L1 — rule-based heuristic routing

POC name: Heuristic Router (complexity features from prompt text)

Concept introduced: deterministic, feature-based routing using only the prompt text. No ML, no
training, no oracle knowledge required. Shows that simple rule-based routing can beat always-cheap
and approach the oracle frontier on the Pareto curve.

Prior concepts reused: the measurement harness, the oracle baseline, and the 45-task suite from L0.

Live service boundary exercised: real chat completions to OpenAI (gpt-4o-mini, gpt-4.1). No new
providers; reuses L0's credential setup.

Real resources required: OPENAI_API_KEY (3 live API calls for confirmation; rest uses cached L0 labelset).

Expected learning:
- Can simple text features (length, keywords, syntax) route between models competently?
- What is the accuracy/cost Pareto frontier for heuristic routing?
- When does a heuristic plateau, requiring ML (L2–L2b) or cascades (L3a) to improve further?

What this POC must prove:
1. A deterministic heuristic can identify high-complexity items and route them to a stronger model.
2. The heuristic beats always-cheap on accuracy while costing less than always-strong.
3. The full threshold sweep is measurable, showing a clear cost-quality tradeoff.
4. A few live API calls confirm the heuristic's routing decisions match measured predictions.

What would count as cheating:
- Using item metadata (difficulty, discipline) in the heuristic. (Oracle leakage.)
- Tuning the heuristic weights to maximize accuracy on this suite (overfitting).
- Mocking the live API calls in the confirmation step.
- Reporting threshold that wasn't actually tested.

Why cheating would destroy the learning:
- If the heuristic uses oracle difficulty labels, it proves nothing about real-world routing.
- If tuned to this suite, it won't generalize to new prompts.
- Mocking hides whether the heuristic's routing actually produces correct answers with real models.
- The degree teaches pragmatic routing; overfitting is a trap that kills production systems.
