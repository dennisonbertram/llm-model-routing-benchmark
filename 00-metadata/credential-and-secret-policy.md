# Credential and Secret Policy

- Secrets live only in `.agent-university/secrets.local.env` (gitignored). Never commit, echo, or
  log key values. Confirm presence with `[ -n "$OPENAI_API_KEY" ] && echo SET || echo UNSET`.
- POC code reads keys from the environment; no key is ever written into source, evidence, or logs.
- Provider responses pasted into evidence are scrubbed of any `Authorization`/`x-api-key` echoes.
