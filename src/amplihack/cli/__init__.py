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

__all__ = ["main"]
