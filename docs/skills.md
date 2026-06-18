# Skills

Workspace skills live under `skills/`. They are workflow descriptions and
prompt templates that humans and agents can read, override, and run locally.

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
- `read_skim`
- `read_deep`
- `read_idea`
- `read_reviewer`
- `read_reproduce`
- `read_related_work`

Each runnable skill has metadata: name, category, description, input type,
output type, required context, recommended model, version, author, tags, and
prompt template. Fresh workspaces include visible files such as
`skills/reading/read_deep.yaml` and `skills/reading/read_deep.md` so users can
inspect or adapt prompts locally.

The preferred custom skill layout is:

```text
skills/
  reading/
    my_lab_reader.yaml
    my_lab_reader.md
```

A skill YAML file can reference its Markdown prompt:

```yaml
name: my_lab_reader
category: reading
description: Read papers with local lab conventions.
input_type: source_or_document
output_type: markdown
required_context:
  - source
  - document
  - chunks
  - warnings
prompt_template: my_lab_reader.md
recommended_model: optional
version: "0.1"
tags:
  - local
```

Prompt templates may use these variables: `$profile`, `$source`, `$document`,
`$metadata`, `$chunks`, `$evidence_instructions`, `$output_schema`,
`$warnings`, `$input_text`, `$source_id`, `$title`, `$target`, `$tags`, and
`$domain`.

Workspace skills override built-ins when they use the same `name`. Older
`skills/<name>/skill.yaml` plus `prompt.md` directories are still readable for
compatibility.

Skills should describe scope, required inputs, expected outputs, and human
approval points. They should not be loose prompt dumps. Good skills preserve
uncertainty, cite evidence, and avoid fabricating papers, experiments, metrics,
or conclusions.

Useful commands:

```bash
researchinfra skill list --workspace /tmp/ri-demo --category reading
researchinfra skill show read_deep --workspace /tmp/ri-demo
researchinfra skill create my_lab_reader --workspace /tmp/ri-demo --category reading
researchinfra skill run read_deep --workspace /tmp/ri-demo --input src-... --dry-run
```

Use `--dry-run` to inspect a rendered prompt before any model call.
