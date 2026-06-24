# Environment

- Repo: `/Users/dennison/conductor/workspaces/agent-university/nashville`
- Credentials: `.agent-university/secrets.local.env` (gitignored). Load:
  `set -a; . .agent-university/secrets.local.env; set +a`
- Required env vars: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `XAI_API_KEY`.
  Optional: `OPENROUTER_API_KEY` (enables the OpenRouter backend).
- No network egress beyond the model provider HTTPS endpoints.
