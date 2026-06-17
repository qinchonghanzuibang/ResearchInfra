# ResearchInfra

ResearchInfra is an AI-native research operating system for managing the full
lifecycle of AI research in a local, file-first workspace.

It is designed for researchers and AI agents to work over the same durable
project state: papers, ideas, projects, experiments, baselines, runs, claims,
drafts, submissions, skills, and agent tasks. The v1 foundation is deliberately
not a web UI, SaaS product, paper summarizer, prompt collection, or fake
experiment tracker. It is a clean substrate for serious research infrastructure.

## Principles

- **File-first:** store research state in Markdown, YAML, JSON, LaTeX, and
  BibTeX whenever possible.
- **Agent-agnostic:** keep Codex, Claude Code, OpenHands, OpenClaw, API models,
  and local models behind adapter interfaces.
- **Evidence-grounded:** link claims and drafts to papers, experiments,
  figures, tables, and run records.
- **Human-in-the-loop:** assist researchers while keeping review, approval, and
  accountability explicit.
- **Open-source quality:** prefer typed Python, tests, readable docs, lightweight
  dependencies, and stable extension points.

## What v1 Provides

- `researchinfra init <workspace>` to create a local workspace.
- Pydantic schemas for core research objects:
  `WorkspaceConfig`, `Paper`, `Claim`, `Idea`, `Project`, `Experiment`, `Run`,
  `Draft`, `Review`, `AgentTask`, `ModelProviderConfig`, and
  `AgentBackendConfig`.
- A file-first workspace layout for sources, memory, projects, experiments,
  runs, figures, drafts, submissions, skills, agents, templates, and docs.
- Agent backend interfaces with placeholder adapters for manual, API, Codex,
  Claude Code, OpenHands, and OpenClaw workflows.
- Model provider interfaces with placeholder adapters for OpenAI-compatible
  APIs, LiteLLM, Ollama, Anthropic, OpenRouter, and vLLM.
- Skill directory conventions for reading, ideation, experiment planning,
  writing, reviewing, LaTeX, and submission support.
- Venue template placeholders for ACL, NeurIPS, ICLR, ICML, and arXiv.
- Example workspaces for data-centric MLLM research and VLA/world-model
  research.

## Quickstart

```bash
pip install -e ".[dev]"
researchinfra --help
researchinfra init my-research
```

The generated workspace is a normal directory:

```text
my-research/
  .researchinfra/workspace.yaml
  sources/
  memory/
  projects/
  experiments/
  runs/
  figures/
  drafts/
  submissions/
  skills/
  agents/
  templates/
  docs/
```

ResearchInfra does not require a specific LLM provider. The default workspace
contains disabled provider placeholders and a manual backend. You can wire real
providers and agents later without changing the research object model.

## Architecture

ResearchInfra separates durable research state from execution.

- **Schemas** define stable, typed objects that can be serialized into
  human-readable files.
- **Workspace initialization** creates a predictable local directory structure
  with starter documentation and placeholders.
- **Agent backends** describe how tasks may be routed to a human, local command,
  API service, or agent tool.
- **Model providers** describe how model inference can be supplied by OpenAI
  compatible APIs, local runtimes, routers, or other providers.
- **Skills** describe repeatable research workflows that agents may use under
  human review.

See [docs/architecture.md](docs/architecture.md) for the longer design.

## Examples

- [examples/data-centric-mllm](examples/data-centric-mllm) shows a workspace for
  studying data quality, coverage, and evaluation design for multimodal LLMs.
- [examples/vla-world-model](examples/vla-world-model) shows a workspace for
  vision-language-action and world-model research planning.

Both examples are intentionally evidence-light. They show structure, not fake
scientific results.

## Development

```bash
pip install -e ".[dev]"
pytest
```

The package keeps dependencies small:

- `pydantic` for typed schemas and validation.
- `PyYAML` for human-readable workspace configuration.
- `pytest` as an optional development dependency.

## Roadmap

- Durable file readers and writers for every schema.
- Import pipelines for BibTeX, PDFs, arXiv metadata, and paper notes.
- Claim-to-evidence maps for drafts and figures.
- Experiment and run record helpers with immutable audit trails.
- Agent task queues with explicit human approval gates.
- Real provider adapters and local command backends.
- Venue-aware submission packaging.
- Reproducibility checks across papers, claims, experiments, and drafts.

ResearchInfra should grow as a dependable research substrate, not as a monolith.
The v1 goal is a clear foundation that can support future ingestion, writing,
experiment tracking, and agent execution.

