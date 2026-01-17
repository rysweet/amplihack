"""Tests for discovery memory adapter.

TDD tests for the sync adapter that bridges discoveries to memory system.
Following testing pyramid: focus on unit tests with mocked coordinator.

Test Coverage:
- store_discovery: Basic storage, metadata structure, error handling
- get_recent_discoveries: Retrieval, formatting, time filtering
- Edge cases: Empty results, backend failures
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestStoreDiscovery:
    """Tests for store_discovery function."""

    def test_store_discovery_basic(self):
        """Test basic discovery storage."""
        from amplihack.memory.discoveries import store_discovery

        with patch("amplihack.memory.discoveries.MemoryCoordinator") as mock_coord_cls:
            mock_coordinator = MagicMock()
            mock_coordinator.store = AsyncMock(return_value="mem-123")
            mock_coord_cls.return_value = mock_coordinator

            result = store_discovery(
                content="Discovered that CI failures often caused by Python version mismatch",
                category="bug-fix",
            )

            assert result == "mem-123"
            mock_coordinator.store.assert_called_once()

    def test_store_discovery_metadata_structure(self):
        """Test that metadata has correct structure."""
        from amplihack.memory.discoveries import store_discovery

        with patch("amplihack.memory.discoveries.MemoryCoordinator") as mock_coord_cls:
            mock_coordinator = MagicMock()
            mock_coordinator.store = AsyncMock(return_value="mem-456")
            mock_coord_cls.return_value = mock_coordinator

            store_discovery(
                content="Discovery content here",
                category="pattern",
                date=datetime(2025, 1, 15, 10, 30),
                summary="Brief summary",
            )

            # Get the StorageRequest that was passed
            call_args = mock_coordinator.store.call_args
            request = call_args[0][0]

            assert request.metadata["source"] == "discovery"
            assert request.metadata["category"] == "pattern"
            assert "2025-01-15" in request.metadata["timestamp"]
            assert request.metadata["summary"] == "Brief summary"

    def test_store_discovery_default_summary(self):
        """Test that summary defaults to first 100 chars of content."""
        from amplihack.memory.discoveries import store_discovery

        with patch("amplihack.memory.discoveries.MemoryCoordinator") as mock_coord_cls:
            mock_coordinator = MagicMock()
            mock_coordinator.store = AsyncMock(return_value="mem-789")
            mock_coord_cls.return_value = mock_coordinator

            long_content = "X" * 200  # 200 chars
            store_discovery(content=long_content)

            call_args = mock_coordinator.store.call_args
            request = call_args[0][0]

            # Summary should be first 100 chars
            assert len(request.metadata["summary"]) == 100

    def test_store_discovery_graceful_failure(self):
        """Test graceful failure when coordinator raises exception."""
        from amplihack.memory.discoveries import store_discovery

        with patch("amplihack.memory.discoveries.MemoryCoordinator") as mock_coord_cls:
            mock_coordinator = MagicMock()
            mock_coordinator.store = AsyncMock(side_effect=RuntimeError("Backend unavailable"))
            mock_coord_cls.return_value = mock_coordinator

            result = store_discovery(content="Test content")

            # Should return None instead of raising
            assert result is None

    def test_store_discovery_uses_semantic_type(self):
        """Test that discoveries use SEMANTIC memory type."""
        from amplihack.memory.discoveries import store_discovery
        from amplihack.memory.types import MemoryType

        with patch("amplihack.memory.discoveries.MemoryCoordinator") as mock_coord_cls:
            mock_coordinator = MagicMock()
            mock_coordinator.store = AsyncMock(return_value="mem-abc")
            mock_coord_cls.return_value = mock_coordinator

            store_discovery(content="Semantic discovery")

            call_args = mock_coordinator.store.call_args
            request = call_args[0][0]

            assert request.memory_type == MemoryType.SEMANTIC


class TestGetRecentDiscoveries:
    """Tests for get_recent_discoveries function."""

    def test_get_recent_discoveries_basic(self):
        """Test basic retrieval of recent discoveries."""
        from amplihack.memory.discoveries import get_recent_discoveries

        mock_memory = MagicMock()
        mock_memory.content = "Discovery content"
        mock_memory.created_at = datetime.now()
        mock_memory.metadata = {"category": "pattern", "summary": "Brief summary"}

        with patch("amplihack.memory.discoveries.MemoryCoordinator") as mock_coord_cls:
            mock_coordinator = MagicMock()
            mock_coordinator.retrieve = AsyncMock(return_value=[mock_memory])
            mock_coord_cls.return_value = mock_coordinator

            results = get_recent_discoveries(days=30, limit=10)

            assert len(results) == 1
            assert results[0]["content"] == "Discovery content"
            assert results[0]["category"] == "pattern"
            assert results[0]["summary"] == "Brief summary"

    def test_get_recent_discoveries_empty(self):
        """Test retrieval when no discoveries exist."""
        from amplihack.memory.discoveries import get_recent_discoveries

        with patch("amplihack.memory.discoveries.MemoryCoordinator") as mock_coord_cls:
            mock_coordinator = MagicMock()
            mock_coordinator.retrieve = AsyncMock(return_value=[])
            mock_coord_cls.return_value = mock_coordinator

            results = get_recent_discoveries()

            assert results == []

    def test_get_recent_discoveries_respects_limit(self):
        """Test that limit parameter is respected."""
        from amplihack.memory.discoveries import get_recent_discoveries

        # Create 5 mock memories
        mock_memories = []
        for i in range(5):
            mock_memory = MagicMock()
            mock_memory.content = f"Discovery {i}"
            mock_memory.created_at = datetime.now()
            mock_memory.metadata = {"category": "test", "summary": f"Summary {i}"}
            mock_memories.append(mock_memory)

        with patch("amplihack.memory.discoveries.MemoryCoordinator") as mock_coord_cls:
            mock_coordinator = MagicMock()
            mock_coordinator.retrieve = AsyncMock(return_value=mock_memories)
            mock_coord_cls.return_value = mock_coordinator

            results = get_recent_discoveries(limit=3)

            # Should return only 3 even though 5 available
            assert len(results) == 3

    def test_get_recent_discoveries_graceful_failure(self):
        """Test graceful failure when coordinator raises exception."""
        from amplihack.memory.discoveries import get_recent_discoveries

        with patch("amplihack.memory.discoveries.MemoryCoordinator") as mock_coord_cls:
            mock_coordinator = MagicMock()
            mock_coordinator.retrieve = AsyncMock(side_effect=RuntimeError("Backend down"))
            mock_coord_cls.return_value = mock_coordinator

            results = get_recent_discoveries()

            # Should return empty list instead of raising
            assert results == []

    def test_get_recent_discoveries_uses_semantic_type(self):
        """Test that retrieval queries SEMANTIC memory type."""
        from amplihack.memory.discoveries import get_recent_discoveries
        from amplihack.memory.types import MemoryType

        with patch("amplihack.memory.discoveries.MemoryCoordinator") as mock_coord_cls:
            mock_coordinator = MagicMock()
            mock_coordinator.retrieve = AsyncMock(return_value=[])
            mock_coord_cls.return_value = mock_coordinator

            get_recent_discoveries()

            call_args = mock_coordinator.retrieve.call_args
            query = call_args[0][0]

            assert MemoryType.SEMANTIC in query.memory_types

    def test_get_recent_discoveries_time_range(self):
        """Test that time range is correctly calculated."""
        from amplihack.memory.discoveries import get_recent_discoveries

        with patch("amplihack.memory.discoveries.MemoryCoordinator") as mock_coord_cls:
            mock_coordinator = MagicMock()
            mock_coordinator.retrieve = AsyncMock(return_value=[])
            mock_coord_cls.return_value = mock_coordinator

            get_recent_discoveries(days=7)

            call_args = mock_coordinator.retrieve.call_args
            query = call_args[0][0]

            # Time range should be set
            assert query.time_range is not None
            start_time, end_time = query.time_range

            # Start should be ~7 days ago, end should be ~now
            days_diff = (end_time - start_time).days
            assert 6 <= days_diff <= 8  # Allow small variance


class TestIntegration:
    """Integration tests with real coordinator (if available)."""

    @pytest.mark.skipif(
        True,  # Skip by default - enable for integration testing
        reason="Integration test - requires memory backend",
    )
    def test_round_trip_store_retrieve(self):
        """Test storing and retrieving a discovery."""
        from amplihack.memory.discoveries import get_recent_discoveries, store_discovery

        # Store a discovery
        content = f"Integration test discovery at {datetime.now().isoformat()}"
        memory_id = store_discovery(
            content=content,
            category="test",
            summary="Integration test",
        )

        assert memory_id is not None

        # Retrieve and verify
        discoveries = get_recent_discoveries(days=1, limit=10)

        assert any(d["content"] == content for d in discoveries)
