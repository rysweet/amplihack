"""Tests for KuzuBackend._open_database_with_retry().

Validates exponential backoff retry on lock contention errors (issue #2834).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("kuzu")


class TestOpenDatabaseWithRetry:
    """Unit tests for the Kuzu DB retry logic."""

    def test_succeeds_on_first_attempt(self):
        """Normal case: DB opens on first try."""
        from amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_db = MagicMock()
        with patch("amplihack.memory.backends.kuzu_backend.kuzu") as mock_kuzu:
            mock_kuzu.Database.return_value = mock_db
            result = KuzuBackend._open_database_with_retry(Path("/tmp/test.db"))
            assert result == mock_db
            assert mock_kuzu.Database.call_count == 1

    def test_retries_on_lock_contention(self):
        """Retries when lock error occurs, succeeds on retry."""
        from amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_db = MagicMock()
        lock_error = RuntimeError("Could not set lock on file : /tmp/test.db")

        with patch("amplihack.memory.backends.kuzu_backend.kuzu") as mock_kuzu:
            mock_kuzu.Database.side_effect = [lock_error, mock_db]
            with patch("amplihack.memory.backends.kuzu_backend.time.sleep"):
                result = KuzuBackend._open_database_with_retry(
                    Path("/tmp/test.db"), max_retries=3, base_delay=0.01
                )
                assert result == mock_db
                assert mock_kuzu.Database.call_count == 2

    def test_raises_after_max_retries(self):
        """Raises RuntimeError after all retries exhausted."""
        from amplihack.memory.backends.kuzu_backend import KuzuBackend

        lock_error = RuntimeError("Could not set lock on file : /tmp/test.db")

        with patch("amplihack.memory.backends.kuzu_backend.kuzu") as mock_kuzu:
            mock_kuzu.Database.side_effect = lock_error
            with patch("amplihack.memory.backends.kuzu_backend.time.sleep"):
                with pytest.raises(RuntimeError, match="Could not set lock"):
                    KuzuBackend._open_database_with_retry(
                        Path("/tmp/test.db"), max_retries=2, base_delay=0.01
                    )
                # 1 initial + 2 retries = 3 total
                assert mock_kuzu.Database.call_count == 3

    def test_does_not_retry_non_lock_errors(self):
        """Non-lock RuntimeErrors should propagate immediately."""
        from amplihack.memory.backends.kuzu_backend import KuzuBackend

        other_error = RuntimeError("Some other database error")

        with patch("amplihack.memory.backends.kuzu_backend.kuzu") as mock_kuzu:
            mock_kuzu.Database.side_effect = other_error
            with pytest.raises(RuntimeError, match="Some other database error"):
                KuzuBackend._open_database_with_retry(Path("/tmp/test.db"))
            # Should fail immediately, no retries
            assert mock_kuzu.Database.call_count == 1

    def test_exponential_backoff_delays(self):
        """Verify exponential backoff: 0.2, 0.4, 0.8 seconds."""
        from amplihack.memory.backends.kuzu_backend import KuzuBackend

        lock_error = RuntimeError("Could not set lock on file : /tmp/test.db")

        with patch("amplihack.memory.backends.kuzu_backend.kuzu") as mock_kuzu:
            mock_kuzu.Database.side_effect = lock_error
            with patch("amplihack.memory.backends.kuzu_backend.time.sleep") as mock_sleep:
                with pytest.raises(RuntimeError):
                    KuzuBackend._open_database_with_retry(
                        Path("/tmp/test.db"), max_retries=3, base_delay=0.2
                    )
                # Should have slept 3 times with exponential delays
                assert mock_sleep.call_count == 3
                delays = [call.args[0] for call in mock_sleep.call_args_list]
                assert delays == [0.2, 0.4, 0.8]
