"""Main entry point for context-management skill.

This module provides the primary skill function that Claude Code invokes
when the context-management skill is activated.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from .orchestrator import ContextManagementOrchestrator


def context_management_skill(action: str, **kwargs) -> Dict[str, Any]:
    """Main entry point for the context-management skill.

    This function coordinates token monitoring, context extraction, and
    selective rehydration for proactive context management.

    Args:
        action: One of 'status', 'snapshot', 'rehydrate', 'list'
        **kwargs: Action-specific parameters:
            - status: current_tokens (int)
            - snapshot: conversation_data (list), name (str, optional)
            - rehydrate: snapshot_id (str), level (str, default='standard')
            - list: (no parameters)

    Returns:
        Dict with action results and recommendations

    Raises:
        ValueError: If action is invalid

    Example:
        >>> # Check token usage status
        >>> result = context_management_skill('status', current_tokens=500000)
        >>> print(result['usage']['percentage'])
        50.0

        >>> # Create a snapshot
        >>> result = context_management_skill(
        ...     'snapshot',
        ...     conversation_data=[...],
        ...     name='auth-feature'
        ... )
        >>> print(result['snapshot']['snapshot_id'])
        '20251116_143522'

        >>> # Rehydrate context
        >>> result = context_management_skill(
        ...     'rehydrate',
        ...     snapshot_id='20251116_143522',
        ...     level='essential'
        ... )
        >>> print(result['context'])
        '# Restored Context: auth-feature...'

        >>> # List all snapshots
        >>> result = context_management_skill('list')
        >>> print(result['count'])
        3
    """
    # Extract configuration from kwargs
    snapshot_dir = kwargs.pop("snapshot_dir", None)
    max_tokens = kwargs.pop("max_tokens", 1_000_000)

    if snapshot_dir and not isinstance(snapshot_dir, Path):
        snapshot_dir = Path(snapshot_dir)

    # Create orchestrator
    orchestrator = ContextManagementOrchestrator(snapshot_dir=snapshot_dir, max_tokens=max_tokens)

    # Delegate to orchestrator
    return orchestrator.handle_action(action, **kwargs)


# Convenience functions for direct access
def check_status(current_tokens: int, **kwargs) -> Dict[str, Any]:
    """Check current token usage status.

    Args:
        current_tokens: Current token count

    Returns:
        Dict with usage statistics and recommendations
    """
    return context_management_skill("status", current_tokens=current_tokens, **kwargs)


def create_snapshot(conversation_data: Any, name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Create a context snapshot.

    Args:
        conversation_data: Conversation history (list of messages)
        name: Optional human-readable snapshot name

    Returns:
        Dict with snapshot creation results
    """
    return context_management_skill(
        "snapshot", conversation_data=conversation_data, name=name, **kwargs
    )


def rehydrate_context(snapshot_id: str, level: str = "standard", **kwargs) -> Dict[str, Any]:
    """Rehydrate context from a snapshot.

    Args:
        snapshot_id: Snapshot ID to restore
        level: Detail level ('essential', 'standard', 'comprehensive')

    Returns:
        Dict with rehydrated context text
    """
    return context_management_skill("rehydrate", snapshot_id=snapshot_id, level=level, **kwargs)


def list_snapshots(**kwargs) -> Dict[str, Any]:
    """List all available context snapshots.

    Returns:
        Dict with list of snapshots and metadata
    """
    return context_management_skill("list", **kwargs)
