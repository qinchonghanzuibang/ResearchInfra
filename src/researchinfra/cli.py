"""Command-line interface for ResearchInfra."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

import yaml

from researchinfra import __version__
from researchinfra.cards import CardError, IdeaCardService, PaperCardService
from researchinfra.discovery import (
    DiscoveryError,
    FeedNotFoundError,
    FeedRegistry,
    FeedSyncer,
    Inbox,
    InboxItemNotFoundError,
    SourceEnricher,
)
from researchinfra.documents import (
    DocumentError,
    DocumentExtractor,
    DocumentNotFoundError,
    DocumentStore,
)
from researchinfra.models.adapters import OpenAICompatibleProvider
from researchinfra.models.base import ModelProviderConfigurationError, ModelProviderRequestError
from researchinfra.readings import ReadingError, ReadingService
from researchinfra.schemas import ModelProviderConfig
from researchinfra.skills import READING_MODES, SkillError, SkillNotFoundError, SkillRunner
from researchinfra.sources import SourceNotFoundError, SourceRegistry
from researchinfra.workflows import (
    DRAFT_SECTIONS,
    TASK_TYPES,
    VENUES,
    AgentTaskService,
    DraftService,
    ExperimentService,
    ProjectNotFoundError,
    ProjectService,
    WorkflowError,
)
from researchinfra.workspace import WorkspaceExistsError, init_workspace


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""

    parser = argparse.ArgumentParser(
        prog="researchinfra",
        description="File-first research workspace tooling for humans and AI agents.",
    )
    parser.add_argument("--version", action="version", version=f"researchinfra {__version__}")

    subparsers = parser.add_subparsers(dest="command")
    init_parser = subparsers.add_parser(
        "init",
        help="Create a local ResearchInfra workspace.",
        description="Create a file-first ResearchInfra workspace.",
    )
    init_parser.add_argument("workspace", help="Directory to initialize.")
    init_parser.add_argument("--name", help="Workspace display name.")
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Add missing files even if the target directory already contains files.",
    )

    source_parser = subparsers.add_parser("source", help="Manage workspace research sources.")
    source_subparsers = source_parser.add_subparsers(dest="source_command")
    source_add = source_subparsers.add_parser("add", help="Add a local file or URL source.")
    source_add.add_argument("target", help="Local path or URL to register.")
    source_add.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")
    source_add.add_argument(
        "--type",
        choices=["paper", "blog", "repo", "note", "web", "unknown"],
        default="unknown",
        help="Source type.",
    )
    source_add.add_argument("--title", help="Optional source title.")
    source_add.add_argument(
        "--tags",
        default="",
        help="Comma-separated tags, for example `mllm,data,baseline`.",
    )

    source_list = source_subparsers.add_parser("list", help="List registered sources.")
    source_list.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")

    source_show = source_subparsers.add_parser("show", help="Show one registered source.")
    source_show.add_argument("source_id", help="Source id to inspect.")
    source_show.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")

    source_enrich = source_subparsers.add_parser("enrich", help="Enrich source metadata.")
    source_enrich.add_argument("source_id", help="Source id to enrich.")
    source_enrich.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")

    source_extract = source_subparsers.add_parser("extract", help="Extract source content.")
    source_extract.add_argument("source_id", help="Source id to extract.")
    source_extract.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")
    source_extract.add_argument(
        "--force",
        action="store_true",
        help="Re-extract even when a document already exists.",
    )

    document_parser = subparsers.add_parser("document", help="Inspect extracted documents.")
    document_subparsers = document_parser.add_subparsers(dest="document_command")
    document_list = document_subparsers.add_parser("list", help="List extracted documents.")
    document_list.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")

    document_show = document_subparsers.add_parser("show", help="Show extracted document text.")
    document_show.add_argument("document_id", help="Document id.")
    document_show.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")
    document_show.add_argument("--section", help="Optional section name, such as body or page-1.")

    document_chunks = document_subparsers.add_parser("chunks", help="Show document chunks.")
    document_chunks.add_argument("document_id", help="Document id.")
    document_chunks.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")
    document_chunks.add_argument("--limit", type=int, default=10, help="Maximum chunks to print.")

    feed_parser = subparsers.add_parser("feed", help="Manage discovery feeds.")
    feed_subparsers = feed_parser.add_subparsers(dest="feed_command")
    feed_add = feed_subparsers.add_parser("add", help="Add a discovery feed.")
    feed_add.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")
    feed_add.add_argument("--type", required=True, choices=["arxiv", "rss", "atom", "web"])
    feed_add.add_argument("--name", required=True, help="Feed name.")
    feed_add.add_argument("--query", help="arXiv query.")
    feed_add.add_argument("--url", help="RSS, Atom, or web URL.")
    feed_add.add_argument("--tags", default="", help="Comma-separated tags.")

    feed_list = feed_subparsers.add_parser("list", help="List discovery feeds.")
    feed_list.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")

    feed_sync = feed_subparsers.add_parser("sync", help="Sync feeds into the inbox.")
    feed_sync.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")
    feed_sync.add_argument("--feed", help="Optional feed id to sync.")
    feed_sync.add_argument("--limit", type=int, default=20, help="Maximum items per feed.")

    inbox_parser = subparsers.add_parser("inbox", help="Review discovered source candidates.")
    inbox_subparsers = inbox_parser.add_subparsers(dest="inbox_command")
    inbox_list = inbox_subparsers.add_parser("list", help="List inbox items.")
    inbox_list.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")
    inbox_list.add_argument("--status", choices=["new", "saved", "skipped"], help="Filter status.")

    inbox_show = inbox_subparsers.add_parser("show", help="Show one inbox item.")
    inbox_show.add_argument("item_id", help="Inbox item id.")
    inbox_show.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")

    inbox_promote = inbox_subparsers.add_parser("promote", help="Promote inbox item to source.")
    inbox_promote.add_argument("item_id", help="Inbox item id.")
    inbox_promote.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")

    inbox_skip = inbox_subparsers.add_parser("skip", help="Skip inbox item.")
    inbox_skip.add_argument("item_id", help="Inbox item id.")
    inbox_skip.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")

    skill_parser = subparsers.add_parser("skill", help="List and run reusable skills.")
    skill_subparsers = skill_parser.add_subparsers(dest="skill_command")
    skill_list = skill_subparsers.add_parser("list", help="List available skills.")
    skill_list.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")
    skill_list.add_argument("--category", help="Optional category filter, such as reading.")

    skill_show = skill_subparsers.add_parser("show", help="Show skill metadata and prompt.")
    skill_show.add_argument("skill_name", help="Skill name.")
    skill_show.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")

    skill_create = skill_subparsers.add_parser("create", help="Create a workspace skill.")
    skill_create.add_argument("skill_name", help="Skill name.")
    skill_create.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")
    skill_create.add_argument(
        "--category",
        default="general",
        help="Skill category directory, such as reading, writing, or reviewing.",
    )

    skill_run = skill_subparsers.add_parser("run", help="Run a skill against a file or source.")
    skill_run.add_argument("skill_name", help="Skill name.")
    skill_run.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")
    skill_run.add_argument("--input", required=True, help="Input file path or source id.")
    skill_run.add_argument("--output", help="Optional output file for model response.")
    skill_run.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the rendered prompt instead of calling a model provider.",
    )

    model_parser = subparsers.add_parser("model", help="Inspect model provider configuration.")
    model_subparsers = model_parser.add_subparsers(dest="model_command")
    model_subparsers.add_parser("check", help="Check OpenAI-compatible provider configuration.")

    paper_parser = subparsers.add_parser("paper", help="Create and inspect paper artifacts.")
    paper_subparsers = paper_parser.add_subparsers(dest="paper_command")
    paper_card = paper_subparsers.add_parser("create-card", help="Create a Paper Card.")
    paper_card.add_argument("source_id", help="Source id to use.")
    paper_card.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")
    paper_card.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the rendered paper-card prompt instead of writing a card.",
    )
    paper_card.add_argument(
        "--use-content",
        action="store_true",
        help="Include extracted document chunks and evidence instructions.",
    )
    paper_read = paper_subparsers.add_parser("read", help="Read a paper with a built-in mode.")
    paper_read.add_argument("source_id", help="Source id to read.")
    paper_read.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")
    paper_read.add_argument(
        "--mode",
        choices=READING_MODES,
        default="skim",
        help="Reading mode.",
    )
    paper_read.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the rendered reading prompt instead of writing reading notes.",
    )

    idea_parser = subparsers.add_parser("idea", help="Generate research idea artifacts.")
    idea_subparsers = idea_parser.add_subparsers(dest="idea_command")
    idea_generate = idea_subparsers.add_parser("generate", help="Generate an Idea Card.")
    idea_generate.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")
    idea_generate.add_argument("--from-paper", required=True, help="Paper Card id.")
    idea_generate.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the rendered idea-card prompt instead of writing a card.",
    )

    project_parser = subparsers.add_parser("project", help="Manage research projects.")
    project_subparsers = project_parser.add_subparsers(dest="project_command")
    project_create = project_subparsers.add_parser("create", help="Create a project.")
    project_create.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")
    project_create.add_argument("--name", required=True, help="Project name.")
    project_create.add_argument("--from-idea", help="Idea Card id.")
    project_create.add_argument("--from-paper", help="Paper Card id.")
    project_create.add_argument("--from-reading", help="Reading artifact id.")

    project_list = project_subparsers.add_parser("list", help="List projects.")
    project_list.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")

    project_show = project_subparsers.add_parser("show", help="Show project YAML.")
    project_show.add_argument("project_id", help="Project id or slug.")
    project_show.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")

    project_status = project_subparsers.add_parser("status", help="Show project status.")
    project_status.add_argument("project_id", help="Project id or slug.")
    project_status.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")

    project_add_paper = project_subparsers.add_parser("add-paper", help="Link a Paper Card.")
    project_add_paper.add_argument("project_id", help="Project id or slug.")
    project_add_paper.add_argument("paper_id", help="Paper Card id.")
    project_add_paper.add_argument(
        "--workspace", required=True, help="ResearchInfra workspace path."
    )

    project_add_reading = project_subparsers.add_parser(
        "add-reading", help="Link a reading artifact."
    )
    project_add_reading.add_argument("project_id", help="Project id or slug.")
    project_add_reading.add_argument("reading_id", help="Reading artifact id.")
    project_add_reading.add_argument(
        "--workspace", required=True, help="ResearchInfra workspace path."
    )

    experiment_parser = subparsers.add_parser(
        "experiment", help="Plan experiments and record runs."
    )
    experiment_subparsers = experiment_parser.add_subparsers(dest="experiment_command")
    experiment_plan = experiment_subparsers.add_parser("plan", help="Create experiment plan.")
    experiment_plan.add_argument("--project", required=True, help="Project id or slug.")
    experiment_plan.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")
    experiment_plan.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the rendered experiment-plan prompt instead of writing files.",
    )

    experiment_list = experiment_subparsers.add_parser("list", help="List project experiments.")
    experiment_list.add_argument("--project", required=True, help="Project id or slug.")
    experiment_list.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")

    experiment_run = experiment_subparsers.add_parser("add-run", help="Add a run record.")
    experiment_run.add_argument("--project", required=True, help="Project id or slug.")
    experiment_run.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")
    experiment_run.add_argument("--experiment", required=True, help="Experiment id.")
    experiment_run.add_argument(
        "--metric",
        action="append",
        default=[],
        help="Metric as name=value. Repeat for multiple metrics.",
    )

    draft_parser = subparsers.add_parser("draft", help="Plan evidence-gated drafts.")
    draft_subparsers = draft_parser.add_subparsers(dest="draft_command")
    draft_outline = draft_subparsers.add_parser("outline", help="Create a draft outline.")
    draft_outline.add_argument("--project", required=True, help="Project id or slug.")
    draft_outline.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")
    draft_outline.add_argument("--venue", choices=VENUES, help="Target venue.")
    draft_outline.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the rendered outline prompt instead of writing files.",
    )

    draft_section = draft_subparsers.add_parser("section", help="Create a section scaffold.")
    draft_section.add_argument("--project", required=True, help="Project id or slug.")
    draft_section.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")
    draft_section.add_argument("--section", required=True, choices=DRAFT_SECTIONS)
    draft_section.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the rendered section prompt instead of writing files.",
    )

    agent_parser = subparsers.add_parser("agent", help="Manage agent task specs.")
    agent_subparsers = agent_parser.add_subparsers(dest="agent_command")
    agent_task = agent_subparsers.add_parser("task", help="Manage project agent tasks.")
    agent_task_subparsers = agent_task.add_subparsers(dest="agent_task_command")
    agent_task_create = agent_task_subparsers.add_parser("create", help="Create an agent task.")
    agent_task_create.add_argument("--project", required=True, help="Project id or slug.")
    agent_task_create.add_argument(
        "--workspace", required=True, help="ResearchInfra workspace path."
    )
    agent_task_create.add_argument("--type", required=True, choices=TASK_TYPES)
    agent_task_create.add_argument("--title", required=True, help="Task title.")

    agent_task_list = agent_task_subparsers.add_parser("list", help="List agent tasks.")
    agent_task_list.add_argument("--project", required=True, help="Project id or slug.")
    agent_task_list.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")

    agent_task_show = agent_task_subparsers.add_parser("show", help="Show agent task YAML.")
    agent_task_show.add_argument("task_id", help="Agent task id.")
    agent_task_show.add_argument("--project", required=True, help="Project id or slug.")
    agent_task_show.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")

    return parser


def run(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""

    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)

    if args.command == "init":
        try:
            result = init_workspace(args.workspace, name=args.name, force=args.force)
        except WorkspaceExistsError as exc:
            return _error(str(exc))

        print(f"Initialized ResearchInfra workspace at {result.path}")
        print(f"Wrote config: {result.config_path}")
        return 0

    if args.command == "source":
        return _run_source(args)

    if args.command == "feed":
        return _run_feed(args)

    if args.command == "inbox":
        return _run_inbox(args)

    if args.command == "document":
        return _run_document(args)

    if args.command == "skill":
        return _run_skill(args)

    if args.command == "model":
        return _run_model(args)

    if args.command == "paper":
        return _run_paper(args)

    if args.command == "idea":
        return _run_idea(args)

    if args.command == "project":
        return _run_project(args)

    if args.command == "experiment":
        return _run_experiment(args)

    if args.command == "draft":
        return _run_draft(args)

    if args.command == "agent":
        return _run_agent(args)

    parser.print_help()
    return 0


def _run_source(args: argparse.Namespace) -> int:
    registry = SourceRegistry(args.workspace)
    if args.source_command == "add":
        source = registry.add(
            args.target,
            source_type=args.type,
            title=args.title,
            tags=_parse_tags(args.tags),
        )
        print(f"Added source: {source.id}")
        print(f"Title: {source.title or '(untitled)'}")
        print(f"Target: {source.target}")
        return 0

    if args.source_command == "list":
        sources = registry.list()
        if not sources:
            print("No sources registered.")
            return 0
        for source in sources:
            title = source.title or "(untitled)"
            print(f"{source.id}\t{source.source_type}\t{title}\t{source.target}")
        return 0

    if args.source_command == "show":
        try:
            source = registry.get(args.source_id)
        except SourceNotFoundError as exc:
            return _error(str(exc), code=2)
        print(yaml.safe_dump(source.model_dump(mode="json"), sort_keys=False).strip())
        return 0

    if args.source_command == "enrich":
        try:
            source = SourceEnricher(args.workspace).enrich(args.source_id)
        except (DiscoveryError, SourceNotFoundError) as exc:
            return _error(str(exc), code=2)
        print(f"Enriched source: {source.id}")
        print(yaml.safe_dump(source.model_dump(mode="json"), sort_keys=False).strip())
        return 0

    if args.source_command == "extract":
        try:
            document = DocumentExtractor(args.workspace).extract(args.source_id, force=args.force)
        except (DocumentError, SourceNotFoundError) as exc:
            return _error(str(exc), code=2)
        print(f"Extracted document: {document.id}")
        print(f"Status: {document.extraction_status}")
        print(f"Text: {document.text_path}")
        print(f"Metadata: {document.metadata_path}")
        if document.warnings:
            print("Warnings:")
            for warning in document.warnings:
                print(f"- {warning}")
        return 0

    return _error("source requires a subcommand: add, list, show, enrich, or extract", code=2)


def _run_document(args: argparse.Namespace) -> int:
    store = DocumentStore(args.workspace)
    if args.document_command == "list":
        documents = store.list()
        if not documents:
            print("No documents extracted.")
            return 0
        for document in documents:
            print(
                f"{document.id}\t{document.source_id}\t{document.content_type}\t"
                f"{document.extraction_status}\t{document.title or '(untitled)'}"
            )
        return 0

    if args.document_command == "show":
        try:
            document = store.get(args.document_id)
            text = store.read_text(document)
        except DocumentNotFoundError as exc:
            return _error(str(exc), code=2)
        if args.section:
            section = next((item for item in document.sections if item.name == args.section), None)
            if section is None:
                return _error(f"Section not found: {args.section}", code=2)
            start = section.start_char or 0
            end = section.end_char if section.end_char is not None else len(text)
            print(text[start:end].strip())
        else:
            print(text)
        return 0

    if args.document_command == "chunks":
        try:
            document = store.get(args.document_id)
        except DocumentNotFoundError as exc:
            return _error(str(exc), code=2)
        for chunk in document.chunks[: args.limit]:
            print(f"{chunk.id}\tsection={chunk.section or 'body'}")
            print(chunk.text)
            print("")
        return 0

    return _error("document requires a subcommand: list, show, or chunks", code=2)


def _run_feed(args: argparse.Namespace) -> int:
    registry = FeedRegistry(args.workspace)
    if args.feed_command == "add":
        try:
            feed = registry.add(
                name=args.name,
                feed_type=args.type,
                query=args.query,
                url=args.url,
                tags=_parse_tags(args.tags),
            )
        except DiscoveryError as exc:
            return _error(str(exc), code=2)
        print(f"Added feed: {feed.id}")
        print(f"Name: {feed.name}")
        print(f"Type: {feed.type}")
        return 0

    if args.feed_command == "list":
        feeds = registry.list()
        if not feeds:
            print("No feeds configured.")
            return 0
        for feed in feeds:
            target = feed.query or feed.url or ""
            synced = feed.last_synced_at.isoformat() if feed.last_synced_at else "never"
            print(f"{feed.id}\t{feed.type}\t{feed.name}\t{target}\tlast_synced={synced}")
        return 0

    if args.feed_command == "sync":
        try:
            added = FeedSyncer(args.workspace).sync(feed_id=args.feed, limit=args.limit)
        except (DiscoveryError, FeedNotFoundError) as exc:
            return _error(str(exc), code=2)
        print(f"Added inbox items: {len(added)}")
        for item in added:
            print(f"{item.id}\t{item.type}\t{item.title}\t{item.url}")
        return 0

    return _error("feed requires a subcommand: add, list, or sync", code=2)


def _run_inbox(args: argparse.Namespace) -> int:
    inbox = Inbox(args.workspace)
    if args.inbox_command == "list":
        items = inbox.list(status=args.status)
        if not items:
            print("No inbox items.")
            return 0
        for item in items:
            print(f"{item.id}\t{item.status}\t{item.type}\t{item.title}\t{item.url}")
        return 0

    if args.inbox_command == "show":
        try:
            item = inbox.get(args.item_id)
        except InboxItemNotFoundError as exc:
            return _error(str(exc), code=2)
        print(yaml.safe_dump(item.model_dump(mode="json"), sort_keys=False).strip())
        return 0

    if args.inbox_command == "promote":
        try:
            source = inbox.promote(args.item_id)
        except (InboxItemNotFoundError, SourceNotFoundError) as exc:
            return _error(str(exc), code=2)
        print(f"Promoted inbox item: {args.item_id}")
        print(f"Source: {source.id}")
        print(f"Target: {source.target}")
        return 0

    if args.inbox_command == "skip":
        try:
            item = inbox.skip(args.item_id)
        except InboxItemNotFoundError as exc:
            return _error(str(exc), code=2)
        print(f"Skipped inbox item: {item.id}")
        return 0

    return _error("inbox requires a subcommand: list, show, promote, or skip", code=2)


def _run_skill(args: argparse.Namespace) -> int:
    runner = SkillRunner(args.workspace)
    if args.skill_command == "list":
        for skill in runner.list(category=args.category):
            print(f"{skill.name}\t{skill.category}\t{skill.origin}\t{skill.description}")
        return 0

    if args.skill_command == "show":
        try:
            skill = runner.get(args.skill_name)
        except SkillNotFoundError as exc:
            return _error(str(exc), code=2)
        print(yaml.safe_dump(skill.model_dump(mode="json"), sort_keys=False).strip())
        return 0

    if args.skill_command == "create":
        try:
            yaml_path, prompt_path = runner.create(args.skill_name, category=args.category)
        except SkillError as exc:
            return _error(str(exc), code=2)
        print(f"Created skill: {args.skill_name}")
        print(f"Metadata: {yaml_path}")
        print(f"Prompt: {prompt_path}")
        return 0

    if args.skill_command == "run":
        try:
            prompt = runner.render(args.skill_name, args.input)
        except (SkillNotFoundError, SourceNotFoundError) as exc:
            return _error(str(exc), code=2)
        if args.dry_run:
            print(prompt)
            return 0

        provider = OpenAICompatibleProvider(
            ModelProviderConfig(id="openai-compatible", provider="openai-compatible")
        )
        try:
            result = provider.complete(prompt)
        except (ModelProviderConfigurationError, ModelProviderRequestError) as exc:
            return _error(str(exc), code=2)
        output = result.text or ""
        if args.output:
            from pathlib import Path

            output_path = Path(args.output).expanduser()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output, encoding="utf-8")
            print(f"Wrote skill output: {output_path}")
        else:
            print(output)
        return 0

    return _error("skill requires a subcommand: list, show, create, or run", code=2)


def _run_model(args: argparse.Namespace) -> int:
    if args.model_command != "check":
        return _error("model requires a subcommand: check", code=2)
    provider = OpenAICompatibleProvider(
        ModelProviderConfig(id="openai-compatible", provider="openai-compatible")
    )
    status = provider.status()
    print(f"Provider: {status['provider']}")
    print(f"Configured: {status['configured']}")
    print(f"API key: {status['api_key']}")
    print(f"Base URL: {status['base_url']}")
    print(f"Model: {status['model']}")
    return 0


def _run_paper(args: argparse.Namespace) -> int:
    if args.paper_command == "read":
        service = ReadingService(args.workspace)
        if args.dry_run:
            try:
                print(service.render_prompt(args.source_id, mode=args.mode))
            except (ReadingError, SkillNotFoundError, SourceNotFoundError) as exc:
                return _error(str(exc), code=2)
            return 0
        try:
            reading_id, notes_path, metadata_path = service.read(args.source_id, mode=args.mode)
        except (ReadingError, SkillNotFoundError, SourceNotFoundError) as exc:
            return _error(str(exc), code=2)
        print(f"Created Reading Notes: {reading_id}")
        print(f"Notes: {notes_path}")
        print(f"Metadata: {metadata_path}")
        return 0

    if args.paper_command == "create-card":
        if args.dry_run:
            try:
                print(
                    PaperCardService(args.workspace).render_prompt(
                        args.source_id, use_content=args.use_content
                    )
                )
            except (CardError, SkillNotFoundError, SourceNotFoundError) as exc:
                return _error(str(exc), code=2)
            return 0

        try:
            paper_id, markdown_path, yaml_path = PaperCardService(args.workspace).create(
                args.source_id, use_content=args.use_content
            )
        except (CardError, SourceNotFoundError) as exc:
            return _error(str(exc), code=2)
        print(f"Created Paper Card: {paper_id}")
        print(f"Markdown: {markdown_path}")
        print(f"Metadata: {yaml_path}")
        return 0

    return _error("paper requires a subcommand: create-card or read", code=2)


def _run_idea(args: argparse.Namespace) -> int:
    if args.idea_command != "generate":
        return _error("idea requires a subcommand: generate", code=2)
    if args.dry_run:
        paper_path = f"{args.workspace}/memory/papers/{args.from_paper}.md"
        try:
            print(SkillRunner(args.workspace).render("idea_card", paper_path))
        except SkillNotFoundError as exc:
            return _error(str(exc), code=2)
        return 0

    try:
        idea_id, markdown_path, yaml_path = IdeaCardService(args.workspace).generate(
            args.from_paper
        )
    except CardError as exc:
        return _error(str(exc), code=2)
    print(f"Created Idea Card: {idea_id}")
    print(f"Markdown: {markdown_path}")
    print(f"Metadata: {yaml_path}")
    return 0


def _run_project(args: argparse.Namespace) -> int:
    service = ProjectService(args.workspace)
    if args.project_command == "create":
        try:
            project, path = service.create(
                name=args.name,
                from_idea=args.from_idea,
                from_paper=args.from_paper,
                from_reading=args.from_reading,
            )
        except WorkflowError as exc:
            return _error(str(exc), code=2)
        print(f"Created Project: {project.id}")
        print(f"Path: {path}")
        print(f"Config: {path / 'project.yaml'}")
        return 0

    if args.project_command == "list":
        projects = service.list()
        if not projects:
            print("No projects.")
            return 0
        for project in projects:
            print(f"{project.id}\t{project.status}\t{project.title}")
        return 0

    if args.project_command == "show":
        try:
            project = service.get(args.project_id)
        except ProjectNotFoundError as exc:
            return _error(str(exc), code=2)
        print(yaml.safe_dump(project.model_dump(mode="json"), sort_keys=False).strip())
        return 0

    if args.project_command == "status":
        try:
            print(service.status(args.project_id))
        except ProjectNotFoundError as exc:
            return _error(str(exc), code=2)
        return 0

    if args.project_command == "add-paper":
        try:
            project = service.add_paper(args.project_id, args.paper_id)
        except WorkflowError as exc:
            return _error(str(exc), code=2)
        print(f"Linked Paper Card: {args.paper_id}")
        print(f"Project: {project.id}")
        return 0

    if args.project_command == "add-reading":
        try:
            project = service.add_reading(args.project_id, args.reading_id)
        except WorkflowError as exc:
            return _error(str(exc), code=2)
        print(f"Linked Reading: {args.reading_id}")
        print(f"Project: {project.id}")
        return 0

    return _error(
        "project requires a subcommand: create, list, show, status, add-paper, or add-reading",
        code=2,
    )


def _run_experiment(args: argparse.Namespace) -> int:
    service = ExperimentService(args.workspace)
    if args.experiment_command == "plan":
        try:
            if args.dry_run:
                print(service.render_plan_prompt(args.project))
                return 0
            paths = service.plan(args.project)
        except (WorkflowError, SkillNotFoundError) as exc:
            return _error(str(exc), code=2)
        print("Created Experiment Plan")
        for path in paths:
            print(f"Artifact: {path}")
        return 0

    if args.experiment_command == "list":
        try:
            experiments = service.list(args.project)
        except WorkflowError as exc:
            return _error(str(exc), code=2)
        if not experiments:
            print("No experiments.")
            return 0
        for experiment_id in experiments:
            print(experiment_id)
        return 0

    if args.experiment_command == "add-run":
        try:
            run_record, path = service.add_run(
                project_id=args.project,
                experiment_id=args.experiment,
                metrics=_parse_metrics(args.metric),
            )
        except WorkflowError as exc:
            return _error(str(exc), code=2)
        print(f"Added Run: {run_record.id}")
        print(f"Registry: {path}")
        return 0

    return _error("experiment requires a subcommand: plan, list, or add-run", code=2)


def _run_draft(args: argparse.Namespace) -> int:
    service = DraftService(args.workspace)
    if args.draft_command == "outline":
        try:
            if args.dry_run:
                print(service.render_outline_prompt(args.project, venue=args.venue))
                return 0
            path = service.outline(args.project, venue=args.venue)
        except (WorkflowError, SkillNotFoundError) as exc:
            return _error(str(exc), code=2)
        print(f"Created Draft Outline: {path}")
        return 0

    if args.draft_command == "section":
        try:
            if args.dry_run:
                print(service.render_section_prompt(args.project, section=args.section))
                return 0
            path = service.section(args.project, section=args.section)
        except (WorkflowError, SkillNotFoundError) as exc:
            return _error(str(exc), code=2)
        print(f"Created Draft Section: {path}")
        return 0

    return _error("draft requires a subcommand: outline or section", code=2)


def _run_agent(args: argparse.Namespace) -> int:
    if args.agent_command != "task":
        return _error("agent requires a subcommand: task", code=2)
    service = AgentTaskService(args.workspace)
    if args.agent_task_command == "create":
        try:
            task, path = service.create(
                project_id=args.project,
                task_type=args.type,
                title=args.title,
            )
        except WorkflowError as exc:
            return _error(str(exc), code=2)
        print(f"Created Agent Task: {task.id}")
        print(f"Spec: {path}")
        return 0

    if args.agent_task_command == "list":
        try:
            tasks = service.list(args.project)
        except WorkflowError as exc:
            return _error(str(exc), code=2)
        if not tasks:
            print("No agent tasks.")
            return 0
        for task in tasks:
            print(f"{task.id}\t{task.task_type or 'unknown'}\t{task.status}\t{task.title}")
        return 0

    if args.agent_task_command == "show":
        try:
            task = service.get(project_id=args.project, task_id=args.task_id)
        except WorkflowError as exc:
            return _error(str(exc), code=2)
        print(yaml.safe_dump(task.model_dump(mode="json"), sort_keys=False).strip())
        return 0

    return _error("agent task requires a subcommand: create, list, or show", code=2)


def _parse_tags(value: str) -> list[str]:
    return [tag.strip() for tag in value.split(",") if tag.strip()]


def _parse_metrics(values: list[str]) -> dict[str, object]:
    metrics: dict[str, object] = {}
    for value in values:
        if "=" not in value:
            raise WorkflowError(f"Metric must use name=value: {value}")
        name, raw = value.split("=", 1)
        name = name.strip()
        if not name:
            raise WorkflowError(f"Metric name is empty: {value}")
        metrics[name] = _parse_metric_value(raw.strip())
    return metrics


def _parse_metric_value(value: str) -> object:
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _error(message: str, *, code: int = 1) -> int:
    print(f"researchinfra: error: {message}", file=sys.stderr)
    return code


def main(argv: Sequence[str] | None = None) -> None:
    """Console script entry point."""

    raise SystemExit(run(argv))


if __name__ == "__main__":
    main(sys.argv[1:])
