"""CLI entry point for the recovery workflow."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from . import coordinator
from .results import recovery_run_to_json


def _add_run_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", required=True, type=Path, help="Repository root to recover")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON ledger output path",
    )
    parser.add_argument(
        "--worktree",
        type=Path,
        help="Optional isolated worktree for Stage 3/4",
    )
    parser.add_argument("--min-audit-cycles", type=int, default=3)
    parser.add_argument("--max-audit-cycles", type=int, default=6)


def add_recovery_subcommand(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the main `amplihack recovery` subcommand tree."""
    recovery_parser = subparsers.add_parser("recovery", help="Recovery workflow commands")
    recovery_subparsers = recovery_parser.add_subparsers(dest="recovery_command", required=True)
    run_parser = recovery_subparsers.add_parser("run", help="Run Stage 1-4 recovery")
    _add_run_arguments(run_parser)


def build_parser(*, prog: str = "python -m amplihack.recovery") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="Run Stage 1-4 recovery")
    _add_run_arguments(run_parser)
    return parser


def run_from_args(args: argparse.Namespace) -> int:
    """Run recovery from an argparse namespace and emit JSON output."""
    run = coordinator.run_recovery(
        repo_path=args.repo,
        output_path=args.output,
        worktree_path=args.worktree,
        min_audit_cycles=args.min_audit_cycles,
        max_audit_cycles=args.max_audit_cycles,
    )
    print(json.dumps(recovery_run_to_json(run), indent=2, sort_keys=True))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Parse CLI arguments, run recovery, and emit the ledger."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return run_from_args(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
