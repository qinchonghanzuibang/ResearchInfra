# ResearchInfra

ResearchInfra is an alpha-stage, AI-native research operating system for
managing the full lifecycle of AI research in a local, file-first workspace.

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
- Source registry commands for adding, listing, and inspecting local files and URLs.
- Feed and inbox commands for discovering sources before promotion.
- Document extraction commands for reading local PDFs, Markdown/text files, and
  lightweight HTML sources into file-first document records.
- Skill commands for listing, inspecting, creating, and dry-running reusable
  research workflows.
- Paper reading modes for skim, deep, idea, reviewer, reproduce, and
  related-work passes, with notes saved under `memory/readings/`.
- Project creation from ideas, Paper Cards, readings, or manual names, with
  project-local context, experiment, draft, agent, and review directories.
- Experiment planning registries, draft outline/section scaffolds, and agent
  task specs that preserve evidence and human approval gates.
- Model provider registry commands for listing providers, setting task-specific
  defaults, and checking readiness without printing secrets.
- Result, table, figure, and claim registries that trace values back to run IDs
  and warn when evidence is missing.
- Paper initialization, checks, LaTeX build hooks, and local submission
  packaging for ACL, NeurIPS, ICLR, ICML, and arXiv placeholders.
- Manual and shell-safe agent execution bridges that write task result records.
- Optional OpenAI-compatible model calls through environment variables.
- Paper Card and Idea Card generation as Markdown plus YAML metadata.
- Pydantic schemas for core research objects:
  `WorkspaceConfig`, `Paper`, `Claim`, `Idea`, `Project`, `Experiment`, `Run`,
  `Draft`, `Review`, `AgentTask`, `ModelProviderConfig`, and
  `AgentBackendConfig`.
- A file-first workspace layout for sources, memory, projects, experiments,
  runs, figures, tables, drafts, submissions, skills, agents, templates, and
  docs.
- Agent backend interfaces with placeholder adapters for manual, API, Codex,
  Claude Code, OpenHands, and OpenClaw workflows.
- Model provider interfaces with placeholder adapters for OpenAI-compatible
  APIs, LiteLLM, Ollama, Anthropic, OpenRouter, and vLLM.
- Skill directory conventions for reading, ideation, experiment planning,
  writing, reviewing, LaTeX, and submission support.
- Venue template placeholders for ACL, NeurIPS, ICLR, ICML, and arXiv.
- Example workspaces for data-centric MLLM research, VLA/world-model research,
  and the complete v1 loop.

## Quickstart

ResearchInfra requires Python 3.10 or newer; Python 3.12 is recommended.
Choose one of the following environment setup options for each checkout.

### uv (recommended)

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if it is
not already available. On macOS or Linux, its official installer is:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Open a new shell if `uv` is not immediately found, then create the environment
and install the development dependencies:

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Conda

Install [Miniforge](https://conda-forge.org/download/) (or another Conda
distribution) if `conda` is not available. Then create the included Conda
environment, which installs ResearchInfra and its development dependencies:

```bash
conda env create -f environment.yml
conda activate researchinfra
```

`mamba env create -f environment.yml` is a compatible, faster alternative when
mamba is installed.

### pip and venv

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

After activating one of the environments above, initialize a workspace and run
the CLI:

```bash
researchinfra --help
python -m researchinfra --help
researchinfra init my-research
researchinfra project create \
  --workspace my-research \
  --name "Grounded Evaluation Study"

researchinfra experiment plan \
  --project project-grounded-evaluation-study \
  --workspace my-research
researchinfra experiment add-run \
  --project project-grounded-evaluation-study \
  --workspace my-research \
  --experiment experiment-grounded-evaluation-study-001 \
  --metric smoke_check=passed

researchinfra result summarize \
  --project project-grounded-evaluation-study \
  --workspace my-research
researchinfra table create \
  --project project-grounded-evaluation-study \
  --workspace my-research \
  --from-runs
researchinfra claim check \
  --project project-grounded-evaluation-study \
  --workspace my-research \
  --dry-run
researchinfra paper init \
  --project project-grounded-evaluation-study \
  --workspace my-research \
  --venue arxiv
researchinfra paper check \
  --project project-grounded-evaluation-study \
  --workspace my-research \
  --venue arxiv
```

Project state lives under `projects/<project-slug>/`. Experiment files are
written under `experiments/`, results under `results/`, tables under `tables/`,
figures under `figures/`, claim reports under `claims/`, paper files under
`paper/`, submissions under `submissions/`, and agent records under `agents/`.
Metrics enter the workspace only through explicit run records such as
`researchinfra experiment add-run --metric name=value`; the `smoke_check`
example above is a workflow check, not a scientific result.

ResearchInfra does not require a specific LLM provider. The default workspace
contains disabled provider placeholders and a manual backend. Inspect them with:

```bash
researchinfra model list --workspace my-research
researchinfra model set-default \
  --workspace my-research \
  --task reading \
  --provider openai-compatible \
  --model gpt-4o-mini
researchinfra model test --workspace my-research --task reading
```

Provider checks never print API keys.

Model defaults are used by model-invoking commands such as `researchinfra skill
run`, `paper read`, Paper Card creation, and Idea Card generation. In this alpha,
the executable runtime adapter is `openai-compatible`; LiteLLM, Ollama,
Anthropic, OpenRouter, and vLLM are visible configuration extension points and
report `can_execute: false` until concrete adapters are added. File-first
planning, claim, result, and submission commands remain provider-free.

Every workspace command validates `.researchinfra/workspace.yaml` before it
reads or writes research state. Run `researchinfra init <workspace>` first; a
typoed workspace path will fail rather than create a partial workspace.

## Architecture

ResearchInfra separates durable research state from execution.

- **Schemas** define stable, typed objects that can be serialized into
  human-readable files.
- **Workspace initialization** creates a predictable local directory structure
  with starter documentation and placeholders.
- **Registries** preserve papers, readings, projects, runs, metrics, tables,
  figures, claims, drafts, paper checks, submissions, and agent results as local
  files.
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
- [examples/v1-loop](examples/v1-loop) shows the complete dry-run v1 loop from
  source notes through claim checks, paper checks, and an agent task result.

Both examples are intentionally evidence-light. They show structure, not fake
scientific results.

## Development

See [docs/development.md](docs/development.md) for complete setup instructions
for `pip`/`venv`, `uv`, and `conda`.

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format .
```

Common commands are also available through `make`:

```bash
make install-dev
make test
make lint
make format
```

The package keeps dependencies small:

- `pydantic` for typed schemas and validation.
- `pypdf` for lightweight local PDF text extraction.
- `PyYAML` for human-readable workspace configuration.
- `pytest` and `ruff` as optional development dependencies.

## Roadmap

- Import pipelines for BibTeX, PDFs, arXiv metadata, and paper notes.
- Richer experiment and run record helpers with immutable audit trails.
- Stronger claim extraction and evidence classification for real drafts.
- Agent task queues and configured external backend command runners.
- Real provider adapters and local command backends.
- Official venue template importers and stricter submission packaging.
- Reproducibility checks across papers, claims, experiments, and drafts.

ResearchInfra should grow as a dependable research substrate, not as a monolith.
The v1 goal is a clear foundation that can support future ingestion, writing,
experiment tracking, and agent execution.
