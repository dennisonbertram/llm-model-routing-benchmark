# Assumptions

- The reader is an autonomous coding agent that can call OpenAI/Anthropic/xAI HTTP APIs.
- Small, in-repo task suites (~12 items/discipline) are sufficient to *demonstrate* routing
  tradeoffs and produce a real Pareto frontier; they are NOT publication-scale benchmarks. This
  limitation is stated wherever results are reported.
- Cost is computed from a price table (provider pricing pages, dated) plus, where available,
  provider-returned cost (xAI `cost_in_usd_ticks`). Relative cost comparisons are robust to small
  price drift; absolute figures are list-price estimates and labeled as such.
- Quality is graded by executing code against unit tests (coding), exact/numeric match (math), and
  an LLM judge (open-ended QA). The judge is itself a model and can err; its model + prompt are
  recorded so results are reproducible.
