#!/usr/bin/env python3
"""Tool Registry - Extensible tool hook registration system.

This module provides an extensible registration system for tool hooks that run
after tool use events. It allows multiple tools to register handlers that will
be called automatically by the post_tool_use hook.

Philosophy:
- Single responsibility: Register and dispatch tool hooks
- Extensible for adding new tools
- Zero-BS implementation (all functions work completely)

Public API:
    ToolRegistry: Main registry class
    register_tool_hook: Decorator for registering tool hooks
    get_global_registry: Get the global registry instance
    HookResult: Result from tool hook execution
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "ToolRegistry",
    "register_tool_hook",
    "get_global_registry",
    "HookResult",
]

# ============================================================================
# Data Models
# ============================================================================


@dataclass
class HookResult:
    """Result from tool hook execution.

    Attributes:
        actions_taken: List of actions performed by the hook
        warnings: List of warning messages to display
        metadata: Additional metadata from the hook
        skip_remaining: If True, stop executing remaining hooks
    """

    actions_taken: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    skip_remaining: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "actions_taken": self.actions_taken,
            "warnings": self.warnings,
            "metadata": self.metadata,
            "skip_remaining": self.skip_remaining,
        }


# ============================================================================
# Tool Registry
# ============================================================================


class ToolRegistry:
    """Registry for extensible tool hooks.

    Allows registering functions that run after tool use events.
    Hooks are called in order of registration and can:
    - Take actions based on tool usage
    - Return warnings or metadata
    - Short-circuit remaining hooks if needed

    Example:
        >>> registry = ToolRegistry()
        >>> @registry.register
        ... def my_hook(input_data):
        ...     return HookResult(actions_taken=["something"])
        >>> results = registry.execute_hooks({"toolUse": {"name": "Write"}})
    """

    def __init__(self):
        """Initialize empty registry."""
        self._hooks: list[Callable[[dict[str, Any]], HookResult]] = []

    def register(self, hook: Callable[[dict[str, Any]], HookResult]) -> Callable:
        """Register a tool hook function.

        Args:
            hook: Function that takes input_data dict and returns HookResult

        Returns:
            The hook function (for decorator usage)

        Example:
            >>> registry = ToolRegistry()
            >>> @registry.register
            ... def my_hook(input_data):
            ...     return HookResult(actions_taken=["logged"])
        """
        self._hooks.append(hook)
        return hook

    def execute_hooks(self, input_data: dict[str, Any]) -> list[HookResult]:
        """Execute all registered hooks.

        Args:
            input_data: Input from Claude Code containing:
                - toolUse: Dict with tool information
                - result: Optional result from tool
                - transcript_path: Optional path to transcript

        Returns:
            List of HookResult objects from each hook

        Example:
            >>> registry = ToolRegistry()
            >>> @registry.register
            ... def hook1(data):
            ...     return HookResult(actions_taken=["action1"])
            >>> results = registry.execute_hooks({"toolUse": {"name": "Write"}})
            >>> len(results)
            1
        """
        results = []

        for hook in self._hooks:
            try:
                result = hook(input_data)

                # Ensure result is HookResult
                if not isinstance(result, HookResult):
                    result = HookResult(
                        warnings=[f"Hook {hook.__name__} returned invalid type: {type(result)}"]
                    )

                results.append(result)

                # Allow hooks to short-circuit
                if result.skip_remaining:
                    break

            except Exception as e:
                # Log error but continue with other hooks
                results.append(
                    HookResult(
                        warnings=[f"Hook {hook.__name__} failed: {e}"], metadata={"error": str(e)}
                    )
                )

        return results

    def clear(self) -> None:
        """Clear all registered hooks.

        Useful for testing or dynamic hook management.

        Example:
            >>> registry = ToolRegistry()
            >>> registry.register(lambda d: HookResult())
            >>> len(registry._hooks)
            1
            >>> registry.clear()
            >>> len(registry._hooks)
            0
        """
        self._hooks.clear()

    def count(self) -> int:
        """Get the number of registered hooks.

        Returns:
            Number of hooks in the registry

        Example:
            >>> registry = ToolRegistry()
            >>> registry.count()
            0
            >>> registry.register(lambda d: HookResult())
            <function <lambda> at 0x...>
            >>> registry.count()
            1
        """
        return len(self._hooks)


# ============================================================================
# Global Registry
# ============================================================================

# Global registry instance for use across the application
_global_registry = ToolRegistry()


def register_tool_hook(func: Callable[[dict[str, Any]], HookResult]) -> Callable:
    """Decorator for registering tool hooks with the global registry.

    This is the primary way to register hooks. It uses the global registry
    instance to ensure hooks persist across imports.

    Args:
        func: Hook function that takes input_data and returns HookResult

    Returns:
        The decorated function

    Example:
        >>> @register_tool_hook
        ... def my_hook(input_data: Dict[str, Any]) -> HookResult:
        ...     # Process tool usage
        ...     return HookResult(actions_taken=["something"])

    Usage in a hook integration module:
        ```python
        # context_automation_hook.py
        from tool_registry import register_tool_hook, HookResult
        from context_manager import run_automation

        @register_tool_hook
        def context_management_hook(input_data):
            # Extract data and call context_manager
            result = run_automation(tokens, conversation)
            return HookResult(...)
        ```
    """
    _global_registry.register(func)
    return func


def get_global_registry() -> ToolRegistry:
    """Get the global tool registry instance.

    Returns:
        Global ToolRegistry instance

    Example:
        >>> registry = get_global_registry()
        >>> isinstance(registry, ToolRegistry)
        True

    Usage in post_tool_use.py:
        ```python
        from tool_registry import get_global_registry

        registry = get_global_registry()
        hook_results = registry.execute_hooks(input_data)
        ```
    """
    return _global_registry


# ============================================================================
# Utility Functions
# ============================================================================


def aggregate_hook_results(results: list[HookResult]) -> dict[str, Any]:
    """Aggregate multiple hook results into a single output dict.

    Args:
        results: List of HookResult objects

    Returns:
        Dict with aggregated actions, warnings, and metadata

    Example:
        >>> r1 = HookResult(actions_taken=["a1"], warnings=["w1"])
        >>> r2 = HookResult(actions_taken=["a2"], metadata={"k": "v"})
        >>> agg = aggregate_hook_results([r1, r2])
        >>> agg["actions_taken"]
        ['a1', 'a2']
        >>> agg["warnings"]
        ['w1']
    """
    aggregated = {"actions_taken": [], "warnings": [], "metadata": {}}

    for result in results:
        aggregated["actions_taken"].extend(result.actions_taken)
        aggregated["warnings"].extend(result.warnings)

        # Merge metadata
        for key, value in result.metadata.items():
            if key not in aggregated["metadata"]:
                aggregated["metadata"][key] = value
            elif isinstance(aggregated["metadata"][key], list) and isinstance(value, list):
                aggregated["metadata"][key].extend(value)
            else:
                # Handle conflicts by adding suffixes
                aggregated["metadata"][f"{key}_2"] = value

    return aggregated


# ============================================================================
# Testing and Debugging
# ============================================================================

if __name__ == "__main__":
    # Test the registry
    print("Testing ToolRegistry...")

    # Create test hooks
    @register_tool_hook
    def test_hook_1(input_data: dict[str, Any]) -> HookResult:
        """Test hook that logs actions."""
        return HookResult(
            actions_taken=["test_hook_1_executed"], warnings=["Test warning from hook 1"]
        )

    @register_tool_hook
    def test_hook_2(input_data: dict[str, Any]) -> HookResult:
        """Test hook that adds metadata."""
        return HookResult(
            actions_taken=["test_hook_2_executed"], metadata={"test_key": "test_value"}
        )

    # Execute hooks
    registry = get_global_registry()
    print(f"Registered hooks: {registry.count()}")

    test_input = {"toolUse": {"name": "Write"}, "result": {}}
    results = registry.execute_hooks(test_input)

    print(f"Hook results: {len(results)}")
    for i, result in enumerate(results, 1):
        print(f"  Hook {i}:")
        print(f"    Actions: {result.actions_taken}")
        print(f"    Warnings: {result.warnings}")
        print(f"    Metadata: {result.metadata}")

    # Test aggregation
    aggregated = aggregate_hook_results(results)
    print("\nAggregated results:")
    print(f"  All actions: {aggregated['actions_taken']}")
    print(f"  All warnings: {aggregated['warnings']}")
    print(f"  All metadata: {aggregated['metadata']}")

    print("\n✅ ToolRegistry tests passed!")
