"""Resolve amplihack bundle assets to absolute paths.

Philosophy:
- Single responsibility: Locate amplifier-bundle assets regardless of CWD
- Self-contained: No dependencies outside the standard library
- Regeneratable: Can be rebuilt from specification

Public API (the "studs"):
    resolve_asset: Resolve a bundle-relative path to an absolute Path
    _validate_relative_path: Validate path safety (exported for tests)

CLI Usage:
    python3 -m amplihack.resolve_bundle_asset <relative-path>

Exit codes:
    0 — Success; absolute path printed to stdout
    1 — Asset not found in any search location
    2 — Invalid input (path traversal, missing prefix, bad chars)
"""

import os
import re
import sys
from pathlib import Path

# Module-level constants — computed once at import, never per-call.
_PKG_DIR: Path = Path(__file__).resolve().parent
_HOME_AMPLIHACK: Path = Path.home() / ".amplihack"

# Allowlist: alphanumeric, hyphen, underscore, dot, forward-slash.
_SAFE_PATH_RE = re.compile(r"^[A-Za-z0-9_\-./]+$")


def _validate_relative_path(relative_path: str) -> None:
    """Validate that *relative_path* is safe and well-formed.

    Args:
        relative_path: The path string to validate.

    Raises:
        ValueError: If the path is empty, absolute, contains ``..``,
            lacks the required ``amplifier-bundle/`` prefix, or contains
            unsafe characters.
    """
    if not relative_path:
        raise ValueError("Relative path must not be empty.")

    if relative_path.startswith("/") or relative_path.startswith("~"):
        raise ValueError(f"Path must be relative, not absolute: {relative_path!r}")

    # Reject any path component equal to ".." to block traversal.
    if ".." in relative_path.split("/"):
        raise ValueError(f"Path traversal not allowed: {relative_path!r}")

    if not relative_path.startswith("amplifier-bundle/"):
        raise ValueError(f"Path must start with 'amplifier-bundle/': {relative_path!r}")

    if not _SAFE_PATH_RE.match(relative_path):
        raise ValueError(
            f"Path contains unsafe characters (allowed: A-Z a-z 0-9 _ - . /): {relative_path!r}"
        )


def resolve_asset(relative_path: str) -> Path:
    """Resolve a bundle asset to an absolute path.

    Searches candidate locations in priority order:

    1. ``$AMPLIHACK_HOME/<relative_path>`` — explicit environment override
    2. ``<pkg_dir>/<relative_path>`` — installed package (amplifier-bundle
       is copied as package data by build_hooks.py)
    3. ``<pkg_dir>.parent.parent/<relative_path>`` — editable install
       (``src/amplihack/`` → repo root has ``amplifier-bundle/``)
    4. ``~/.amplihack/<relative_path>`` — user home installation

    Args:
        relative_path: Bundle-relative path, e.g.
            ``"amplifier-bundle/tools/orch_helper.py"``.
            Must start with ``amplifier-bundle/``.

    Returns:
        Canonicalised absolute :class:`~pathlib.Path` of the first
        candidate that exists.

    Raises:
        ValueError: If *relative_path* fails safety validation.
        FileNotFoundError: If no candidate location contains the asset.
    """
    _validate_relative_path(relative_path)

    candidates: list[Path] = []

    # 1. Explicit override via $AMPLIHACK_HOME.
    amplihack_home = os.environ.get("AMPLIHACK_HOME", "").strip()
    if amplihack_home:
        home_path = Path(amplihack_home)
        if home_path.is_dir():
            candidates.append(home_path / relative_path)
        else:
            # Print variable name only — never the value — to avoid leaking paths.
            print(
                "WARNING: AMPLIHACK_HOME is set but is not a directory; "
                "falling back to other search locations.",
                file=sys.stderr,
            )

    # 2. Installed package: amplifier-bundle/ is package data adjacent to this file.
    candidates.append(_PKG_DIR / relative_path)

    # 3. Editable install: this file is src/amplihack/resolve_bundle_asset.py,
    #    so the repo root (which contains amplifier-bundle/) is two levels up.
    candidates.append(_PKG_DIR.parent.parent / relative_path)

    # 4. User home installation.
    candidates.append(_HOME_AMPLIHACK / relative_path)

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    raise FileNotFoundError(
        f"Bundle asset not found: {relative_path}\n"
        "Set AMPLIHACK_HOME to your amplihack installation root."
    )


def _main(argv: list[str]) -> int:
    """CLI entry point for ``python3 -m amplihack.resolve_bundle_asset``.

    Args:
        argv: Argument list (typically ``sys.argv``); expects exactly two
            elements: the module name and the relative asset path.

    Returns:
        Exit code: 0 on success, 1 if asset not found, 2 for invalid input.
    """
    if len(argv) != 2:
        print(
            "Usage: python3 -m amplihack.resolve_bundle_asset <relative-path>",
            file=sys.stderr,
        )
        print(
            "  <relative-path> must start with 'amplifier-bundle/'",
            file=sys.stderr,
        )
        return 2

    relative_path = argv[1]

    try:
        resolved = resolve_asset(relative_path)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(resolved)
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
