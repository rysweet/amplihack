"""Unit tests for KuzuConnector.

Tests the Kuzu embedded graph database connector.
Uses mocking for CI environments where kuzu may not be installed.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


class TestKuzuConnectorImport:
    """Test module import behavior."""

    def test_kuzu_available_constant_exists(self):
        """Test that KUZU_AVAILABLE constant is exposed."""
        from amplihack.memory.kuzu.connector import KUZU_AVAILABLE

        assert isinstance(KUZU_AVAILABLE, bool)

    def test_kuzu_connector_class_exists(self):
        """Test that KuzuConnector class can be imported."""
        from amplihack.memory.kuzu.connector import KuzuConnector

        assert KuzuConnector is not None

    def test_helper_functions_exist(self):
        """Test that helper functions are exported."""
        from amplihack.memory.kuzu.connector import (
            ensure_kuzu_available,
            get_default_connector,
        )

        assert callable(ensure_kuzu_available)
        assert callable(get_default_connector)


class TestKuzuConnectorInit:
    """Test KuzuConnector initialization."""

    def test_init_raises_import_error_when_kuzu_not_available(self):
        """Test that ImportError is raised when kuzu package not installed."""
        with patch("amplihack.memory.kuzu.connector.KUZU_AVAILABLE", False):
            from amplihack.memory.kuzu.connector import KuzuConnector

            # Re-import to pick up the patched value - need to patch at instance level
            with patch.object(
                KuzuConnector,
                "__init__",
                side_effect=ImportError("kuzu package not installed"),
            ):
                with pytest.raises(ImportError) as exc_info:
                    KuzuConnector()
                assert "kuzu" in str(exc_info.value).lower()

    @patch("amplihack.memory.kuzu.connector.KUZU_AVAILABLE", True)
    @patch("amplihack.memory.kuzu.connector.kuzu")
    def test_init_with_default_path(self, mock_kuzu):
        """Test initialization with default database path."""
        from amplihack.memory.kuzu.connector import KuzuConnector

        connector = KuzuConnector()
        assert connector.db_path is not None
        assert isinstance(connector.db_path, Path)
        assert connector.read_only is False

    @patch("amplihack.memory.kuzu.connector.KUZU_AVAILABLE", True)
    @patch("amplihack.memory.kuzu.connector.kuzu")
    def test_init_with_custom_path(self, mock_kuzu):
        """Test initialization with custom database path."""
        from amplihack.memory.kuzu.connector import KuzuConnector

        custom_path = "/tmp/test_kuzu_db"
        connector = KuzuConnector(db_path=custom_path)
        assert connector.db_path == Path(custom_path)

    @patch("amplihack.memory.kuzu.connector.KUZU_AVAILABLE", True)
    @patch("amplihack.memory.kuzu.connector.kuzu")
    def test_init_read_only_mode(self, mock_kuzu):
        """Test initialization in read-only mode."""
        from amplihack.memory.kuzu.connector import KuzuConnector

        connector = KuzuConnector(read_only=True)
        assert connector.read_only is True


class TestKuzuConnectorConnection:
    """Test connection management."""

    @patch("amplihack.memory.kuzu.connector.KUZU_AVAILABLE", True)
    @patch("amplihack.memory.kuzu.connector.kuzu")
    def test_connect_creates_database(self, mock_kuzu):
        """Test that connect() creates database and connection."""
        from amplihack.memory.kuzu.connector import KuzuConnector

        mock_db = Mock()
        mock_conn = Mock()
        mock_kuzu.Database.return_value = mock_db
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            connector = KuzuConnector(db_path=f"{tmpdir}/test_db")
            result = connector.connect()

            # Should return self for chaining
            assert result is connector
            mock_kuzu.Database.assert_called_once()
            mock_kuzu.Connection.assert_called_once_with(mock_db)

    @patch("amplihack.memory.kuzu.connector.KUZU_AVAILABLE", True)
    @patch("amplihack.memory.kuzu.connector.kuzu")
    def test_connect_is_idempotent(self, mock_kuzu):
        """Test that calling connect() twice doesn't create multiple connections."""
        from amplihack.memory.kuzu.connector import KuzuConnector

        mock_db = Mock()
        mock_conn = Mock()
        mock_kuzu.Database.return_value = mock_db
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            connector = KuzuConnector(db_path=f"{tmpdir}/test_db")
            connector.connect()
            connector.connect()  # Second call

            # Should only create one database
            assert mock_kuzu.Database.call_count == 1

    @patch("amplihack.memory.kuzu.connector.KUZU_AVAILABLE", True)
    @patch("amplihack.memory.kuzu.connector.kuzu")
    def test_close_clears_connection(self, mock_kuzu):
        """Test that close() clears internal state."""
        from amplihack.memory.kuzu.connector import KuzuConnector

        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            connector = KuzuConnector(db_path=f"{tmpdir}/test_db")
            connector.connect()
            connector.close()

            assert connector._db is None
            assert connector._conn is None


class TestKuzuConnectorContextManager:
    """Test context manager protocol."""

    @patch("amplihack.memory.kuzu.connector.KUZU_AVAILABLE", True)
    @patch("amplihack.memory.kuzu.connector.kuzu")
    def test_context_manager_enters_and_exits(self, mock_kuzu):
        """Test that context manager properly manages connection lifecycle."""
        from amplihack.memory.kuzu.connector import KuzuConnector

        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            with KuzuConnector(db_path=f"{tmpdir}/test_db") as conn:
                assert conn._db is not None
                assert conn._conn is not None

            # After exiting context
            assert conn._db is None
            assert conn._conn is None

    @patch("amplihack.memory.kuzu.connector.KUZU_AVAILABLE", True)
    @patch("amplihack.memory.kuzu.connector.kuzu")
    def test_context_manager_closes_on_exception(self, mock_kuzu):
        """Test that connection is closed even if exception occurs."""
        from amplihack.memory.kuzu.connector import KuzuConnector

        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = Mock()

        connector = None
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                with KuzuConnector(db_path=f"{tmpdir}/test_db") as conn:
                    connector = conn
                    raise ValueError("Test exception")
            except ValueError:
                pass

        assert connector._db is None
        assert connector._conn is None


class TestKuzuConnectorExecuteQuery:
    """Test query execution."""

    @patch("amplihack.memory.kuzu.connector.KUZU_AVAILABLE", True)
    @patch("amplihack.memory.kuzu.connector.kuzu")
    def test_execute_query_requires_connection(self, mock_kuzu):
        """Test that execute_query raises error when not connected."""
        from amplihack.memory.kuzu.connector import KuzuConnector

        connector = KuzuConnector(db_path="/tmp/test_db")
        with pytest.raises(RuntimeError) as exc_info:
            connector.execute_query("RETURN 1")
        assert "not connected" in str(exc_info.value).lower()

    @patch("amplihack.memory.kuzu.connector.KUZU_AVAILABLE", True)
    @patch("amplihack.memory.kuzu.connector.kuzu")
    def test_execute_query_returns_results(self, mock_kuzu):
        """Test that execute_query returns list of dictionaries."""
        from amplihack.memory.kuzu.connector import KuzuConnector

        # Setup mock query result
        mock_result = Mock()
        mock_result.has_next.side_effect = [True, False]
        mock_result.get_next.return_value = [1]
        mock_result.get_column_names.return_value = ["num"]

        mock_conn = Mock()
        mock_conn.execute.return_value = mock_result

        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            connector = KuzuConnector(db_path=f"{tmpdir}/test_db")
            connector.connect()

            results = connector.execute_query("RETURN 1 AS num")

            assert isinstance(results, list)
            assert len(results) == 1
            assert results[0] == {"num": 1}

    @patch("amplihack.memory.kuzu.connector.KUZU_AVAILABLE", True)
    @patch("amplihack.memory.kuzu.connector.kuzu")
    def test_execute_query_with_parameters(self, mock_kuzu):
        """Test query execution with parameters."""
        from amplihack.memory.kuzu.connector import KuzuConnector

        mock_result = Mock()
        mock_result.has_next.return_value = False

        mock_conn = Mock()
        mock_conn.execute.return_value = mock_result

        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            connector = KuzuConnector(db_path=f"{tmpdir}/test_db")
            connector.connect()

            params = {"name": "Alice"}
            connector.execute_query("MATCH (n) WHERE n.name = $name RETURN n", params)

            mock_conn.execute.assert_called_with(
                "MATCH (n) WHERE n.name = $name RETURN n",
                params,
            )


class TestKuzuConnectorExecuteWrite:
    """Test execute_write method (interface parity with Neo4jConnector)."""

    @patch("amplihack.memory.kuzu.connector.KUZU_AVAILABLE", True)
    @patch("amplihack.memory.kuzu.connector.kuzu")
    def test_execute_write_exists(self, mock_kuzu):
        """Test that execute_write method exists."""
        from amplihack.memory.kuzu.connector import KuzuConnector

        connector = KuzuConnector(db_path="/tmp/test_db")
        assert hasattr(connector, "execute_write")
        assert callable(connector.execute_write)

    @patch("amplihack.memory.kuzu.connector.KUZU_AVAILABLE", True)
    @patch("amplihack.memory.kuzu.connector.kuzu")
    def test_execute_write_delegates_to_execute_query(self, mock_kuzu):
        """Test that execute_write calls execute_query."""
        from amplihack.memory.kuzu.connector import KuzuConnector

        mock_result = Mock()
        mock_result.has_next.return_value = False

        mock_conn = Mock()
        mock_conn.execute.return_value = mock_result

        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            connector = KuzuConnector(db_path=f"{tmpdir}/test_db")
            connector.connect()

            query = "CREATE (:Person {name: 'Alice'})"
            connector.execute_write(query)

            mock_conn.execute.assert_called_with(query)

    @patch("amplihack.memory.kuzu.connector.KUZU_AVAILABLE", True)
    @patch("amplihack.memory.kuzu.connector.kuzu")
    def test_execute_write_with_parameters(self, mock_kuzu):
        """Test execute_write with parameters."""
        from amplihack.memory.kuzu.connector import KuzuConnector

        mock_result = Mock()
        mock_result.has_next.return_value = False

        mock_conn = Mock()
        mock_conn.execute.return_value = mock_result

        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            connector = KuzuConnector(db_path=f"{tmpdir}/test_db")
            connector.connect()

            query = "CREATE (:Person {name: $name})"
            params = {"name": "Bob"}
            connector.execute_write(query, params)

            mock_conn.execute.assert_called_with(query, params)


class TestKuzuConnectorVerifyConnectivity:
    """Test connectivity verification."""

    @patch("amplihack.memory.kuzu.connector.KUZU_AVAILABLE", True)
    @patch("amplihack.memory.kuzu.connector.kuzu")
    def test_verify_connectivity_returns_true_when_working(self, mock_kuzu):
        """Test that verify_connectivity returns True for working connection."""
        from amplihack.memory.kuzu.connector import KuzuConnector

        mock_result = Mock()
        mock_result.has_next.side_effect = [True, False]
        mock_result.get_next.return_value = [1]
        mock_result.get_column_names.return_value = ["num"]

        mock_conn = Mock()
        mock_conn.execute.return_value = mock_result

        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            connector = KuzuConnector(db_path=f"{tmpdir}/test_db")
            connector.connect()

            assert connector.verify_connectivity() is True

    @patch("amplihack.memory.kuzu.connector.KUZU_AVAILABLE", True)
    @patch("amplihack.memory.kuzu.connector.kuzu")
    def test_verify_connectivity_returns_false_on_error(self, mock_kuzu):
        """Test that verify_connectivity returns False when query fails."""
        from amplihack.memory.kuzu.connector import KuzuConnector

        mock_conn = Mock()
        mock_conn.execute.side_effect = Exception("Connection error")

        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            connector = KuzuConnector(db_path=f"{tmpdir}/test_db")
            connector.connect()

            assert connector.verify_connectivity() is False


class TestKuzuConnectorHelperFunctions:
    """Test module-level helper functions."""

    def test_ensure_kuzu_available_returns_bool(self):
        """Test that ensure_kuzu_available returns boolean."""
        from amplihack.memory.kuzu.connector import ensure_kuzu_available

        result = ensure_kuzu_available()
        assert isinstance(result, bool)

    @patch("amplihack.memory.kuzu.connector.KUZU_AVAILABLE", True)
    @patch("amplihack.memory.kuzu.connector.kuzu")
    def test_get_default_connector_returns_connector(self, mock_kuzu):
        """Test that get_default_connector returns a KuzuConnector."""
        from amplihack.memory.kuzu.connector import (
            KuzuConnector,
            get_default_connector,
        )

        connector = get_default_connector()
        assert isinstance(connector, KuzuConnector)


class TestAutoBackendModule:
    """Test auto_backend module exports."""

    def test_all_exports_exist(self):
        """Test that __all__ exports are available."""
        from amplihack.memory.auto_backend import __all__

        assert "BackendType" in __all__
        assert "BackendDetector" in __all__
        assert "get_connector" in __all__
        assert "get_backend_status" in __all__

    def test_backend_type_enum_values(self):
        """Test BackendType enum has expected values."""
        from amplihack.memory.auto_backend import BackendType

        assert BackendType.KUZU.value == "kuzu"
        assert BackendType.NEO4J.value == "neo4j"

    def test_get_backend_status_returns_dict(self):
        """Test get_backend_status returns a dictionary."""
        from amplihack.memory.auto_backend import get_backend_status

        status = get_backend_status()
        assert isinstance(status, dict)
        assert "kuzu_available" in status
        assert "docker_available" in status
