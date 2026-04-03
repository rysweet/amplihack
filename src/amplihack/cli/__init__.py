"""CLI package for amplihack. Re-exports main from the sibling cli.py module."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_cli_module():
    """Load amplihack/cli.py directly since this package shadows it."""
    cli_py = Path(__file__).parent.parent / "cli.py"
    spec = importlib.util.spec_from_file_location("amplihack._cli_module", cli_py)
    mod = importlib.util.module_from_spec(spec)
    # Set the parent package so relative imports work
    mod.__package__ = "amplihack"
    spec.loader.exec_module(mod)
    return mod


_cli = _load_cli_module()
main = _cli.main

# Eagerly bind frequently-used public names so they appear in tab-completion
# and explicit imports (``from amplihack.cli import X``) work without the
# dynamic fallback below.
add_auto_mode_args = _cli.add_auto_mode_args
resolve_timeout = _cli.resolve_timeout
create_parser = _cli.create_parser


def __getattr__(name: str):
    """Forward any attribute lookup to the underlying cli.py module.

    This allows ``from amplihack.cli import X`` and
    ``mock.patch("amplihack.cli.X")`` to work for any name defined in
    cli.py without having to enumerate every function explicitly.
    """
    try:
        return getattr(_cli, name)
    except AttributeError:
        raise AttributeError(f"module 'amplihack.cli' has no attribute {name!r}") from None


__all__ = [
    "main",
    "add_auto_mode_args",
    "resolve_timeout",
    "create_parser",
]
