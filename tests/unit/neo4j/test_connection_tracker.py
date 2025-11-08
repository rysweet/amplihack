"""Unit tests for Neo4jConnectionTracker.

Tests connection counting and last connection detection.
"""

import pytest
import requests
from unittest.mock import Mock, patch

from amplihack.neo4j.connection_tracker import Neo4jConnectionTracker


class TestNeo4jConnectionTracker:
    """Test suite for Neo4jConnectionTracker."""

    @pytest.fixture
    def tracker(self):
        """Create connection tracker instance."""
        return Neo4jConnectionTracker(container_name="neo4j-test", timeout=2.0)

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
                "http://localhost:7474/db/data/transaction/commit",
                json={
                    "statements": [
                        {
                            "statement": "CALL dbms.listConnections() YIELD connectionId RETURN count(connectionId) as count"
                        }
                    ]
                },
                auth=("neo4j", "amplihack"),
                timeout=2.0,
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
        tracker = Neo4jConnectionTracker()

        assert tracker.container_name == "neo4j-amplihack"
        assert tracker.timeout == 2.0
        assert tracker.http_url == "http://localhost:7474/db/data/transaction/commit"
        assert tracker.auth == ("neo4j", "amplihack")

    def test_initialization_with_custom_values(self):
        """Test tracker initialization with custom values."""
        tracker = Neo4jConnectionTracker(container_name="custom-neo4j", timeout=5.0)

        assert tracker.container_name == "custom-neo4j"
        assert tracker.timeout == 5.0
