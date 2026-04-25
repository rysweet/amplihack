#!/usr/bin/env python3
"""CLI entry point: produce per-language mermaid diagrams for a target path.

Usage:
    visualizer.py <path> [--output DIR] [--basename NAME]
                  [--combined] [--check-staleness]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Make sibling modules importable when invoked as a script.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from dispatcher import analyze
from mermaid_renderer import render, render_combined
from staleness import is_stale

_BASENAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="visualizer",
        description="Generate mermaid diagrams of imports/dependencies per language.",
    )
    p.add_argument("path", help="Target source directory to scan.")
    p.add_argument(
        "--output",
        default=".",
        help="Directory to write .mmd files into (default: current directory).",
    )
    p.add_argument(
        "--basename",
        default="diagram",
        help="Base filename for output (default: 'diagram'). "
        "Final files are <basename>-<language>.mmd.",
    )
    p.add_argument(
        "--combined",
        action="store_true",
        help="Also emit a <basename>-combined.mmd with one subgraph per language.",
    )
    p.add_argument(
        "--check-staleness",
        action="store_true",
        help="Only check whether existing diagrams are stale; exit 1 if stale.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if not _BASENAME_RE.match(args.basename):
        print(
            f"error: --basename must match {_BASENAME_RE.pattern}; got {args.basename!r}",
            file=sys.stderr,
        )
        return 2

    target = Path(args.path).resolve()
    if not target.exists():
        print(f"error: path does not exist: {target}", file=sys.stderr)
        return 2
    if not target.is_dir():
        print(f"error: path is not a directory: {target}", file=sys.stderr)
        return 2

    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    graphs = analyze(target)

    if args.check_staleness:
        any_stale = False
        for lang in graphs:
            diag = output_dir / f"{args.basename}-{lang}.mmd"
            if is_stale(target, diag, [lang]):
                print(f"stale: {diag}")
                any_stale = True
        return 1 if any_stale else 0

    for lang, graph in graphs.items():
        out = output_dir / f"{args.basename}-{lang}.mmd"
        out.write_text(render(graph), encoding="utf-8")
        print(f"wrote {out}")

    if args.combined:
        combined = output_dir / f"{args.basename}-combined.mmd"
        combined.write_text(render_combined(graphs), encoding="utf-8")
        print(f"wrote {combined}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
