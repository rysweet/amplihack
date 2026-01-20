#!/usr/bin/env python3
"""Example usage of the pluggable backend system.

Demonstrates:
- Backend selection
- Backend capabilities
- Switching between backends
- Custom backend configuration
"""

import asyncio
from datetime import datetime

from amplihack.memory.coordinator import MemoryCoordinator, StorageRequest
from amplihack.memory.types import MemoryType


async def example_default_backend():
    """Example 1: Using default backend (Kùzu or SQLite)."""
    print("=" * 60)
    print("Example 1: Default Backend")
    print("=" * 60)

    coordinator = MemoryCoordinator()

    # Check which backend was selected
    backend_info = coordinator.get_backend_info()
    print(f"\nBackend: {backend_info['backend_name']} v{backend_info['backend_version']}")
    print(f"Supports graph queries: {backend_info['supports_graph_queries']}")
    print(f"Supports vector search: {backend_info['supports_vector_search']}")

    # Store a memory
    request = StorageRequest(
        content="Learned about pluggable backend architecture in memory system",
        memory_type=MemoryType.SEMANTIC,
        metadata={"topic": "architecture", "importance": "high"},
    )

    memory_id = await coordinator.store(request)
    print(f"\nStored memory: {memory_id}")

    # Get statistics
    stats = coordinator.get_statistics()
    print(f"Total stored: {stats['total_stored']}")
    print(f"Total memories: {stats['total_memories']}")


async def example_explicit_sqlite():
    """Example 2: Explicitly using SQLite backend."""
    print("\n" + "=" * 60)
    print("Example 2: Explicit SQLite Backend")
    print("=" * 60)

    coordinator = MemoryCoordinator(backend_type="sqlite", db_path="/tmp/example_memory.db")

    backend_info = coordinator.get_backend_info()
    print(f"\nBackend: {backend_info['backend_name']}")
    print(f"Max connections: {backend_info['max_concurrent_connections']}")

    # Store episodic memory
    request = StorageRequest(
        content="User requested SQLite backend explicitly in example script",
        memory_type=MemoryType.EPISODIC,
        context={"timestamp": datetime.now().isoformat(), "source": "example"},
    )

    memory_id = await coordinator.store(request)
    print(f"\nStored episodic memory: {memory_id}")


async def example_backend_comparison():
    """Example 3: Comparing backend capabilities."""
    print("\n" + "=" * 60)
    print("Example 3: Backend Comparison")
    print("=" * 60)

    # Create coordinators with different backends
    backends = ["sqlite"]  # Add "kuzu" when available

    for backend_name in backends:
        try:
            coordinator = MemoryCoordinator(backend_type=backend_name)
            info = coordinator.get_backend_info()

            print(f"\n{backend_name.upper()} Backend:")
            print(f"  - Transactions: {info['supports_transactions']}")
            print(f"  - Graph queries: {info['supports_graph_queries']}")
            print(f"  - Vector search: {info['supports_vector_search']}")
            print(f"  - Full-text search: {info['supports_fulltext_search']}")
            print(f"  - Max connections: {info['max_concurrent_connections']}")

        except Exception as e:
            print(f"\n{backend_name.upper()} Backend: Not available ({e})")


async def example_working_memory():
    """Example 4: Working memory with task management."""
    print("\n" + "=" * 60)
    print("Example 4: Working Memory (Task Context)")
    print("=" * 60)

    coordinator = MemoryCoordinator()

    # Store working memory fer active task
    request = StorageRequest(
        content="Currently implementing backend abstraction layer",
        memory_type=MemoryType.WORKING,
        context={"task_id": "task-123", "status": "in_progress"},
        metadata={
            "variables": {"current_file": "backend_usage.py", "line": 100},
            "dependencies": ["SQLite", "Kùzu"],
        },
    )

    memory_id = await coordinator.store(request)
    print(f"\nStored working memory: {memory_id}")

    # Clear working memory when task completes
    await coordinator.mark_task_complete("task-123")
    print("Task completed - working memory cleared")


async def example_prospective_memory():
    """Example 5: Prospective memory (future intentions)."""
    print("\n" + "=" * 60)
    print("Example 5: Prospective Memory (TODOs)")
    print("=" * 60)

    coordinator = MemoryCoordinator()

    # Store prospective memory (TODO/reminder)
    request = StorageRequest(
        content="TODO: Test Kùzu backend with real installation",
        memory_type=MemoryType.PROSPECTIVE,
        metadata={
            "trigger": "when_kuzu_installed",
            "deadline": "2024-12-31",
            "priority": "high",
        },
    )

    memory_id = await coordinator.store(request)
    print(f"\nStored prospective memory (TODO): {memory_id}")


async def main():
    """Run all examples."""
    print("\n🔱 Pluggable Backend System Examples 🔱\n")

    await example_default_backend()
    await example_explicit_sqlite()
    await example_backend_comparison()
    await example_working_memory()
    await example_prospective_memory()

    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
