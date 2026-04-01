#!/usr/bin/env python3
"""Import smoke test for pre-commit hook.

Validates Python files can be imported without errors and catches missing type
hint imports (Any, Optional, etc.).

Usage:
    python scripts/pre-commit/check_imports.py file1.py file2.py
    python scripts/pre-commit/check_imports.py --files-from validation-scope.txt

Exit Codes:
    0: All imports successful
    1: Import errors found
    2: Invalid CLI usage or invalid --files-from input
"""

from __future__ import annotations

import argparse
import ast
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

# Type hints that must be imported
REQUIRED_TYPE_IMPORTS = {
    "Any": "typing",
    "Optional": "typing",
    "Union": "typing",
    "List": "typing",
    "Dict": "typing",
    "Tuple": "typing",
    "TYPE_CHECKING": "typing",
}
PATH_CONTROL_CHARACTERS = {"\x00", "\n", "\r"}
SAFE_IMPORT_ENV_KEYS = (
    "HOME",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "PATH",
    "PYTHONHOME",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "TMPDIR",
    "USERPROFILE",
    "WINDIR",
)
IMPORT_TEST_CODE = """
import sys
import json
sys.path.insert(0, 'src')
module_name = json.loads(sys.argv[1])
def fail(kind, error_type, module_name=None):
    payload = {"ok": False, "kind": kind, "error_type": error_type}
    if module_name:
        payload["module"] = module_name
    print(json.dumps(payload))
    sys.exit(1)
try:
    __import__(module_name)
except ModuleNotFoundError as exc:
    fail("module-not-found", type(exc).__name__, exc.name or module_name)
except ImportError as exc:
    fail("import-error", type(exc).__name__, getattr(exc, "name", None))
except BaseException as exc:
    fail("import-exception", type(exc).__name__)
print(json.dumps({"ok": True}))
"""


def analyze_file_imports(file_path: Path) -> tuple[set[str], dict[str | None, set[str]]]:
    """Extract used typing names and actual imports in one AST pass."""
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    except Exception as exc:
        logging.debug("Failed to analyze imports for %s: %s", file_path, exc)
        return set(), {}

    used_types: set[str] = set()
    imports: dict[str | None, set[str]] = {}

    class ImportAnalyzer(ast.NodeVisitor):
        def visit_Name(self, node: ast.Name) -> None:
            if node.id in REQUIRED_TYPE_IMPORTS:
                used_types.add(node.id)
            self.generic_visit(node)

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            imported_names = imports.setdefault(node.module, set())
            for alias in node.names:
                imported_names.add(alias.name)
            self.generic_visit(node)

        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                imports[alias.name] = {"*"}  # Treat as importing everything
            self.generic_visit(node)

    ImportAnalyzer().visit(tree)
    return used_types, imports


def check_type_imports(file_path: Path) -> list[str]:
    """Check if used type hints are imported."""
    errors: list[str] = []

    try:
        used_types, actual_imports = analyze_file_imports(file_path)

        for type_name in used_types:
            module = REQUIRED_TYPE_IMPORTS[type_name]

            is_imported = (
                (module in actual_imports and type_name in actual_imports[module])
                or (module in actual_imports and "*" in actual_imports[module])
                or (module in actual_imports and {"*"} == actual_imports.get(module, set()))
            )

            if not is_imported:
                errors.append(
                    f"{file_path}: {type_name} used but not imported\n"
                    f"  Fix: from {module} import {type_name}"
                )

    except Exception as exc:
        errors.append(f"{file_path}: Error checking imports: {exc}")

    return errors


def normalize_repo_relative_file(
    repo_root: Path,
    candidate: str,
    *,
    require_python: bool,
    description: str,
    resolved_repo: Path | None = None,
) -> str:
    """Normalize and validate a repo-relative file path."""
    trimmed = candidate.strip()
    if not trimmed:
        raise ValueError(f"{description} is empty")
    if any(char in trimmed for char in PATH_CONTROL_CHARACTERS):
        raise ValueError(f"{description} contains control characters: {trimmed!r}")

    raw_path = Path(trimmed)
    if raw_path.is_absolute():
        raise ValueError(f"{description} must be repo-relative: {trimmed}")
    if any(part == ".." for part in raw_path.parts):
        raise ValueError(f"{description} must not contain traversal segments: {trimmed}")

    if resolved_repo is None:
        resolved_repo = repo_root.resolve()
    resolved_candidate = (resolved_repo / raw_path).resolve()
    try:
        relative_path = resolved_candidate.relative_to(resolved_repo)
    except ValueError as exc:
        raise ValueError(f"{description} resolves outside repository root: {trimmed}") from exc

    if not resolved_candidate.exists():
        raise ValueError(f"{description} does not exist: {trimmed}")
    if not resolved_candidate.is_file():
        raise ValueError(f"{description} must be a file: {trimmed}")
    if require_python and resolved_candidate.suffix != ".py":
        raise ValueError(f"{description} must reference a .py file: {trimmed}")

    return relative_path.as_posix()


def load_repo_relative_file_list(
    list_path: Path,
    repo_root: Path,
    *,
    require_python: bool,
    description: str,
) -> list[Path]:
    """Read, normalize, and deduplicate repo-relative file paths from a text file."""
    try:
        raw_text = list_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"{description} is not readable: {list_path} ({exc})") from exc

    normalized_paths: list[Path] = []
    seen: set[str] = set()
    resolved_repo = repo_root.resolve()

    for line_number, raw_line in enumerate(raw_text.splitlines(), start=1):
        entry = raw_line.strip()
        if not entry:
            continue

        normalized = normalize_repo_relative_file(
            repo_root,
            entry,
            require_python=require_python,
            description=f"{description} line {line_number}",
            resolved_repo=resolved_repo,
        )
        if normalized not in seen:
            seen.add(normalized)
            normalized_paths.append(Path(normalized))

    return normalized_paths


def normalize_positional_python_files(files: list[str], repo_root: Path) -> list[Path]:
    """Normalize and deduplicate positional repo-relative Python file paths."""
    normalized_paths: list[Path] = []
    seen: set[str] = set()
    resolved_repo = repo_root.resolve()

    for index, raw_file_name in enumerate(files, start=1):
        if not raw_file_name.endswith(".py"):
            continue

        normalized = normalize_repo_relative_file(
            repo_root,
            raw_file_name,
            require_python=True,
            description=f"file argument {index}",
            resolved_repo=resolved_repo,
        )
        if normalized not in seen:
            seen.add(normalized)
            normalized_paths.append(Path(normalized))

    return normalized_paths


def build_import_test_env() -> dict[str, str]:
    """Return the minimal environment used for smoke-import subprocesses."""
    env = {"PYTHONNOUSERSITE": "1"}
    for key in SAFE_IMPORT_ENV_KEYS:
        value = os.environ.get(key)
        if value:
            env[key] = value
    return env


def format_import_failure(stdout: str, returncode: int) -> str:
    """Render a sanitized failure summary from the child process output."""
    for line in reversed(stdout.splitlines()):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            continue

        if not isinstance(payload, dict) or payload.get("ok") is True:
            continue

        error_type = str(payload.get("error_type") or "ImportError")
        missing_module = payload.get("module")
        if missing_module:
            return f"{error_type}: missing dependency {missing_module!r}"
        return f"{error_type}: import raised during smoke test"

    return f"Import test failed with exit code {returncode}"


def test_import(file_path: Path, *, repo_root: Path | None = None) -> tuple[Path, bool, str]:
    """Test if file can be imported successfully."""
    if repo_root is None:
        repo_root = Path.cwd().resolve()

    try:
        file_path = file_path.resolve()
        file_path.relative_to(repo_root)
    except (ValueError, RuntimeError):
        return file_path, False, "Path traversal: File outside repository"

    if file_path.is_absolute():
        try:
            rel_path = file_path.relative_to(repo_root)
        except ValueError:
            return file_path, False, "Cannot resolve relative path"
    else:
        rel_path = file_path

    if rel_path.parts[0] == "src":
        module_parts = rel_path.parts[1:-1] + (rel_path.stem,)
    else:
        module_parts = rel_path.parts[:-1] + (rel_path.stem,)

    module_name = ".".join(module_parts)

    try:
        result = subprocess.run(
            [sys.executable, "-c", IMPORT_TEST_CODE, json.dumps(module_name)],
            capture_output=True,
            cwd=repo_root,
            env=build_import_test_env(),
            text=True,
            timeout=15,
        )

        if result.returncode == 0:
            return file_path, True, ""
        return file_path, False, format_import_failure(result.stdout, result.returncode)

    except subprocess.TimeoutExpired:
        return file_path, False, "Import timeout (>15s)"
    except Exception as exc:
        return file_path, False, f"Test error: {exc!s}"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Validate Python imports and type hints.")
    parser.add_argument("files", nargs="*", help="Python files to validate")
    parser.add_argument(
        "--files-from",
        dest="files_from",
        help="Read the exact repo-relative .py file list from a newline-delimited file",
    )

    args = parser.parse_args(argv)
    if args.files_from and args.files:
        parser.error("--files-from and positional FILES are mutually exclusive")

    return args


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    args = parse_args(argv)
    repo_root = Path.cwd()

    if not args.files and not args.files_from:
        print("No files to check")
        return 0

    if args.files_from:
        try:
            files = load_repo_relative_file_list(
                Path(args.files_from),
                repo_root,
                require_python=True,
                description="scope file",
            )
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
    else:
        try:
            files = normalize_positional_python_files(args.files, repo_root)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    if not files:
        print("No Python files to check")
        return 0

    print(f"Checking imports for {len(files)} file(s)...")

    print("\n1. Validating type hint imports...")
    type_errors: list[str] = []
    for file_path in files:
        type_errors.extend(check_type_imports(file_path))

    if type_errors:
        print("\n❌ Type import errors:")
        for error in type_errors:
            print(f"  {error}")

    print("\n2. Testing module imports...")
    import_errors: list[tuple[Path, str]] = []
    resolved_repo_root = repo_root.resolve()

    for file_path in files:
        file_path, success, error_msg = test_import(file_path, repo_root=resolved_repo_root)
        if not success:
            import_errors.append((file_path, error_msg))
            print(f"  ❌ {file_path}: FAILED")
        else:
            print(f"  ✅ {file_path}: OK")

    if import_errors or type_errors:
        print("\n" + "=" * 60)
        print("❌ IMPORT VALIDATION FAILED - FIX BEFORE COMMITTING")
        print("=" * 60)

        if type_errors:
            print("\nMissing Type Imports:")
            for error in type_errors:
                print(f"  {error}")

        if import_errors:
            print("\nImport Errors:")
            for file_path, error in import_errors:
                print(f"\n  {file_path}:")
                print(f"    {error}")

        return 1

    print("\n✅ All imports valid!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
