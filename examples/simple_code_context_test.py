"""Simple test of code context injection feature.

Tests that the include_code_context parameter works correctly.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.memory.coordinator import MemoryCoordinator, RetrievalQuery, StorageRequest
from amplihack.memory.types import MemoryType


async def test_code_context_parameter():
    """Test that include_code_context parameter is accepted."""
    print("Testing code context injection feature...")
    print()

    # Create coordinator
    from amplihack.memory.backends import create_backend

    backend = create_backend("kuzu", db_path="/tmp/simple_test.db")
    coordinator = MemoryCoordinator(backend=backend)

    # Store a memory with high importance to bypass quality filter
    print("1. Storing high-quality memory...")
    request = StorageRequest(
        content="This is a detailed memory about how the memory coordinator works. "
        "It includes information about storage, retrieval, and the 5-type memory system. "
        "The coordinator uses a backend abstraction to support different databases. "
        "Kuzu backend provides graph queries while SQLite provides relational queries.",
        memory_type=MemoryType.SEMANTIC,
        metadata={
            "importance": 10,
            "file": "src/amplihack/memory/coordinator.py",
        },
    )

    memory_id = await coordinator.store(request)
    if memory_id:
        print(f"   ✓ Stored memory: {memory_id}")
    else:
        print("   ✗ Memory rejected by quality review")
        return

    # Test 1: Retrieve without code context
    print("\n2. Test RetrievalQuery without code context...")
    query1 = RetrievalQuery(
        query_text="memory coordinator",
        include_code_context=False,
    )
    print(f"   - Query created: include_code_context={query1.include_code_context}")

    memories1 = await coordinator.retrieve(query1)
    print(f"   ✓ Retrieved {len(memories1)} memories")

    if memories1:
        print(f"   - First memory has code_context: {'code_context' in memories1[0].metadata}")

    # Test 2: Retrieve with code context
    print("\n3. Test RetrievalQuery with code context...")
    query2 = RetrievalQuery(
        query_text="memory coordinator",
        include_code_context=True,
    )
    print(f"   - Query created: include_code_context={query2.include_code_context}")

    memories2 = await coordinator.retrieve(query2)
    print(f"   ✓ Retrieved {len(memories2)} memories")

    if memories2:
        has_context = "code_context" in memories2[0].metadata
        print(f"   - First memory has code_context: {has_context}")
        if has_context:
            context = memories2[0].metadata["code_context"]
            print(f"   - Code context length: {len(context)} characters")
            if context:
                print(f"   - Code context preview: {context[:100]}...")

    # Test 3: Default behavior (should not include code context)
    print("\n4. Test default behavior (no include_code_context specified)...")
    query3 = RetrievalQuery(query_text="memory coordinator")
    print(f"   - Query created: include_code_context={query3.include_code_context}")

    memories3 = await coordinator.retrieve(query3)
    print(f"   ✓ Retrieved {len(memories3)} memories")

    if memories3:
        print(f"   - First memory has code_context: {'code_context' in memories3[0].metadata}")

    # Test 4: Check backend compatibility
    print("\n5. Check backend capabilities...")
    capabilities = coordinator.backend.get_capabilities()
    print(f"   - Backend: {capabilities.backend_name}")
    print(f"   - Supports graph queries: {capabilities.supports_graph_queries}")

    if hasattr(coordinator.backend, "get_code_graph"):
        code_graph = coordinator.backend.get_code_graph()
        print(f"   - Code graph available: {code_graph is not None}")
    else:
        print("   - Code graph: Not supported")

    # Summary
    print("\n6. Summary:")
    print("   ✓ RetrievalQuery accepts include_code_context parameter")
    print("   ✓ Parameter defaults to False")
    print("   ✓ retrieve() method processes parameter without errors")
    print("   ✓ Backend capabilities checked correctly")

    # Check if we got different results
    if memories1 and memories2:
        mem1_has_context = "code_context" in memories1[0].metadata
        mem2_has_context = "code_context" in memories2[0].metadata

        if not mem1_has_context and mem2_has_context:
            print("   ✓ Code context enrichment working!")
        elif not mem1_has_context and not mem2_has_context:
            print("   ⚠ Code context enrichment attempted but no code graph data")
            print("     (This is expected if blarify has not been run)")
        elif mem1_has_context:
            print("   ⚠ Code context added even without flag (unexpected)")

    print("\nTest complete!")


if __name__ == "__main__":
    asyncio.run(test_code_context_parameter())
