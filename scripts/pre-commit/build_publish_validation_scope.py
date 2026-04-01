#!/usr/bin/env python3
"""Build scoped file list for pre-commit import validation.

Reads git staged files and produces a newline-delimited scope file
containing only the Python files that should be validated. Excludes
paths that are not part of the publishable source (e.g. .claude/scenarios,
tests, vendor code).

Usage:
    python scripts/pre-commit/build_publish_validation_scope.py [--output FILE]

    Without --output, prints the scoped file list to stdout.
    With --output FILE, writes to FILE (one path per line).

Exit Codes:
    0: Scope built successfully (may be empty)
    1: Error reading staged files
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Directories excluded from import validation scope.
# These contain non-publishable code (tools, scenarios, tests, vendor).
EXCLUDED_PREFIXES = (
    ".claude/scenarios/",
    ".claude/tools/",
    ".claude/skills/",
    ".github/scripts/",
    "tests/",
    "archive/",
    "experiments/",
    "deploy/",
    "build_hooks.py",
)

# Specific files excluded (matched exactly after repo-root-relative path).
EXCLUDED_FILES = frozenset(
    {
        "build_hooks.py",
    }
)


def get_staged_python_files() -> list[str]:
    """Return repo-root-relative paths of staged Python files.

    Uses ``git diff --cached --name-only --diff-filter=ACM`` to list
    files that are Added, Copied, or Modified in the index.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            print(f"ERROR: git diff failed: {result.stderr.strip()}", file=sys.stderr)
            sys.exit(1)

        return [
            line
            for line in result.stdout.splitlines()
            if line.strip() and line.strip().endswith(".py")
        ]
    except FileNotFoundError:
        print("ERROR: git not found in PATH", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("ERROR: git diff timed out after 30s", file=sys.stderr)
        sys.exit(1)


def is_excluded(filepath: str) -> bool:
    """Return True if *filepath* should be excluded from validation scope."""
    if filepath in EXCLUDED_FILES:
        return True
    for prefix in EXCLUDED_PREFIXES:
        if filepath.startswith(prefix):
            return True
    # Also exclude any nested tests/ directories (e.g. src/pkg/tests/...)
    parts = Path(filepath).parts
    if "tests" in parts:
        return True
    return False


def build_scope(staged_files: list[str] | None = None) -> list[str]:
    """Build the validation scope from staged files.

    Args:
        staged_files: Optional pre-supplied list. If None, reads from git.

    Returns:
        Sorted list of repo-root-relative Python file paths to validate.
    """
    if staged_files is None:
        staged_files = get_staged_python_files()

    return sorted(f for f in staged_files if not is_excluded(f))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build scoped file list for pre-commit import validation."
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Write scope to FILE instead of stdout.",
    )
    args = parser.parse_args()

    scope = build_scope()

    output_text = "\n".join(scope)
    if args.output:
        Path(args.output).write_text(output_text + "\n" if output_text else "")
        print(f"Wrote {len(scope)} file(s) to {args.output}", file=sys.stderr)
    else:
        if output_text:
            print(output_text)

    # Always exit 0 — an empty scope is valid (no staged Python files).


if __name__ == "__main__":
    main()
