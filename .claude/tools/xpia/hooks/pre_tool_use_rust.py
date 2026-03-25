#!/usr/bin/env python3
"""Compatibility shim for the canonical Rust-backed XPIA pre-tool hook.

Historically this repo carried two files with inverted meanings:
``pre_tool_use.py`` became the real Rust-backed bridge, while
``pre_tool_use_rust.py`` kept an older regex implementation. Keep the
legacy filename for compatibility, but execute the canonical hook so both
entry points enforce the same Rust-backed behavior.
"""

from __future__ import annotations

import runpy
from pathlib import Path

CANONICAL_HOOK = Path(__file__).with_name("pre_tool_use.py")


def main() -> None:
    runpy.run_path(str(CANONICAL_HOOK), run_name="__main__")


if __name__ == "__main__":
    main()
