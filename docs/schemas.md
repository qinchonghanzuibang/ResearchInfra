# Schemas

The core schemas live in `researchinfra.schemas` and use Pydantic v2.

## Core Objects

- `WorkspaceConfig`
- `Paper`
- `Claim`
- `Idea`
- `Project`
- `Experiment`
- `Run`
- `Draft`
- `Review`
- `AgentTask`
- `ModelProviderConfig`
- `AgentBackendConfig`

## Evidence Links

`EvidenceLink` is used by claims and drafts to connect text to papers,
experiments, runs, figures, tables, drafts, claims, or projects. This keeps
ResearchInfra oriented around inspectable support rather than generated prose.

## Compatibility

The initial schema version is `0.1`. Future versions should include migrations
when object formats change in incompatible ways.

