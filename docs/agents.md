# Agents

ResearchInfra is agent-agnostic. The v1 foundation includes interfaces and
placeholder adapters, but no provider-specific automation.

## Backends

Supported backend configuration kinds:

- `manual`
- `shell`
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
suggested backend.

Execute or dry-run a task through the v1 bridge:

```bash
researchinfra agent run task-writing-0001 \
  --project project-... \
  --workspace /tmp/ri-demo \
  --backend manual \
  --dry-run
```

Manual runs print instructions and, without `--dry-run`, write a result file
under `projects/<project-slug>/agents/results/`. The shell backend can run only
commands already declared in `AgentTask.safe_commands`, and only after `--yes`.
Codex, Claude Code, and OpenHands wrappers report missing installation or
configuration instructions instead of modifying files silently.

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

## Model Registry

Workspace model commands:

```bash
researchinfra model list --workspace /tmp/ri-demo
researchinfra model set-default \
  --workspace /tmp/ri-demo \
  --task reading \
  --provider openai-compatible \
  --model gpt-4o-mini
researchinfra model test --workspace /tmp/ri-demo --task reading
```

`researchinfra model check` is kept as a quick OpenAI-compatible environment
check. All model commands report only secret presence, never secret values.
Runtime OpenAI-compatible calls use:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL` optional
- `OPENAI_MODEL` optional
