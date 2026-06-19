# ResearchInfra v1 Loop Demo

This example is a file-first walkthrough of the v1 loop:

source -> extract -> read -> paper card -> idea card -> project -> experiment
plan -> run metric -> table -> draft outline -> claim check -> paper check ->
agent task.

The recorded run contains a smoke-check metric only. It is included to show how
ResearchInfra links a user-provided run record into tables, claims, and paper
checks. It is not a scientific result, benchmark, or model claim.

## No-API-Key Local Walkthrough

The commands below require no API key. `result summarize`, `table create`, and
`paper check` refresh local registry or report files, so run the walkthrough in
a copy to keep the repository checkout unchanged:

```bash
WORKSPACE="$(mktemp -d)/researchinfra-v1-loop"
cp -R examples/v1-loop "$WORKSPACE"

researchinfra model list --workspace "$WORKSPACE"
researchinfra result summarize --project project-evidence-loop --workspace "$WORKSPACE"
researchinfra table create --project project-evidence-loop --workspace "$WORKSPACE" --from-runs
researchinfra claim check --project project-evidence-loop --workspace "$WORKSPACE" --dry-run
researchinfra paper check --project project-evidence-loop --workspace "$WORKSPACE" --venue arxiv
researchinfra agent run task-writing-0001 --project project-evidence-loop --workspace "$WORKSPACE" --backend manual --dry-run
```

`model list`, `claim check --dry-run`, and `agent run --dry-run` are read-only.
The other commands above intentionally write their refreshed local artifacts to
the copied workspace.
