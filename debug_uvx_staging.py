#!/usr/bin/env python3
"""Debug script to test UVX staging and verify what's being staged."""

import os
import sys
from pathlib import Path


def debug_uvx_staging():
    print("=== UVX Staging Debug ===")
    print(f"Current working directory: {Path.cwd()}")
    print(f"Python executable: {sys.executable}")
    print(f"UV_PYTHON: {os.environ.get('UV_PYTHON', 'Not set')}")
    print(f"AMPLIHACK_ROOT: {os.environ.get('AMPLIHACK_ROOT', 'Not set')}")

    # Check if .claude directory exists
    claude_dir = Path.cwd() / ".claude"
    print(f"\n.claude directory exists: {claude_dir.exists()}")

    if claude_dir.exists():
        print("\n=== .claude directory contents ===")
        for item in claude_dir.rglob("*"):
            if item.is_file():
                print(f"FILE: {item}")
            elif item.is_dir():
                print(f"DIR:  {item}")

    # Check specific hook files
    hooks_to_check = [
        ".claude/tools/amplihack/hooks/post_tool_use.py",
        ".claude/tools/amplihack/hooks/stop.py",
        ".claude/tools/amplihack/hooks/session_start.py",
    ]

    print("\n=== Hook files check ===")
    for hook_path in hooks_to_check:
        full_path = Path.cwd() / hook_path
        exists = full_path.exists()
        print(f"{hook_path}: {'EXISTS' if exists else 'MISSING'}")
        if exists:
            print(f"  Size: {full_path.stat().st_size} bytes")
            print(f"  Executable: {os.access(full_path, os.X_OK)}")

    # Check agents directory
    agents_dir = Path.cwd() / ".claude" / "agents"
    print(f"\n.claude/agents directory exists: {agents_dir.exists()}")
    if agents_dir.exists():
        agent_files = list(agents_dir.rglob("*.md"))
        print(f"Found {len(agent_files)} agent files")
        for agent in agent_files[:5]:  # Show first 5
            print(f"  {agent}")

    # Test UVX detection
    print("\n=== UVX Detection ===")
    try:
        from src.amplihack.utils.uvx_staging import is_uvx_deployment

        print(f"is_uvx_deployment(): {is_uvx_deployment()}")
    except ImportError as e:
        print(f"Could not import UVX detection: {e}")

    # Test staging
    print("\n=== UVX Staging Test ===")
    try:
        from src.amplihack.utils.uvx_staging import stage_uvx_framework

        print("Attempting to stage framework...")
        result = stage_uvx_framework()
        print(f"Staging result: {result}")
    except ImportError as e:
        print(f"Could not import UVX staging: {e}")
    except Exception as e:
        print(f"Staging failed: {e}")


if __name__ == "__main__":
    debug_uvx_staging()
