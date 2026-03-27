"""Resolve runtime asset paths for installed and editable amplihack layouts."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable
from pathlib import Path

_ASSET_RELATIVE_PATHS: dict[str, tuple[str, ...]] = {
    "helper-path": ("amplifier-bundle/tools/orch_helper.py",),
    "session-tree-path": ("amplifier-bundle/tools/session_tree.py",),
    "hooks-dir": (
        ".claude/tools/amplihack/hooks",
        "amplifier-bundle/tools/amplihack/hooks",
    ),
}


def iter_runtime_roots() -> list[Path]:
    """Return candidate roots for bundled runtime assets."""
    roots: list[Path] = []

    env_root = os.environ.get("AMPLIHACK_HOME")
    if env_root:
        roots.append(Path(env_root).expanduser())

    roots.append(Path.home() / ".amplihack")

    package_root = Path(__file__).resolve().parent
    roots.append(package_root)

    repo_root = package_root.parent.parent
    roots.append(repo_root)

    roots.append(Path.cwd().resolve())

    unique_roots: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        resolved = root.resolve()
        if resolved not in seen and resolved.is_dir():
            seen.add(resolved)
            unique_roots.append(resolved)

    return unique_roots


def resolve_asset_path(asset_name: str, search_roots: Iterable[Path] | None = None) -> Path:
    """Resolve the first existing runtime asset path for the requested asset."""
    if asset_name not in _ASSET_RELATIVE_PATHS:
        valid = ", ".join(sorted(_ASSET_RELATIVE_PATHS))
        raise ValueError(f"Unknown asset {asset_name!r}. Expected one of: {valid}")

    roots = list(search_roots) if search_roots is not None else iter_runtime_roots()
    rel_paths = _ASSET_RELATIVE_PATHS[asset_name]

    for root in roots:
        base = Path(root).expanduser().resolve()
        for rel_path in rel_paths:
            candidate = base / rel_path
            if candidate.exists():
                return candidate

    attempted = ", ".join(str(Path(root).expanduser()) for root in roots)
    raise FileNotFoundError(
        f"Could not resolve {asset_name} from any runtime root. Checked: {attempted}"
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for recipe shell commands."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        valid = " | ".join(sorted(_ASSET_RELATIVE_PATHS))
        print(f"Usage: python -m amplihack.runtime_assets <{valid}>", file=sys.stderr)
        return 2

    try:
        print(resolve_asset_path(args[0]))
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
