# CLI

The CLI entry point is `researchinfra`.

## Help

```bash
researchinfra --help
```

## Initialize Workspace

```bash
researchinfra init my-research
```

Options:

- `--name <name>` sets the workspace display name.
- `--force` adds missing starter files even if the directory already contains
  files.

The command writes `.researchinfra/workspace.yaml`, starter directory guides,
skill placeholders, venue template placeholders, and agent backend placeholders.

## Sources

Add a URL or local file:

```bash
researchinfra source add https://arxiv.org/abs/1234.5678 \
  --workspace /tmp/ri-demo \
  --type paper \
  --title "Demo Paper" \
  --tags demo,arxiv
```

List and inspect sources:

```bash
researchinfra source list --workspace /tmp/ri-demo
researchinfra source show src-... --workspace /tmp/ri-demo
```

Source records are stored in `.researchinfra/sources.yaml`.

Enrich a source with lightweight metadata when a local enricher is available:

```bash
researchinfra source enrich src-... --workspace /tmp/ri-demo
```

For arXiv URLs, enrichment can add an arXiv external id and PDF URL without
downloading the PDF. If the arXiv API is reachable, it may also add title,
authors, abstract, and published date.

Extract source content into a local document record:

```bash
researchinfra source extract src-... --workspace /tmp/ri-demo
researchinfra source extract src-... --workspace /tmp/ri-demo --force
```

Extraction stores text and YAML metadata under `memory/documents/`.

## Documents

List extracted documents:

```bash
researchinfra document list --workspace /tmp/ri-demo
```

Show document text or a specific section:

```bash
researchinfra document show doc-... --workspace /tmp/ri-demo
researchinfra document show doc-... --workspace /tmp/ri-demo --section page-1
```

Inspect chunks:

```bash
researchinfra document chunks doc-... --workspace /tmp/ri-demo --limit 5
```

## Feeds

Add an arXiv feed:

```bash
researchinfra feed add \
  --workspace /tmp/ri-demo \
  --type arxiv \
  --name "MLLM papers" \
  --query 'cat:cs.CV AND "multimodal"'
```

Add an RSS feed:

```bash
researchinfra feed add \
  --workspace /tmp/ri-demo \
  --type rss \
  --name "Lab blog" \
  --url https://example.com/feed.xml
```

List and sync feeds:

```bash
researchinfra feed list --workspace /tmp/ri-demo
researchinfra feed sync --workspace /tmp/ri-demo --limit 5
researchinfra feed sync --workspace /tmp/ri-demo --feed feed-... --limit 5
```

Feed records are stored in `.researchinfra/feeds.yaml`.

## Inbox

Review discovered items before promoting them into the main source registry:

```bash
researchinfra inbox list --workspace /tmp/ri-demo
researchinfra inbox list --workspace /tmp/ri-demo --status new
researchinfra inbox show inbox-... --workspace /tmp/ri-demo
researchinfra inbox promote inbox-... --workspace /tmp/ri-demo
researchinfra inbox skip inbox-... --workspace /tmp/ri-demo
```

Inbox records are stored in `.researchinfra/inbox.yaml`. Promotion creates a
normal Source record; skipping keeps the item in the inbox with status
`skipped`.

## Skills

List reusable skills:

```bash
researchinfra skill list --workspace /tmp/ri-demo
researchinfra skill list --workspace /tmp/ri-demo --category reading
researchinfra skill show paper_card --workspace /tmp/ri-demo
researchinfra skill create my_reader --workspace /tmp/ri-demo --category reading
```

Dry-run a skill to inspect the prompt without calling a model:

```bash
researchinfra skill run paper_card \
  --workspace /tmp/ri-demo \
  --input src-... \
  --dry-run
```

Running without `--dry-run` uses the workspace default selected for the skill's
task tier. In this alpha, only `openai-compatible` has an executable runtime
adapter; set its default and configure `OPENAI_API_KEY` before running a skill.
Other provider kinds are recorded as extension points and fail with setup
guidance rather than silently falling back to a different provider.

## Reading

Render or save reading notes for a paper source:

```bash
researchinfra paper read src-... --workspace /tmp/ri-demo --mode skim --dry-run
researchinfra paper read src-... --workspace /tmp/ri-demo --mode deep
```

Available modes are `skim`, `deep`, `idea`, `reviewer`, `reproduce`, and
`related_work`. Saved notes live under `memory/readings/<reading-id>/notes.md`
with sibling `metadata.yaml`. If no provider is configured, ResearchInfra saves
an explicit prompt-only artifact rather than inventing a reading.

## Models

List workspace providers and set task-specific defaults:

```bash
researchinfra model list --workspace /tmp/ri-demo
researchinfra model set-default \
  --workspace /tmp/ri-demo \
  --task reading \
  --provider openai-compatible \
  --model gpt-4o-mini
researchinfra model test --workspace /tmp/ri-demo --task reading
researchinfra model check --workspace /tmp/ri-demo
```

`model test` performs a local readiness check and prints setup instructions when
a provider is missing, uninstalled, or unconfigured. It never prints API key
values. Supported provider kinds are `openai-compatible`, `litellm`, `ollama`,
`anthropic`, `openrouter`, and `vllm`.

Model defaults are used by `skill run`, `paper read`, Paper Card creation, and
Idea Card generation. `can_execute: true` currently means an OpenAI-compatible
runtime is configured; the remaining provider kinds are non-executable
placeholders until concrete adapters are installed.

OpenAI-compatible runtime calls use:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL` optional
- `OPENAI_MODEL` optional

## Cards

Create a Paper Card:

```bash
researchinfra paper create-card src-... --workspace /tmp/ri-demo
researchinfra paper create-card src-... --workspace /tmp/ri-demo --use-content --dry-run
```

Generate an Idea Card from a Paper Card:

```bash
researchinfra idea generate --workspace /tmp/ri-demo --from-paper paper-...
```

Cards are Markdown files with YAML front matter plus sibling YAML metadata
files. Paper Cards live under `memory/papers/`; Idea Cards live under
`memory/ideas/`.

## Projects

Create a project from existing artifacts or a manual name:

```bash
researchinfra project create \
  --workspace /tmp/ri-demo \
  --name "Grounded Evaluation Study" \
  --from-idea idea-... \
  --from-paper paper-... \
  --from-reading reading-...
```

Inspect and link project context:

```bash
researchinfra project list --workspace /tmp/ri-demo
researchinfra project show project-grounded-evaluation-study --workspace /tmp/ri-demo
researchinfra project status project-grounded-evaluation-study --workspace /tmp/ri-demo
researchinfra project add-paper project-grounded-evaluation-study paper-... --workspace /tmp/ri-demo
researchinfra project add-reading project-grounded-evaluation-study reading-... --workspace /tmp/ri-demo
```

Projects live under `projects/<project-slug>/` with `project.yaml`, `README.md`,
`context/`, `experiments/`, `results/`, `tables/`, `figures/`, `claims/`,
`draft/`, `paper/`, `submissions/`, `agents/`, and `reviews/`.

## Experiments

Dry-run the skill-driven experiment prompt or write local planning artifacts:

```bash
researchinfra experiment plan \
  --project project-grounded-evaluation-study \
  --workspace /tmp/ri-demo \
  --dry-run
researchinfra experiment plan \
  --project project-grounded-evaluation-study \
  --workspace /tmp/ri-demo
researchinfra experiment list \
  --project project-grounded-evaluation-study \
  --workspace /tmp/ri-demo
```

Planning writes `experiment_plan.md`, `baseline_registry.yaml`,
`ablation_matrix.yaml`, `run_registry.yaml`, and `claim_evidence.yaml` under the
project's `experiments/` directory. Add explicit, user-provided run metrics:

```bash
researchinfra experiment add-run \
  --project project-grounded-evaluation-study \
  --workspace /tmp/ri-demo \
  --experiment experiment-grounded-evaluation-study-001 \
  --metric accuracy=0.5
```

ResearchInfra does not invent baselines, datasets, metrics, or results.

## Results, Tables, And Figures

Refresh and summarize run-grounded result registries:

```bash
researchinfra result list \
  --project project-grounded-evaluation-study \
  --workspace /tmp/ri-demo
researchinfra result summarize \
  --project project-grounded-evaluation-study \
  --workspace /tmp/ri-demo
```

Create a Markdown/YAML table from recorded runs:

```bash
researchinfra table create \
  --project project-grounded-evaluation-study \
  --workspace /tmp/ri-demo \
  --from-runs
```

Create a figure registry placeholder linked to available run IDs:

```bash
researchinfra figure create \
  --project project-grounded-evaluation-study \
  --workspace /tmp/ri-demo \
  --title "Evidence Flow"
```

These commands write under `projects/<project-slug>/results/`, `tables/`, and
`figures/`. Tables only use values already present in run records; figure
records do not generate plots or visual claims.

## Claims

List and check project claims:

```bash
researchinfra claim list \
  --project project-grounded-evaluation-study \
  --workspace /tmp/ri-demo
researchinfra claim check \
  --project project-grounded-evaluation-study \
  --workspace /tmp/ri-demo \
  --draft projects/grounded-evaluation-study/draft/outline.md \
  --dry-run
```

Without `--dry-run`, claim checks write `claims/claim_report.md` and
`claims/claim_evidence.yaml`, plus a project experiment evidence map. The check
warns about unsupported claims, comparison overclaims, missing baselines,
missing OOD/ablation evidence, and result claims without run IDs.

## Drafts

Render or write evidence-gated draft scaffolds:

```bash
researchinfra draft outline \
  --project project-grounded-evaluation-study \
  --workspace /tmp/ri-demo \
  --venue acl \
  --dry-run
researchinfra draft section \
  --project project-grounded-evaluation-study \
  --workspace /tmp/ri-demo \
  --section limitations
```

Draft outputs live under `projects/<project-slug>/draft/` and include warnings
for missing evidence and missing experiments.

## Paper And Submission

Initialize, check, build, and package project-local paper files:

```bash
researchinfra paper init \
  --project project-grounded-evaluation-study \
  --workspace /tmp/ri-demo \
  --venue arxiv
researchinfra paper check \
  --project project-grounded-evaluation-study \
  --workspace /tmp/ri-demo \
  --venue arxiv
researchinfra paper build \
  --project project-grounded-evaluation-study \
  --workspace /tmp/ri-demo \
  --venue arxiv
researchinfra paper package \
  --project project-grounded-evaluation-study \
  --workspace /tmp/ri-demo \
  --venue arxiv \
  --arxiv
```

Supported placeholders are `acl`, `iclr`, `neurips`, `icml`, and `arxiv`.
Checks look for missing sections, missing citations, broken references, missing
results, unsupported claims, anonymous/camera-ready metadata issues, and local
LaTeX tools. Build fails gracefully with setup instructions if `latexmk` or
`pdflatex` is unavailable.

## Agent Tasks

Create task specs for future human-approved backend execution:

```bash
researchinfra agent task create \
  --project project-grounded-evaluation-study \
  --workspace /tmp/ri-demo \
  --type writing \
  --title "Draft limitations section"
researchinfra agent task list \
  --project project-grounded-evaluation-study \
  --workspace /tmp/ri-demo
researchinfra agent task show task-writing-0001 \
  --project project-grounded-evaluation-study \
  --workspace /tmp/ri-demo
researchinfra agent run task-writing-0001 \
  --project project-grounded-evaluation-study \
  --workspace /tmp/ri-demo \
  --backend manual \
  --dry-run
```

Task specs live under `projects/<project-slug>/agents/tasks/` and record context
files, expected outputs, constraints, verification commands, and suggested
backend. Manual runs print instructions and non-dry runs write
`agents/results/<task-id>-manual.yaml`. The shell backend can run only
`safe_commands` already present in the task spec, and only with `--yes`.
Codex, Claude Code, and OpenHands wrappers report setup/configuration guidance
unless an explicit local command bridge is configured.
