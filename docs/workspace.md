# Workspace

`researchinfra init <workspace>` creates a local directory with predictable
places for research state:

```text
.researchinfra/        Workspace configuration
sources/               Papers, BibTeX, PDFs, and external references
memory/                Claims, ideas, reviews, and durable notes
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

