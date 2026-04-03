"""CLI package for amplihack. Re-exports main from the sibling cli.py module."""

from __future__ import annotations

import ast
import importlib
import importlib.util
from pathlib import Path

_CLI_PY = Path(__file__).parent.parent / "cli.py"


def _load_cli_module():
    """Load amplihack/cli.py directly since this package shadows it."""
    spec = importlib.util.spec_from_file_location("amplihack._cli_module", _CLI_PY)
    assert spec is not None and spec.loader is not None, f"Cannot load spec for {_CLI_PY}"
    mod = importlib.util.module_from_spec(spec)
    # Set the parent package so relative imports work
    mod.__package__ = "amplihack"
    spec.loader.exec_module(mod)
    return mod


def _collect_cli_relative_imports() -> dict[str, tuple[str, str]]:
    """Map lazily imported names in cli.py to their relative import targets."""
    tree = ast.parse(_CLI_PY.read_text(), filename=str(_CLI_PY))
    imports: dict[str, tuple[str, str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.level < 1:
            continue
        module = "." * node.level + (node.module or "")
        for alias in node.names:
            if alias.name == "*":
                continue
            imports.setdefault(alias.asname or alias.name, (module, alias.name))
    return imports


_cli = _load_cli_module()
_RELATIVE_IMPORTS = _collect_cli_relative_imports()
main = _cli.main


class _LazyAttrProxy:
    """Callable proxy that resolves a lazily imported CLI helper on first use."""

    def __init__(self, module_name: str, attr_name: str):
        self._module_name = module_name
        self._attr_name = attr_name

    def _resolve(self):
        module = importlib.import_module(self._module_name, package=_cli.__package__)
        value = getattr(module, self._attr_name)
        globals()[self._attr_name] = value
        setattr(_cli, self._attr_name, value)
        return value

    def __call__(self, *args, **kwargs):
        return self._resolve()(*args, **kwargs)

    def __getattr__(self, name: str):
        return getattr(self._resolve(), name)

    def __repr__(self) -> str:
        return f"<lazy attr proxy for {self._module_name}:{self._attr_name}>"


# Eagerly bind frequently-used public names so they appear in tab-completion
# and explicit imports (``from amplihack.cli import X``) work without the
# dynamic fallback below.
add_auto_mode_args = _cli.add_auto_mode_args
create_parser = _cli.create_parser
AutoMode = _LazyAttrProxy(".launcher.auto_mode", "AutoMode")


def __getattr__(name: str):
    """Forward any attribute lookup to the underlying cli.py module.

    This allows ``from amplihack.cli import X`` and
    ``mock.patch("amplihack.cli.X")`` to work for cli.py globals plus
    names that cli.py imports lazily inside helper functions.
    """
    try:
        return getattr(_cli, name)
    except AttributeError:
        target = _RELATIVE_IMPORTS.get(name)
        if target is None:
            raise AttributeError(f"module 'amplihack.cli' has no attribute {name!r}") from None
        module_name, attr_name = target
        value = getattr(importlib.import_module(module_name, package=_cli.__package__), attr_name)
        globals()[name] = value
        return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_cli)) | set(_RELATIVE_IMPORTS))


__all__ = [
    "main",
    "add_auto_mode_args",
    "create_parser",
    "AutoMode",
]
