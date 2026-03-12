# File: src/amplihack/resolve_bundle_asset.py
"""CLI module that resolves amplihack bundle assets to absolute paths.

Usage (from shell):
    python3 -m amplihack.resolve_bundle_asset amplifier-bundle/tools/orch_helper.py

Exit codes:
    0  — asset found; absolute path printed to stdout
    1  — asset not found after exhausting all fallbacks; actionable error on stderr
    2  — invalid/unsafe relative path (usage error); message on stderr

Resolution priority (first valid path wins):
    1. $AMPLIHACK_HOME/<relative-asset>
    2. <pkg_dir>/<relative-asset>          (installed package layout)
    3. <pkg_dir>.parent.parent/<relative-asset>  (editable install: src/amplihack/ → repo root)
    4. ~/.amplihack/<relative-asset>

Security:
    - Relative path must start with 'amplifier-bundle/'
    - No '..' components allowed
    - No absolute-path prefix
    - No null bytes
    - Output contains only alphanumeric + [-_./] characters (safe for unquoted bash use)

Platform:
    POSIX only. Backslashes in paths are rejected at the validation stage.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# Characters allowed in the output path (safe for unquoted bash usage).
_SAFE_OUTPUT_RE = re.compile(r"^[A-Za-z0-9_\-./]+$")

# Required prefix — prevents resolving secrets, .env files, etc.
_REQUIRED_PREFIX = "amplifier-bundle/"


def _validate_relative_path(relative_path: str) -> None:
    """Validate that *relative_path* is safe to resolve.

    Raises:
        ValueError: with a human-readable message if the path is unsafe or malformed.
    """
    if not relative_path:
        raise ValueError("Relative asset path must not be empty.")

    if "\x00" in relative_path:
        raise ValueError("Relative asset path must not contain null bytes.")

    # Reject backslashes (Windows paths are not supported).
    if "\\" in relative_path:
        raise ValueError(
            f"Backslashes are not allowed in asset paths (POSIX only): {relative_path!r}"
        )

    # Reject absolute paths.
    if relative_path.startswith("/") or relative_path.startswith("~"):
        raise ValueError(
            f"Asset path must be relative, not absolute: {relative_path!r}"
        )

    # Reject path traversal.
    parts = relative_path.split("/")
    if ".." in parts or "." in parts:
        raise ValueError(
            f"Path traversal components ('..', '.') are not allowed: {relative_path!r}"
        )

    # Enforce amplifier-bundle/ prefix.
    if not relative_path.startswith(_REQUIRED_PREFIX):
        raise ValueError(
            f"Asset path must start with '{_REQUIRED_PREFIX}', got: {relative_path!r}"
        )


def resolve_asset(relative_path: str) -> Path:
    """Resolve *relative_path* to an absolute filesystem path.

    Tries four candidate locations in priority order and returns the first
    one where the asset exists (file or directory).

    Args:
        relative_path: A relative path starting with 'amplifier-bundle/'.
                       Must pass :func:`_validate_relative_path`.

    Returns:
        Absolute :class:`~pathlib.Path` to the asset.

    Raises:
        ValueError: If *relative_path* fails validation.
        FileNotFoundError: If no candidate location contains the asset.
    """
    _validate_relative_path(relative_path)

    candidates: list[Path] = []

    # Candidate 1: $AMPLIHACK_HOME env var.
    amplihack_home = os.environ.get("AMPLIHACK_HOME", "").strip()
    if amplihack_home:
        home_path = Path(amplihack_home)
        if home_path.is_dir():
            candidates.append(home_path / relative_path)
        else:
            # Env var is set but invalid — warn on stderr, do NOT use it.
            print(
                f"WARNING: AMPLIHACK_HOME is set but is not a valid directory, skipping.",
                file=sys.stderr,
            )

    # Candidate 2: Installed package layout.
    #   Path(__file__) is src/amplihack/resolve_bundle_asset.py in editable install,
    #   or <site-packages>/amplihack/resolve_bundle_asset.py in a wheel install.
    pkg_dir = Path(__file__).resolve().parent
    candidates.append(pkg_dir / relative_path)

    # Candidate 3: Editable install — pkg_dir is src/amplihack/, so .parent.parent
    #   steps up to the repo root that contains amplifier-bundle/.
    candidates.append(pkg_dir.parent.parent / relative_path)

    # Candidate 4: ~/.amplihack installation.
    candidates.append(Path.home() / ".amplihack" / relative_path)

    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.exists():
            return resolved

    # Construct a human-readable list of tried paths for the error message.
    tried = "\n  ".join(str(c) for c in candidates)
    raise FileNotFoundError(
        f"Asset not found: {relative_path!r}\n"
        f"Tried:\n  {tried}\n"
        f"Set AMPLIHACK_HOME to your amplihack installation root."
    )


def _main(argv: list[str]) -> int:
    """Entry point for ``python3 -m amplihack.resolve_bundle_asset``.

    Args:
        argv: sys.argv (including the module name at argv[0]).

    Returns:
        Exit code: 0 (success), 1 (not found), 2 (invalid input).
    """
    if len(argv) != 2:
        print(
            "Usage: python3 -m amplihack.resolve_bundle_asset <relative-asset-path>",
            file=sys.stderr,
        )
        print(
            "Example: python3 -m amplihack.resolve_bundle_asset "
            "amplifier-bundle/tools/orch_helper.py",
            file=sys.stderr,
        )
        return 2

    relative_path = argv[1]

    try:
        _validate_relative_path(relative_path)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print(
            "Usage: python3 -m amplihack.resolve_bundle_asset <relative-asset-path>",
            file=sys.stderr,
        )
        return 2

    try:
        resolved = resolve_asset(relative_path)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    abs_path = str(resolved)

    # Safety check: output must be safe for unquoted bash use.
    if not _SAFE_OUTPUT_RE.match(abs_path):
        print(
            f"ERROR: Resolved path contains characters unsafe for shell use: {abs_path!r}",
            file=sys.stderr,
        )
        return 1

    print(abs_path)
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
