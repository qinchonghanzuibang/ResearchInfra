# Architecture

ResearchInfra is organized around durable local files and small Python
interfaces. The project intentionally avoids web UI concerns, cloud accounts,
authentication, and provider-specific assumptions in the v1 foundation.

## Layers

1. **Workspace files** hold the canonical state. Markdown, YAML, JSON, LaTeX,
   and BibTeX are preferred because humans and agents can inspect them directly.
2. **Schemas** define the typed contract for research objects. Pydantic models
   validate object shape before data is written to disk or passed to adapters.
3. **Workspace services** create and inspect local directory layouts, registries,
   and project-local artifacts.
4. **Registries** collect source-grounded and run-grounded state into durable
   YAML/Markdown files for results, tables, figures, claims, paper checks,
   submissions, and agent task results.
5. **Agent backends** route tasks to manual workflows, local tools, API-backed
   agents, or future integrations such as Codex, Claude Code, OpenHands, and
   OpenClaw.
6. **Model providers** route inference to provider adapters such as
   OpenAI-compatible APIs, LiteLLM, Ollama, Anthropic, OpenRouter, and vLLM.
7. **Skills** package reusable research workflows as local YAML metadata plus
   Markdown prompt templates that can be overridden per workspace.

## Design Boundaries

ResearchInfra tracks research state. It does not claim scientific conclusions,
invent missing results, or run provider-specific automation without an adapter.
Claims should be tied to evidence links, and agent tasks should keep human
approval explicit.

The v1 execution bridge is intentionally narrow. Manual task runs print
instructions and write result files. Shell task runs execute only
task-declared `safe_commands` and require `--yes`. External agent wrappers must
record status, stdout, stderr, and setup/configuration gaps instead of modifying
files silently.

## Extension Points

- Add schema-specific file readers and writers under the package without
  changing workspace layout.
- Add concrete model providers by subclassing `ModelProvider`.
- Add concrete agent runners by subclassing `AgentBackend`.
- Add workspace-local skills as `skills/<category>/<skill-name>.yaml` plus an
  optional Markdown prompt template.
- Add venue templates under `templates/venues/<venue>/`.
- Add richer result/claim/paper services while preserving the project-local
  registry layout.
