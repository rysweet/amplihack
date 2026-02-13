#!/usr/bin/env python3
"""Blarify staleness detection hook for post tool use events.

Detects when code files are modified via Edit/Write tools and triggers
incremental reindexing if the index becomes stale.
"""

import sys
from pathlib import Path
from typing import Any

# Add hook directory to path
sys.path.insert(0, str(Path(__file__).parent / "hooks"))

# Import tool registry
try:
    from tool_registry import ToolHookResult, get_global_registry

    REGISTRY_AVAILABLE = True
except ImportError:
    REGISTRY_AVAILABLE = False

# Code file extensions that should trigger reindexing
CODE_FILE_EXTENSIONS = {
    ".py",  # Python
    ".js",
    ".jsx",  # JavaScript
    ".ts",
    ".tsx",  # TypeScript
    ".cs",  # C#
    ".go",  # Go
    ".rs",  # Rust
    ".c",
    ".h",  # C
    ".cpp",
    ".hpp",
    ".cc",
    ".cxx",  # C++
    ".java",  # Java
    ".php",  # PHP
    ".rb",  # Ruby
}


def is_code_file(file_path: str) -> bool:
    """Check if file is a code file that should trigger reindexing.

    Args:
        file_path: Path to file

    Returns:
        True if file is a code file
    """
    try:
        path = Path(file_path)
        return path.suffix in CODE_FILE_EXTENSIONS
    except Exception:
        return False


def handle_blarify_staleness(input_data: dict[str, Any]) -> ToolHookResult:
    """Handle blarify staleness detection after tool use.

    Args:
        input_data: Tool use input data

    Returns:
        ToolHookResult with any warnings or actions
    """
    tool_use = input_data.get("toolUse", {})
    tool_name = tool_use.get("name", "")

    # Only track Edit/Write/MultiEdit on code files
    if tool_name not in ["Edit", "Write", "MultiEdit"]:
        return ToolHookResult(handled=False)

    # Extract file path from tool input
    tool_input = tool_use.get("input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path or not is_code_file(file_path):
        return ToolHookResult(handled=False)

    # Check if this is a code file modification
    result = ToolHookResult(handled=True)
    result.metadata["code_file_modified"] = file_path

    try:
        # Import staleness detector (lazy import to avoid startup cost)
        import sys
        from pathlib import Path

        # Add src to path
        src_path = Path(__file__).parent.parent.parent.parent / "src"
        if src_path.exists():
            sys.path.insert(0, str(src_path))

        from amplihack.memory.kuzu.indexing.staleness_detector import check_index_status

        # Get project root (current working directory)
        project_path = Path.cwd()

        # Check index status
        status = check_index_status(project_path)

        # If index is now stale or missing, suggest reindexing
        if status.needs_indexing:
            result.metadata["blarify_index_stale"] = True
            result.metadata["blarify_reason"] = status.reason
            result.metadata["estimated_files"] = status.estimated_files

            # Add user-facing warning
            if status.reason == "missing":
                result.warnings.append(
                    "Code index is missing. Run blarify indexing to enable code-aware features."
                )
            elif status.reason == "stale":
                result.warnings.append(
                    f"Code index is stale (modified {status.estimated_files} files). "
                    "Consider running incremental reindexing."
                )

            # Log action taken
            result.actions_taken.append(f"Detected stale blarify index after modifying {file_path}")

            # FUTURE: Trigger automatic incremental reindexing
            # For now, just warn the user - they can manually trigger it
            # result.actions_taken.append("Triggered incremental reindexing in background")

    except ImportError as e:
        # Staleness detector not available - log once so user knows
        result.metadata["blarify_import_error"] = str(e)
    except Exception as e:
        # Log error but don't fail the hook
        result.metadata["blarify_check_error"] = str(e)

    return result


def register_blarify_staleness_hook():
    """Register blarify staleness hook with global registry."""
    if not REGISTRY_AVAILABLE:
        return

    registry = get_global_registry()
    registry.register_tool_hook(
        "blarify_staleness",
        handle_blarify_staleness,
        description="Check blarify index staleness after code file modifications",
    )
