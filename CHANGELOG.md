# Changelog

All notable changes to ResearchInfra will be documented here.

The project follows Conventional Commits and aims to keep schema and workspace
layout changes explicit.

## 0.1.0 - 2026-06-19

- Redact provider failure details so upstream responses cannot echo credentials
  into CLI errors.
- Make `init --force` additive, preserve existing workspace configuration, and
  require `--reinitialize --yes` for explicit starter-file resets.
- Report malformed workspace YAML with file paths and repair guidance instead
  of Python tracebacks.
- Harden public-alpha release behavior: validate workspaces before command
  execution, reject empty/path-like CLI inputs, and render validation failures
  without tracebacks.
- Route model-invoking workflows through task defaults, and report placeholder
  providers as non-executable until concrete adapters exist.
- Add module execution support, package build verification, canonical project
  URLs, practical reporting guidance, and copy-safe demo walkthrough wording.
- Initialize the file-first ResearchInfra foundation.
- Add typed schemas for core research objects.
- Add CLI workspace initialization.
- Add placeholder agent backend and model provider interfaces.
- Add workspace-local skill metadata, overrides, and built-in paper reading modes.
- Add saved paper reading notes under `memory/readings/`.
- Add project, experiment, draft, and agent task workflow commands.
- Add model provider registry commands for task defaults and readiness checks.
- Add project-local result, metric, table, figure, and claim evidence registries.
- Add paper initialization, checks, LaTeX build hooks, and submission packaging.
- Add manual and shell-safe agent execution bridge with task result files.
- Add the `examples/v1-loop` dry-run demo workspace.
- Add docs, examples, tests, and open-source project metadata.
