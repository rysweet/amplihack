#!/usr/bin/env python3
"""Comprehensive test script for Neo4j Memory API.

Tests all CRUD operations for the five memory types:
- Episodic Memory
- Short-Term Memory
- Procedural Memory
- Declarative Memory
- Prospective Memory

Usage:
    python scripts/test_memory_api.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.memory.neo4j import (
    DeclarativeMemory,
    EpisodicMemory,
    MemoryStore,
    ProceduralMemory,
    ProspectiveMemory,
    ShortTermMemory,
    Neo4jConnector,
    ensure_neo4j_running,
)


def test_episodic_memory(store: MemoryStore):
    """Test episodic memory CRUD operations."""
    print("\n=== Testing Episodic Memory ===")

    # Create
    memory = EpisodicMemory(
        content="User requested authentication feature implementation",
        agent_type="architect",
        metadata={"session_id": "test-123", "task": "auth-feature"},
    )

    memory_id = store.create_memory(
        content=memory.content,
        agent_type=memory.agent_type,
        memory_type="episodic",
        metadata=memory.metadata,
    )
    print(f"✓ Created episodic memory: {memory_id}")

    # Read
    retrieved = store.get_memory(memory_id)
    assert retrieved is not None, "Memory should exist"
    assert retrieved["content"] == memory.content
    print(f"✓ Retrieved episodic memory: {retrieved['id']}")

    # Update
    updated = store.update_memory(
        memory_id,
        content="User requested authentication with OAuth2 support",
    )
    assert updated, "Memory should be updated"
    print(f"✓ Updated episodic memory: {memory_id}")

    # Search
    memories = store.search_memories("authentication", agent_type="architect")
    assert len(memories) > 0, "Should find memories"
    print(f"✓ Found {len(memories)} episodic memories via search")

    # Delete
    deleted = store.delete_memory(memory_id)
    assert deleted, "Memory should be deleted"
    print(f"✓ Deleted episodic memory: {memory_id}")

    print("✅ Episodic memory tests passed!")


def test_short_term_memory(store: MemoryStore):
    """Test short-term memory CRUD operations."""
    print("\n=== Testing Short-Term Memory ===")

    # Create
    memory = ShortTermMemory(
        content="Current module uses async/await pattern",
        agent_type="builder",
        metadata={"file": "auth.py", "pattern": "async"},
    )

    memory_id = store.create_memory(
        content=memory.content,
        agent_type=memory.agent_type,
        memory_type="short_term",
        metadata=memory.metadata,
    )
    print(f"✓ Created short-term memory: {memory_id}")

    # Read
    retrieved = store.get_memory(memory_id)
    assert retrieved is not None
    print(f"✓ Retrieved short-term memory: {retrieved['id']}")

    # Update metadata
    updated = store.update_memory(
        memory_id,
        metadata={"file": "auth.py", "pattern": "async", "updated": True},
    )
    assert updated
    print(f"✓ Updated short-term memory: {memory_id}")

    # Delete
    deleted = store.delete_memory(memory_id)
    assert deleted
    print(f"✓ Deleted short-term memory: {memory_id}")

    print("✅ Short-term memory tests passed!")


def test_procedural_memory(store: MemoryStore):
    """Test procedural memory CRUD operations."""
    print("\n=== Testing Procedural Memory ===")

    # Create
    memory = ProceduralMemory(
        content="To add new API endpoint: 1) Define route 2) Add handler 3) Write tests",
        agent_type="builder",
        metadata={"category": "api-development", "complexity": "medium"},
    )

    memory_id = store.create_memory(
        content=memory.content,
        agent_type=memory.agent_type,
        memory_type="procedural",
        metadata=memory.metadata,
    )
    print(f"✓ Created procedural memory: {memory_id}")

    # Read
    retrieved = store.get_memory(memory_id)
    assert retrieved is not None
    print(f"✓ Retrieved procedural memory: {retrieved['id']}")

    # Search by agent type (set min_quality to 0.0 to include all)
    memories = store.get_memories_by_agent_type("builder", min_quality=0.0)
    assert len(memories) > 0
    print(f"✓ Found {len(memories)} procedural memories for builder agent")

    # Delete
    deleted = store.delete_memory(memory_id)
    assert deleted
    print(f"✓ Deleted procedural memory: {memory_id}")

    print("✅ Procedural memory tests passed!")


def test_declarative_memory(store: MemoryStore):
    """Test declarative memory CRUD operations."""
    print("\n=== Testing Declarative Memory ===")

    # Create
    memory = DeclarativeMemory(
        content="System uses PostgreSQL 15 with UUID primary keys",
        agent_type="architect",
        metadata={"category": "database", "source": "architecture-doc"},
    )

    memory_id = store.create_memory(
        content=memory.content,
        agent_type=memory.agent_type,
        memory_type="declarative",
        metadata=memory.metadata,
    )
    print(f"✓ Created declarative memory: {memory_id}")

    # Read
    retrieved = store.get_memory(memory_id)
    assert retrieved is not None
    print(f"✓ Retrieved declarative memory: {retrieved['id']}")

    # Search
    memories = store.search_memories("PostgreSQL")
    assert len(memories) > 0
    print(f"✓ Found {len(memories)} declarative memories via search")

    # Delete
    deleted = store.delete_memory(memory_id)
    assert deleted
    print(f"✓ Deleted declarative memory: {memory_id}")

    print("✅ Declarative memory tests passed!")


def test_prospective_memory(store: MemoryStore):
    """Test prospective memory CRUD operations."""
    print("\n=== Testing Prospective Memory ===")

    # Create
    memory = ProspectiveMemory(
        content="Add rate limiting to API after authentication is complete",
        agent_type="architect",
        metadata={"status": "pending", "depends_on": "auth-feature"},
    )

    memory_id = store.create_memory(
        content=memory.content,
        agent_type=memory.agent_type,
        memory_type="prospective",
        metadata=memory.metadata,
    )
    print(f"✓ Created prospective memory: {memory_id}")

    # Read
    retrieved = store.get_memory(memory_id)
    assert retrieved is not None
    print(f"✓ Retrieved prospective memory: {retrieved['id']}")

    # Update status
    updated = store.update_memory(
        memory_id,
        metadata={"status": "completed", "depends_on": "auth-feature"},
    )
    assert updated
    print(f"✓ Updated prospective memory status: {memory_id}")

    # Delete
    deleted = store.delete_memory(memory_id)
    assert deleted
    print(f"✓ Deleted prospective memory: {memory_id}")

    print("✅ Prospective memory tests passed!")


def test_agent_type_linking(store: MemoryStore):
    """Test agent type linking functionality."""
    print("\n=== Testing Agent Type Linking ===")

    # Create memories for different agent types
    architect_memory = store.create_memory(
        content="Design decision: Use microservices architecture",
        agent_type="architect",
        memory_type="declarative",
    )
    print(f"✓ Created memory for architect: {architect_memory}")

    builder_memory = store.create_memory(
        content="Implemented user service",
        agent_type="builder",
        memory_type="episodic",
    )
    print(f"✓ Created memory for builder: {builder_memory}")

    # Retrieve by agent type
    architect_memories = store.get_memories_by_agent_type("architect")
    assert len(architect_memories) > 0
    print(f"✓ Found {len(architect_memories)} memories for architect")

    builder_memories = store.get_memories_by_agent_type("builder")
    assert len(builder_memories) > 0
    print(f"✓ Found {len(builder_memories)} memories for builder")

    # Cleanup
    store.delete_memory(architect_memory)
    store.delete_memory(builder_memory)
    print("✓ Cleaned up test memories")

    print("✅ Agent type linking tests passed!")


def test_statistics(store: MemoryStore):
    """Test memory statistics."""
    print("\n=== Testing Memory Statistics ===")

    # Create some test memories
    memory_ids = []
    for i in range(3):
        memory_id = store.create_memory(
            content=f"Test memory {i}",
            agent_type="tester",
            memory_type="episodic",
        )
        memory_ids.append(memory_id)

    print(f"✓ Created {len(memory_ids)} test memories")

    # Get statistics
    stats = store.get_memory_stats(agent_type="tester")
    assert stats["total_memories"] >= 3
    print(f"✓ Statistics: {stats}")

    # Cleanup
    for memory_id in memory_ids:
        store.delete_memory(memory_id)
    print("✓ Cleaned up test memories")

    print("✅ Statistics tests passed!")


def main():
    """Run all tests."""
    print("=" * 70)
    print("Neo4j Memory API Comprehensive Test Suite")
    print("=" * 70)

    # Ensure Neo4j is running
    print("\nEnsuring Neo4j is running...")
    ensure_neo4j_running(blocking=True)
    print("✓ Neo4j is running")

    # Create connector and store
    print("\nConnecting to Neo4j...")
    connector = Neo4jConnector()
    connector.connect()
    print("✓ Connected to Neo4j")

    store = MemoryStore(connector)
    print("✓ Memory store initialized")

    try:
        # Run all tests
        test_episodic_memory(store)
        test_short_term_memory(store)
        test_procedural_memory(store)
        test_declarative_memory(store)
        test_prospective_memory(store)
        test_agent_type_linking(store)
        test_statistics(store)

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        return 0

    except Exception as e:
        print("\n" + "=" * 70)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 70)
        import traceback

        traceback.print_exc()
        return 1

    finally:
        connector.close()
        print("\n✓ Connection closed")


if __name__ == "__main__":
    sys.exit(main())
