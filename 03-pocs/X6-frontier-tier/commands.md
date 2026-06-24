# Commands

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd source
python3 run_x6.py        # gpt-5.5 + gpt-5.4 over 45 tasks; per-model acc/cost/latency; 2- vs 3-tier oracle
python3 x6_3tier.py      # realizable 3-tier router (CV logistic, two thresholds)
```
Prices: gpt-5.5 $5/$30, gpt-5.4 $2.50/$15 per 1M (openai.com/api/pricing, aipricing.guru, 2026-06-22).
First run bills the gpt-5.5/5.4 calls (~$0.16 total); cached after.
