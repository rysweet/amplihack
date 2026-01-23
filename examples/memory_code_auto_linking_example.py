"""Example demonstrating automated memory-code linking.

This example shows how memories are automatically linked to code entities
when they are stored in the Kuzu backend.

Week 3 functionality:
- Auto-linking to files based on metadata
- Auto-linking to functions based on content
- Relevance scoring (1.0 for metadata, 0.8 for content)
- Link deduplication

Run this after running blarify on your codebase:
    python examples/memory_code_auto_linking_example.py
"""

import tempfile
from datetime import datetime
from pathlib import Path

from src.amplihack.memory.backends.kuzu_backend import KuzuBackend
from src.amplihack.memory.kuzu.code_graph import KuzuCodeGraph
from src.amplihack.memory.kuzu.connector import KuzuConnector
from src.amplihack.memory.models import MemoryEntry, MemoryQuery, MemoryType


def setup_sample_code_graph(backend: KuzuBackend):
    """Create sample code entities for demonstration."""
    print("\n📦 Setting up sample code graph...")

    # Create sample code files
    backend.connection.execute(
        """
        CREATE (cf:CodeFile {
            file_id: 'src/main.py',
            file_path: 'src/main.py',
            language: 'python',
            size_bytes: 1500,
            last_modified: $now,
            created_at: $now,
            metadata: '{}'
        })
        """,
        {"now": datetime.now()},
    )

    backend.connection.execute(
        """
        CREATE (cf:CodeFile {
            file_id: 'src/utils.py',
            file_path: 'src/utils.py',
            language: 'python',
            size_bytes: 800,
            last_modified: $now,
            created_at: $now,
            metadata: '{}'
        })
        """,
        {"now": datetime.now()},
    )

    # Create sample functions
    backend.connection.execute(
        """
        CREATE (f:Function {
            function_id: 'src/main.py::process_data',
            function_name: 'process_data',
            fully_qualified_name: 'main.process_data',
            signature: 'process_data(data: dict) -> dict',
            docstring: 'Processes input data and returns results',
            is_async: false,
            cyclomatic_complexity: 5,
            created_at: $now,
            metadata: '{}'
        })
        """,
        {"now": datetime.now()},
    )

    backend.connection.execute(
        """
        CREATE (f:Function {
            function_id: 'src/utils.py::validate_input',
            function_name: 'validate_input',
            fully_qualified_name: 'utils.validate_input',
            signature: 'validate_input(data: dict) -> bool',
            docstring: 'Validates input data structure',
            is_async: false,
            cyclomatic_complexity: 3,
            created_at: $now,
            metadata: '{}'
        })
        """,
        {"now": datetime.now()},
    )

    # Link functions to files
    backend.connection.execute(
        """
        MATCH (f:Function {function_id: 'src/main.py::process_data'})
        MATCH (cf:CodeFile {file_id: 'src/main.py'})
        CREATE (f)-[:DEFINED_IN_FUNCTION {line_number: 10, end_line: 30}]->(cf)
        """
    )

    backend.connection.execute(
        """
        MATCH (f:Function {function_id: 'src/utils.py::validate_input'})
        MATCH (cf:CodeFile {file_id: 'src/utils.py'})
        CREATE (f)-[:DEFINED_IN_FUNCTION {line_number: 5, end_line: 15}]->(cf)
        """
    )

    print("✓ Sample code graph created")


def demonstrate_file_linking(backend: KuzuBackend):
    """Demonstrate auto-linking to files via metadata."""
    print("\n🔗 Demonstrating file-based auto-linking...")

    # Create a memory with file path in metadata
    memory = MemoryEntry(
        id="mem-file-1",
        session_id="demo-session",
        agent_id="demo-agent",
        memory_type=MemoryType.EPISODIC,
        title="Modified Main Module",
        content="Refactored data processing logic for better performance",
        metadata={"file": "src/main.py", "change_type": "refactor"},
        created_at=datetime.now(),
        accessed_at=datetime.now(),
    )

    # Store memory - auto-linking happens automatically
    success = backend.store_memory(memory)
    print(f"  Memory stored: {success}")

    # Verify the link was created
    result = backend.connection.execute(
        """
        MATCH (m:EpisodicMemory {memory_id: $memory_id})-[r:RELATES_TO_FILE_EPISODIC]->(cf:CodeFile)
        RETURN cf.file_path, r.relevance_score, r.context
        """,
        {"memory_id": memory.id},
    )

    if result.has_next():
        row = result.get_next()
        print(f"  ✓ Auto-linked to: {row[0]}")
        print(f"    Relevance score: {row[1]} (metadata match)")
        print(f"    Context: {row[2]}")
    else:
        print("  ✗ No link created")


def demonstrate_function_linking(backend: KuzuBackend):
    """Demonstrate auto-linking to functions via content."""
    print("\n🔗 Demonstrating function-based auto-linking...")

    # Create a memory mentioning a function name
    memory = MemoryEntry(
        id="mem-func-1",
        session_id="demo-session",
        agent_id="demo-agent",
        memory_type=MemoryType.SEMANTIC,
        title="Input Validation Pattern",
        content="The validate_input function ensures all required fields are present before processing",
        metadata={"category": "patterns"},
        created_at=datetime.now(),
        accessed_at=datetime.now(),
    )

    # Store memory - auto-linking happens automatically
    success = backend.store_memory(memory)
    print(f"  Memory stored: {success}")

    # Verify the link was created
    result = backend.connection.execute(
        """
        MATCH (m:SemanticMemory {memory_id: $memory_id})-[r:RELATES_TO_FUNCTION_SEMANTIC]->(f:Function)
        RETURN f.function_name, r.relevance_score, r.context
        """,
        {"memory_id": memory.id},
    )

    if result.has_next():
        row = result.get_next()
        print(f"  ✓ Auto-linked to: {row[0]}()")
        print(f"    Relevance score: {row[1]} (content match)")
        print(f"    Context: {row[2]}")
    else:
        print("  ✗ No link created")


def demonstrate_mixed_linking(backend: KuzuBackend):
    """Demonstrate auto-linking to both files and functions."""
    print("\n🔗 Demonstrating mixed auto-linking...")

    # Create a memory with both file metadata and function mention
    memory = MemoryEntry(
        id="mem-mixed-1",
        session_id="demo-session",
        agent_id="demo-agent",
        memory_type=MemoryType.PROCEDURAL,
        title="Data Processing Workflow",
        content="Call process_data after validation to transform the input",
        metadata={"file": "src/main.py", "workflow": "etl"},
        created_at=datetime.now(),
        accessed_at=datetime.now(),
    )

    # Store memory - auto-linking happens automatically
    success = backend.store_memory(memory)
    print(f"  Memory stored: {success}")

    # Verify file link
    file_result = backend.connection.execute(
        """
        MATCH (m:ProceduralMemory {memory_id: $memory_id})-[r:RELATES_TO_FILE_PROCEDURAL]->(cf:CodeFile)
        RETURN cf.file_path, r.relevance_score
        """,
        {"memory_id": memory.id},
    )

    if file_result.has_next():
        row = file_result.get_next()
        print(f"  ✓ Linked to file: {row[0]} (score: {row[1]})")

    # Verify function link
    func_result = backend.connection.execute(
        """
        MATCH (m:ProceduralMemory {memory_id: $memory_id})-[r:RELATES_TO_FUNCTION_PROCEDURAL]->(f:Function)
        RETURN f.function_name, r.relevance_score
        """,
        {"memory_id": memory.id},
    )

    if func_result.has_next():
        row = func_result.get_next()
        print(f"  ✓ Linked to function: {row[0]}() (score: {row[1]})")


def demonstrate_link_deduplication(backend: KuzuBackend):
    """Demonstrate that duplicate links are not created."""
    print("\n🔗 Demonstrating link deduplication...")

    # Store first memory
    memory1 = MemoryEntry(
        id="mem-dedup-1",
        session_id="demo-session",
        agent_id="demo-agent",
        memory_type=MemoryType.EPISODIC,
        title="File Update",
        content="Updated configuration",
        metadata={"file": "src/utils.py"},
        created_at=datetime.now(),
        accessed_at=datetime.now(),
    )

    backend.store_memory(memory1)
    print("  First memory stored")

    # Count links after first storage
    result1 = backend.connection.execute(
        """
        MATCH (m:EpisodicMemory {memory_id: $memory_id})-[r:RELATES_TO_FILE_EPISODIC]->()
        RETURN COUNT(r) AS link_count
        """,
        {"memory_id": memory1.id},
    )

    if result1.has_next():
        first_count = result1.get_next()[0]
        print(f"  Links after first memory: {first_count}")

    # Store second memory with same file (should not create duplicate link to same file)
    memory2 = MemoryEntry(
        id="mem-dedup-2",
        session_id="demo-session",
        agent_id="demo-agent",
        memory_type=MemoryType.EPISODIC,
        title="Another File Update",
        content="More updates",
        metadata={"file": "src/utils.py"},
        created_at=datetime.now(),
        accessed_at=datetime.now(),
    )

    backend.store_memory(memory2)
    print("  Second memory stored (same file)")

    # Count links for second memory
    result2 = backend.connection.execute(
        """
        MATCH (m:EpisodicMemory {memory_id: $memory_id})-[r:RELATES_TO_FILE_EPISODIC]->()
        RETURN COUNT(r) AS link_count
        """,
        {"memory_id": memory2.id},
    )

    if result2.has_next():
        second_count = result2.get_next()[0]
        print(f"  Links for second memory: {second_count}")

        # Both memories should have their own links (no duplication at memory level)
        if first_count == 1 and second_count == 1:
            print("  ✓ Each memory has its own link (no interference)")
        else:
            print("  ✗ Unexpected link counts")


def demonstrate_disabled_linking(backend: KuzuBackend):
    """Demonstrate that auto-linking can be disabled."""
    print("\n🔗 Demonstrating disabled auto-linking...")

    # Create backend with auto-linking disabled
    with tempfile.TemporaryDirectory() as tmpdir:
        disabled_backend = KuzuBackend(
            db_path=f"{tmpdir}/disabled_db", enable_auto_linking=False
        )
        disabled_backend.initialize()

        # Setup same code graph
        setup_sample_code_graph(disabled_backend)

        memory = MemoryEntry(
            id="mem-disabled-1",
            session_id="demo-session",
            agent_id="demo-agent",
            memory_type=MemoryType.EPISODIC,
            title="Test Event",
            content="Test content mentioning validate_input",
            metadata={"file": "src/main.py"},
            created_at=datetime.now(),
            accessed_at=datetime.now(),
        )

        disabled_backend.store_memory(memory)
        print("  Memory stored with auto-linking disabled")

        # Check for links (check both file and function relationships)
        file_result = disabled_backend.connection.execute(
            """
            MATCH (m:EpisodicMemory {memory_id: $memory_id})-[r:RELATES_TO_FILE_EPISODIC]->()
            RETURN COUNT(r) AS link_count
            """,
            {"memory_id": memory.id},
        )

        func_result = disabled_backend.connection.execute(
            """
            MATCH (m:EpisodicMemory {memory_id: $memory_id})-[r:RELATES_TO_FUNCTION_EPISODIC]->()
            RETURN COUNT(r) AS link_count
            """,
            {"memory_id": memory.id},
        )

        file_count = file_result.get_next()[0] if file_result.has_next() else 0
        func_count = func_result.get_next()[0] if func_result.has_next() else 0
        total_count = file_count + func_count

        if total_count == 0:
            print("  ✓ No auto-links created (as expected)")
        else:
            print(f"  ✗ {total_count} links created (unexpected)")


def main():
    """Run all auto-linking demonstrations."""
    print("=" * 60)
    print("Memory-Code Auto-Linking Demonstration")
    print("=" * 60)

    # Create temporary database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "demo_db"

        # Initialize backend with auto-linking enabled (default)
        backend = KuzuBackend(db_path=str(db_path), enable_auto_linking=True)
        backend.initialize()

        print("\n✓ Database initialized")
        print(f"  Location: {db_path}")
        print(f"  Auto-linking: enabled")

        # Setup sample code graph
        setup_sample_code_graph(backend)

        # Run demonstrations
        demonstrate_file_linking(backend)
        demonstrate_function_linking(backend)
        demonstrate_mixed_linking(backend)
        demonstrate_link_deduplication(backend)
        demonstrate_disabled_linking(backend)

        # Summary
        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)

        # Count all memories
        mem_result = backend.connection.execute(
            """
            MATCH (m:EpisodicMemory)
            RETURN COUNT(m) AS count
            """
        )
        episodic_count = mem_result.get_next()[0] if mem_result.has_next() else 0

        mem_result = backend.connection.execute(
            """
            MATCH (m:SemanticMemory)
            RETURN COUNT(m) AS count
            """
        )
        semantic_count = mem_result.get_next()[0] if mem_result.has_next() else 0

        mem_result = backend.connection.execute(
            """
            MATCH (m:ProceduralMemory)
            RETURN COUNT(m) AS count
            """
        )
        procedural_count = mem_result.get_next()[0] if mem_result.has_next() else 0

        # Count all links (manually sum all RELATES_TO relationships)
        link_count = 0
        for memory_type in ["EPISODIC", "SEMANTIC", "PROCEDURAL", "PROSPECTIVE", "WORKING"]:
            for target in ["FILE", "FUNCTION"]:
                rel_type = f"RELATES_TO_{target}_{memory_type}"
                try:
                    result = backend.connection.execute(
                        f"MATCH ()-[r:{rel_type}]->() RETURN COUNT(r) AS count"
                    )
                    if result.has_next():
                        link_count += result.get_next()[0]
                except Exception:
                    pass  # Relationship type may not have any instances

        print(f"  Total memories created: {episodic_count + semantic_count + procedural_count}")
        print(f"    Episodic: {episodic_count}")
        print(f"    Semantic: {semantic_count}")
        print(f"    Procedural: {procedural_count}")
        print(f"  Total auto-links created: {link_count}")
        print("\n✓ Auto-linking demonstration complete!")


if __name__ == "__main__":
    main()
