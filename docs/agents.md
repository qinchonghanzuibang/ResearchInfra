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

Project-local task specs are created with:

```bash
researchinfra agent task create \
  --project project-... \
  --workspace /tmp/ri-demo \
  --type coding \
  --title "Implement baseline loader"
```

The command writes YAML under `projects/<project-slug>/agents/tasks/` with
context files, expected outputs, constraints, verification commands, and a
suggested backend. It does not execute Codex, Claude Code, OpenHands, OpenClaw,
or any other backend.

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

## OpenAI-Compatible Check

The `researchinfra model check` command reports whether the
OpenAI-compatible provider is configured through environment variables without
printing secret values. Runtime model calls use:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL` optional
- `OPENAI_MODEL` optional
