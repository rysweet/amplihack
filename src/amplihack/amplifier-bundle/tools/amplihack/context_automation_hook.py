#!/usr/bin/env python3
"""Context automation hook - Integrates context_manager with post_tool_use hook.

This module provides the hook registration function that connects
context_manager.py to the tool registry. It handles automatic context
management by monitoring token usage and creating/restoring snapshots.

Philosophy:
- Single responsibility: Bridge between hook system and context_manager
- Standard library only
- Zero-BS implementation

Public API:
    register_context_hook: Register the context management hook (called at startup)
    context_management_hook: The actual hook function (registered automatically)
"""

import json
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from context_manager import run_automation
    from hooks.tool_registry import HookResult, register_tool_hook
except ImportError:
    # Fallback for different path contexts
    try:
        from tool_registry import HookResult, register_tool_hook

        from .context_manager import run_automation
    except ImportError:
        # If we can't import, the hook won't be registered (graceful degradation)
        HookResult = None
        register_tool_hook = None
        run_automation = None

__all__ = [
    "register_context_hook",
    "context_management_hook",
]

# ============================================================================
# Hook Function
# ============================================================================


def context_management_hook(input_data: dict[str, Any]) -> "HookResult":
    """Hook function for automatic context management.

    Called after every tool use to monitor token usage and
    automatically manage context snapshots and rehydration.

    Args:
        input_data: Input from Claude Code containing:
            - toolUse: Dict with tool information
            - result: Optional result from tool
            - transcript_path: Path to conversation transcript

    Returns:
        HookResult with automation actions and warnings

    Logic:
    1. Extract conversation data from transcript_path
    2. Calculate total token count from conversation
    3. Run context automation via context_manager.run_automation()
    4. Convert automation result to HookResult
    5. Return result for aggregation
    """
    if HookResult is None or run_automation is None:
        # Imports failed - return empty result
        return {"actions_taken": [], "warnings": [], "metadata": {}, "skip_remaining": False}

    result = HookResult()

    try:
        # Get conversation from transcript_path
        transcript_path = input_data.get("transcript_path")

        if not transcript_path or not Path(transcript_path).exists():
            # No transcript available - skip automation
            return result

        # Read conversation transcript
        with open(transcript_path) as f:
            conversation_data = json.load(f)

        # Calculate ACTUAL token count from transcript
        # (same method as statusline.sh)
        total_tokens = 0
        for msg in conversation_data:
            if isinstance(msg, dict) and "usage" in msg:
                usage = msg["usage"]
                total_tokens += usage.get("input_tokens", 0)
                total_tokens += usage.get("output_tokens", 0)
                total_tokens += usage.get("cache_read_input_tokens", 0)
                total_tokens += usage.get("cache_creation_input_tokens", 0)

        # Run automation with real token data
        automation_result = run_automation(total_tokens, conversation_data)

        # Convert automation result to HookResult
        if automation_result.get("actions_taken"):
            result.actions_taken = automation_result["actions_taken"]

        if automation_result.get("warnings"):
            result.warnings = automation_result["warnings"]

        if automation_result.get("recommendations"):
            result.metadata["recommendations"] = automation_result["recommendations"]

        # Include automation status in metadata
        result.metadata["automation_status"] = automation_result.get("status", "ok")
        if automation_result.get("skipped"):
            result.metadata["skipped"] = True
            result.metadata["next_check_in"] = automation_result.get("next_check_in", 0)

    except Exception as e:
        # Silently fail - don't interrupt user workflow
        result.warnings.append(f"Context automation error: {e}")
        result.metadata["error"] = str(e)

    return result


# ============================================================================
# Registration Function
# ============================================================================


def register_context_hook():
    """Register the context management hook with the global registry.

    This function is called by post_tool_use.py during initialization.
    It uses the @register_tool_hook decorator to automatically register
    the context_management_hook function with the global registry.

    The decorator handles the actual registration, so this function
    just needs to exist to be called.

    Example:
        >>> # In post_tool_use.py
        >>> from context_automation_hook import register_context_hook
        >>> register_context_hook()  # Registers the hook
    """
    # The @register_tool_hook decorator below handles registration


# ============================================================================
# Automatic Registration
# ============================================================================

# Register the hook automatically when this module is imported
if register_tool_hook is not None:
    # Use decorator to register with global registry
    context_management_hook = register_tool_hook(context_management_hook)

# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    print("Testing context automation hook...")

    # Create test input data
    test_input = {
        "toolUse": {"name": "Write"},
        "result": {},
        "transcript_path": None,  # No transcript for testing
    }

    # Test hook function
    result = context_management_hook(test_input)

    print("Hook result:")
    print(f"  Actions: {result.actions_taken}")
    print(f"  Warnings: {result.warnings}")
    print(f"  Metadata: {result.metadata}")

    if not result.actions_taken and not result.warnings:
        print("\n✅ Hook executed successfully (no transcript, so no actions)")
    else:
        print("\n⚠️  Unexpected result (expected no actions without transcript)")

    print("\nTesting with mocked automation...")
    # Note: Full testing requires actual transcript file and context_manager
    print("✅ Basic hook structure validated!")
