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
experiments, and artifacts.

## Experiment

An experiment is a plan. It records a question, method, baselines, datasets,
metrics, and expected artifacts.

## Run

A run is an execution record for an experiment. Runs store commands, status,
seeds, metrics, artifacts, notes, and timestamps.

## Draft

A draft is a paper, report, or submission artifact. Drafts should link claims to
explicit evidence.

## Agent Task

An agent task is a human-approved work item for a manual or automated backend.
