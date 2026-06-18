# Workspace

`researchinfra init <workspace>` creates a local directory with predictable
places for research state:

```text
.researchinfra/        Workspace configuration
.researchinfra/feeds.yaml
.researchinfra/inbox.yaml
.researchinfra/sources.yaml
sources/               Papers, BibTeX, PDFs, and external references
memory/                Claims, ideas, reviews, and durable notes
memory/documents/      Extracted document text and metadata
memory/papers/         Generated Paper Cards and metadata
memory/readings/       Saved paper reading notes and prompt-only artifacts
projects/              Scoped research efforts
experiments/           Experiment plans and baseline definitions
runs/                  Concrete execution records
figures/               Figures and visual artifacts
tables/                Table registries linked to runs
drafts/                Markdown and LaTeX drafts
submissions/           Venue packaging and checklists
skills/                Workspace-local research workflows
agents/                Agent backend configs and task records
templates/             Reusable project, experiment, draft, and venue templates
docs/                  Workspace-local documentation
```

The hidden `.researchinfra/workspace.yaml` file stores the workspace config.
It includes directory mappings plus disabled placeholder provider and backend
configuration. Credentials should not be stored in workspace files.

Feed registry records are stored in `.researchinfra/feeds.yaml`; discovered
inbox items are stored in `.researchinfra/inbox.yaml`; promoted source records
are stored in `.researchinfra/sources.yaml`. Generated Paper Cards live under
`memory/papers/`; generated Idea Cards live under `memory/ideas/`; paper
reading notes live under `memory/readings/<reading-id>/`. Extracted document
text and metadata live under `memory/documents/<document-id>/`.

Project directories are self-contained:

```text
projects/<project-slug>/
  project.yaml
  README.md
  context/
  experiments/
  results/
  tables/
  figures/
  claims/
  draft/
  paper/
  submissions/
  agents/tasks/
  agents/results/
  reviews/
```

Experiment planning writes `experiment_plan.md`, `baseline_registry.yaml`,
`ablation_matrix.yaml`, `run_registry.yaml`, and `claim_evidence.yaml` under the
project. Draft scaffolds live under `draft/`, and agent task specs live under
`agents/tasks/`.

Result commands refresh `results/metrics.yaml`,
`results/result_bundle.yaml`, and `results/summary.md` from run records.
Tables live under `tables/`; figure registry placeholders live under
`figures/`; claim checks write `claims/claim_report.md` and
`claims/claim_evidence.yaml`. Paper commands write venue-local LaTeX files under
`paper/<venue>/` and package outputs under `submissions/<venue>/<phase>/`.
Agent executions write status records under `agents/results/`.
