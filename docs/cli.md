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

