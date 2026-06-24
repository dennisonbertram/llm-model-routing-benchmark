# Commands
set -a; . .agent-university/secrets.local.env; set +a
cd source && python3 run_fugu.py   # fugu + fugu-ultra + gpt-5.5 over the 21 S0 tasks -> fugu_results.json
# Note: fugu-ultra can exceed 120s/query (multi-agent); timeout set to 300s. Cost folds orchestration tokens.
