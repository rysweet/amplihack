#!/usr/bin/env python3
"""Detect drift between triplicated skill and agent files.

Skills and agents exist in up to 3 locations that must stay in sync:
  1. .claude/skills/ and .claude/agents/amplihack/ (source of truth)
  2. amplifier-bundle/skills/ and amplifier-bundle/agents/ (distribution)
  3. docs/claude/skills/ and docs/claude/agents/ (documentation, optional)

This script compares checksums between these locations and reports drift.

Severity levels:
  CHANGED  -- same file exists in both locations but content differs (ERROR by default)
  MISSING  -- file exists in source but not in target (WARNING by default)
  EXTRA    -- file exists in target but not in source (WARNING by default)

Exit codes:
  0 -- no drift, or only MISSING/EXTRA drift in default mode
  1 -- CHANGED files detected (always), or any drift in --strict mode

Use --strict to fail on ALL drift types (MISSING + EXTRA + CHANGED).

References: https://github.com/microsoft/amplihack/issues/2820
"""

import argparse
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
) -> tuple[list[str], list[str], list[str]]:
    """Compare two directories and return (missing, extra, changed) drift lists.

    source_dir is treated as the source of truth.
    Returns three lists:
      missing -- files in source but not in target
      extra   -- files in target but not in source
      changed -- files in both with differing content
    """
    missing: list[str] = []
    extra: list[str] = []
    changed: list[str] = []

    if not source_dir.is_dir():
        return missing, extra, changed

    if not target_dir.is_dir():
        # Target doesn't exist at all -- not an error if it's optional (docs)
        return missing, extra, changed

    source_files = collect_files(source_dir)
    target_files = collect_files(target_dir)

    source_keys = set(source_files.keys())
    target_keys = set(target_files.keys())

    # Files only in source (missing from target)
    for rel in sorted(source_keys - target_keys):
        missing.append(f"  MISSING in {target_label}: {rel}")

    # Files only in target (extra in target)
    for rel in sorted(target_keys - source_keys):
        extra.append(f"  EXTRA in {target_label}: {rel}")

    # Files in both -- compare checksums
    for rel in sorted(source_keys & target_keys):
        src_hash = file_checksum(source_files[rel])
        tgt_hash = file_checksum(target_files[rel])
        if src_hash != tgt_hash:
            changed.append(f"  CHANGED: {rel}")

    return missing, extra, changed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect drift between triplicated skill/agent files."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Fail (exit 1) on ALL drift types: MISSING, EXTRA, and CHANGED. "
            "By default only CHANGED files cause failure."
        ),
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent

    # Collect results per comparison group: (header, missing, extra, changed)
    groups: list[tuple[str, list[str], list[str], list[str]]] = []

    # --- Skills ---
    skills_source = repo_root / ".claude" / "skills"
    skills_bundle = repo_root / "amplifier-bundle" / "skills"
    skills_docs = repo_root / "docs" / "claude" / "skills"

    missing, extra, changed = compare_directories(
        skills_source, skills_bundle, ".claude/skills", "amplifier-bundle/skills"
    )
    if missing or extra or changed:
        groups.append((".claude/skills vs amplifier-bundle/skills", missing, extra, changed))

    missing, extra, changed = compare_directories(
        skills_source, skills_docs, ".claude/skills", "docs/claude/skills"
    )
    if missing or extra or changed:
        groups.append((".claude/skills vs docs/claude/skills", missing, extra, changed))

    # --- Agents ---
    agents_source = repo_root / ".claude" / "agents"
    agents_bundle = repo_root / "amplifier-bundle" / "agents"

    missing, extra, changed = compare_directories(
        agents_source, agents_bundle, ".claude/agents", "amplifier-bundle/agents"
    )
    if missing or extra or changed:
        groups.append((".claude/agents vs amplifier-bundle/agents", missing, extra, changed))

    # --- Report ---
    if not groups:
        print("No drift detected. All locations are in sync.")
        return 0

    total_missing = sum(len(m) for _, m, _, _ in groups)
    total_extra = sum(len(e) for _, _, e, _ in groups)
    total_changed = sum(len(c) for _, _, _, c in groups)

    # Determine if we have errors (things that fail CI)
    has_errors = total_changed > 0
    if args.strict:
        has_errors = has_errors or total_missing > 0 or total_extra > 0

    # Print report
    for header, missing, extra, changed in groups:
        section_items = missing + extra + changed
        if not section_items:
            continue
        print(f"[{header}]")
        for item in missing + extra:
            print(f"WARNING: {item.strip()}")
        for item in changed:
            print(f"ERROR:   {item.strip()}")
        print()

    # Summary
    warning_count = total_missing + total_extra
    if warning_count > 0:
        warning_label = "MISSING/EXTRA" if args.strict else "MISSING/EXTRA (warnings)"
        print(f"Warnings: {warning_count} file(s) with {warning_label} drift.")
    if total_changed > 0:
        print(f"Errors:   {total_changed} file(s) with CHANGED (content) drift.")

    print()
    if has_errors:
        if args.strict and total_changed == 0:
            print(
                "FAILURE (--strict): MISSING/EXTRA drift detected. "
                "Source of truth is .claude/skills/ and .claude/agents/."
            )
        else:
            print(
                "FAILURE: CHANGED files detected — content differs between source and target. "
                "Copy changed files from .claude/ (source of truth) to the other locations to fix."
            )
        return 1
    else:
        if warning_count > 0:
            print(
                "WARNING: MISSING/EXTRA files detected (informational only). "
                "Not all skills are bundled — this is expected. "
                "Use --strict to fail on MISSING/EXTRA drift."
            )
        return 0


if __name__ == "__main__":
    sys.exit(main())
