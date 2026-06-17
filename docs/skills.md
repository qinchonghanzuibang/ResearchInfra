# Skills

Workspace skills are local directories under `skills/`. They are workflow
descriptions that humans and agents can read.

The default workspace includes general workflow skill directories:

- `reading`
- `ideation`
- `experiment-planning`
- `writing`
- `reviewing`
- `latex`
- `submission`

ResearchInfra also ships built-in runnable skills:

- `paper_card`
- `idea_card`
- `claim_check`
- `experiment_plan`

Each runnable skill has metadata: name, description, inputs, outputs,
recommended model tier, and prompt template. Fresh workspaces include visible
`skill.yaml` and `prompt.md` files for these built-ins so users can inspect or
adapt the prompts locally.

Skills should describe scope, required inputs, expected outputs, and human
approval points. They should not be loose prompt dumps. Good skills preserve
uncertainty, cite evidence, and avoid fabricating papers, experiments, metrics,
or conclusions.

Use `researchinfra skill run <name> --dry-run` to inspect a rendered prompt
before any model call.
