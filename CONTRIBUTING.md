# Contributing

Thank you for helping build ResearchInfra.

## Development Setup

```bash
pip install -e ".[dev]"
pytest
```

## Contribution Guidelines

- Keep the system file-first and provider-agnostic.
- Do not add cloud account requirements, SaaS assumptions, or hard-coded model
  providers.
- Do not add fake paper ingestion, fake experiments, fake metrics, or fabricated
  scientific claims.
- Prefer typed Python, small interfaces, tests, and readable docs.
- Use Conventional Commits, such as `feat(schema): add claim evidence links`.

## Pull Requests

Pull requests should explain the research workflow being improved, list tests
run, and call out schema or workspace-layout compatibility changes.

