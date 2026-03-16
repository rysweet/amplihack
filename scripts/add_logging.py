#!/usr/bin/env python3
"""Add @log_call decorator to all functions in the amplihack codebase.

Decision log:
- Uses AST to find function line numbers → precise, syntax-aware
- Inserts @log_call as the INNERMOST decorator (just before `def`) → safe
  with @property, @staticmethod, @classmethod, etc.
- Line-insertion approach (not ast.unparse) → preserves all comments and formatting
- Absolute import: `from amplihack.utils.logging_utils import log_call`
- Skips: logging_utils.py itself (to avoid circular import), __pycache__,
  and files that already have @log_call on every qualifying function
- Handles both sync and async functions identically (decorator detects at runtime)

Usage:
    python scripts/add_logging.py [--dry-run] [--path PATH]

Philosophy: ruthless simplicity — one pass, file-safe, idempotent.
"""

import argparse
import ast
import sys
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────

DECORATOR_NAME = "log_call"
IMPORT_LINE = "from amplihack.utils.logging_utils import log_call\n"

# Files to never touch
SKIP_FILENAMES = {
    "logging_utils.py",  # the decorator itself — circular import
    "add_logging.py",  # this script
    "conftest.py",  # pytest fixtures use special decorator rules
}

# ── AST helpers ────────────────────────────────────────────────────────────────


def _has_log_call(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True if @log_call is already on this function."""
    for d in func_node.decorator_list:
        if isinstance(d, ast.Name) and d.id == DECORATOR_NAME:
            return True
        if isinstance(d, ast.Attribute) and d.attr == DECORATOR_NAME:
            return True
    return False


def _get_def_line(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Return 0-indexed line index of the `def` / `async def` keyword.

    We always insert @log_call DIRECTLY before the `def` keyword, making it
    the innermost decorator. This is the only universally safe insertion point:
    it works correctly with @property, @staticmethod, @classmethod, etc.
    """
    return func_node.lineno - 1  # ast is 1-indexed


def _find_insert_positions(
    source: str,
) -> set[int]:
    """Parse source and return 0-indexed line numbers where @log_call must be inserted."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()

    positions: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not _has_log_call(node):
                positions.add(_get_def_line(node))
    return positions


# ── Import-insertion helpers ───────────────────────────────────────────────────


def _already_has_import(lines: list[str]) -> bool:
    """Return True if the file already imports log_call in any form.

    Scans ALL lines (not just the top N) to be safe with long-preamble files.
    Only matches top-level import lines (unindented).
    """
    for line in lines:
        if not line or line[0].isspace():
            continue  # skip indented lines (function-body imports)
        if DECORATOR_NAME in line and "import" in line:
            return True
    return False


def _find_import_insert_pos(lines: list[str]) -> int:
    """Return 0-indexed position AFTER the last TOP-LEVEL import statement.

    Uses AST ``end_lineno`` so multiline imports like::

        from foo import (
            A,
            B,
        )

    are handled correctly — insertion happens after the closing ``)``, not
    inside the group.

    Only top-level (col-0, depth-0) ``Import`` / ``ImportFrom`` nodes are
    considered.  Function-body imports at deeper nesting are ignored entirely.

    Falls back to the line after the module docstring (or line 0) when the
    file has no top-level imports.
    """
    source = "".join(lines)
    # Use AST to find end of last top-level import
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # AST unavailable — fall back to naive column-0 scan
        return _find_import_insert_pos_fallback(lines)

    last_end_lineno = -1  # 1-indexed end line of the last top-level import
    for node in ast.iter_child_nodes(tree):
        # ast.Module children are all top-level statements
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            end = getattr(node, "end_lineno", node.lineno)
            if end > last_end_lineno:
                last_end_lineno = end

    if last_end_lineno >= 1:
        return last_end_lineno  # 0-indexed insert position = 1-indexed end line

    # No top-level imports — place after module docstring
    return _module_docstring_end(lines)


def _find_import_insert_pos_fallback(lines: list[str]) -> int:
    """Naive fallback: last unindented import line + 1."""
    last_pos = -1
    for i, raw in enumerate(lines):
        if raw and not raw[0].isspace():
            s = raw.strip()
            if s.startswith("import ") or s.startswith("from "):
                last_pos = i
    return last_pos + 1 if last_pos >= 0 else _module_docstring_end(lines)


def _module_docstring_end(lines: list[str]) -> int:
    """Return the 0-indexed line just after the module docstring (or 0)."""
    in_ds = False
    for i, raw in enumerate(lines):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if not in_ds:
            if s.startswith('"""') or s.startswith("'''"):
                quote = s[:3]
                if s.count(quote) >= 2 and len(s) > 3:
                    return i + 1  # single-line docstring
                in_ds = True
                continue
            return i  # no docstring; insert before first real line
        if s.endswith('"""') or s.endswith("'''"):
            return i + 1
    return 0


# ── File processor ─────────────────────────────────────────────────────────────


def process_file(filepath: Path, *, dry_run: bool = False) -> str:
    """Process a single .py file.

    Returns a status string: 'modified', 'skipped', 'no_functions', or 'error:<msg>'.
    """
    try:
        source = filepath.read_text(encoding="utf-8")
    except Exception as exc:
        return f"error:read:{exc}"

    # --- Find functions needing @log_call ---
    insert_positions = _find_insert_positions(source)
    if not insert_positions:
        return "no_functions"

    lines = source.splitlines(keepends=True)

    # --- Insert @log_call decorators (bottom → top to preserve line offsets) ---
    for line_no in sorted(insert_positions, reverse=True):
        func_line = lines[line_no]
        indent = len(func_line) - len(func_line.lstrip())
        decorator_line = " " * indent + f"@{DECORATOR_NAME}\n"
        lines.insert(line_no, decorator_line)

    # --- Add import if missing ---
    if not _already_has_import(lines):
        insert_pos = _find_import_insert_pos(lines)
        lines.insert(insert_pos, IMPORT_LINE)

    new_source = "".join(lines)

    # Sanity-check: new source must be parseable
    try:
        ast.parse(new_source)
    except SyntaxError as exc:
        return f"error:syntax_after_transform:{exc}"

    if not dry_run:
        try:
            filepath.write_text(new_source, encoding="utf-8")
        except Exception as exc:
            return f"error:write:{exc}"

    return "modified"


# ── Main ───────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add @log_call to all functions in the amplihack codebase.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing files.",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("/home/azureuser/src/amplihack/src/amplihack"),
        help="Root directory to process (default: amplihack src package).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print a line for every file processed.",
    )
    args = parser.parse_args()

    src_dir: Path = args.path.resolve()
    if not src_dir.is_dir():
        print(f"ERROR: path does not exist: {src_dir}", file=sys.stderr)
        return 1

    py_files = sorted(src_dir.rglob("*.py"))

    counts = {"modified": 0, "no_functions": 0, "skipped": 0, "errors": 0}
    error_details: list[str] = []

    for filepath in py_files:
        # Skip unwanted files
        if "__pycache__" in filepath.parts:
            continue
        if filepath.name in SKIP_FILENAMES:
            counts["skipped"] += 1
            if args.verbose:
                print(f"  SKIP  {filepath.relative_to(src_dir)}")
            continue

        status = process_file(filepath, dry_run=args.dry_run)

        if status == "modified":
            counts["modified"] += 1
            marker = "DRY " if args.dry_run else "  ✓  "
            print(f"{marker} {filepath.relative_to(src_dir)}")
        elif status == "no_functions":
            counts["no_functions"] += 1
            if args.verbose:
                print(f"  ─    {filepath.relative_to(src_dir)}")
        elif status.startswith("error:"):
            counts["errors"] += 1
            msg = f"  ✗  {filepath.relative_to(src_dir)}: {status}"
            error_details.append(msg)
            print(msg, file=sys.stderr)

    # ── Summary ───────────────────────────────────────────────────────────────
    mode = " (dry run)" if args.dry_run else ""
    print(
        f"\n{'─' * 60}\n"
        f"Done{mode}:\n"
        f"  {counts['modified']:>5} files {'would be ' if args.dry_run else ''}modified\n"
        f"  {counts['no_functions']:>5} files had no undecorated functions\n"
        f"  {counts['skipped']:>5} files skipped\n"
        f"  {counts['errors']:>5} errors\n"
        f"{'─' * 60}"
    )

    return 1 if counts["errors"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
