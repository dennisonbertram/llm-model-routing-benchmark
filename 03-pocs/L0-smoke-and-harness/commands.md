# Commands

```bash
# Load credentials (gitignored)
set -a; . .agent-university/secrets.local.env; set +a

cd model-routing/degrees/01-llm-model-routing/03-pocs/L0-smoke-and-harness/source

# GREEN — 3 live behavioral tests
python3 test_l0.py            # -> green-output.txt (OK, 3 tests, ~5s)

# Baseline report (cheap vs strong vs oracle over 45 tasks)
python3 run_l0.py            # -> run-output.txt + l0_summary.json

# RED — live-access blocker (run with keys unset)
( unset OPENAI_API_KEY ANTHROPIC_API_KEY XAI_API_KEY; python3 test_l0.py )  # -> red-output.txt
```

First run populates `harness/.cache/labelset.json`; later POCs reuse it so each unique
`(model, task)` pair is billed once.
