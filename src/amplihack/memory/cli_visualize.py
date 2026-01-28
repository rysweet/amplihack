"""Terminal tree visualization fer Kùzu memory graph.

Provides Rich-based tree display of memory hierarchies with color-coding,
emojis, and importance scores.

Philosophy:
- Ruthless simplicity: Uses Rich Tree, no complex graph algorithms
- Zero-BS: Everything works, real queries and real data
- Self-contained: All visualization logic in one module
- Backend agnostic: Works with any backend implementing the interface

Public API:
    visualize_memory_tree: Main visualization function (sync wrapper)
    visualize_memory_tree_async: Async visualization function
    build_memory_tree: Build Rich Tree from backend data (async)
    format_importance_score: Format importance score as stars
    get_memory_emoji: Get emoji fer memory type
"""

import asyncio
import inspect
import logging
from datetime import datetime
from typing import Any

try:
    from rich.console import Console  # type: ignore[import-untyped]
    from rich.tree import Tree  # type: ignore[import-untyped]

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None  # type: ignore[assignment]
    Tree = None  # type: ignore[assignment]

from .models import MemoryQuery, MemoryType

logger = logging.getLogger(__name__)


def get_memory_emoji(memory_type: MemoryType) -> str:
    """Get emoji fer memory type.

    Maps old 6-type system to new 5-type visual system.

    Args:
        memory_type: Type of memory

    Returns:
        Emoji string fer the type
    """
    emoji_map = {
        MemoryType.CONVERSATION: "📝",  # Episodic-like
        MemoryType.PATTERN: "💡",  # Semantic
        MemoryType.DECISION: "📌",  # Prospective-like
        MemoryType.LEARNING: "💡",  # Semantic
        MemoryType.CONTEXT: "🔧",  # Working-like
        MemoryType.ARTIFACT: "📄",  # Artifact
    }
    return emoji_map.get(memory_type, "❓")


def format_importance_score(importance: int | None) -> str:
    """Format importance score as stars.

    Args:
        importance: Score from 1-10 (or None)

    Returns:
        Formatted string like "★★★★★★★★☆☆ 8/10"
    """
    if importance is None:
        return ""

    # Clamp to 0-10
    importance = max(0, min(10, importance))

    filled = "★" * importance
    empty = "☆" * (10 - importance)
    return f"{filled}{empty} {importance}/10"


async def build_memory_tree_async(
    backend: Any,
    session_id: str | None = None,
    memory_type: MemoryType | None = None,
    depth: int | None = None,
) -> Any:  # Returns Tree if Rich available, None otherwise
    """Build Rich Tree from backend data (async version).

    Args:
        backend: Memory backend (KuzuBackend or MemoryDatabase)
        session_id: Filter by session (optional)
        memory_type: Filter by memory type (optional)
        depth: Maximum tree depth (optional)

    Returns:
        Rich Tree ready fer display (or None if Rich not available)

    Raises:
        ImportError: If Rich library not installed
    """
    if not RICH_AVAILABLE:
        raise ImportError("Rich library required. Install with: pip install rich")

    # Get backend name
    backend_name = "unknown"
    if hasattr(backend, "get_capabilities"):
        caps = backend.get_capabilities()
        backend_name = caps.backend_name if hasattr(caps, "backend_name") else backend_name

    # Create root
    assert Tree is not None, "Rich library required"
    root = Tree(f"🧠 [bold blue]Memory Graph[/bold blue] (Backend: {backend_name})")

    try:
        # Get sessions
        sessions_result = backend.list_sessions()
        # Handle both sync and async backends
        if inspect.iscoroutine(sessions_result):
            sessions = await sessions_result
        else:
            sessions = sessions_result

        if not sessions:
            root.add("[yellow](empty - no memories found)[/yellow]")
            return root

        # Filter sessions if requested
        if session_id:
            sessions = [s for s in sessions if s.session_id == session_id]

        # Create sessions branch
        sessions_branch = root.add(f"📅 [cyan]Sessions[/cyan] ({len(sessions)})")

        # Add each session
        for session in sessions:
            # Session node with count
            session_node = sessions_branch.add(
                f"[blue]{session.session_id}[/blue] ({session.memory_count} memories)"
            )

            # Query memories fer this session
            query = MemoryQuery(
                session_id=session.session_id,
                memory_type=memory_type,
                limit=1000,  # Reasonable limit
            )

            memories_result = backend.retrieve_memories(query)
            # Handle both sync and async backends
            if inspect.iscoroutine(memories_result):
                memories = await memories_result
            else:
                memories = memories_result

            # Add memories
            for memory in memories:
                emoji = get_memory_emoji(memory.memory_type)
                type_name = memory.memory_type.value.capitalize()

                # Build memory line
                memory_line = f"{emoji} [green]{type_name}[/green]: {memory.title}"

                # Add importance score if present
                if memory.importance is not None:
                    score_str = format_importance_score(memory.importance)
                    memory_line += f" ([yellow]{score_str}[/yellow])"

                # Add confidence if present (semantic memories)
                if "confidence" in memory.metadata:
                    conf = memory.metadata["confidence"]
                    memory_line += f" ([yellow]confidence: {conf}[/yellow])"

                # Add usage count if present (procedural memories)
                if "usage_count" in memory.metadata:
                    count = memory.metadata["usage_count"]
                    memory_line += f" ([yellow]used: {count}x[/yellow])"

                # Add expiry if present (working memories)
                if memory.expires_at:
                    now = datetime.now()
                    if memory.expires_at > now:
                        delta = memory.expires_at - now
                        hours = int(delta.total_seconds() / 3600)
                        memory_line += f" ([yellow]expires: {hours}h[/yellow])"
                    else:
                        memory_line += " ([red]expired[/red])"

                session_node.add(memory_line)

            # Respect depth limit (if session level is depth 2)
            if depth is not None and depth <= 2:
                break

        # Add agents branch
        if (not session_id and depth is None) or (depth and depth > 2):
            # Get unique agents from sessions
            all_agent_ids = set()
            for session in sessions:
                all_agent_ids.update(session.agent_ids)

            if all_agent_ids:
                agents_branch = root.add(f"👥 [magenta]Agents[/magenta] ({len(all_agent_ids)})")

                # Count memories per agent
                for agent_id in sorted(all_agent_ids):
                    query = MemoryQuery(agent_id=agent_id, limit=10000)
                    agent_memories_result = backend.retrieve_memories(query)
                    # Handle both sync and async backends
                    if inspect.iscoroutine(agent_memories_result):
                        agent_memories = await agent_memories_result
                    else:
                        agent_memories = agent_memories_result
                    count = len(agent_memories)
                    agents_branch.add(f"[magenta]{agent_id}[/magenta] ({count} memories)")

    except Exception as e:
        logger.error(f"Error building memory tree: {e}", exc_info=True)
        root.add(f"[red]Error: {e!s}[/red]")

    return root


async def visualize_memory_tree_async(
    backend: Any,
    session_id: str | None = None,
    memory_type: MemoryType | None = None,
    depth: int | None = None,
) -> None:
    """Visualize memory graph as terminal tree (async version).

    Displays the graph hierarchy with:
    - Color-coded memory types
    - Emoji indicators
    - Importance/confidence scores
    - Hierarchical structure

    Args:
        backend: Memory backend (KuzuBackend or MemoryDatabase)
        session_id: Filter by session (optional)
        memory_type: Filter by memory type (optional)
        depth: Maximum tree depth (optional)

    Raises:
        ImportError: If Rich library not installed

    Example:
        >>> from amplihack.memory.backends.kuzu_backend import KuzuBackend
        >>> backend = KuzuBackend()
        >>> await visualize_memory_tree_async(backend)

        🧠 Memory Graph (Backend: kuzu)
        ├── 📅 Sessions (2)
        │   ├── Session-2026-01-11 (5 memories)
        │   │   ├── 📝 Episodic: User discussed auth (★★★★★★★★☆☆ 8/10)
        │   │   ├── 💡 Semantic: Pattern - JWT (confidence: 0.95)
        │   │   └── 📌 Prospective: TODO - Review PR
        │   └── Session-2026-01-10
        └── 👥 Agents (3)
            ├── architect (8 memories)
            └── builder (12 memories)
    """
    if not RICH_AVAILABLE:
        raise ImportError("Rich library required. Install with: pip install rich")

    try:
        # Build tree
        tree = await build_memory_tree_async(
            backend=backend,
            session_id=session_id,
            memory_type=memory_type,
            depth=depth,
        )

        # Display using Rich console
        assert Console is not None, "Rich library required"
        console = Console()
        console.print(tree)

    except Exception as e:
        logger.error(f"Error visualizing memory tree: {e}", exc_info=True)
        print(f"Error: {e!s}")


def build_memory_tree(
    backend: Any,
    session_id: str | None = None,
    memory_type: MemoryType | None = None,
    depth: int | None = None,
) -> Any:  # Returns Tree if Rich available, None otherwise
    """Build Rich Tree from backend data (sync wrapper).

    This is a synchronous wrapper around build_memory_tree_async for
    convenience in non-async contexts (tests, etc).

    Args:
        backend: Memory backend (KuzuBackend or MemoryDatabase)
        session_id: Filter by session (optional)
        memory_type: Filter by memory type (optional)
        depth: Maximum tree depth (optional)

    Returns:
        Rich Tree ready fer display (or None if Rich not available)

    Raises:
        ImportError: If Rich library not installed
    """
    return asyncio.run(build_memory_tree_async(backend, session_id, memory_type, depth))


def visualize_memory_tree(
    backend: Any,
    session_id: str | None = None,
    memory_type: MemoryType | None = None,
    depth: int | None = None,
) -> None:
    """Visualize memory graph as terminal tree (sync wrapper).

    This is a synchronous wrapper around visualize_memory_tree_async for
    convenience in non-async contexts (CLI, tests, etc).

    Displays the graph hierarchy with:
    - Color-coded memory types
    - Emoji indicators
    - Importance/confidence scores
    - Hierarchical structure

    Args:
        backend: Memory backend (KuzuBackend or MemoryDatabase)
        session_id: Filter by session (optional)
        memory_type: Filter by memory type (optional)
        depth: Maximum tree depth (optional)

    Raises:
        ImportError: If Rich library not installed

    Example:
        >>> from amplihack.memory.backends.kuzu_backend import KuzuBackend
        >>> backend = KuzuBackend()
        >>> visualize_memory_tree(backend)

        🧠 Memory Graph (Backend: kuzu)
        ├── 📅 Sessions (2)
        │   ├── Session-2026-01-11 (5 memories)
        │   │   ├── 📝 Episodic: User discussed auth (★★★★★★★★☆☆ 8/10)
        │   │   ├── 💡 Semantic: Pattern - JWT (confidence: 0.95)
        │   │   └── 📌 Prospective: TODO - Review PR
        │   └── Session-2026-01-10
        └── 👥 Agents (3)
            ├── architect (8 memories)
            └── builder (12 memories)
    """
    asyncio.run(visualize_memory_tree_async(backend, session_id, memory_type, depth))


__all__ = [
    "visualize_memory_tree",
    "visualize_memory_tree_async",
    "build_memory_tree",
    "format_importance_score",
    "get_memory_emoji",
]
