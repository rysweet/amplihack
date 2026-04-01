#!/usr/bin/env python3
"""Build the exact Python import-validation scope for a staged publish surface."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache
from pathlib import Path

PATH_CONTROL_CHARACTERS = {"\x00", "\n", "\r"}


@dataclass(frozen=True)
class SearchRoot:
    """A root boundary the scope expansion is allowed to search within."""

    base_dir: Path
    allowed_prefix: Path
    package_prefix: tuple[str, ...] | None = None

    def allows(self, repo_relative_path: Path) -> bool:
        """Return True when *repo_relative_path* stays inside this root boundary."""
        try:
            repo_relative_path.relative_to(self.allowed_prefix)
        except ValueError:
            return False
        return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Build the scoped Python file list for publish import validation."
    )
    parser.add_argument(
        "--manifest", required=True, help="Path to newline-delimited publish manifest"
    )
    parser.add_argument("--output", required=True, help="Path to write the scoped .py file list")
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root used for path normalization (default: current working directory)",
    )
    parser.add_argument(
        "--exclude-claude-scenarios",
        action="store_true",
        help="Exclude .claude/scenarios/** seed files from the scoped publish surface",
    )
    return parser.parse_args(argv)


def normalize_manifest_entry(resolved_repo: Path, entry: str, *, line_number: int) -> Path:
    """Normalize and validate one manifest entry."""
    trimmed = entry.strip()
    if not trimmed:
        raise ValueError(f"manifest line {line_number} is empty")
    if any(char in trimmed for char in PATH_CONTROL_CHARACTERS):
        raise ValueError(f"manifest line {line_number} contains control characters: {trimmed!r}")

    raw_path = Path(trimmed)
    if raw_path.is_absolute():
        raise ValueError(f"manifest line {line_number} must be repo-relative: {trimmed}")
    if any(part == ".." for part in raw_path.parts):
        raise ValueError(
            f"manifest line {line_number} must not contain traversal segments: {trimmed}"
        )

    resolved_candidate = (resolved_repo / raw_path).resolve()

    try:
        repo_relative = resolved_candidate.relative_to(resolved_repo)
    except ValueError as exc:
        raise ValueError(
            f"manifest line {line_number} resolves outside repository root: {trimmed}"
        ) from exc

    if not resolved_candidate.exists():
        raise ValueError(f"manifest line {line_number} does not exist: {trimmed}")
    if not resolved_candidate.is_file():
        raise ValueError(f"manifest line {line_number} must be a file: {trimmed}")

    return Path(repo_relative.as_posix())


def load_manifest(manifest_path: Path, repo_root: Path) -> list[Path]:
    """Read, normalize, and deduplicate manifest entries."""
    try:
        manifest_text = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"manifest is not readable: {manifest_path} ({exc})") from exc

    resolved_repo = repo_root.resolve()
    normalized_entries: list[Path] = []
    seen: set[str] = set()
    for line_number, line in enumerate(manifest_text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        normalized = normalize_manifest_entry(resolved_repo, stripped, line_number=line_number)
        normalized_key = normalized.as_posix()
        if normalized_key not in seen:
            seen.add(normalized_key)
            normalized_entries.append(normalized)
    return normalized_entries


def is_claude_scenario_path(path: Path) -> bool:
    """Return True when *path* points under .claude/scenarios."""
    parts = path.parts
    return len(parts) >= 2 and parts[0] == ".claude" and parts[1] == "scenarios"


def find_generic_package_root(repo_root: Path, directory: Path) -> SearchRoot | None:
    """Return a package-aware search root for a generic Python file if one exists."""
    current = directory
    package_root: Path | None = None

    while current != Path("."):
        if not (repo_root / current / "__init__.py").is_file():
            break
        package_root = current
        current = current.parent

    if package_root is None:
        return None

    parent_dir = package_root.parent
    package_prefix = (package_root.name,)
    base_dir = repo_root / parent_dir if parent_dir != Path(".") else repo_root
    return SearchRoot(
        base_dir=base_dir,
        allowed_prefix=package_root,
        package_prefix=package_prefix,
    )


def derive_search_root(repo_root: Path, seed_path: Path) -> SearchRoot:
    """Derive the allowed dependency-expansion root for a seed file."""
    parts = seed_path.parts
    if not parts:
        raise ValueError(f"Cannot derive root for empty path: {seed_path}")

    if parts[0] == "src" and len(parts) >= 2:
        return SearchRoot(
            base_dir=repo_root / "src",
            allowed_prefix=Path("src") / parts[1],
            package_prefix=(parts[1],),
        )

    if parts[0] == "amplifier-bundle" and len(parts) >= 3 and parts[1] == "modules":
        root = Path("amplifier-bundle") / "modules" / parts[2]
        return SearchRoot(
            base_dir=repo_root / root,
            allowed_prefix=root,
        )

    if parts[0] == "amplifier-bundle" and len(parts) >= 2:
        root = Path("amplifier-bundle") / parts[1]
        return SearchRoot(
            base_dir=repo_root / root,
            allowed_prefix=root,
        )

    if parts[0] == ".claude" and len(parts) >= 3 and parts[1] == "scenarios":
        root = Path(".claude") / "scenarios" / parts[2]
        return SearchRoot(
            base_dir=repo_root / root,
            allowed_prefix=root,
        )

    package_root = find_generic_package_root(repo_root, seed_path.parent)
    if package_root is not None:
        return package_root

    return SearchRoot(
        base_dir=repo_root / seed_path.parent,
        allowed_prefix=seed_path.parent,
    )


def parse_import_requests(file_path: Path) -> list[tuple[str, int, str, tuple[str, ...]]]:
    """Extract import requests from a Python file in source order."""
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return []

    requests: list[tuple[str, int, str, tuple[str, ...]]] = []

    class ImportCollector(ast.NodeVisitor):
        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                requests.append(("import", 0, alias.name, ()))
            self.generic_visit(node)

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            names = tuple(alias.name for alias in node.names)
            requests.append(("from", node.level, node.module or "", names))
            self.generic_visit(node)

    ImportCollector().visit(tree)
    return requests


@cache
def normalize_candidate(
    repo_root: Path, candidate: Path, search_roots: tuple[SearchRoot, ...]
) -> Path | None:
    """Return a normalized repo-relative candidate if it is inside an allowed root."""
    if not candidate.exists() or not candidate.is_file() or candidate.suffix != ".py":
        return None

    resolved_repo = repo_root.resolve()
    resolved_candidate = candidate.resolve()
    try:
        repo_relative = Path(resolved_candidate.relative_to(resolved_repo).as_posix())
    except ValueError:
        return None

    if not any(root.allows(repo_relative) for root in search_roots):
        return None

    return repo_relative


def module_candidates(base_dir: Path, module_parts: tuple[str, ...]) -> list[Path]:
    """Return file candidates for a dotted module under *base_dir*."""
    if not module_parts:
        return [base_dir / "__init__.py"]

    joined = base_dir.joinpath(*module_parts)
    return [joined.with_suffix(".py"), joined / "__init__.py"]


@cache
def resolve_absolute_module(
    repo_root: Path,
    module: str,
    search_roots: tuple[SearchRoot, ...],
) -> tuple[Path, ...]:
    """Resolve an absolute module import within the allowed roots."""
    module_parts = tuple(part for part in module.split(".") if part)
    if not module_parts:
        return ()

    resolved: list[Path] = []
    seen: set[str] = set()
    for root in search_roots:
        if root.package_prefix and module_parts[: len(root.package_prefix)] != root.package_prefix:
            continue
        for candidate in module_candidates(root.base_dir, module_parts):
            normalized = normalize_candidate(repo_root, candidate, search_roots)
            if normalized is None:
                continue
            key = normalized.as_posix()
            if key not in seen:
                seen.add(key)
                resolved.append(normalized)
    return tuple(resolved)


@cache
def resolve_relative_module(
    repo_root: Path,
    importing_file: Path,
    level: int,
    module: str,
    search_roots: tuple[SearchRoot, ...],
) -> tuple[Path, ...]:
    """Resolve a relative import within the allowed roots."""
    if level <= 0:
        return ()

    base_dir = (repo_root / importing_file).resolve().parent
    for _ in range(level - 1):
        base_dir = base_dir.parent

    module_parts = tuple(part for part in module.split(".") if part)
    resolved: list[Path] = []
    seen: set[str] = set()
    for candidate in module_candidates(base_dir, module_parts):
        normalized = normalize_candidate(repo_root, candidate, search_roots)
        if normalized is None:
            continue
        key = normalized.as_posix()
        if key not in seen:
            seen.add(key)
            resolved.append(normalized)
    return tuple(resolved)


def resolve_request_targets(
    repo_root: Path,
    importing_file: Path,
    request: tuple[str, int, str, tuple[str, ...]],
    search_roots: tuple[SearchRoot, ...],
) -> list[Path]:
    """Resolve one import request to repo-local Python files."""
    request_kind, level, module, names = request
    resolved: list[Path] = []
    seen: set[str] = set()

    def add_paths(paths: Iterable[Path]) -> None:
        for path in paths:
            key = path.as_posix()
            if key not in seen:
                seen.add(key)
                resolved.append(path)

    if request_kind == "import":
        add_paths(resolve_absolute_module(repo_root, module, search_roots))
        return resolved

    if level > 0:
        add_paths(resolve_relative_module(repo_root, importing_file, level, module, search_roots))
        if names and "*" not in names:
            for name in names:
                combined = f"{module}.{name}" if module else name
                add_paths(
                    resolve_relative_module(
                        repo_root, importing_file, level, combined, search_roots
                    )
                )
        return resolved

    if module:
        add_paths(resolve_absolute_module(repo_root, module, search_roots))

    if names and "*" not in names:
        for name in names:
            combined = f"{module}.{name}" if module else name
            add_paths(resolve_absolute_module(repo_root, combined, search_roots))

    return resolved


def expand_seed_dependencies(repo_root: Path, seed_files: list[Path]) -> list[Path]:
    """Expand repo-local Python dependencies without escaping the seed-derived roots."""
    search_roots: list[SearchRoot] = []
    seen_roots: set[tuple[str, str, tuple[str, ...] | None]] = set()
    for seed in seed_files:
        root = derive_search_root(repo_root, seed)
        root_key = (
            root.base_dir.resolve().as_posix(),
            root.allowed_prefix.as_posix(),
            root.package_prefix,
        )
        if root_key not in seen_roots:
            seen_roots.add(root_key)
            search_roots.append(root)

    resolved_roots = tuple(search_roots)
    scope: list[Path] = list(seed_files)
    seen_paths = {path.as_posix() for path in seed_files}
    pending = deque(seed_files)

    while pending:
        current = pending.popleft()
        current_requests = parse_import_requests(repo_root / current)
        current_candidates: set[str] = set()
        for request in current_requests:
            for candidate in resolve_request_targets(repo_root, current, request, resolved_roots):
                key = candidate.as_posix()
                if key in current_candidates or key in seen_paths:
                    continue
                current_candidates.add(key)
                seen_paths.add(key)
                scope.append(candidate)
                pending.append(candidate)

    return scope


def select_seed_files(
    manifest_entries: list[Path], *, exclude_claude_scenarios: bool
) -> list[Path]:
    """Return manifest .py seeds after applying Step-15 surface filters."""
    seed_files: list[Path] = []
    for entry in manifest_entries:
        if entry.suffix != ".py":
            continue
        if exclude_claude_scenarios and is_claude_scenario_path(entry):
            continue
        seed_files.append(entry)
    return seed_files


def main(argv: list[str] | None = None) -> int:
    """Build the scoped validation file list."""
    args = parse_args(argv)
    repo_root = Path(args.repo_root).resolve()

    try:
        manifest_entries = load_manifest(Path(args.manifest), repo_root)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    seed_files = select_seed_files(
        manifest_entries,
        exclude_claude_scenarios=args.exclude_claude_scenarios,
    )
    scoped_files = expand_seed_dependencies(repo_root, seed_files)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_text = "\n".join(path.as_posix() for path in scoped_files)
    if output_text:
        output_text += "\n"
    output_path.write_text(output_text, encoding="utf-8")

    counts = {
        "seed_count": len(seed_files),
        "expanded_local_dep_count": len(scoped_files) - len(seed_files),
        "validated_count": len(scoped_files),
    }
    print(json.dumps(counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
