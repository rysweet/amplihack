"""Resolve amplihack bundle assets to absolute paths.

Philosophy:
- Single responsibility: Locate amplifier-bundle assets regardless of CWD
- Self-contained: No dependencies outside the standard library
- Regeneratable: Can be rebuilt from specification

Public API (the "studs"):
    resolve_asset: Resolve a bundle-relative path to an absolute Path
    _validate_relative_path: Validate path safety (exported for tests)
    _safe_join: Containment-checked path join (exported for tests, SR-004)

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

    Validation order is security-significant:

    1. Null byte rejection (SR-003) — must be first; catches injection before
       any other check can be confused by embedded terminators.
    2. Empty string check.
    3. Absolute / home-relative path check.
    4. Segment-level traversal check (SR-001) — rejects any segment that is
       exactly ``..`` (path traversal) or ``.`` (no-op, blurs boundary check).
       Filenames that merely *start* with ``..`` (e.g. ``..hidden``) are allowed.
    5. ``amplifier-bundle/`` prefix enforcement.
    6. Character allowlist (regex) — defense-in-depth for any remaining edge
       cases not caught by the structural checks above.

    Args:
        relative_path: The path string to validate.

    Raises:
        ValueError: If the path contains a null byte, is empty, is absolute,
            contains a ``..`` or ``.`` segment, lacks the required
            ``amplifier-bundle/`` prefix, or contains unsafe characters.
    """
    # SR-003: Null byte must be caught as the very first check.
    if "\x00" in relative_path:
        raise ValueError("Path must not contain null bytes.")

    if not relative_path:
        raise ValueError("Relative path must not be empty.")

    if relative_path.startswith("/") or relative_path.startswith("~"):
        raise ValueError(f"Path must be relative, not absolute: {relative_path!r}")

    # SR-001: Reject any segment that is exactly '..' or '.'.
    # Note: filenames like '..hidden' are NOT rejected — only exact matches.
    for segment in relative_path.split("/"):
        if segment == ".." or segment == ".":
            raise ValueError(f"Path segments '.' and '..' are not allowed: {relative_path!r}")

    if not relative_path.startswith("amplifier-bundle/"):
        raise ValueError(f"Path must start with 'amplifier-bundle/': {relative_path!r}")

    if not _SAFE_PATH_RE.match(relative_path):
        raise ValueError(
            f"Path contains unsafe characters (allowed: A-Z a-z 0-9 _ - . /): {relative_path!r}"
        )


def _safe_join(base: Path, relative: str) -> "Path | None":
    """Join *base* and *relative* with a containment check (SR-004).

    Uses ``Path.resolve()`` to follow symlinks and then verifies the resolved
    candidate remains inside *base*.  Returns ``None`` if the path escapes
    (e.g., via a symlink pointing outside the base, or via path traversal).

    This is a defence-in-depth measure.  ``_validate_relative_path`` should
    have already rejected overt traversal; ``_safe_join`` catches cases where
    a symlink inside the bundle directory points outside the search root.

    Args:
        base: The directory that must contain the resolved candidate.
        relative: A relative path string to join onto *base*.

    Returns:
        The resolved :class:`~pathlib.Path` if it is safely contained inside
        *base*, or ``None`` if it escapes the boundary.
    """
    try:
        candidate = (base / relative).resolve()
        candidate.relative_to(base.resolve())
        return candidate
    except ValueError:
        return None


def resolve_asset(relative_path: str) -> Path:
    """Resolve a bundle asset to an absolute path.

    Searches candidate locations in priority order:

    1. ``$AMPLIHACK_HOME/<relative_path>`` — explicit environment override
    2. ``<pkg_dir>/<relative_path>`` — installed package (amplifier-bundle
       is copied as package data by build_hooks.py)
    3. ``<pkg_dir>.parent.parent/<relative_path>`` — editable install
       (``src/amplihack/`` → repo root has ``amplifier-bundle/``)
    4. ``~/.amplihack/<relative_path>`` — user home installation

    Each candidate is checked via :func:`_safe_join` to ensure the resolved
    path does not escape the search root (SR-004 containment check).

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

    search_bases: list[Path] = []

    # 1. Explicit override via $AMPLIHACK_HOME.
    amplihack_home = os.environ.get("AMPLIHACK_HOME", "").strip()
    if amplihack_home:
        home_path = Path(amplihack_home)
        if home_path.is_dir():
            search_bases.append(home_path)
        else:
            # Print variable name only — never the value — to avoid leaking paths.
            print(
                "WARNING: AMPLIHACK_HOME is set but is not a directory; "
                "falling back to other search locations.",
                file=sys.stderr,
            )

    # 2. Installed package: amplifier-bundle/ is package data adjacent to this file.
    search_bases.append(_PKG_DIR)

    # 3. Editable install: this file is src/amplihack/resolve_bundle_asset.py,
    #    so the repo root (which contains amplifier-bundle/) is two levels up.
    search_bases.append(_PKG_DIR.parent.parent)

    # 4. User home installation.
    search_bases.append(_HOME_AMPLIHACK)

    for base in search_bases:
        candidate = _safe_join(base, relative_path)
        if candidate is not None and candidate.exists():
            return candidate

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
