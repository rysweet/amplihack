"""Source-checkout import shim for running ``python`` from the repo root."""

from __future__ import annotations

from pathlib import Path

_SRC_PACKAGE_DIR = Path(__file__).resolve().parent.parent / "src" / "amplihack"
_SRC_INIT = _SRC_PACKAGE_DIR / "__init__.py"

__file__ = str(_SRC_INIT)
__path__ = [str(_SRC_PACKAGE_DIR)]

if __spec__ is not None:
    __spec__.origin = __file__
    __spec__.submodule_search_locations = __path__

exec(compile(_SRC_INIT.read_text(), __file__, "exec"), globals(), globals())
