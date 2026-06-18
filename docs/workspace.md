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
projects/              Scoped research efforts
experiments/           Experiment plans and baseline definitions
runs/                  Concrete execution records
figures/               Figures and tables
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
`memory/papers/`; generated Idea Cards live under `memory/ideas/`. Extracted
document text and metadata live under `memory/documents/<document-id>/`.
