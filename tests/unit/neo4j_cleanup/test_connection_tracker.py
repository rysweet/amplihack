"""Unit tests for Neo4jConnectionTracker.

Tests connection counting and last connection detection.
"""

from unittest.mock import Mock, patch

import pytest
import requests

from amplihack.neo4j.connection_tracker import Neo4jConnectionTracker


class TestNeo4jConnectionTracker:
    """Test suite for Neo4jConnectionTracker."""

    @pytest.fixture
    def tracker(self):
        """Create connection tracker instance."""
        # Explicitly set credentials for consistent test behavior
        return Neo4jConnectionTracker(
            container_name="neo4j-test", timeout=4.0, username="neo4j", password="amplihack"
        )

    def test_get_active_connection_count_success(self, tracker):
        """Test successful connection count retrieval."""
        # Mock successful HTTP response with 2 connections
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "data": [
                        {"row": [2]}  # 2 active connections
                    ]
                }
            ],
            "errors": [],
        }

        with patch("requests.post", return_value=mock_response) as mock_post:
            count = tracker.get_active_connection_count()

            assert count == 2
            mock_post.assert_called_once_with(
                "http://localhost:7474/db/neo4j/tx/commit",
                json={
                    "statements": [
                        {
                            "statement": "CALL dbms.listConnections() YIELD connectionId RETURN count(connectionId) as count"
                        }
                    ]
                },
                auth=("neo4j", "amplihack"),
                timeout=4.0,
            )

    def test_get_active_connection_count_timeout(self, tracker):
        """Test timeout handling."""
        with patch("requests.post", side_effect=requests.exceptions.Timeout):
            count = tracker.get_active_connection_count()

            assert count is None

    def test_get_active_connection_count_container_not_running(self, tracker):
        """Test connection error when container not running."""
        with patch("requests.post", side_effect=requests.exceptions.ConnectionError):
            count = tracker.get_active_connection_count()

            assert count is None

    def test_get_active_connection_count_http_error(self, tracker):
        """Test HTTP error response."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("requests.post", return_value=mock_response):
            count = tracker.get_active_connection_count()

            assert count is None

    def test_get_active_connection_count_neo4j_error(self, tracker):
        """Test Neo4j query error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [],
            "errors": [{"code": "Neo.ClientError.Statement.SyntaxError", "message": "Invalid query"}],
        }

        with patch("requests.post", return_value=mock_response):
            count = tracker.get_active_connection_count()

            assert count is None

    def test_get_active_connection_count_no_results(self, tracker):
        """Test missing results in response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [], "errors": []}

        with patch("requests.post", return_value=mock_response):
            count = tracker.get_active_connection_count()

            assert count is None

    def test_get_active_connection_count_no_data(self, tracker):
        """Test missing data in results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"data": []}], "errors": []}

        with patch("requests.post", return_value=mock_response):
            count = tracker.get_active_connection_count()

            assert count is None

    def test_get_active_connection_count_zero_connections(self, tracker):
        """Test zero connections case."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"data": [{"row": [0]}]}],
            "errors": [],
        }

        with patch("requests.post", return_value=mock_response):
            count = tracker.get_active_connection_count()

            assert count == 0

    def test_is_last_connection_true(self, tracker):
        """Test last connection detection (1 connection)."""
        # Mock 1 connection
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"data": [{"row": [1]}]}],
            "errors": [],
        }

        with patch("requests.post", return_value=mock_response):
            result = tracker.is_last_connection()

            assert result is True

    def test_is_last_connection_false_multiple(self, tracker):
        """Test last connection detection (multiple connections)."""
        # Mock 3 connections
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"data": [{"row": [3]}]}],
            "errors": [],
        }

        with patch("requests.post", return_value=mock_response):
            result = tracker.is_last_connection()

            assert result is False

    def test_is_last_connection_false_none(self, tracker):
        """Test last connection detection (error case - None)."""
        # Mock error case
        with patch("requests.post", side_effect=requests.exceptions.Timeout):
            result = tracker.is_last_connection()

            # Safe default: False when cannot determine
            assert result is False

    def test_is_last_connection_false_zero(self, tracker):
        """Test last connection detection (zero connections)."""
        # Mock 0 connections
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"data": [{"row": [0]}]}],
            "errors": [],
        }

        with patch("requests.post", return_value=mock_response):
            result = tracker.is_last_connection()

            assert result is False

    def test_initialization_with_defaults(self):
        """Test tracker initialization with default values."""
        # Use explicit credentials to avoid environment variable interference
        tracker = Neo4jConnectionTracker(username="neo4j", password="amplihack")

        assert tracker.container_name == "neo4j-amplihack"
        assert tracker.timeout == 4.0
        assert tracker.http_url == "http://localhost:7474/db/neo4j/tx/commit"
        assert tracker.auth == ("neo4j", "amplihack")

    def test_initialization_with_custom_values(self):
        """Test tracker initialization with custom values."""
        tracker = Neo4jConnectionTracker(container_name="custom-neo4j", timeout=5.0)

        assert tracker.container_name == "custom-neo4j"
        assert tracker.timeout == 5.0

    def test_retry_on_timeout(self, tracker):
        """Test retry logic on timeout."""
        # Mock first attempt to timeout, second to succeed
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"data": [{"row": [2]}]}],
            "errors": [],
        }

        with patch("requests.post") as mock_post:
            mock_post.side_effect = [requests.exceptions.Timeout, mock_response]
            with patch("time.sleep"):  # Mock sleep to speed up test
                count = tracker.get_active_connection_count()

            assert count == 2
            # Should have called post twice (1 failure + 1 retry)
            assert mock_post.call_count == 2

    def test_max_retries_exhausted(self, tracker):
        """Test max retries reached."""
        with patch("requests.post", side_effect=requests.exceptions.Timeout):
            with patch("time.sleep"):  # Mock sleep to speed up test
                count = tracker.get_active_connection_count(max_retries=2)

            # Should fail after 3 total attempts (initial + 2 retries)
            assert count is None

    def test_exponential_backoff(self, tracker):
        """Test exponential backoff timing."""
        with patch("requests.post", side_effect=requests.exceptions.Timeout):
            with patch("time.sleep") as mock_sleep:
                tracker.get_active_connection_count(max_retries=2)

            # Should have called sleep twice with exponential backoff
            assert mock_sleep.call_count == 2
            # First backoff: 0.5 * (1.5 ** 0) = 0.5
            mock_sleep.assert_any_call(0.5)
            # Second backoff: 0.5 * (1.5 ** 1) = 0.75
            mock_sleep.assert_any_call(0.75)

    def test_connection_error_no_retry(self, tracker):
        """Test ConnectionError does not trigger retry."""
        with patch("requests.post", side_effect=requests.exceptions.ConnectionError) as mock_post:
            with patch("time.sleep") as mock_sleep:
                count = tracker.get_active_connection_count(max_retries=2)

            # Should only call once (no retries for ConnectionError)
            assert mock_post.call_count == 1
            # Should not sleep
            assert mock_sleep.call_count == 0
            assert count is None

    def test_sanitize_for_log(self, tracker):
        """Test log sanitization."""
        # Test basic sanitization
        result = tracker._sanitize_for_log("normal string")
        assert result == "normal string"

        # Test newline removal
        result = tracker._sanitize_for_log("line1\nline2\rline3")
        assert result == "line1\\nline2\\rline3"

        # Test truncation
        long_string = "a" * 150
        result = tracker._sanitize_for_log(long_string, max_length=100)
        assert len(result) == 114  # 100 + len("...[truncated]")
        assert result.endswith("...[truncated]")

    def test_generic_exception_logging(self, tracker):
        """Test generic exception logging with sanitization."""
        with patch("requests.post", side_effect=ValueError("Sensitive data\nwith newlines")):
            count = tracker.get_active_connection_count()

            # Should return None for generic exceptions
            assert count is None
