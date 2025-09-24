#!/usr/bin/env python3
"""Session start hook for Claude Code.

This hook runs when a Claude Code session starts and handles:
1. Changing to the project root directory when in UVX mode
2. Setting up the environment for proper framework access
"""

import os
import sys
from pathlib import Path


def main():
    """Main entry point for session start hook."""
    # Check if AMPLIHACK_PROJECT_ROOT is set (indicates UVX mode with --add-dir)
    project_root = os.environ.get("AMPLIHACK_PROJECT_ROOT")

    if project_root:
        project_path = Path(project_root)

        # Verify the path exists and is a directory
        if project_path.exists() and project_path.is_dir():
            try:
                # Change to the project root directory
                os.chdir(project_path)
                print(f"[Session Hook] Changed directory to project root: {project_path}")

                # Verify .claude directory exists
                claude_dir = project_path / ".claude"
                if claude_dir.exists():
                    print(f"[Session Hook] Verified .claude directory at: {claude_dir}")
                else:
                    print(f"[Session Hook] Warning: .claude directory not found at {claude_dir}")

            except Exception as e:
                # More graceful error handling - warn but don't fail
                print(
                    f"[Session Hook] Warning: Could not change to project root: {e}",
                    file=sys.stderr,
                )
                print("[Session Hook] Continuing with current directory", file=sys.stderr)
                # Don't return error code - allow session to continue
                return 0
        else:
            print(
                f"[Session Hook] Warning: Project root does not exist or is not a directory: {project_root}",
                file=sys.stderr,
            )
            return 1
    else:
        # Not in UVX mode or no project root set
        print("[Session Hook] Not in UVX mode, no directory change needed")

    return 0


if __name__ == "__main__":
    sys.exit(main())
