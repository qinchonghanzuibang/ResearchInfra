# Concepts

## Paper

A paper is a source object: title, authors, venue, identifiers, local paths,
BibTeX keys, tags, and notes.

## Feed

A feed is a configured discovery source, such as an arXiv query, RSS feed, Atom
feed, or manually tracked web source.

## Inbox Item

An inbox item is a discovered source candidate that has not yet been promoted
into the main source registry. Researchers can inspect, promote, or skip inbox
items.

## Document

A document is extracted source content stored in the workspace. Documents keep
plain text, metadata, sections, chunks, extraction status, and warnings.

## Evidence Span

An evidence span is a short excerpt tied to a document, source, section, and
chunk id. Generated cards should cite spans instead of making unsupported claims.

## Claim

A claim is a statement that should be linkable to evidence. Claims can begin as
hypotheses and later become supported, challenged, retracted, or unknown.

## Idea

An idea is a research possibility before it becomes a scoped project. Ideas may
link to papers and claims.

## Project

A project is a scoped research effort with owners, related ideas, claims,
experiments, and artifacts. In the workspace, projects also carry a thesis,
research question, motivation, linked papers/readings/ideas, open questions,
decisions, risks, next actions, target venue, and status.

## Experiment

An experiment is a plan. It records a question, method, baselines, datasets,
metrics, and expected artifacts.

## Baseline And Ablation

Baselines and ablations are planned comparison objects. They can be proposed
before implementation, but they are not evidence until linked to run records.

## Result Record

A result record stores user-provided run metrics and artifacts. ResearchInfra
does not generate fake results.

## Metric, Table, Figure, And Result Bundle

A metric record is a single value copied from a run record. A table record
stores rows and cell evidence linked to run IDs. A figure record stores inputs
and warnings for a visual artifact, but does not generate a plot. A result
bundle summarizes the project-local metrics, tables, figures, and warnings.

## Run

A run is an execution record for an experiment. Runs store commands, status,
seeds, metrics, artifacts, notes, and timestamps.

## Draft

A draft is a paper, report, or submission artifact. Drafts should link claims to
explicit evidence.

## Paper And Submission

Project-local paper files live under `paper/<venue>/`. Submission packages live
under `submissions/<venue>/<phase>/`. Checks look for missing sections,
citations, results, claim support, references, and venue metadata issues.

## Agent Task

An agent task is a human-approved work item for a manual or automated backend.
Task specs include context files, expected outputs, constraints, verification
commands, and a suggested backend. Creating a task does not execute the backend.
Manual or shell-safe execution writes a task result record so humans and agents
can audit what happened.
