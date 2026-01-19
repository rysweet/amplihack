"""Discovery memory adapter - sync interface fer session hooks.

Provides simple sync functions to store/retrieve discoveries
from the memory system. Used by session_start.py hook.

Philosophy:
- Thin adapter, not an abstraction layer
- Sync wrappers fer async MemoryCoordinator
- Discovery-specific metadata structure
- Graceful fallback when memory unavailable

Public API:
    store_discovery: Store a discovery in memory
    get_recent_discoveries: Retrieve recent discoveries fer context
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from .coordinator import MemoryCoordinator, RetrievalQuery, StorageRequest
from .types import MemoryType

logger = logging.getLogger(__name__)


def store_discovery(
    content: str,
    *,
    category: str | None = None,
    date: datetime | None = None,
    summary: str | None = None,
    session_id: str | None = None,
) -> str | None:
    """Store a discovery in memory (sync wrapper).

    Args:
        content: Full discovery content
        category: Optional category (e.g., "bug-fix", "pattern", "architecture")
        date: Discovery date (defaults to now)
        summary: Brief summary (first 100 chars of content if not provided)
        session_id: Session ID fer coordinator

    Returns:
        Memory ID if stored, None if rejected or failed
    """
    coordinator = MemoryCoordinator(session_id=session_id)

    # Build metadata with discovery-specific fields
    metadata = {
        "source": "discovery",
        "category": category or "uncategorized",
        "timestamp": (date or datetime.now()).isoformat(),
        "summary": summary or content[:100].strip(),
    }

    request = StorageRequest(
        content=content,
        memory_type=MemoryType.SEMANTIC,  # Discoveries are long-term learnings
        metadata=metadata,
    )

    try:
        return asyncio.run(coordinator.store(request))
    except Exception as e:
        logger.warning(f"Failed to store discovery: {e}")
        return None  # Graceful failure


def get_recent_discoveries(
    days: int = 30,
    limit: int = 10,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve recent discoveries fer session context.

    Args:
        days: How far back to look (default 30)
        limit: Maximum discoveries to return
        session_id: Session ID fer coordinator

    Returns:
        List of discovery dicts with content and metadata
    """
    coordinator = MemoryCoordinator(session_id=session_id)

    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    query = RetrievalQuery(
        query_text="discovery learning pattern solution",  # Semantic search terms
        memory_types=[MemoryType.SEMANTIC],
        time_range=(start_time, end_time),
        token_budget=4000,  # Reasonable budget fer context
    )

    try:
        memories = asyncio.run(coordinator.retrieve(query))
        return [
            {
                "content": m.content,
                "date": m.created_at.isoformat() if m.created_at else None,
                "category": m.metadata.get("category"),
                "summary": m.metadata.get("summary"),
            }
            for m in memories[:limit]
        ]
    except Exception as e:
        logger.warning(f"Failed to retrieve discoveries: {e}")
        return []  # Graceful failure


__all__ = ["store_discovery", "get_recent_discoveries"]
