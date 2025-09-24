"""
Test suite for Agent Memory Interface - TDD approach
Following the testing pyramid: 60% unit, 30% integration, 10% E2E
"""
# type: ignore

import tempfile
import time
from pathlib import Path

import pytest

# These imports will fail initially - TDD approach
try:
    from ..core import MemoryBackend
    from ..interface import AgentMemory
except ImportError:
    # Expected to fail initially
    AgentMemory = None  # type: ignore
    MemoryBackend = None  # type: ignore


@pytest.mark.skipif(AgentMemory is None, reason="AgentMemory not implemented yet")
class TestAgentMemoryInterface:
    """Test the AgentMemory interface contract"""

    def test_memory_storage_retrieval(self):
        """Test basic store/retrieve cycle - FAILING TEST"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory = AgentMemory("test-agent", db_path=Path(tmp_dir) / "test.db")

            # Store markdown content
            result = memory.store("key1", "# Test Content\nSome markdown")
            assert result is True

            # Retrieve content
            retrieved = memory.retrieve("key1")
            assert retrieved == "# Test Content\nSome markdown"

    def test_performance_requirement(self):
        """Test <50ms operation requirement - FAILING TEST"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory = AgentMemory("perf-agent", db_path=Path(tmp_dir) / "perf.db")

            # Store operation
            start = time.time()
            memory.store("perf-key", "large content" * 100)
            store_duration = time.time() - start
            assert store_duration < 0.050, f"Store took {store_duration:.3f}s > 50ms"

            # Retrieve operation
            start = time.time()
            memory.retrieve("perf-key")
            retrieve_duration = time.time() - start
            assert retrieve_duration < 0.050, f"Retrieve took {retrieve_duration:.3f}s > 50ms"

    def test_session_isolation(self):
        """Test memories isolated between sessions - FAILING TEST"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "isolation.db"

            memory1 = AgentMemory("agent1", session_id="session1", db_path=db_path)
            memory2 = AgentMemory("agent1", session_id="session2", db_path=db_path)

            # Store in session1
            memory1.store("shared-key", "session1-value")

            # Should not be visible in session2
            assert memory2.retrieve("shared-key") is None

    def test_optional_activation(self):
        """Test system works when disabled - FAILING TEST"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory = AgentMemory("agent", enabled=False, db_path=Path(tmp_dir) / "disabled.db")

            # Should succeed but not persist
            assert memory.store("key", "value") is True
            assert memory.retrieve("key") is None  # Not persisted when disabled

    def test_markdown_json_fallback(self):
        """Test markdown-first storage with JSON fallback - FAILING TEST"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory = AgentMemory("test-agent", db_path=Path(tmp_dir) / "types.db")

            # Store markdown
            memory.store("md-key", "# Header\nContent", memory_type="markdown")
            assert memory.retrieve("md-key") == "# Header\nContent"

            # Store JSON
            json_data = {"key": "value", "number": 42}
            memory.store("json-key", json_data, memory_type="json")
            assert memory.retrieve("json-key") == json_data

    def test_list_keys_functionality(self):
        """Test key listing with pattern matching - FAILING TEST"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory = AgentMemory("test-agent", db_path=Path(tmp_dir) / "list.db")

            # Store multiple keys
            memory.store("user-1", "data1")
            memory.store("user-2", "data2")
            memory.store("config-setting", "value")

            # List all keys
            all_keys = memory.list_keys()
            assert "user-1" in all_keys
            assert "user-2" in all_keys
            assert "config-setting" in all_keys

            # List with pattern
            user_keys = memory.list_keys(pattern="user-*")
            assert "user-1" in user_keys
            assert "user-2" in user_keys
            assert "config-setting" not in user_keys

    def test_delete_memory(self):
        """Test memory deletion - FAILING TEST"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory = AgentMemory("test-agent", db_path=Path(tmp_dir) / "delete.db")

            # Store and verify
            memory.store("delete-me", "content")
            assert memory.retrieve("delete-me") == "content"

            # Delete and verify
            result = memory.delete("delete-me")
            assert result is True
            assert memory.retrieve("delete-me") is None

    def test_clear_session(self):
        """Test session memory clearing - FAILING TEST"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory = AgentMemory("test-agent", db_path=Path(tmp_dir) / "clear.db")

            # Store multiple memories
            memory.store("key1", "value1")
            memory.store("key2", "value2")

            # Clear session
            result = memory.clear_session()
            assert result is True

            # Verify all cleared
            assert memory.retrieve("key1") is None
            assert memory.retrieve("key2") is None
            assert memory.list_keys() == []

    def test_error_handling_corrupted_db(self):
        """Test graceful handling of corrupted database - FAILING TEST"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "corrupted.db"

            # Create corrupted database file
            db_path.write_text("not a database")

            # Should handle gracefully
            memory = AgentMemory("test-agent", db_path=db_path)

            # Operations should fail gracefully
            assert memory.store("key", "value") is False
            assert memory.retrieve("key") is None

    def test_boundary_conditions(self):
        """Test boundary conditions - FAILING TEST"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory = AgentMemory("test-agent", db_path=Path(tmp_dir) / "boundary.db")

            # Empty key handling
            with pytest.raises(ValueError):
                memory.store("", "value")

            # None value handling
            with pytest.raises(ValueError):
                memory.store("key", None)

            # Very long key
            long_key = "x" * 1000
            assert memory.store(long_key, "value") is True
            assert memory.retrieve(long_key) == "value"

            # Large content
            large_content = "x" * 10000
            assert memory.store("large", large_content) is True
            assert memory.retrieve("large") == large_content


@pytest.mark.skipif(MemoryBackend is None, reason="MemoryBackend not implemented yet")
class TestMemoryBackend:
    """Test the SQLite backend implementation"""

    def test_database_initialization(self):
        """Test database schema creation - FAILING TEST"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "init.db"
            MemoryBackend(db_path)

            # Database should be created
            assert db_path.exists()

            # Should have correct permissions (600)
            assert oct(db_path.stat().st_mode)[-3:] == "600"

    def test_concurrent_access(self):
        """Test thread-safe operations - FAILING TEST"""
        import threading

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "concurrent.db"
            backend = MemoryBackend(db_path)

            results = []

            def worker(worker_id):
                for i in range(10):
                    key = f"worker-{worker_id}-key-{i}"
                    value = f"worker-{worker_id}-value-{i}"
                    success = backend.store("test-session", key, value, "markdown")
                    results.append(success)

            # Run concurrent workers
            threads = []
            for i in range(3):
                t = threading.Thread(target=worker, args=(i,))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            # All operations should succeed
            assert all(results)
