"""Tests for memory cleanup CLI utility.

Tests the cleanup_memory_sessions function with different patterns
and backends.
"""

from datetime import datetime
from unittest.mock import Mock

from src.amplihack.memory.cli_cleanup import cleanup_memory_sessions
from src.amplihack.memory.models import SessionInfo


class TestCleanupMemorySessions:
    """Test cleanup_memory_sessions function."""

    def test_cleanup_with_no_matches(self):
        """Test cleanup when no sessions match pattern."""
        mock_backend = Mock()
        mock_backend.list_sessions.return_value = [
            SessionInfo(
                session_id="production-1",
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                agent_ids=["agent-1"],
                memory_count=5,
                metadata={},
            )
        ]

        result = cleanup_memory_sessions(
            backend=mock_backend,
            pattern="test_*",
            dry_run=True,
            confirm=False,
        )

        assert result["matched"] == 0
        assert result["deleted"] == 0
        assert result["errors"] == 0

    def test_cleanup_dry_run_mode(self):
        """Test cleanup in dry-run mode does not delete."""
        mock_backend = Mock()
        mock_backend.list_sessions.return_value = [
            SessionInfo(
                session_id="test_session_1",
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                agent_ids=["agent-1"],
                memory_count=5,
                metadata={},
            ),
            SessionInfo(
                session_id="test_session_2",
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                agent_ids=["agent-1"],
                memory_count=3,
                metadata={},
            ),
        ]

        result = cleanup_memory_sessions(
            backend=mock_backend,
            pattern="test_*",
            dry_run=True,
            confirm=False,
        )

        assert result["matched"] == 2
        assert result["deleted"] == 0
        assert result["errors"] == 0
        # Verify delete_session was never called
        mock_backend.delete_session.assert_not_called()

    def test_cleanup_actual_deletion_with_confirm(self):
        """Test cleanup actually deletes with confirm flag."""
        mock_backend = Mock()
        mock_backend.list_sessions.return_value = [
            SessionInfo(
                session_id="test_session_1",
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                agent_ids=["agent-1"],
                memory_count=5,
                metadata={},
            )
        ]
        mock_backend.delete_session.return_value = True

        result = cleanup_memory_sessions(
            backend=mock_backend,
            pattern="test_*",
            dry_run=False,
            confirm=True,
        )

        assert result["matched"] == 1
        assert result["deleted"] == 1
        assert result["errors"] == 0
        # Verify delete_session was called
        mock_backend.delete_session.assert_called_once_with("test_session_1")

    def test_cleanup_pattern_matching(self):
        """Test pattern matching with different patterns."""
        mock_backend = Mock()
        mock_backend.list_sessions.return_value = [
            SessionInfo(
                session_id="test_session_1",
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                agent_ids=["agent-1"],
                memory_count=5,
                metadata={},
            ),
            SessionInfo(
                session_id="prod_session_1",
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                agent_ids=["agent-1"],
                memory_count=3,
                metadata={},
            ),
            SessionInfo(
                session_id="test_another",
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                agent_ids=["agent-1"],
                memory_count=2,
                metadata={},
            ),
        ]

        # Test pattern "test_*" matches only "test_session_1"
        result = cleanup_memory_sessions(
            backend=mock_backend,
            pattern="test_session_*",
            dry_run=True,
            confirm=False,
        )

        assert result["matched"] == 1
        assert "test_session_1" in result["session_ids"]

    def test_cleanup_handles_deletion_errors(self):
        """Test cleanup handles errors during deletion gracefully."""
        mock_backend = Mock()
        mock_backend.list_sessions.return_value = [
            SessionInfo(
                session_id="test_session_1",
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                agent_ids=["agent-1"],
                memory_count=5,
                metadata={},
            ),
            SessionInfo(
                session_id="test_session_2",
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                agent_ids=["agent-1"],
                memory_count=3,
                metadata={},
            ),
        ]

        # First delete succeeds, second fails
        mock_backend.delete_session.side_effect = [True, False]

        result = cleanup_memory_sessions(
            backend=mock_backend,
            pattern="test_*",
            dry_run=False,
            confirm=True,
        )

        assert result["matched"] == 2
        assert result["deleted"] == 1
        assert result["errors"] == 1

    def test_cleanup_wildcard_pattern(self):
        """Test cleanup with * wildcard matching all sessions."""
        mock_backend = Mock()
        mock_backend.list_sessions.return_value = [
            SessionInfo(
                session_id="session_1",
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                agent_ids=["agent-1"],
                memory_count=5,
                metadata={},
            ),
            SessionInfo(
                session_id="session_2",
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                agent_ids=["agent-1"],
                memory_count=3,
                metadata={},
            ),
        ]

        result = cleanup_memory_sessions(
            backend=mock_backend,
            pattern="*",
            dry_run=True,
            confirm=False,
        )

        assert result["matched"] == 2
