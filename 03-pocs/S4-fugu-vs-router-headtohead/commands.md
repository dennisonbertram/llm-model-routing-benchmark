# Commands
set -a; . .agent-university/secrets.local.env; set +a
cd source
python3 verify_tasks.py    # 15 fresh tasks; math golds computed, coding refs validated
python3 headtohead.py      # all systems on identical tasks -> headtohead_results.json + falsification checks
# Routers decide from prompt only; classifier trained on the OLD 45-suite (leakage-free). Fugu timeout 300s.
