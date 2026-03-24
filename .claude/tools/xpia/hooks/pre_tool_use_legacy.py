#!/usr/bin/env python3
"""Legacy compatibility shim for the canonical XPIA pre-tool hook.

R4: renamed from ``pre_tool_use_rust.py`` — the old name was misleading
because the file is a Python shim, not a Rust implementation.  The new
name ``pre_tool_use_legacy.py`` clarifies its role as a compatibility
entry point that delegates to the canonical ``pre_tool_use.py``.
"""

from __future__ import annotations

import runpy
from pathlib import Path

CANONICAL_HOOK = Path(__file__).with_name("pre_tool_use.py")


def main() -> None:
    runpy.run_path(str(CANONICAL_HOOK), run_name="__main__")


if __name__ == "__main__":
    main()
