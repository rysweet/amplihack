"""Pytest configuration for outside-in tests.

Adds .claude/tools to sys.path so tests can import the remote module.
"""
import sys
from pathlib import Path

# Add .claude/tools to path so amplihack.remote is importable
_tools_path = str(Path(__file__).parent.parent.parent / ".claude" / "tools")
if _tools_path not in sys.path:
    sys.path.insert(0, _tools_path)
