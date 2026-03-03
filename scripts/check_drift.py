#!/usr/bin/env python3
"""Detect drift between triplicated skill and agent files.

Skills and agents exist in up to 3 locations that must stay in sync:
  1. .claude/skills/ and .claude/agents/amplihack/ (source of truth)
  2. amplifier-bundle/skills/ and amplifier-bundle/agents/ (distribution)
  3. docs/claude/skills/ and docs/claude/agents/ (documentation, optional)

This script compares checksums between these locations and reports any drift.
Exits non-zero if drift is detected.

References: https://github.com/microsoft/amplihack/issues/2820
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
) -> list[str]:
    """Compare two directories and return a list of drift descriptions.

    source_dir is treated as the source of truth.
    """
    drifts = []

    if not source_dir.is_dir():
        return drifts

    if not target_dir.is_dir():
        # Target doesn't exist at all -- not an error if it's optional (docs)
        return drifts

    source_files = collect_files(source_dir)
    target_files = collect_files(target_dir)

    source_keys = set(source_files.keys())
    target_keys = set(target_files.keys())

    # Files only in source (missing from target)
    for rel in sorted(source_keys - target_keys):
        drifts.append(f"  MISSING in {target_label}: {rel}")

    # Files only in target (extra in target)
    for rel in sorted(target_keys - source_keys):
        drifts.append(f"  EXTRA in {target_label}: {rel}")

    # Files in both -- compare checksums
    for rel in sorted(source_keys & target_keys):
        src_hash = file_checksum(source_files[rel])
        tgt_hash = file_checksum(target_files[rel])
        if src_hash != tgt_hash:
            drifts.append(f"  CHANGED: {rel}")

    return drifts


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    all_drifts: list[tuple[str, list[str]]] = []

    # --- Skills ---
    skills_source = repo_root / ".claude" / "skills"
    skills_bundle = repo_root / "amplifier-bundle" / "skills"
    skills_docs = repo_root / "docs" / "claude" / "skills"

    drifts = compare_directories(
        skills_source, skills_bundle, ".claude/skills", "amplifier-bundle/skills"
    )
    if drifts:
        all_drifts.append(
            (".claude/skills vs amplifier-bundle/skills", drifts)
        )

    drifts = compare_directories(
        skills_source, skills_docs, ".claude/skills", "docs/claude/skills"
    )
    if drifts:
        all_drifts.append((".claude/skills vs docs/claude/skills", drifts))

    # --- Agents ---
    agents_source = repo_root / ".claude" / "agents"
    agents_bundle = repo_root / "amplifier-bundle" / "agents"

    drifts = compare_directories(
        agents_source, agents_bundle, ".claude/agents", "amplifier-bundle/agents"
    )
    if drifts:
        all_drifts.append(
            (".claude/agents vs amplifier-bundle/agents", drifts)
        )

    # --- Report ---
    if not all_drifts:
        print("No drift detected. All locations are in sync.")
        return 0

    print("Drift detected between the following locations:\n")
    for header, items in all_drifts:
        print(f"[{header}]")
        for item in items:
            print(item)
        print()

    total = sum(len(items) for _, items in all_drifts)
    print(f"Total: {total} file(s) out of sync.")
    print(
        "Source of truth is .claude/skills/ and .claude/agents/. "
        "Copy changed files to the other locations to fix."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
