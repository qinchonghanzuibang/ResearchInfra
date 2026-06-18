# Schemas

The core schemas live in `researchinfra.schemas` and use Pydantic v2.

## Core Objects

- `WorkspaceConfig`
- `Feed`
- `InboxItem`
- `Source`
- `Document`
- `DocumentChunk`
- `DocumentSection`
- `EvidenceSpan`
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

Sources can also store lightweight enrichment metadata such as title, authors,
abstract, published date, external id, PDF URL, BibTeX, tags, and raw metadata.

## Feeds And Inbox

`Feed` records describe configured discovery sources such as arXiv queries,
RSS feeds, Atom feeds, or web links. They are stored in
`.researchinfra/feeds.yaml`.

`InboxItem` records describe discovered items that have not yet been promoted
into the source registry. Inbox items include title, URL, abstract, authors,
published date, external id, tags, status, and raw metadata. They are stored in
`.researchinfra/inbox.yaml`.

## Documents And Evidence

`Document` records describe extracted source content stored under
`memory/documents/<document-id>/`. Each document points to `text.md` and
`metadata.yaml`, records extraction status and warnings, and stores sections and
chunks.

`EvidenceSpan` records identify a document, source, section, chunk id, quote or
short excerpt, and optional character offsets. Paper Card prompts can use these
spans to ask models to cite explicit evidence.

## Skills

`Skill` records describe reusable prompt workflows with metadata, expected
inputs and outputs, a recommended model tier, and a prompt template.

## Compatibility

The initial schema version is `0.1`. Future versions should include migrations
when object formats change in incompatible ways.
