#!/usr/bin/env python3
"""Detect drift between triplicated skill and agent files, and verify hooks symlink.

Skills and agents exist in up to 3 locations that must stay in sync:
  1. .claude/skills/ and .claude/agents/amplihack/ (source of truth)
  2. amplifier-bundle/skills/ and amplifier-bundle/agents/ (distribution)
  3. docs/claude/skills/ and docs/claude/agents/ (documentation, optional)

Hooks: .claude/tools/amplihack/hooks/ is the canonical source of truth.
  amplifier-bundle/tools/amplihack/hooks is a symlink to the canonical location.
  This script verifies the symlink is intact.

This script compares checksums between these locations and reports any drift.

Severity levels:
  - MISSING/EXTRA: printed as warnings, do NOT cause exit 1 (intentional structural differences)
  - CHANGED: printed as errors, cause exit 1 (content drift must be fixed)
  - SYMLINK BROKEN: printed as error, causes exit 1 (hooks symlink must point to .claude/)

References: https://github.com/microsoft/amplihack/issues/2820
            https://github.com/microsoft/amplihack/issues/2845
"""

import hashlib
import sys
from pathlib import Path

# Files to skip when comparing directories
SKIP_PATTERNS = {"__pycache__", "*.pyc"}


def should_skip(path: Path) -> bool:
    """Return True if this path should be excluded from comparison."""
    for part in path.parts:
        if part == "__pycache__":
            return True
    if path.suffix == ".pyc":
        return True
    return False


def file_checksum(path: Path) -> str:
    """Return SHA-256 hex digest of a file's contents."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def collect_files(directory: Path) -> dict[str, Path]:
    """Collect all non-skipped files under directory, keyed by relative path."""
    files = {}
    if not directory.is_dir():
        return files
    for path in sorted(directory.rglob("*")):
        if path.is_file() and not should_skip(path):
            rel = str(path.relative_to(directory))
            files[rel] = path
    return files


def compare_directories(
    source_dir: Path,
    target_dir: Path,
    source_label: str,
    target_label: str,
) -> tuple[list[str], list[str]]:
    """Compare two directories and return (warnings, errors).

    source_dir is treated as the source of truth.

    Returns:
        warnings: MISSING and EXTRA files (structural differences, not failures)
        errors: CHANGED files (content drift, causes exit 1)
    """
    warnings: list[str] = []
    errors: list[str] = []

    if not source_dir.is_dir():
        return warnings, errors

    if not target_dir.is_dir():
        # Target doesn't exist at all -- not an error if it's optional (docs)
        return warnings, errors

    source_files = collect_files(source_dir)
    target_files = collect_files(target_dir)

    source_keys = set(source_files.keys())
    target_keys = set(target_files.keys())

    # Files only in source (missing from target) -- structural difference, warn only
    for rel in sorted(source_keys - target_keys):
        warnings.append(f"  MISSING in {target_label}: {rel}")

    # Files only in target (extra in target) -- structural difference, warn only
    for rel in sorted(target_keys - source_keys):
        warnings.append(f"  EXTRA in {target_label}: {rel}")

    # Files in both -- compare checksums (content drift is an error)
    for rel in sorted(source_keys & target_keys):
        src_hash = file_checksum(source_files[rel])
        tgt_hash = file_checksum(target_files[rel])
        if src_hash != tgt_hash:
            errors.append(f"  CHANGED: {rel}")

    return warnings, errors


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    all_warnings: list[tuple[str, list[str]]] = []
    all_errors: list[tuple[str, list[str]]] = []

    # --- Skills ---
    skills_source = repo_root / ".claude" / "skills"
    skills_bundle = repo_root / "amplifier-bundle" / "skills"
    skills_docs = repo_root / "docs" / "claude" / "skills"

    warnings, errors = compare_directories(
        skills_source, skills_bundle, ".claude/skills", "amplifier-bundle/skills"
    )
    if warnings:
        all_warnings.append((".claude/skills vs amplifier-bundle/skills", warnings))
    if errors:
        all_errors.append((".claude/skills vs amplifier-bundle/skills", errors))

    warnings, errors = compare_directories(
        skills_source, skills_docs, ".claude/skills", "docs/claude/skills"
    )
    if warnings:
        all_warnings.append((".claude/skills vs docs/claude/skills", warnings))
    if errors:
        all_errors.append((".claude/skills vs docs/claude/skills", errors))

    # --- Agents ---
    agents_source = repo_root / ".claude" / "agents"
    agents_bundle = repo_root / "amplifier-bundle" / "agents"

    warnings, errors = compare_directories(
        agents_source, agents_bundle, ".claude/agents", "amplifier-bundle/agents"
    )
    if warnings:
        all_warnings.append((".claude/agents vs amplifier-bundle/agents", warnings))
    if errors:
        all_errors.append((".claude/agents vs amplifier-bundle/agents", errors))

    # --- Hooks symlink verification ---
    hooks_symlink = repo_root / "amplifier-bundle" / "tools" / "amplihack" / "hooks"
    hooks_canonical = repo_root / ".claude" / "tools" / "amplihack" / "hooks"
    expected_target = "../../../.claude/tools/amplihack/hooks"

    if hooks_symlink.is_symlink():
        actual_target = str(hooks_symlink.readlink())
        if actual_target != expected_target:
            all_errors.append((
                "hooks symlink target",
                [f"  Expected: {expected_target}", f"  Actual: {actual_target}"],
            ))
        elif not hooks_symlink.resolve().is_dir():
            all_errors.append((
                "hooks symlink resolution",
                [f"  Symlink exists but target does not resolve to a directory"],
            ))
        else:
            print("Hooks symlink OK: amplifier-bundle/tools/amplihack/hooks -> .claude/tools/amplihack/hooks")
    elif hooks_symlink.is_dir():
        # Directory exists instead of symlink -- drift has occurred
        all_errors.append((
            "hooks symlink missing",
            [
                "  amplifier-bundle/tools/amplihack/hooks/ is a directory, not a symlink.",
                "  It should be a symlink to ../../../.claude/tools/amplihack/hooks",
                "  Run: rm -rf amplifier-bundle/tools/amplihack/hooks && "
                "ln -s ../../../.claude/tools/amplihack/hooks amplifier-bundle/tools/amplihack/hooks",
            ],
        ))
    elif not hooks_symlink.exists():
        all_errors.append((
            "hooks symlink missing",
            [f"  amplifier-bundle/tools/amplihack/hooks does not exist at all"],
        ))

    # --- Report warnings (MISSING/EXTRA) ---
    if all_warnings:
        total_warnings = sum(len(items) for _, items in all_warnings)
        print(f"WARNING: {total_warnings} structural difference(s) found (MISSING/EXTRA).")
        print("These are intentional and do not cause failure.\n")
        for header, items in all_warnings:
            print(f"[{header}]")
            for item in items:
                print(item)
            print()

    # --- Report errors (CHANGED) ---
    if all_errors:
        total_errors = sum(len(items) for _, items in all_errors)
        print(f"ERROR: {total_errors} file(s) have content drift (CHANGED). These must be fixed.\n")
        for header, items in all_errors:
            print(f"[{header}]")
            for item in items:
                print(item)
            print()
        print(
            "Source of truth is .claude/skills/, .claude/agents/, and .claude/tools/amplihack/hooks/. "
            "Copy changed files to the other locations to fix."
        )
        return 1

    if not all_warnings and not all_errors:
        print("No drift detected. All locations are in sync.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
