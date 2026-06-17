# Schemas

The core schemas live in `researchinfra.schemas` and use Pydantic v2.

## Core Objects

- `WorkspaceConfig`
- `Source`
- `Paper`
- `Claim`
- `Idea`
- `Project`
- `Experiment`
- `Run`
- `Draft`
- `Review`
- `AgentTask`
- `Skill`
- `ModelProviderConfig`
- `AgentBackendConfig`

## Evidence Links

`EvidenceLink` is used by claims and drafts to connect text to papers,
experiments, runs, figures, tables, drafts, claims, or projects. This keeps
ResearchInfra oriented around inspectable support rather than generated prose.

## Sources

`Source` records track local files and URLs. Local file records can include
path, filename, extension, size, and created timestamp. URL records can include
the URL and domain. The source registry is stored in
`.researchinfra/sources.yaml`.

## Skills

`Skill` records describe reusable prompt workflows with metadata, expected
inputs and outputs, a recommended model tier, and a prompt template.

## Compatibility

The initial schema version is `0.1`. Future versions should include migrations
when object formats change in incompatible ways.
