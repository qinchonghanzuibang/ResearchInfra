# ResearchInfra v1 Loop Demo

This example is a file-first walkthrough of the v1 loop:

source -> extract -> read -> paper card -> idea card -> project -> experiment
plan -> run metric -> table -> draft outline -> claim check -> paper check ->
agent task.

The recorded run contains a smoke-check metric only. It is included to show how
ResearchInfra links a user-provided run record into tables, claims, and paper
checks. It is not a scientific result, benchmark, or model claim.

Dry-run command path:

```bash
researchinfra model list --workspace examples/v1-loop
researchinfra result summarize --project project-evidence-loop --workspace examples/v1-loop
researchinfra table create --project project-evidence-loop --workspace examples/v1-loop --from-runs
researchinfra claim check --project project-evidence-loop --workspace examples/v1-loop --dry-run
researchinfra paper check --project project-evidence-loop --workspace examples/v1-loop --venue arxiv
researchinfra agent run task-writing-0001 --project project-evidence-loop --workspace examples/v1-loop --backend manual --dry-run
```

