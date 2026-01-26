#!/usr/bin/env python3
"""Example usage of Kuzu code graph integration.

Demonstrates:
1. Running blarify on a codebase
2. Importing code graph into Kuzu
3. Linking memories to code
4. Querying code context
"""

import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.memory.kuzu import KuzuCodeGraph, KuzuConnector


def example_import_code():
    """Example: Import code graph from blarify JSON."""
    print("=" * 60)
    print("EXAMPLE 1: Import Code Graph")
    print("=" * 60)

    # Create sample blarify output
    sample_data = {
        "files": [
            {
                "path": "example/app.py",
                "language": "python",
                "lines_of_code": 100,
                "last_modified": "2025-01-01T00:00:00Z",
            }
        ],
        "classes": [
            {
                "id": "class:App",
                "name": "App",
                "file_path": "example/app.py",
                "line_number": 10,
                "docstring": "Main application class",
                "is_abstract": False,
            }
        ],
        "functions": [
            {
                "id": "func:App.run",
                "name": "run",
                "file_path": "example/app.py",
                "line_number": 20,
                "docstring": "Run the application",
                "parameters": ["self"],
                "return_type": "None",
                "is_async": False,
                "complexity": 5,
                "class_id": "class:App",
            }
        ],
        "imports": [],
        "relationships": [],
    }

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(sample_data, f)
        json_path = Path(f.name)

    try:
        # Connect to Kuzu
        with KuzuConnector(db_path=":memory:") as conn:
            # Initialize schema (simplified for example)
            conn.execute_query("""
                CREATE NODE TABLE IF NOT EXISTS CodeFile(
                    file_id STRING PRIMARY KEY,
                    file_path STRING,
                    language STRING,
                    size_bytes INT64,
                    last_modified TIMESTAMP,
                    created_at TIMESTAMP,
                    metadata STRING
                )
            """)

            conn.execute_query("""
                CREATE NODE TABLE IF NOT EXISTS Class(
                    class_id STRING PRIMARY KEY,
                    class_name STRING,
                    fully_qualified_name STRING,
                    docstring STRING,
                    is_abstract BOOL,
                    created_at TIMESTAMP,
                    metadata STRING
                )
            """)

            conn.execute_query("""
                CREATE NODE TABLE IF NOT EXISTS Function(
                    function_id STRING PRIMARY KEY,
                    function_name STRING,
                    fully_qualified_name STRING,
                    signature STRING,
                    docstring STRING,
                    is_async BOOL,
                    cyclomatic_complexity INT64,
                    created_at TIMESTAMP,
                    metadata STRING
                )
            """)

            conn.execute_query("""
                CREATE REL TABLE IF NOT EXISTS DEFINED_IN(
                    FROM Class TO CodeFile,
                    line_number INT64,
                    end_line INT64
                )
            """)

            conn.execute_query("""
                CREATE REL TABLE IF NOT EXISTS DEFINED_IN_FUNCTION(
                    FROM Function TO CodeFile,
                    line_number INT64,
                    end_line INT64
                )
            """)

            conn.execute_query("""
                CREATE REL TABLE IF NOT EXISTS METHOD_OF(
                    FROM Function TO Class,
                    method_type STRING,
                    visibility STRING
                )
            """)

            # Import code graph
            code_graph = KuzuCodeGraph(conn)
            counts = code_graph.import_blarify_output(json_path)

            print("\n✓ Import successful:")
            print(f"  Files:     {counts['files']}")
            print(f"  Classes:   {counts['classes']}")
            print(f"  Functions: {counts['functions']}")

            # Query imported data
            files = conn.execute_query("MATCH (cf:CodeFile) RETURN cf.file_path")
            print("\n✓ Files in database:")
            for row in files:
                print(f"  - {row['cf.file_path']}")

            classes = conn.execute_query("MATCH (c:Class) RETURN c.class_name, c.docstring")
            print("\n✓ Classes in database:")
            for row in classes:
                print(f"  - {row['c.class_name']}: {row['c.docstring']}")

    finally:
        json_path.unlink()


def example_link_memories():
    """Example: Link memories to code."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Link Memories to Code")
    print("=" * 60)

    # Create sample blarify output
    sample_data = {
        "files": [
            {
                "path": "utils.py",
                "language": "python",
                "lines_of_code": 50,
                "last_modified": "2025-01-01T00:00:00Z",
            }
        ],
        "classes": [],
        "functions": [
            {
                "id": "func:helper",
                "name": "helper",
                "file_path": "utils.py",
                "line_number": 5,
                "docstring": "Helper function",
                "parameters": ["x"],
                "return_type": "int",
                "is_async": False,
                "complexity": 1,
                "class_id": None,
            }
        ],
        "imports": [],
        "relationships": [],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(sample_data, f)
        json_path = Path(f.name)

    try:
        with KuzuConnector(db_path=":memory:") as conn:
            # Initialize schema
            conn.execute_query("""
                CREATE NODE TABLE IF NOT EXISTS CodeFile(
                    file_id STRING PRIMARY KEY,
                    file_path STRING,
                    language STRING,
                    size_bytes INT64,
                    last_modified TIMESTAMP,
                    created_at TIMESTAMP,
                    metadata STRING
                )
            """)

            conn.execute_query("""
                CREATE NODE TABLE IF NOT EXISTS Function(
                    function_id STRING PRIMARY KEY,
                    function_name STRING,
                    fully_qualified_name STRING,
                    signature STRING,
                    docstring STRING,
                    is_async BOOL,
                    cyclomatic_complexity INT64,
                    created_at TIMESTAMP,
                    metadata STRING
                )
            """)

            conn.execute_query("""
                CREATE REL TABLE IF NOT EXISTS DEFINED_IN_FUNCTION(
                    FROM Function TO CodeFile,
                    line_number INT64,
                    end_line INT64
                )
            """)

            conn.execute_query("""
                CREATE NODE TABLE IF NOT EXISTS EpisodicMemory(
                    memory_id STRING PRIMARY KEY,
                    timestamp TIMESTAMP,
                    content STRING,
                    event_type STRING,
                    emotional_valence DOUBLE,
                    importance_score DOUBLE,
                    title STRING,
                    metadata STRING,
                    tags STRING,
                    created_at TIMESTAMP,
                    accessed_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    agent_id STRING
                )
            """)

            conn.execute_query("""
                CREATE REL TABLE IF NOT EXISTS RELATES_TO_FILE_EPISODIC(
                    FROM EpisodicMemory TO CodeFile,
                    relevance_score DOUBLE,
                    context STRING,
                    timestamp TIMESTAMP
                )
            """)

            conn.execute_query("""
                CREATE REL TABLE IF NOT EXISTS RELATES_TO_FUNCTION_EPISODIC(
                    FROM EpisodicMemory TO Function,
                    relevance_score DOUBLE,
                    context STRING,
                    timestamp TIMESTAMP
                )
            """)

            # Import code
            code_graph = KuzuCodeGraph(conn)
            code_graph.import_blarify_output(json_path)

            # Create memory mentioning the function
            now = datetime.now()
            conn.execute_write(
                """
                CREATE (m:EpisodicMemory {
                    memory_id: $memory_id,
                    timestamp: $timestamp,
                    content: $content,
                    event_type: $event_type,
                    emotional_valence: $emotional_valence,
                    importance_score: $importance_score,
                    title: $title,
                    metadata: $metadata,
                    tags: $tags,
                    created_at: $created_at,
                    accessed_at: $accessed_at,
                    expires_at: $expires_at,
                    agent_id: $agent_id
                })
                """,
                {
                    "memory_id": "mem-1",
                    "timestamp": now,
                    "content": "The helper function is very useful for data processing",
                    "event_type": "code_review",
                    "emotional_valence": 0.7,
                    "importance_score": 0.8,
                    "title": "Helper function review",
                    "metadata": json.dumps({"file": "utils.py"}),
                    "tags": "[]",
                    "created_at": now,
                    "accessed_at": now,
                    "expires_at": None,
                    "agent_id": "reviewer",
                },
            )

            print("\n✓ Created memory mentioning 'helper' function")

            # Link memories to code
            link_count = code_graph.link_code_to_memories()
            print(f"✓ Created {link_count} memory-code links")

            # Query code context for memory
            context = code_graph.query_code_context("mem-1")
            print("\n✓ Code context for memory:")
            print(f"  Files:     {len(context['files'])}")
            print(f"  Functions: {len(context['functions'])}")

            for func in context["functions"]:
                print(f"\n  Function: {func['name']}")
                print(f"    Signature: {func['signature']}")
                print(f"    Complexity: {func['complexity']}")

    finally:
        json_path.unlink()


def example_code_stats():
    """Example: Get code statistics."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Code Statistics")
    print("=" * 60)

    sample_data = {
        "files": [
            {
                "path": "a.py",
                "language": "python",
                "lines_of_code": 100,
                "last_modified": "2025-01-01T00:00:00Z",
            },
            {
                "path": "b.py",
                "language": "python",
                "lines_of_code": 200,
                "last_modified": "2025-01-01T00:00:00Z",
            },
        ],
        "classes": [
            {
                "id": "c1",
                "name": "A",
                "file_path": "a.py",
                "line_number": 1,
                "docstring": "",
                "is_abstract": False,
            },
            {
                "id": "c2",
                "name": "B",
                "file_path": "b.py",
                "line_number": 1,
                "docstring": "",
                "is_abstract": False,
            },
        ],
        "functions": [
            {
                "id": "f1",
                "name": "f1",
                "file_path": "a.py",
                "line_number": 10,
                "docstring": "",
                "parameters": [],
                "return_type": "",
                "is_async": False,
                "complexity": 1,
                "class_id": None,
            },
            {
                "id": "f2",
                "name": "f2",
                "file_path": "b.py",
                "line_number": 20,
                "docstring": "",
                "parameters": [],
                "return_type": "",
                "is_async": False,
                "complexity": 2,
                "class_id": None,
            },
        ],
        "imports": [],
        "relationships": [],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(sample_data, f)
        json_path = Path(f.name)

    try:
        with KuzuConnector(db_path=":memory:") as conn:
            # Initialize minimal schema
            conn.execute_query(
                "CREATE NODE TABLE IF NOT EXISTS CodeFile(file_id STRING PRIMARY KEY, file_path STRING, language STRING, size_bytes INT64, last_modified TIMESTAMP, created_at TIMESTAMP, metadata STRING)"
            )
            conn.execute_query(
                "CREATE NODE TABLE IF NOT EXISTS Class(class_id STRING PRIMARY KEY, class_name STRING, fully_qualified_name STRING, docstring STRING, is_abstract BOOL, created_at TIMESTAMP, metadata STRING)"
            )
            conn.execute_query(
                "CREATE NODE TABLE IF NOT EXISTS Function(function_id STRING PRIMARY KEY, function_name STRING, fully_qualified_name STRING, signature STRING, docstring STRING, is_async BOOL, cyclomatic_complexity INT64, created_at TIMESTAMP, metadata STRING)"
            )
            conn.execute_query(
                "CREATE REL TABLE IF NOT EXISTS DEFINED_IN(FROM Class TO CodeFile, line_number INT64, end_line INT64)"
            )
            conn.execute_query(
                "CREATE REL TABLE IF NOT EXISTS DEFINED_IN_FUNCTION(FROM Function TO CodeFile, line_number INT64, end_line INT64)"
            )

            # Import and get stats
            code_graph = KuzuCodeGraph(conn)
            code_graph.import_blarify_output(json_path)

            stats = code_graph.get_code_stats()

            print("\n✓ Code Graph Statistics:")
            print(f"  Files:     {stats['file_count']}")
            print(f"  Classes:   {stats['class_count']}")
            print(f"  Functions: {stats['function_count']}")
            print(f"  Total LOC: {stats['total_lines']}")

    finally:
        json_path.unlink()


if __name__ == "__main__":
    example_import_code()
    example_link_memories()
    example_code_stats()

    print("\n" + "=" * 60)
    print("✓ All examples completed successfully!")
    print("=" * 60)
