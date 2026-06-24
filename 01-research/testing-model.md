# Testing Model

**Target**: Model Routing — LLM/model selection for cost-efficient agent inference
**Evidence status**: Research supported but not live verified (no POCs executed yet)
**Grounding**: RouterBench (Hu et al., arXiv:2403.12031, ICML 2024); LLMRouterBench (arXiv:2601.07206v1); RouteLLM (Ong et al., arXiv:2406.18665); FrugalGPT (Chen, Zaharia, Zou, arXiv:2305.05176)

---

## Core tension: routers are evaluated, not just tested

A unit test checks a contract; a router evaluation checks a *policy* against real model outputs. These are different operations. A router can pass all local unit tests and still perform worse than the cheapest model on your actual task distribution. Honest evaluation therefore requires:

1. **Real model calls** (no mocks) producing actual outputs that feed into graders.
2. **Held-out splits** — training labels and evaluation labels must be disjoint.
3. **Reference baselines** — the oracle upper bound and the always-cheap / always-strong bounds.
4. **Aggregate metrics** — accuracy and cost together on a Pareto frontier, not accuracy alone.

The harness (`harness/router_base.py`, `harness/metrics.py`) implements this discipline. The sections below explain why each element matters.

---

## Task suites

### Discipline mapping

The harness ships four task suites (see `harness/tasks.py`). Each targets a distinct grading modality:

| Suite | # items | Grader | Gold answer |
|---|---|---|---|
| `coding` | ~12 | Unit-test execution (subprocess) | Pass/fail per test |
| `math` | ~12 | Exact / numeric match | Numeric scalar |
| `qa` | ~12 | LLM-judge (strong model, binary) | Short canonical string |
| `mixed-easy` / `mixed-hard` | ~12 each | Mixed (above) | Per-item grader tag |

Items are authored locally — no licensed dataset is copied. This matters for two reasons: (1) licensed benchmark answers may appear in training corpora of the models under test, inflating accuracy; (2) short, self-contained items keep live run costs manageable.

**Discipline coverage rationale** (grounded in RouterBench methodology):

RouterBench (Hu et al., 2024) used eight datasets spanning commonsense reasoning (Hellaswag, Winogrande, ARC), knowledge (MMLU 57 subtasks), conversation (MT-Bench), math (GSM8K), coding (MBPP), and RAG (657 custom QA pairs) for a total of 405,467 samples across 11 models. Their finding: "monetary costs of LLM services can routinely vary by factors of 2–5× for comparable levels of performance." Because coding is this degree's primary discipline (per the spec), the coding suite is the most important routing signal. Math and QA cover the orthogonal reasoning and retrieval cases.

*Research supported but not live verified — the RouterBench numbers above are the paper's reported figures, not measurements from this repo.*

### Why small suites demonstrate rather than prove

The harness suites are intentionally small (~12 items per discipline) to keep live POC runs fast and cheap. This is sufficient to *demonstrate* routing behaviour and rank strategies relative to each other. It does **not** provide statistical power to claim that a router generalises to a broader distribution:

- A 12-item coding suite has ~±14% confidence intervals at 95% (binomial). A router that scores 8/12 vs 7/12 is indistinguishable from noise.
- RouterBench used 405k samples to measure fine-grained AIQ differences between KNN and MLP routers; our suite cannot replicate that resolution.
- The `mixed-easy` / `mixed-hard` split is chosen to make routing **measurable** — if every item is hard, cheap models always fail and there is nothing to route; if every item is easy, every model passes and routing has no value. The mix ensures the cheap-model tier and the strong-model tier occupy different regions of the Pareto space.

**Operational rule**: POC reports must describe results as "on the 12-item harness suite" and must not extrapolate to claimed generalisation across unseen tasks.

---

## Graders

### Coding — unit-test execution

The gold standard for code evaluation. The model produces a Python function; the grader runs a hidden test file in a subprocess and records pass/fail per test case. A partially passing function scores the fraction of tests that pass.

```python
# harness/judge.py — coding grader sketch
import subprocess, tempfile, os

def grade_coding(code: str, test_file_path: str) -> float:
    """Run unit tests against model-produced code. Returns fraction passing."""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code + "\n")
        f.write(open(test_file_path).read())
        tmp = f.name
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", tmp, "-q", "--tb=no"],
            capture_output=True, text=True, timeout=10
        )
        # Parse "X passed, Y failed" from stdout
        lines = result.stdout.splitlines()
        for line in lines:
            if "passed" in line or "failed" in line:
                passed = int(line.split(" passed")[0].split()[-1]) if "passed" in line else 0
                total = passed + (int(line.split(" failed")[0].split()[-1]) if "failed" in line else 0)
                return passed / total if total > 0 else 0.0
        return 0.0
    finally:
        os.unlink(tmp)
```

**No mock grading**: grading by running the code is the only valid evidence. An LLM-judge grading code quality is a weaker signal — use it only if unit tests are unavailable for a given item.

### Math — exact / numeric match

For math items the gold answer is a numeric scalar. The grader normalises both the model output and the gold (strip whitespace, trailing zeros, convert fractions) and checks equality. A tolerance of ±0.001 is used for floating-point answers.

```python
def grade_numeric(answer: str, gold: str, tol: float = 1e-3) -> bool:
    try:
        return abs(float(answer.strip()) - float(gold.strip())) <= tol
    except ValueError:
        return answer.strip().lower() == gold.strip().lower()
```

### QA — LLM-judge

Open-ended factual questions where gold is a short reference string. The judge calls a strong model (e.g. `gpt-4.1` or `claude-opus-4-8`) with a fixed prompt asking "Does the candidate answer correctly answer the question given the reference? Answer YES or NO." The prompt is templated in `harness/judge.py`.

**LLM-judge failure modes to watch**:
- Sycophantic agreement: the judge tends to say YES for confident-sounding wrong answers. Mitigation: use a strict prompt that requires the answer to contain the key fact, not just sound plausible.
- Cost: each judge call uses the strong model. Budget ~$0.002 per QA item judged.
- Non-determinism: run temperature=0 for the judge to stabilise verdicts.

RouterBench used GPT-4 for MT-Bench, MBPP, and RAG evaluation with binary 0/1 conversion. This is the same approach used here.

*Research supported but not live verified.*

---

## Held-out splits and the no-leakage rule

Router training (for kNN and classifier POCs) uses labels generated from real model runs on a training split. The evaluation split must never overlap with training items.

**Split discipline** (from LLMRouterBench methodology, arXiv:2601.07206):

> Fixed-split evaluation: consistent train-test splits given the same random seed, averaged across runs.

In the harness:
- `tasks.py` assigns each item a `split` field: `"train"` or `"eval"`.
- `router_base.run_suite(router, suite, split="eval")` filters to eval items only.
- Training labels for the kNN/classifier routers are generated on `split="train"` items.
- The `split` field is frozen at item authoring time — **never** re-split after looking at results.

Without this discipline a classifier trained on "hard" items from the eval split will appear to route well but will fail on unseen queries.

---

## The oracle upper bound

The oracle is the theoretical ceiling on what a perfect router could achieve if it knew in advance which model would answer correctly for every item.

**Oracle definition** (from RouterBench, Hu et al., 2024):

> The oracle routes to the best-performing LLM for each item; when multiple models answer correctly, it selects the cheapest.

In code:
```python
def oracle_route(item, model_outputs: dict[str, str], grader) -> str:
    """Given pre-generated outputs from all models, return the cheapest correct model."""
    correct_models = [m for m, out in model_outputs.items() if grader(item, out)]
    if not correct_models:
        return min(model_outputs, key=lambda m: pricing.usd_for(m, 1, 1))  # cheapest anyway
    return min(correct_models, key=lambda m: pricing.usd_for(m, item["est_pt"], item["est_ct"]))
```

The oracle is computed in X5 (`X5-router-benchmark-pareto`) where all model outputs have already been collected. It is **not** a router you can deploy — it requires knowing answers in advance.

**Why the oracle matters**: RouterBench found that the oracle dramatically outperforms all learned routers on cost-at-quality. LLMRouterBench introduced `Gap@Oracle` — the average ratio of oracle accuracy to router accuracy — as the primary advancement metric. A large Gap@Oracle means there is room for improvement; a small gap means the router is near-optimal for the dataset.

The oracle also reveals when cheap models are sufficient: if the oracle rarely selects the strong model on coding items, the strong model adds marginal value and you are overpaying with always-strong.

*Research supported but not live verified — oracle values will be computed from live POC runs in X5.*

---

## Measuring on the Pareto frontier

A single accuracy number hides the cost story. A router that achieves 90% accuracy at $0.001 per item and another that achieves 90% accuracy at $0.01 per item are not equivalent. The Pareto frontier is the set of routing configurations that are not dominated — there is no other configuration that is both cheaper and more accurate.

**Construction** (Non-Decreasing Convex Hull, RouterBench methodology):

For any two points (c₁, q₁) and (c₂, q₂) with c₂ ≥ c₁, require q₂ ≥ q₁. This eliminates configurations that are more expensive but less accurate. The convex hull of the remaining points forms the frontier.

**X-axis (cost)**: total USD spent across all items in the suite at a given configuration (threshold / model assignment).
**Y-axis (accuracy)**: fraction of items correctly answered.

**AIQ (Average Improvement in Quality)** — RouterBench's aggregate metric:

```
AIQ(R) = 1 / (c_max - c_min) × ∫[c_min to c_max] R̃(c) dc
```

where R̃(c) is the quality achieved by router R at cost c. This is the area under the cost-quality curve, normalised by the cost range. Higher AIQ = better routing across the cost spectrum.

**ParetoDist** — LLMRouterBench's metric: normalised L1 distance from a point to the empirical Pareto frontier. Lower = closer to optimal.

In this degree, the Pareto plot is produced in X5 (`X5-router-benchmark-pareto`). Each POC contributes one point (or a curve if it has a tunable threshold). The capstone (`L-capstone`) should dominate or match the individual strategy curves.

**Practical note on threshold sweeping**: for routers with a scalar threshold (confidence cutoff in FrugalGPT cascade, decision threshold in classifier), sweep the threshold across its range and plot each (cost, accuracy) pair. The resulting curve should approximate the frontier between the always-cheap and always-strong anchors.

---

## RouterBench methodology — compressed reference

Paper: Hu et al., "RouterBench: A Benchmark for Multi-LLM Routing System," arXiv:2403.12031, ICML 2024.
Code/data: https://github.com/qitian-jason-hu/RouterBench (linked from abstract).

Key methodological choices to adopt or adapt:

| RouterBench choice | This harness | Reason for adaptation |
|---|---|---|
| 405k samples, 11 models | ~12 items, 3 models | Cost control for live runs |
| Precomputed inference outputs | Live model calls per POC | Honesty — no stale data |
| 5-shot for most datasets | 0-shot (task-authored) | Avoid licensed dataset copying |
| GPT-4 judge for open tasks | Strong model judge (configurable) | Same discipline |
| Oracle = cheapest correct model | Identical definition | Direct comparability |
| AIQ as primary metric | AIQ + % routed cheap | Added cost breakdown |

RouterBench finding (paper's claim, not reproduced here): KNN and MLP predictive routers "achieve a level of performance comparable to the best individual LLMs with lower or similar costs," but "none significantly outperform the baseline Zero router across all datasets." Cascading routers degrade rapidly when verifier error rate exceeds 0.2.

*Research supported but not live verified. The above are the paper's reported results.*

---

## What the POCs test (mapping to graders)

| POC | Task suite(s) | Grader(s) | What is measured |
|---|---|---|---|
| L0-smoke | all | all | Baseline accuracy + cost for always-cheap / always-strong |
| L1-heuristic | mixed | appropriate per item | Does heuristic land between baselines? |
| L2-embedding-knn | all | all | kNN router accuracy + cost vs baselines |
| L2b-classifier | held-out eval | all | Classifier Pareto curve via threshold sweep |
| L3a-frugalgpt | qa, math | LLM-judge, exact | Cost reduction at matched accuracy |
| L3b-harness-routing | coding | unit tests | All-strong vs routed harness on code tasks |
| X2-self-consistency | math | exact | Sample-k vs single-strong cost+accuracy |
| X5-router-benchmark | all | all | Full Pareto frontier across all strategies |
| L-capstone | all | all | Capstone vs baselines on Pareto frontier |

---

## No-mock rule

No mock at any LLM service boundary. `unittest.mock.patch("providers.chat")` patching is **not** valid POC evidence. It proves only that your code handles a pre-shaped string — not that the model produces the right output, not that cost is accurate, not that the fallback fires on real 429s.

Mocks are permitted only for:
- Pure local parser logic (a function that parses a pre-formatted string).
- Testing the router's control flow in isolation, explicitly labelled "Invalid for service evidence."

All POC green output must include real request IDs and real token/cost numbers from the live API.

---

## Sources

- RouterBench: https://arxiv.org/abs/2403.12031 (Hu et al., ICML 2024)
- LLMRouterBench: https://arxiv.org/html/2601.07206v1
- RouteLLM: https://arxiv.org/abs/2406.18665 (Ong et al., ICLR 2025)
- FrugalGPT: https://arxiv.org/abs/2305.05176 (Chen, Zaharia, Zou, 2023)
