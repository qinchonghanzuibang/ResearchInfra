# Architecture

ResearchInfra is organized around durable local files and small Python
interfaces. The project intentionally avoids web UI concerns, cloud accounts,
authentication, and provider-specific assumptions in the v1 foundation.

## Layers

1. **Workspace files** hold the canonical state. Markdown, YAML, JSON, LaTeX,
   and BibTeX are preferred because humans and agents can inspect them directly.
2. **Schemas** define the typed contract for research objects. Pydantic models
   validate object shape before data is written to disk or passed to adapters.
3. **Workspace services** create and inspect local directory layouts.
4. **Agent backends** route tasks to manual workflows, local tools, API-backed
   agents, or future integrations such as Codex, Claude Code, OpenHands, and
   OpenClaw.
5. **Model providers** route inference to provider adapters such as
   OpenAI-compatible APIs, LiteLLM, Ollama, Anthropic, OpenRouter, and vLLM.

## Design Boundaries

ResearchInfra tracks research state. It does not claim scientific conclusions,
invent missing results, or run provider-specific automation without an adapter.
Claims should be tied to evidence links, and agent tasks should keep human
approval explicit.

## Extension Points

- Add schema-specific file readers and writers under the package without
  changing workspace layout.
- Add concrete model providers by subclassing `ModelProvider`.
- Add concrete agent runners by subclassing `AgentBackend`.
- Add workspace-local skills by creating directories under `skills/`.
- Add venue templates under `templates/venues/<venue>/`.

