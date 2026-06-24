# Commands

```bash
set -a; . .agent-university/secrets.local.env; set +a
cd source
python3 benchmark.py        # -> green-output.txt + benchmark_results.json
```
5-fold CV for kNN/logistic (every task held out once); embeddings + ensembles are live.
First run bills the MoA/self-consistency calls; cached after (re-runs free).
