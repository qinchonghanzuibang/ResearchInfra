# Agents

ResearchInfra is agent-agnostic. The v1 foundation includes interfaces and
placeholder adapters, but no provider-specific automation.

## Backends

Supported backend configuration kinds:

- `manual`
- `api`
- `codex`
- `claude-code`
- `openhands`
- `openclaw`

Concrete adapters should subclass `AgentBackend` and return
`AgentBackendResult`. Agent tasks should remain file-first and should require
human approval before changing claims, results, or submissions.

## Model Providers

Supported provider configuration kinds:

- `openai-compatible`
- `litellm`
- `ollama`
- `anthropic`
- `openrouter`
- `vllm`

Credentials belong in environment variables or caller-managed secret stores, not
in workspace files.

