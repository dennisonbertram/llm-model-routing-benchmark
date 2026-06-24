# Commands
set -a; . .agent-university/secrets.local.env; set +a
cd source && python3 run_s2.py   # vendored AB-MCTS-A engine = abmcts.py ; results -> s2_results.json
# budgets {1,8}; budget 16 hung on slow OpenRouter calls (1+8 already conclusive). public/hidden split, no leakage.
