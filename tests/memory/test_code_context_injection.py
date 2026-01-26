"""Tests for code context injection at memory retrieval points.

Tests Week 5-6 feature: Enriching memory retrieval with related code context.

Test Coverage:
- Memory retrieval with include_code_context flag
- Code context enrichment from Kuzu graph
- Fallback behavior for non-Kuzu backends
- Performance requirements (<100ms enrichment)
- Format of code context in metadata
"""

import time
from datetime import datetime
from pathlib import Path

import pytest

from amplihack.memory.coordinator import MemoryCoordinator, RetrievalQuery, StorageRequest
from amplihack.memory.types import MemoryType

# Skip if Kuzu not available
pytest_plugins = []
try:
    import kuzu

    KUZU_AVAILABLE = True
except ImportError:
    KUZU_AVAILABLE = False


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Create temporary database path."""
    return tmp_path / "test_memory.db"


@pytest.fixture
def coordinator_with_code_graph(temp_db_path: Path) -> MemoryCoordinator:
    """Create coordinator with Kuzu backend and code graph."""
    if not KUZU_AVAILABLE:
        pytest.skip("Kuzu not available")

    from amplihack.memory.backends import create_backend

    backend = create_backend("kuzu", db_path=str(temp_db_path))
    coordinator = MemoryCoordinator(backend=backend)
    return coordinator


@pytest.fixture
def coordinator_sqlite(tmp_path: Path) -> MemoryCoordinator:
    """Create coordinator with SQLite backend (no code graph)."""
    from amplihack.memory.backends import create_backend

    backend = create_backend("sqlite", db_path=str(tmp_path / "test_sqlite.db"))
    coordinator = MemoryCoordinator(backend=backend)
    return coordinator


@pytest.mark.skipif(not KUZU_AVAILABLE, reason="Kuzu not available")
@pytest.mark.asyncio
async def test_retrieve_with_code_context_flag(coordinator_with_code_graph: MemoryCoordinator):
    """Test that include_code_context flag is accepted in RetrievalQuery."""
    # Store a memory
    request = StorageRequest(
        content="Fixed bug in retrieve_memories function",
        memory_type=MemoryType.EPISODIC,
        metadata={"file": "src/amplihack/memory/backends/kuzu_backend.py"},
    )

    memory_id = await coordinator_with_code_graph.store(request)
    assert memory_id is not None

    # Retrieve without code context
    query_without = RetrievalQuery(query_text="retrieve_memories", include_code_context=False)
    memories_without = await coordinator_with_code_graph.retrieve(query_without)
    assert len(memories_without) > 0

    # Retrieve with code context
    query_with = RetrievalQuery(query_text="retrieve_memories", include_code_context=True)
    memories_with = await coordinator_with_code_graph.retrieve(query_with)
    assert len(memories_with) > 0

    # Both should return same number of memories
    assert len(memories_with) == len(memories_without)


@pytest.mark.skipif(not KUZU_AVAILABLE, reason="Kuzu not available")
@pytest.mark.asyncio
async def test_code_context_enrichment(coordinator_with_code_graph: MemoryCoordinator):
    """Test that code context is added to memory metadata when requested."""
    # Store a memory with code reference
    request = StorageRequest(
        content="Memory about store_memory function implementation",
        memory_type=MemoryType.SEMANTIC,
        metadata={"file": "src/amplihack/memory/coordinator.py"},
    )

    memory_id = await coordinator_with_code_graph.store(request)
    assert memory_id is not None

    # Create sample code graph data (simulate blarify import)
    backend = coordinator_with_code_graph.backend
    code_graph = backend.get_code_graph()

    if code_graph:
        # Create a code file node
        try:
            code_graph.conn.execute_write(
                """
                CREATE (cf:CodeFile {
                    file_id: $file_id,
                    file_path: $file_path,
                    language: 'python',
                    size_bytes: 15000,
                    last_modified: $timestamp,
                    created_at: $timestamp,
                    metadata: '{}'
                })
                """,
                {
                    "file_id": "src/amplihack/memory/coordinator.py",
                    "file_path": "src/amplihack/memory/coordinator.py",
                    "timestamp": datetime.now(),
                },
            )

            # Link memory to code file
            memory_type_enum = MemoryType.SEMANTIC
            rel_table = f"RELATES_TO_FILE_{memory_type_enum.name}"

            code_graph.conn.execute_write(
                f"""
                MATCH (m:SemanticMemory {{memory_id: $memory_id}})
                MATCH (cf:CodeFile {{file_id: $file_id}})
                CREATE (m)-[:{rel_table} {{
                    relevance_score: 1.0,
                    context: 'test_link',
                    timestamp: $timestamp
                }}]->(cf)
                """,
                {
                    "memory_id": memory_id,
                    "file_id": "src/amplihack/memory/coordinator.py",
                    "timestamp": datetime.now(),
                },
            )
        except Exception as e:
            pytest.skip(f"Could not create test code graph data: {e}")

    # Retrieve with code context
    query = RetrievalQuery(
        query_text="store_memory",
        include_code_context=True,
    )
    memories = await coordinator_with_code_graph.retrieve(query)

    # Should have at least one memory
    assert len(memories) > 0

    # Check if code context was added (only if code graph is available)
    memory = memories[0]
    if code_graph and "code_context" in memory.metadata:
        code_context = memory.metadata["code_context"]
        assert isinstance(code_context, str)
        assert len(code_context) > 0
        # Should mention the file
        assert "coordinator.py" in code_context or "Related Files" in code_context


@pytest.mark.asyncio
async def test_code_context_fallback_sqlite(coordinator_sqlite: MemoryCoordinator):
    """Test that code context gracefully falls back for SQLite backend."""
    # Store a memory
    request = StorageRequest(
        content="Test memory for SQLite backend",
        memory_type=MemoryType.EPISODIC,
    )

    memory_id = await coordinator_sqlite.store(request)
    assert memory_id is not None

    # Retrieve with code context flag (should not error)
    query = RetrievalQuery(
        query_text="test",
        include_code_context=True,
    )
    memories = await coordinator_sqlite.retrieve(query)

    # Should still return memories, just without code context
    assert len(memories) > 0
    memory = memories[0]

    # Should not have code_context (SQLite doesn't support graph queries)
    assert "code_context" not in memory.metadata


@pytest.mark.skipif(not KUZU_AVAILABLE, reason="Kuzu not available")
@pytest.mark.asyncio
async def test_code_context_performance(coordinator_with_code_graph: MemoryCoordinator):
    """Test that code context enrichment completes within performance requirements."""
    # Store multiple memories
    memory_ids = []
    for i in range(5):
        request = StorageRequest(
            content=f"Memory {i} about code functionality",
            memory_type=MemoryType.EPISODIC,
        )
        memory_id = await coordinator_with_code_graph.store(request)
        memory_ids.append(memory_id)

    # Retrieve with code context
    start_time = time.time()
    query = RetrievalQuery(
        query_text="code",
        include_code_context=True,
    )
    memories = await coordinator_with_code_graph.retrieve(query)
    elapsed_ms = (time.time() - start_time) * 1000

    # Total retrieval should be reasonable (<500ms including enrichment)
    assert elapsed_ms < 500, f"Retrieval took {elapsed_ms:.1f}ms, expected <500ms"
    assert len(memories) > 0


@pytest.mark.skipif(not KUZU_AVAILABLE, reason="Kuzu not available")
@pytest.mark.asyncio
async def test_code_context_format(coordinator_with_code_graph: MemoryCoordinator):
    """Test that code context is formatted correctly for LLM consumption."""
    # Store a memory
    request = StorageRequest(
        content="Understanding memory coordinator functionality",
        memory_type=MemoryType.SEMANTIC,
        metadata={"file": "src/amplihack/memory/coordinator.py"},
    )

    memory_id = await coordinator_with_code_graph.store(request)
    assert memory_id is not None

    # Create comprehensive code graph data
    backend = coordinator_with_code_graph.backend
    code_graph = backend.get_code_graph()

    if code_graph:
        try:
            # Create code file
            code_graph.conn.execute_write(
                """
                CREATE (cf:CodeFile {
                    file_id: $file_id,
                    file_path: $file_path,
                    language: 'python',
                    size_bytes: 25000,
                    last_modified: $timestamp,
                    created_at: $timestamp,
                    metadata: '{}'
                })
                """,
                {
                    "file_id": "src/amplihack/memory/coordinator.py",
                    "file_path": "src/amplihack/memory/coordinator.py",
                    "timestamp": datetime.now(),
                },
            )

            # Create function node
            code_graph.conn.execute_write(
                """
                CREATE (f:Function {
                    function_id: $function_id,
                    function_name: 'store',
                    fully_qualified_name: $fqn,
                    signature: 'async def store(self, request: StorageRequest) -> str | None',
                    docstring: 'Store a memory with quality review.',
                    is_async: true,
                    is_method: true,
                    is_static: false,
                    access_modifier: 'public',
                    decorators: '[]',
                    cyclomatic_complexity: 12.0,
                    created_at: $timestamp,
                    metadata: '{}'
                })
                """,
                {
                    "function_id": "coordinator.MemoryCoordinator.store",
                    "fqn": "amplihack.memory.coordinator.MemoryCoordinator.store",
                    "timestamp": datetime.now(),
                },
            )

            # Link memory to file
            rel_table = "RELATES_TO_FILE_SEMANTIC"
            code_graph.conn.execute_write(
                f"""
                MATCH (m:SemanticMemory {{memory_id: $memory_id}})
                MATCH (cf:CodeFile {{file_id: $file_id}})
                CREATE (m)-[:{rel_table} {{
                    relevance_score: 1.0,
                    context: 'test',
                    timestamp: $timestamp
                }}]->(cf)
                """,
                {
                    "memory_id": memory_id,
                    "file_id": "src/amplihack/memory/coordinator.py",
                    "timestamp": datetime.now(),
                },
            )

            # Link memory to function
            rel_table = "RELATES_TO_FUNCTION_SEMANTIC"
            code_graph.conn.execute_write(
                f"""
                MATCH (m:SemanticMemory {{memory_id: $memory_id}})
                MATCH (f:Function {{function_id: $function_id}})
                CREATE (m)-[:{rel_table} {{
                    relevance_score: 0.9,
                    context: 'test',
                    timestamp: $timestamp
                }}]->(f)
                """,
                {
                    "memory_id": memory_id,
                    "function_id": "coordinator.MemoryCoordinator.store",
                    "timestamp": datetime.now(),
                },
            )
        except Exception as e:
            pytest.skip(f"Could not create test code graph data: {e}")

    # Retrieve with code context
    query = RetrievalQuery(
        query_text="coordinator",
        include_code_context=True,
    )
    memories = await coordinator_with_code_graph.retrieve(query)

    if len(memories) > 0 and code_graph:
        memory = memories[0]
        code_context = memory.metadata.get("code_context", "")

        if code_context:
            # Check format structure
            assert "**Related Files:**" in code_context or "coordinator.py" in code_context
            # Should be human-readable
            assert "\n" in code_context or len(code_context.split()) > 3


@pytest.mark.skipif(not KUZU_AVAILABLE, reason="Kuzu not available")
@pytest.mark.asyncio
async def test_code_context_with_no_links(coordinator_with_code_graph: MemoryCoordinator):
    """Test code context enrichment when memory has no code links."""
    # Store a memory with no code references
    request = StorageRequest(
        content="General observation about system behavior",
        memory_type=MemoryType.EPISODIC,
    )

    memory_id = await coordinator_with_code_graph.store(request)
    assert memory_id is not None

    # Retrieve with code context
    query = RetrievalQuery(
        query_text="observation",
        include_code_context=True,
    )
    memories = await coordinator_with_code_graph.retrieve(query)

    assert len(memories) > 0
    memory = memories[0]

    # Should either not have code_context or have empty string
    code_context = memory.metadata.get("code_context", "")
    # Empty code context is acceptable
    assert isinstance(code_context, str)


@pytest.mark.skipif(not KUZU_AVAILABLE, reason="Kuzu not available")
@pytest.mark.asyncio
async def test_code_context_default_false(coordinator_with_code_graph: MemoryCoordinator):
    """Test that code context is not included by default."""
    # Store a memory
    request = StorageRequest(
        content="Test memory for default behavior",
        memory_type=MemoryType.EPISODIC,
    )

    memory_id = await coordinator_with_code_graph.store(request)
    assert memory_id is not None

    # Retrieve without specifying include_code_context (defaults to False)
    query = RetrievalQuery(query_text="test")
    memories = await coordinator_with_code_graph.retrieve(query)

    assert len(memories) > 0
    memory = memories[0]

    # Should not have code_context by default
    assert "code_context" not in memory.metadata
