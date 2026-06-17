"""Command-line interface for ResearchInfra."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from researchinfra import __version__
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
            parser.exit(2, f"researchinfra: error: {exc}\n")

        print(f"Initialized ResearchInfra workspace at {result.path}")
        print(f"Wrote config: {result.config_path}")
        return 0

    parser.print_help()
    return 0


def main(argv: Sequence[str] | None = None) -> None:
    """Console script entry point."""

    raise SystemExit(run(argv))


if __name__ == "__main__":
    main(sys.argv[1:])
