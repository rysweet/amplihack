#!/usr/bin/env python3
"""Simple test runner for memory system validation."""

import os
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from amplihack.memory import MemoryManager, MemoryType


class TestResults:
    """Simple test results collector."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def assert_test(self, condition, message):
        """Assert a test condition."""
        if condition:
            self.passed += 1
            print(f"  ✓ {message}")
        else:
            self.failed += 1
            error_msg = f"  ✗ {message}"
            print(error_msg)
            self.errors.append(error_msg)

    def assert_equals(self, actual, expected, message):
        """Assert equality."""
        self.assert_test(actual == expected, f"{message} (expected: {expected}, got: {actual})")

    def assert_not_none(self, value, message):
        """Assert value is not None."""
        self.assert_test(value is not None, f"{message} (got None)")

    def assert_performance(self, duration_ms, limit_ms, operation):
        """Assert performance requirement."""
        self.assert_test(
            duration_ms < limit_ms,
            f"{operation} performance: {duration_ms:.2f}ms (limit: {limit_ms}ms)",
        )

    def print_summary(self):
        """Print test summary."""
        total = self.passed + self.failed
        print(f"\nTest Results: {self.passed}/{total} passed")
        if self.failed > 0:
            print("Failures:")
            for error in self.errors:
                print(error)


def test_basic_memory_operations():
    """Test basic memory storage and retrieval operations."""
    print("\n=== Testing Basic Memory Operations ===")
    results = TestResults()

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = str(Path(temp_dir) / "test_memory.db")
        manager = MemoryManager(db_path=db_path, session_id="test_session")

        # Test storage
        memory_id = manager.store(
            agent_id="test_agent",
            title="Test Memory",
            content="This is test content",
            memory_type=MemoryType.CONTEXT,
            metadata={"test": True},
            tags=["test", "basic"],
            importance=8,
        )

        results.assert_not_none(memory_id, "Memory storage")

        # Test retrieval
        memory = manager.get(memory_id)
        results.assert_not_none(memory, "Memory retrieval")

        if memory:
            results.assert_equals(memory.title, "Test Memory", "Memory title")
            results.assert_equals(memory.content, "This is test content", "Memory content")
            results.assert_equals(memory.agent_id, "test_agent", "Memory agent ID")
            results.assert_equals(memory.importance, 8, "Memory importance")
            results.assert_equals(memory.tags, ["test", "basic"], "Memory tags")

    results.print_summary()
    return results


def test_memory_performance():
    """Test memory performance requirements (<50ms operations)."""
    print("\n=== Testing Memory Performance ===")
    results = TestResults()

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = str(Path(temp_dir) / "perf_memory.db")
        manager = MemoryManager(db_path=db_path, session_id="perf_session")

        # Test single store performance
        start_time = time.time()
        memory_id = manager.store(
            agent_id="perf_agent",
            title="Performance Test Memory",
            content="Testing storage performance",
            memory_type=MemoryType.CONTEXT,
        )
        store_duration = (time.time() - start_time) * 1000

        results.assert_not_none(memory_id, "Performance store operation")
        results.assert_performance(store_duration, 50, "Store operation")

        # Test single retrieve performance
        start_time = time.time()
        memory = manager.get(memory_id)
        retrieve_duration = (time.time() - start_time) * 1000

        results.assert_not_none(memory, "Performance retrieve operation")
        results.assert_performance(retrieve_duration, 50, "Retrieve operation")

        # Test batch storage performance
        batch_data = [
            {
                "agent_id": f"agent_{i}",
                "title": f"Batch Memory {i}",
                "content": f"Batch content {i}",
                "memory_type": "context",
            }
            for i in range(10)
        ]

        start_time = time.time()
        memory_ids = manager.store_batch(batch_data)
        batch_duration = (time.time() - start_time) * 1000
        avg_batch_duration = batch_duration / len(batch_data)

        results.assert_equals(len(memory_ids), len(batch_data), "Batch storage count")
        results.assert_performance(avg_batch_duration, 50, "Average batch store operation")

        # Test search performance
        start_time = time.time()
        search_results = manager.search("Batch")
        search_duration = (time.time() - start_time) * 1000

        results.assert_test(len(search_results) > 0, "Search results found")
        results.assert_performance(search_duration, 50, "Search operation")

    results.print_summary()
    return results


def test_session_isolation():
    """Test session isolation between different sessions."""
    print("\n=== Testing Session Isolation ===")
    results = TestResults()

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = str(Path(temp_dir) / "isolation_memory.db")

        # Create two managers with different sessions
        manager1 = MemoryManager(db_path=db_path, session_id="session1")
        manager2 = MemoryManager(db_path=db_path, session_id="session2")

        # Store memory in session 1
        memory_id1 = manager1.store(
            agent_id="agent1", title="Session 1 Memory", content="Content for session 1"
        )

        # Store memory in session 2
        memory_id2 = manager2.store(
            agent_id="agent1",  # Same agent, different session
            title="Session 2 Memory",
            content="Content for session 2",
        )

        results.assert_not_none(memory_id1, "Session 1 memory storage")
        results.assert_not_none(memory_id2, "Session 2 memory storage")

        # Test session isolation
        session1_memories = manager1.retrieve()
        session2_memories = manager2.retrieve()

        results.assert_equals(len(session1_memories), 1, "Session 1 memory count")
        results.assert_equals(len(session2_memories), 1, "Session 2 memory count")

        # Test cross-session access (should be blocked)
        cross_access1 = manager1.get(memory_id2)
        cross_access2 = manager2.get(memory_id1)

        results.assert_test(cross_access1 is None, "Session 1 cannot access session 2 memory")
        results.assert_test(cross_access2 is None, "Session 2 cannot access session 1 memory")

    results.print_summary()
    return results


def test_concurrency():
    """Test concurrent operations and thread safety."""
    print("\n=== Testing Concurrency ===")
    results = TestResults()

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = str(Path(temp_dir) / "concurrent_memory.db")
        manager = MemoryManager(db_path=db_path, session_id="concurrent_session")

        def store_memories(thread_id):
            """Store memories from a specific thread."""
            thread_results = []
            for i in range(5):
                memory_id = manager.store(
                    agent_id=f"agent_{thread_id}",
                    title=f"Thread {thread_id} Memory {i}",
                    content=f"Content from thread {thread_id}, memory {i}",
                )
                thread_results.append(memory_id)
                time.sleep(0.001)  # Small delay to increase race condition chances
            return thread_results

        # Execute concurrent writes
        num_threads = 5
        thread_results = {}

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = {executor.submit(store_memories, i): i for i in range(num_threads)}

            for future in as_completed(futures):
                thread_id = futures[future]
                thread_results[thread_id] = future.result()

        # Verify results
        results.assert_equals(len(thread_results), num_threads, "All threads completed")

        # Check for unique memory IDs
        all_memory_ids = []
        for thread_result in thread_results.values():
            all_memory_ids.extend(thread_result)

        unique_ids = set(all_memory_ids)
        results.assert_equals(len(all_memory_ids), len(unique_ids), "All memory IDs are unique")

        # Verify all memories can be retrieved
        stored_memories = manager.retrieve()
        expected_count = num_threads * 5
        results.assert_equals(
            len(stored_memories), expected_count, "All concurrent memories stored"
        )

    results.print_summary()
    return results


def test_memory_expiration():
    """Test memory expiration functionality."""
    print("\n=== Testing Memory Expiration ===")
    results = TestResults()

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = str(Path(temp_dir) / "expiration_memory.db")
        manager = MemoryManager(db_path=db_path, session_id="expiration_session")

        # Store memory with short expiration
        memory_id = manager.store(
            agent_id="test_agent",
            title="Expiring Memory",
            content="This will expire soon",
            expires_in=timedelta(milliseconds=100),
        )

        results.assert_not_none(memory_id, "Expiring memory storage")

        # Verify memory exists initially
        memory = manager.get(memory_id)
        results.assert_not_none(memory, "Memory exists before expiration")

        if memory:
            results.assert_test(memory.expires_at is not None, "Memory has expiration time")

        # Wait for expiration
        time.sleep(0.2)

        # Cleanup expired memories
        cleanup_count = manager.cleanup_expired()
        results.assert_test(cleanup_count >= 0, "Cleanup operation completed")

        # Memory should be gone after cleanup
        expired_memory = manager.get(memory_id)
        results.assert_test(expired_memory is None, "Memory removed after expiration")

    results.print_summary()
    return results


def test_database_persistence():
    """Test database persistence across restarts."""
    print("\n=== Testing Database Persistence ===")
    results = TestResults()

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = str(Path(temp_dir) / "persistent_memory.db")

        # Phase 1: Store memory
        manager1 = MemoryManager(db_path=db_path, session_id="persistent_session")
        memory_id = manager1.store(
            agent_id="persistent_agent",
            title="Persistent Memory",
            content="This should survive restart",
            metadata={"persistence": True},
            importance=9,
        )

        results.assert_not_none(memory_id, "Persistent memory storage")

        # Verify storage
        stored_memory = manager1.get(memory_id)
        results.assert_not_none(stored_memory, "Memory exists after storage")

        # Close first manager
        del manager1

        # Phase 2: Create new manager and verify persistence
        manager2 = MemoryManager(db_path=db_path, session_id="persistent_session")

        # Retrieve memory with new manager
        retrieved_memory = manager2.get(memory_id)
        results.assert_not_none(retrieved_memory, "Memory persists across restart")

        if retrieved_memory:
            results.assert_equals(
                retrieved_memory.title, "Persistent Memory", "Persistent memory title"
            )
            results.assert_equals(
                retrieved_memory.content, "This should survive restart", "Persistent memory content"
            )
            results.assert_equals(retrieved_memory.importance, 9, "Persistent memory importance")

    results.print_summary()
    return results


def main():
    """Run all memory system tests."""
    print("Starting Memory System Validation Tests")
    print("=" * 50)

    all_results = []

    # Run all test suites
    all_results.append(test_basic_memory_operations())
    all_results.append(test_memory_performance())
    all_results.append(test_session_isolation())
    all_results.append(test_concurrency())
    all_results.append(test_memory_expiration())
    all_results.append(test_database_persistence())

    # Calculate overall results
    total_passed = sum(r.passed for r in all_results)
    total_failed = sum(r.failed for r in all_results)
    total_tests = total_passed + total_failed

    print("\n" + "=" * 50)
    print(f"OVERALL RESULTS: {total_passed}/{total_tests} tests passed")

    if total_failed > 0:
        print(f"{total_failed} tests failed")
        return 1
    else:
        print("All tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
