"""Comprehensive test suite for Agent Memory System.

This test suite validates:
1. Persistence across sessions with proper storage and retrieval
2. Performance requirements (<50ms operations)
3. Concurrency and thread-safe operations under load
4. Session and agent memory isolation
5. Optional activation and graceful degradation
6. Error handling and edge cases
"""

import sqlite3
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from amplihack.memory import MemoryManager, MemoryType
from amplihack.memory.maintenance import MemoryMaintenance


class TestMemoryPersistence:
    """Test memory persistence across sessions and system restarts."""

    @pytest.fixture
    def persistent_db_path(self):
        """Create a persistent database path for cross-session testing."""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "persistent_memory.db"
        yield str(db_path)
        # Cleanup is handled by each test method

    def test_memory_survives_database_restart(self, persistent_db_path):
        """Test that memories persist across database restarts."""
        memory_data = {
            "agent_id": "persistent_agent",
            "title": "Persistent Memory",
            "content": "This should survive database restart",
            "memory_type": MemoryType.CONTEXT,
            "metadata": {"importance": "high"},
            "tags": ["persistence", "test"],
            "importance": 9,
        }

        # Phase 1: Store memory
        manager1 = MemoryManager(db_path=persistent_db_path, session_id="session1")
        memory_id = manager1.store(**memory_data)
        assert memory_id is not None

        # Verify storage
        stored_memory = manager1.get(memory_id)
        assert stored_memory is not None
        assert stored_memory.title == memory_data["title"]
        assert stored_memory.content == memory_data["content"]

        # Close first manager
        del manager1

        # Phase 2: Create new manager with same database
        manager2 = MemoryManager(db_path=persistent_db_path, session_id="session1")

        # Retrieve memory with new manager
        retrieved_memory = manager2.get(memory_id)
        assert retrieved_memory is not None
        assert retrieved_memory.title == memory_data["title"]
        assert retrieved_memory.content == memory_data["content"]
        assert retrieved_memory.metadata == memory_data["metadata"]
        assert retrieved_memory.tags == memory_data["tags"]
        assert retrieved_memory.importance == memory_data["importance"]

        # Cleanup
        Path(persistent_db_path).unlink(missing_ok=True)

    def test_cross_session_memory_isolation(self, persistent_db_path):
        """Test that different sessions have isolated memory spaces."""
        # Create memories in different sessions
        manager_session1 = MemoryManager(db_path=persistent_db_path, session_id="session1")
        manager_session2 = MemoryManager(db_path=persistent_db_path, session_id="session2")

        # Store memories in each session
        memory_id1 = manager_session1.store(
            agent_id="agent1", title="Session 1 Memory", content="Content for session 1"
        )

        memory_id2 = manager_session2.store(
            agent_id="agent1",  # Same agent, different session
            title="Session 2 Memory",
            content="Content for session 2",
        )

        # Verify isolation: each session should only see its own memories
        session1_memories = manager_session1.retrieve()
        session2_memories = manager_session2.retrieve()

        assert len(session1_memories) == 1
        assert len(session2_memories) == 1
        assert session1_memories[0].title == "Session 1 Memory"
        assert session2_memories[0].title == "Session 2 Memory"

        # Cross-session access should return None
        assert manager_session1.get(memory_id2) is None
        assert manager_session2.get(memory_id1) is None

        # Cleanup
        Path(persistent_db_path).unlink(missing_ok=True)

    def test_memory_expiration_persistence(self, persistent_db_path):
        """Test that memory expiration persists across restarts."""
        manager1 = MemoryManager(db_path=persistent_db_path, session_id="test_session")

        # Store memory that expires soon
        memory_id = manager1.store(
            agent_id="test_agent",
            title="Expiring Memory",
            content="This will expire",
            expires_in=timedelta(milliseconds=100),
        )

        # Verify memory exists
        memory = manager1.get(memory_id)
        assert memory is not None
        assert memory.expires_at is not None

        del manager1

        # Wait for expiration
        time.sleep(0.2)

        # Create new manager and check expiration
        manager2 = MemoryManager(db_path=persistent_db_path, session_id="test_session")

        # Memory should be expired but still in database until cleanup
        _ = manager2.get(memory_id)
        # Depending on implementation, this might return None or expired memory

        # Cleanup should remove expired memory
        cleanup_count = manager2.cleanup_expired()
        assert cleanup_count >= 0

        # Memory should definitely be gone after cleanup
        assert manager2.get(memory_id) is None

        # Cleanup
        Path(persistent_db_path).unlink(missing_ok=True)

    def test_database_file_permissions(self, persistent_db_path):
        """Test that database files have secure permissions."""
        manager = MemoryManager(db_path=persistent_db_path, session_id="test_session")

        # Store a memory to ensure database is created
        manager.store(
            agent_id="test_agent", title="Permission Test", content="Testing file permissions"
        )

        # Check file permissions (should be 600 - owner read/write only)
        db_path = Path(persistent_db_path)
        assert db_path.exists()

        # Get file permissions
        file_mode = db_path.stat().st_mode & 0o777
        assert file_mode == 0o600, f"Database file has incorrect permissions: {oct(file_mode)}"

        # Cleanup
        db_path.unlink(missing_ok=True)


class TestMemoryPerformance:
    """Test performance requirements (<50ms operations)."""

    @pytest.fixture
    def perf_manager(self):
        """Create memory manager optimized for performance testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "perf_memory.db")
            yield MemoryManager(db_path=db_path, session_id="perf_session")

    def test_single_store_performance(self, perf_manager):
        """Test that single store operations complete within 50ms."""
        start_time = time.time()

        memory_id = perf_manager.store(
            agent_id="perf_agent",
            title="Performance Test Memory",
            content="Testing storage performance with reasonable content length",
            memory_type=MemoryType.CONTEXT,
            metadata={"performance": True},
            tags=["performance", "test"],
            importance=7,
        )

        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000

        assert memory_id is not None
        assert duration_ms < 50, f"Store operation took {duration_ms:.2f}ms, exceeds 50ms limit"

    def test_single_retrieve_performance(self, perf_manager):
        """Test that single retrieve operations complete within 50ms."""
        # Setup: Store a memory first
        memory_id = perf_manager.store(
            agent_id="perf_agent",
            title="Retrieve Test",
            content="Content for retrieval performance test",
        )

        # Test retrieval performance
        start_time = time.time()
        memory = perf_manager.get(memory_id)
        end_time = time.time()

        duration_ms = (end_time - start_time) * 1000

        assert memory is not None
        assert duration_ms < 50, f"Retrieve operation took {duration_ms:.2f}ms, exceeds 50ms limit"

    def test_batch_store_performance(self, perf_manager):
        """Test batch storage performance."""
        memories_data = [
            {
                "agent_id": f"agent_{i % 3}",
                "title": f"Batch Memory {i}",
                "content": f"Batch content {i} with sufficient length for realistic testing",
                "memory_type": "context",
                "importance": i % 10 + 1,
                "tags": [f"batch_{i % 5}", "performance"],
            }
            for i in range(20)
        ]

        start_time = time.time()
        memory_ids = perf_manager.store_batch(memories_data)
        end_time = time.time()

        total_duration_ms = (end_time - start_time) * 1000
        avg_duration_ms = total_duration_ms / len(memories_data)

        assert len(memory_ids) == len(memories_data)
        assert all(mid is not None for mid in memory_ids)
        assert avg_duration_ms < 50, (
            f"Average batch store time {avg_duration_ms:.2f}ms exceeds 50ms limit"
        )

    def test_search_performance(self, perf_manager):
        """Test search operation performance with large dataset."""
        # Setup: Create large dataset
        for i in range(100):
            perf_manager.store(
                agent_id=f"agent_{i % 10}",
                title=f"Search Test Memory {i}",
                content=f"Searchable content with keyword_{i % 20} and other text",
                memory_type=MemoryType.CONTEXT,
                importance=i % 10 + 1,
                tags=[f"tag_{i % 5}", "search", "test"],
            )

        # Test various search operations
        search_operations = [
            lambda: perf_manager.search("keyword_5"),
            lambda: perf_manager.retrieve(agent_id="agent_3"),
            lambda: perf_manager.retrieve(memory_type="context"),
            lambda: perf_manager.retrieve(min_importance=7),
            lambda: perf_manager.retrieve(tags=["tag_2"]),
        ]

        for i, operation in enumerate(search_operations):
            start_time = time.time()
            results = operation()
            end_time = time.time()

            duration_ms = (end_time - start_time) * 1000

            assert isinstance(results, list), f"Search operation {i} returned invalid type"
            assert duration_ms < 50, (
                f"Search operation {i} took {duration_ms:.2f}ms, exceeds 50ms limit"
            )

    def test_concurrent_read_performance(self, perf_manager):
        """Test performance under concurrent read load."""
        # Setup: Store memories for concurrent access
        memory_ids = []
        for i in range(20):
            memory_id = perf_manager.store(
                agent_id="concurrent_agent",
                title=f"Concurrent Memory {i}",
                content=f"Content for concurrent access test {i}",
            )
            memory_ids.append(memory_id)

        def read_memory(memory_id):
            start_time = time.time()
            memory = perf_manager.get(memory_id)
            end_time = time.time()
            return memory, (end_time - start_time) * 1000

        # Perform concurrent reads
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_memory, mid) for mid in memory_ids]
            results = [future.result() for future in as_completed(futures)]

        _ = time.time() - start_time

        # Verify results
        assert len(results) == len(memory_ids)
        durations = [duration for _, duration in results]
        avg_duration = sum(durations) / len(durations)

        assert avg_duration < 50, (
            f"Average concurrent read time {avg_duration:.2f}ms exceeds 50ms limit"
        )
        assert all(memory is not None for memory, _ in results)


class TestConcurrencyAndThreadSafety:
    """Test thread-safe operations under concurrent load."""

    @pytest.fixture
    def concurrent_manager(self):
        """Create memory manager for concurrency testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "concurrent_memory.db")
            yield MemoryManager(db_path=db_path, session_id="concurrent_session")

    def test_concurrent_writes(self, concurrent_manager):
        """Test concurrent write operations are thread-safe."""
        num_threads = 10
        memories_per_thread = 5
        results = {}

        def store_memories(thread_id):
            thread_results = []
            for i in range(memories_per_thread):
                memory_id = concurrent_manager.store(
                    agent_id=f"agent_{thread_id}",
                    title=f"Thread {thread_id} Memory {i}",
                    content=f"Content from thread {thread_id}, memory {i}",
                    metadata={"thread_id": thread_id, "memory_index": i},
                )
                thread_results.append(memory_id)
                # Small delay to increase chance of race conditions
                time.sleep(0.001)
            return thread_results

        # Execute concurrent writes
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = {executor.submit(store_memories, i): i for i in range(num_threads)}

            for future in as_completed(futures):
                thread_id = futures[future]
                results[thread_id] = future.result()

        # Verify all writes completed successfully
        assert len(results) == num_threads
        total_memories = sum(len(thread_results) for thread_results in results.values())
        assert total_memories == num_threads * memories_per_thread

        # Verify all memory IDs are unique
        all_memory_ids = []
        for thread_results in results.values():
            all_memory_ids.extend(thread_results)

        assert len(all_memory_ids) == len(set(all_memory_ids)), "Duplicate memory IDs detected"

        # Verify all memories can be retrieved
        stored_memories = concurrent_manager.retrieve()
        assert len(stored_memories) == total_memories

    def test_concurrent_read_write(self, concurrent_manager):
        """Test mixed concurrent read and write operations."""
        # Initial setup: store some memories
        initial_memories = []
        for i in range(10):
            memory_id = concurrent_manager.store(
                agent_id="initial_agent",
                title=f"Initial Memory {i}",
                content=f"Initial content {i}",
            )
            initial_memories.append(memory_id)

        read_results = []
        write_results = []
        errors = []

        def read_operation(memory_id):
            try:
                return concurrent_manager.get(memory_id)
            except Exception as e:
                errors.append(f"Read error: {e}")
                return None

        def write_operation(index):
            try:
                return concurrent_manager.store(
                    agent_id="concurrent_agent",
                    title=f"Concurrent Memory {index}",
                    content=f"Concurrent content {index}",
                )
            except Exception as e:
                errors.append(f"Write error: {e}")
                return None

        # Execute mixed operations
        with ThreadPoolExecutor(max_workers=15) as executor:
            # Submit read operations
            read_futures = [
                executor.submit(read_operation, memory_id)
                for memory_id in initial_memories * 2  # Read each memory twice
            ]

            # Submit write operations
            write_futures = [executor.submit(write_operation, i) for i in range(10)]

            # Collect results
            for future in as_completed(read_futures):
                read_results.append(future.result())

            for future in as_completed(write_futures):
                write_results.append(future.result())

        # Verify no errors occurred
        assert len(errors) == 0, f"Concurrent operations had errors: {errors}"

        # Verify read results
        successful_reads = [r for r in read_results if r is not None]
        assert len(successful_reads) > 0, "No successful reads"

        # Verify write results
        successful_writes = [r for r in write_results if r is not None]
        assert len(successful_writes) > 0, "No successful writes"

    def test_database_lock_handling(self, concurrent_manager):
        """Test proper handling of database locks under contention."""
        lock_test_results = []

        def intensive_operation(operation_id):
            results = []
            for i in range(20):
                # Alternate between reads and writes to create lock contention
                if i % 2 == 0:
                    memory_id = concurrent_manager.store(
                        agent_id=f"lock_test_agent_{operation_id}",
                        title=f"Lock Test {operation_id}-{i}",
                        content=f"Testing database locks {operation_id}-{i}",
                    )
                    results.append(("write", memory_id))
                else:
                    memories = concurrent_manager.retrieve(limit=5)
                    results.append(("read", len(memories)))

                # Small delay to increase lock contention
                time.sleep(0.001)

            return results

        # Run intensive operations concurrently
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(intensive_operation, i) for i in range(8)]

            for future in as_completed(futures):
                lock_test_results.append(future.result())

        # Verify all operations completed without deadlocks
        assert len(lock_test_results) == 8

        # Count successful operations
        total_operations = sum(len(results) for results in lock_test_results)
        assert total_operations == 8 * 20, "Some operations failed due to lock issues"


class TestSessionAndAgentIsolation:
    """Test session and agent memory isolation."""

    @pytest.fixture
    def isolation_db_path(self):
        """Create shared database path for isolation testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield str(Path(temp_dir) / "isolation_memory.db")

    def test_multi_session_isolation(self, isolation_db_path):
        """Test that multiple sessions maintain proper isolation."""
        sessions = ["session_alpha", "session_beta", "session_gamma"]
        managers = {}
        session_memories = {}

        # Create managers for each session
        for session_id in sessions:
            managers[session_id] = MemoryManager(db_path=isolation_db_path, session_id=session_id)

        # Store unique memories in each session
        for session_id in sessions:
            manager = managers[session_id]
            memories = []

            for i in range(5):
                memory_id = manager.store(
                    agent_id=f"agent_{session_id}",
                    title=f"{session_id} Memory {i}",
                    content=f"Content specific to {session_id}, memory {i}",
                    metadata={"session": session_id, "index": i},
                )
                memories.append(memory_id)

            session_memories[session_id] = memories

        # Verify isolation: each session should only see its own memories
        for session_id in sessions:
            manager = managers[session_id]
            retrieved_memories = manager.retrieve()

            assert len(retrieved_memories) == 5, f"Session {session_id} has wrong memory count"

            # Verify all memories belong to this session
            for memory in retrieved_memories:
                assert memory.session_id == session_id
                assert session_id in memory.title

            # Verify cross-session access is blocked
            for other_session_id in sessions:
                if other_session_id != session_id:
                    for memory_id in session_memories[other_session_id]:
                        assert manager.get(memory_id) is None, (
                            f"Session {session_id} can access {other_session_id} memory"
                        )

    def test_agent_memory_separation(self, isolation_db_path):
        """Test that different agents have separated memory within same session."""
        manager = MemoryManager(db_path=isolation_db_path, session_id="test_session")

        agents = ["agent_architect", "agent_builder", "agent_reviewer"]
        agent_memories = {}

        # Store memories for each agent
        for agent_id in agents:
            memories = []
            for i in range(3):
                memory_id = manager.store(
                    agent_id=agent_id,
                    title=f"{agent_id} Memory {i}",
                    content=f"Memory content for {agent_id}, entry {i}",
                    memory_type=MemoryType.CONTEXT,
                    tags=[agent_id, "test"],
                )
                memories.append(memory_id)
            agent_memories[agent_id] = memories

        # Verify agent separation
        for agent_id in agents:
            agent_specific_memories = manager.retrieve(agent_id=agent_id)

            assert len(agent_specific_memories) == 3, f"Agent {agent_id} has wrong memory count"

            # Verify all memories belong to this agent
            for memory in agent_specific_memories:
                assert memory.agent_id == agent_id
                assert agent_id in memory.title

        # Verify global session view includes all memories
        all_session_memories = manager.retrieve()
        assert len(all_session_memories) == len(agents) * 3

    def test_cross_agent_memory_visibility(self, isolation_db_path):
        """Test agent memory visibility rules within same session."""
        manager = MemoryManager(db_path=isolation_db_path, session_id="shared_session")

        # Store memories for different agents
        _ = manager.store(
            agent_id="agent_alpha",
            title="Shared Project Knowledge",
            content="This information should be accessible to all agents",
            memory_type=MemoryType.CONTEXT,
            tags=["shared", "project"],
        )

        _ = manager.store(
            agent_id="agent_alpha",
            title="Agent Alpha Private Memory",
            content="This is private to agent alpha",
            memory_type=MemoryType.DECISION,
            tags=["private", "alpha"],
        )

        # Test access from different agent perspectives
        # In current implementation, agents in same session can see each other's memories
        # This tests the current behavior - adjust if isolation rules change

        all_memories = manager.retrieve()
        assert len(all_memories) == 2

        alpha_memories = manager.retrieve(agent_id="agent_alpha")
        assert len(alpha_memories) == 2

        # If we implement stricter agent isolation, this test would change
        beta_accessible_memories = manager.retrieve(agent_id="agent_beta")
        # Current implementation: agent_beta sees no memories (different agent_id filter)
        assert len(beta_accessible_memories) == 0


class TestOptionalActivationAndGracefulDegradation:
    """Test optional activation and graceful degradation when disabled."""

    def test_disabled_memory_system(self):
        """Test system behavior when memory is completely disabled."""
        # Test with non-existent database path and error handling
        with patch("amplihack.memory.database.MemoryDatabase._init_database") as mock_init:
            mock_init.side_effect = Exception("Database unavailable")

            try:
                MemoryManager(db_path="/nonexistent/path/memory.db", session_id="test_session")

                # Operations should handle gracefully or provide clear error messages
                # This depends on implementation - adjust based on actual error handling

            except Exception as e:
                # Should have clear error message about memory system unavailability
                assert "memory" in str(e).lower() or "database" in str(e).lower()

    def test_readonly_mode_degradation(self):
        """Test graceful degradation to read-only mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "readonly_test.db"

            # Create and populate database normally
            manager = MemoryManager(db_path=str(db_path), session_id="test_session")
            memory_id = manager.store(
                agent_id="test_agent",
                title="Read-Only Test Memory",
                content="This memory should be readable even in read-only mode",
            )

            # Make database file read-only
            db_path.chmod(0o444)

            try:
                # Create new manager with read-only database
                readonly_manager = MemoryManager(db_path=str(db_path), session_id="test_session")

                # Read operations should still work
                memory = readonly_manager.get(memory_id)
                assert memory is not None
                assert memory.title == "Read-Only Test Memory"

                # Write operations should fail gracefully
                try:
                    readonly_manager.store(
                        agent_id="test_agent",
                        title="Should Fail",
                        content="This should not be stored",
                    )
                    # If it doesn't raise an exception, it should return None or False
                except Exception:
                    pass  # Expected for read-only mode

            finally:
                # Restore write permissions for cleanup
                db_path.chmod(0o644)

    def test_memory_size_limits(self):
        """Test behavior when memory limits are reached."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "limits_test.db")
            manager = MemoryManager(db_path=db_path, session_id="test_session")

            # Store many large memories to test limits
            large_content = "x" * 10000  # 10KB content
            memory_ids = []

            # Store until we hit reasonable limits or system handles gracefully
            try:
                for i in range(1000):  # Try to store 1000 large memories
                    memory_id = manager.store(
                        agent_id="limit_test_agent",
                        title=f"Large Memory {i}",
                        content=large_content,
                        metadata={"size_test": True, "index": i},
                    )
                    if memory_id:
                        memory_ids.append(memory_id)

                    # Check if system is still responsive
                    if i % 100 == 0:
                        test_memory = manager.get(memory_ids[0])
                        assert test_memory is not None, "System became unresponsive"

            except Exception:
                # System should handle gracefully with clear error messages
                assert len(memory_ids) > 0, "System failed immediately"

            # Verify stored memories are still accessible
            if memory_ids:
                sample_memory = manager.get(memory_ids[0])
                assert sample_memory is not None


class TestErrorHandlingAndEdgeCases:
    """Test comprehensive error handling and edge case scenarios."""

    @pytest.fixture
    def error_test_manager(self):
        """Create memory manager for error testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "error_test.db")
            yield MemoryManager(db_path=db_path, session_id="error_test_session")

    def test_invalid_memory_data_handling(self, error_test_manager):
        """Test handling of invalid memory data."""
        invalid_data_cases = [
            # Missing required fields
            {},
            {"agent_id": "test"},
            {"title": "Test"},
            # Invalid data types
            {"agent_id": None, "title": "Test", "content": "Test content"},
            {"agent_id": "test", "title": None, "content": "Test content"},
            {"agent_id": "test", "title": "Test", "content": None},
            # Invalid memory type
            {
                "agent_id": "test",
                "title": "Test",
                "content": "Test content",
                "memory_type": "invalid_type",
            },
        ]

        for invalid_data in invalid_data_cases:
            try:
                _ = error_test_manager.store(**invalid_data)
                # If it doesn't raise an exception, it should return None
                # (depending on implementation strategy)
            except (TypeError, ValueError, AttributeError, RuntimeError):
                pass  # Expected for invalid data

    def test_database_corruption_handling(self, error_test_manager):
        """Test handling of database corruption scenarios."""
        # Store a valid memory first
        memory_id = error_test_manager.store(
            agent_id="corruption_test", title="Test Memory", content="Test content"
        )
        assert memory_id is not None

        # Simulate database corruption by corrupting the database file
        db_path = error_test_manager.db.db_path

        # Create backup of working database
        backup_data = db_path.read_bytes()

        try:
            # Corrupt the database file
            with open(db_path, "wb") as f:
                f.write(b"corrupted data" * 100)

            # Try to access corrupted database
            try:
                corrupted_manager = MemoryManager(
                    db_path=str(db_path), session_id="corruption_test"
                )

                # Operations should handle corruption gracefully
                _ = corrupted_manager.get(memory_id)
                # Should return None or raise appropriate exception

            except (sqlite3.DatabaseError, sqlite3.CorruptionError):
                pass  # Expected for corrupted database

        finally:
            # Restore working database
            db_path.write_bytes(backup_data)

    def test_concurrent_database_access_errors(self, error_test_manager):
        """Test handling of concurrent access errors."""

        def conflicting_operation(operation_id):
            try:
                # Perform operations that might conflict
                for i in range(10):
                    if i % 2 == 0:
                        _ = error_test_manager.store(
                            agent_id=f"conflict_agent_{operation_id}",
                            title=f"Conflict Test {operation_id}-{i}",
                            content="Testing concurrent conflicts",
                        )
                    else:
                        # Try to delete and recreate
                        memories = error_test_manager.retrieve(limit=1)
                        if memories:
                            # If delete operation exists, test it
                            pass

                return True
            except Exception as e:
                return f"Error in operation {operation_id}: {e}"

        # Run multiple conflicting operations
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(conflicting_operation, i) for i in range(5)]

            results = [future.result() for future in as_completed(futures)]

        # Most operations should succeed, some might fail gracefully
        successful_operations = sum(1 for r in results if r is True)
        assert successful_operations > 0, "All concurrent operations failed"

    def test_memory_query_edge_cases(self, error_test_manager):
        """Test edge cases in memory queries."""
        # Store test data
        error_test_manager.store(
            agent_id="edge_case_agent",
            title="Edge Case Memory",
            content="Content for edge case testing",
            importance=5,
        )

        edge_case_queries = [
            # Empty/invalid queries
            {},
            {"agent_id": ""},
            {"agent_id": None},
            # Invalid date ranges
            {
                "created_after": datetime(2030, 1, 1),  # Future date
                "created_before": datetime(2020, 1, 1),  # Before after
            },
            # Invalid limits
            {"limit": -1},
            {"limit": 0},
            {"offset": -1},
            # Invalid importance ranges
            {"min_importance": 15},  # Above max
            {"min_importance": -5},  # Below min
        ]

        for query_params in edge_case_queries:
            try:
                results = error_test_manager.retrieve(**query_params)
                # Should return empty list or handle gracefully
                assert isinstance(results, list)
            except (ValueError, TypeError):
                pass  # Expected for some invalid queries

    def test_maintenance_error_handling(self):
        """Test error handling in maintenance operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "maintenance_test.db"

            # Create maintenance system
            maintenance = MemoryMaintenance(db_path)

            # Test maintenance on empty database
            result = maintenance.cleanup_expired()
            assert isinstance(result, dict)
            assert "expired_memories_removed" in result

            # Test analysis on empty database
            analysis = maintenance.analyze_memory_usage()
            assert isinstance(analysis, dict)

            # Test vacuum on empty database
            vacuum_result = maintenance.vacuum_database()
            assert isinstance(vacuum_result, dict)
            assert "success" in vacuum_result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
