"""Command-line interface for ResearchInfra."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

import yaml

from researchinfra import __version__
from researchinfra.cards import CardError, IdeaCardService, PaperCardService
from researchinfra.models.adapters import OpenAICompatibleProvider
from researchinfra.models.base import ModelProviderConfigurationError, ModelProviderRequestError
from researchinfra.schemas import ModelProviderConfig
from researchinfra.skills import SkillNotFoundError, SkillRunner
from researchinfra.sources import SourceNotFoundError, SourceRegistry
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

    skill_parser = subparsers.add_parser("skill", help="List and run reusable skills.")
    skill_subparsers = skill_parser.add_subparsers(dest="skill_command")
    skill_list = skill_subparsers.add_parser("list", help="List available skills.")
    skill_list.add_argument("--workspace", required=True, help="ResearchInfra workspace path.")

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

    if args.command == "skill":
        return _run_skill(args)

    if args.command == "model":
        return _run_model(args)

    if args.command == "paper":
        return _run_paper(args)

    if args.command == "idea":
        return _run_idea(args)

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

    return _error("source requires a subcommand: add, list, or show", code=2)


def _run_skill(args: argparse.Namespace) -> int:
    runner = SkillRunner(args.workspace)
    if args.skill_command == "list":
        for skill in runner.list():
            print(f"{skill.name}\t{skill.origin}\t{skill.description}")
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

    return _error("skill requires a subcommand: list or run", code=2)


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
    if args.paper_command != "create-card":
        return _error("paper requires a subcommand: create-card", code=2)
    if args.dry_run:
        try:
            print(SkillRunner(args.workspace).render("paper_card", args.source_id))
        except (SkillNotFoundError, SourceNotFoundError) as exc:
            return _error(str(exc), code=2)
        return 0

    try:
        paper_id, markdown_path, yaml_path = PaperCardService(args.workspace).create(args.source_id)
    except (CardError, SourceNotFoundError) as exc:
        return _error(str(exc), code=2)
    print(f"Created Paper Card: {paper_id}")
    print(f"Markdown: {markdown_path}")
    print(f"Metadata: {yaml_path}")
    return 0


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


def _parse_tags(value: str) -> list[str]:
    return [tag.strip() for tag in value.split(",") if tag.strip()]


def _error(message: str, *, code: int = 1) -> int:
    print(f"researchinfra: error: {message}", file=sys.stderr)
    return code


def main(argv: Sequence[str] | None = None) -> None:
    """Console script entry point."""

    raise SystemExit(run(argv))


if __name__ == "__main__":
    main(sys.argv[1:])
