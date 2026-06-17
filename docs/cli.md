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

## Skills

List reusable skills:

```bash
researchinfra skill list --workspace /tmp/ri-demo
```

Dry-run a skill to inspect the prompt without calling a model:

```bash
researchinfra skill run paper_card \
  --workspace /tmp/ri-demo \
  --input src-... \
  --dry-run
```

Running without `--dry-run` uses the OpenAI-compatible provider when
`OPENAI_API_KEY` is configured.

## Models

Check provider configuration without exposing secrets:

```bash
researchinfra model check
```

Supported environment variables:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL` optional
- `OPENAI_MODEL` optional

## Cards

Create a Paper Card:

```bash
researchinfra paper create-card src-... --workspace /tmp/ri-demo
```

Generate an Idea Card from a Paper Card:

```bash
researchinfra idea generate --workspace /tmp/ri-demo --from-paper paper-...
```

Cards are Markdown files with YAML front matter plus sibling YAML metadata
files. Paper Cards live under `memory/papers/`; Idea Cards live under
`memory/ideas/`.
