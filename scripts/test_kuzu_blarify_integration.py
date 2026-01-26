#!/usr/bin/env python3
"""Test blarify integration with Kuzu memory system.

Tests:
1. Schema initialization
2. Sample code import
3. Code-memory relationships
4. Query functionality
5. Incremental updates

This is a port of test_blarify_integration.py from Neo4j to Kuzu.
"""

import json
import logging
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.memory.kuzu.code_graph import KuzuCodeGraph
from amplihack.memory.kuzu.connector import KuzuConnector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_sample_blarify_output() -> dict:
    """Create sample blarify output for testing.

    Returns realistic code graph structure without needing blarify installed.
    """
    return {
        "files": [
            {
                "path": "src/amplihack/memory/kuzu/connector.py",
                "language": "python",
                "lines_of_code": 345,
                "last_modified": "2025-01-01T00:00:00Z",
            },
            {
                "path": "src/amplihack/memory/kuzu/code_graph.py",
                "language": "python",
                "lines_of_code": 820,
                "last_modified": "2025-01-01T00:00:00Z",
            },
            {
                "path": "src/amplihack/memory/backends/kuzu_backend.py",
                "language": "python",
                "lines_of_code": 1520,
                "last_modified": "2025-01-01T00:00:00Z",
            },
        ],
        "classes": [
            {
                "id": "class:KuzuConnector",
                "name": "KuzuConnector",
                "file_path": "src/amplihack/memory/kuzu/connector.py",
                "line_number": 25,
                "docstring": "Kùzu embedded graph database connector.",
                "is_abstract": False,
            },
            {
                "id": "class:KuzuCodeGraph",
                "name": "KuzuCodeGraph",
                "file_path": "src/amplihack/memory/kuzu/code_graph.py",
                "line_number": 50,
                "docstring": "Integrates blarify code graphs with Kuzu memory system.",
                "is_abstract": False,
            },
            {
                "id": "class:KuzuBackend",
                "name": "KuzuBackend",
                "file_path": "src/amplihack/memory/backends/kuzu_backend.py",
                "line_number": 40,
                "docstring": "Kùzu graph database backend.",
                "is_abstract": False,
            },
        ],
        "functions": [
            {
                "id": "func:KuzuConnector.connect",
                "name": "connect",
                "file_path": "src/amplihack/memory/kuzu/connector.py",
                "line_number": 98,
                "docstring": "Open connection to Kùzu database.",
                "parameters": ["self"],
                "return_type": "KuzuConnector",
                "is_async": False,
                "complexity": 2,
                "class_id": "class:KuzuConnector",
            },
            {
                "id": "func:KuzuConnector.execute_query",
                "name": "execute_query",
                "file_path": "src/amplihack/memory/kuzu/connector.py",
                "line_number": 139,
                "docstring": "Execute a Cypher query and return results.",
                "parameters": ["self", "query", "parameters"],
                "return_type": "list[dict[str, Any]]",
                "is_async": False,
                "complexity": 4,
                "class_id": "class:KuzuConnector",
            },
            {
                "id": "func:KuzuCodeGraph.import_blarify_output",
                "name": "import_blarify_output",
                "file_path": "src/amplihack/memory/kuzu/code_graph.py",
                "line_number": 155,
                "docstring": "Import blarify JSON output into Kuzu.",
                "parameters": ["self", "blarify_json_path", "project_id"],
                "return_type": "dict[str, int]",
                "is_async": False,
                "complexity": 3,
                "class_id": "class:KuzuCodeGraph",
            },
            {
                "id": "func:KuzuBackend.store_memory",
                "name": "store_memory",
                "file_path": "src/amplihack/memory/backends/kuzu_backend.py",
                "line_number": 538,
                "docstring": "Store a memory entry in appropriate node type.",
                "parameters": ["self", "memory"],
                "return_type": "bool",
                "is_async": False,
                "complexity": 10,
                "class_id": "class:KuzuBackend",
            },
        ],
        "imports": [
            {
                "source_file": "src/amplihack/memory/kuzu/code_graph.py",
                "target_file": "src/amplihack/memory/kuzu/connector.py",
                "symbol": "KuzuConnector",
                "alias": None,
            },
        ],
        "relationships": [
            {
                "type": "CALLS",
                "source_id": "func:KuzuCodeGraph.import_blarify_output",
                "target_id": "func:KuzuConnector.execute_query",
            },
            {
                "type": "CALLS",
                "source_id": "func:KuzuBackend.store_memory",
                "target_id": "func:KuzuConnector.execute_query",
            },
        ],
    }


def initialize_schema(conn: KuzuConnector) -> bool:
    """Initialize Kuzu schema for code graph testing."""
    logger.info("Initializing Kuzu schema for code graph")

    try:
        # Create code node tables
        conn.execute_query("""
            CREATE NODE TABLE IF NOT EXISTS CodeFile(
                file_id STRING,
                file_path STRING,
                language STRING,
                size_bytes INT64,
                last_modified TIMESTAMP,
                created_at TIMESTAMP,
                metadata STRING,
                PRIMARY KEY (file_id)
            )
        """)

        conn.execute_query("""
            CREATE NODE TABLE IF NOT EXISTS Class(
                class_id STRING,
                class_name STRING,
                fully_qualified_name STRING,
                docstring STRING,
                is_abstract BOOL,
                created_at TIMESTAMP,
                metadata STRING,
                PRIMARY KEY (class_id)
            )
        """)

        conn.execute_query("""
            CREATE NODE TABLE IF NOT EXISTS Function(
                function_id STRING,
                function_name STRING,
                fully_qualified_name STRING,
                signature STRING,
                docstring STRING,
                is_async BOOL,
                cyclomatic_complexity INT64,
                created_at TIMESTAMP,
                metadata STRING,
                PRIMARY KEY (function_id)
            )
        """)

        # Create relationship tables
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

        conn.execute_query("""
            CREATE REL TABLE IF NOT EXISTS CALLS(
                FROM Function TO Function,
                call_count INT64,
                context STRING
            )
        """)

        conn.execute_query("""
            CREATE REL TABLE IF NOT EXISTS INHERITS(
                FROM Class TO Class,
                inheritance_order INT64,
                inheritance_type STRING
            )
        """)

        conn.execute_query("""
            CREATE REL TABLE IF NOT EXISTS IMPORTS(
                FROM CodeFile TO CodeFile,
                import_type STRING,
                alias STRING
            )
        """)

        conn.execute_query("""
            CREATE REL TABLE IF NOT EXISTS REFERENCES_CLASS(
                FROM Function TO Class,
                reference_type STRING,
                context STRING
            )
        """)

        # Create memory node tables for linking tests
        conn.execute_query("""
            CREATE NODE TABLE IF NOT EXISTS EpisodicMemory(
                memory_id STRING,
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
                agent_id STRING,
                PRIMARY KEY (memory_id)
            )
        """)

        # Memory-code relationship tables
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

        logger.info("✓ Schema initialized successfully")
        return True

    except Exception as e:
        logger.error("✗ Schema initialization failed: %s", e)
        return False


def test_sample_import(integration: KuzuCodeGraph, temp_file: Path) -> bool:
    """Test importing sample blarify output."""
    logger.info("\nTEST 1: Sample code import")

    # Create sample data
    sample_data = create_sample_blarify_output()

    # Write to temp file
    with open(temp_file, "w") as f:
        json.dump(sample_data, f, indent=2)

    logger.info("Created sample blarify output: %s", temp_file)

    # Import
    try:
        counts = integration.import_blarify_output(temp_file)

        logger.info("✓ Import successful:")
        logger.info("  - Files:         %d", counts["files"])
        logger.info("  - Classes:       %d", counts["classes"])
        logger.info("  - Functions:     %d", counts["functions"])
        logger.info("  - Imports:       %d", counts["imports"])
        logger.info("  - Relationships: %d", counts["relationships"])

        # Verify counts match expected
        expected = {
            "files": 3,
            "classes": 3,
            "functions": 4,
            "imports": 1,
            "relationships": 2,
        }

        all_match = all(counts[k] == expected[k] for k in expected)

        if all_match:
            logger.info("✓ All counts match expected values")
            return True
        logger.warning("⚠ Some counts don't match expected values")
        logger.warning("  Expected: %s", expected)
        logger.warning("  Got:      %s", counts)
        return False

    except Exception as e:
        logger.error("✗ Import failed: %s", e, exc_info=True)
        return False


def test_code_memory_relationships(
    integration: KuzuCodeGraph,
    conn: KuzuConnector,
) -> bool:
    """Test creating relationships between code and memories."""
    logger.info("\nTEST 2: Code-memory relationships")

    try:
        from datetime import datetime

        # Create test memory with file reference
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
                "memory_id": "test-memory-1",
                "timestamp": now,
                "content": "Use KuzuConnector.execute_query for all database queries",
                "event_type": "best_practice",
                "emotional_valence": 0.5,
                "importance_score": 0.8,
                "title": "Database query pattern",
                "metadata": json.dumps({"file": "connector.py"}),
                "tags": "[]",
                "created_at": now,
                "accessed_at": now,
                "expires_at": None,
                "agent_id": "builder",
            },
        )

        logger.info("Created test memory: test-memory-1")

        # Link code to memories
        link_count = integration.link_code_to_memories()

        logger.info("✓ Created %d code-memory relationships", link_count)

        # Query code context for memory
        context = integration.query_code_context("test-memory-1")

        logger.info("Code context for memory:")
        logger.info("  - Files:     %d", len(context["files"]))
        logger.info("  - Functions: %d", len(context["functions"]))
        logger.info("  - Classes:   %d", len(context["classes"]))

        if context["files"] or context["functions"]:
            logger.info("✓ Memory successfully linked to code")
            return True
        logger.warning("⚠ Memory not linked to any code")
        return False

    except Exception as e:
        logger.error("✗ Code-memory linking failed: %s", e, exc_info=True)
        return False


def test_query_functionality(integration: KuzuCodeGraph, conn: KuzuConnector) -> bool:
    """Test querying code graph."""
    logger.info("\nTEST 3: Query functionality")

    try:
        # Test 1: Query all files
        result = conn.execute_query("""
            MATCH (cf:CodeFile)
            RETURN cf.file_path as path, cf.language as language
            ORDER BY cf.file_path
        """)

        logger.info("✓ Found %d code files", len(result))
        for row in result[:3]:
            logger.info("  - %s (%s)", row["path"], row["language"])

        # Test 2: Query classes and their methods
        result = conn.execute_query("""
            MATCH (c:Class)<-[:METHOD_OF]-(f:Function)
            RETURN c.class_name as class_name, count(f) as method_count
        """)

        logger.info("✓ Found %d classes with methods", len(result))
        for row in result[:3]:
            logger.info("  - %s: %d methods", row["class_name"], row["method_count"])

        # Test 3: Query function call graph
        result = conn.execute_query("""
            MATCH (source:Function)-[:CALLS]->(target:Function)
            RETURN source.function_name as caller, target.function_name as callee
        """)

        logger.info("✓ Found %d function calls", len(result))
        for row in result:
            logger.info("  - %s -> %s", row["caller"], row["callee"])

        # Test 4: Get code stats
        stats = integration.get_code_stats()
        logger.info("✓ Code statistics:")
        logger.info("  - Total files:     %d", stats["file_count"])
        logger.info("  - Total classes:   %d", stats["class_count"])
        logger.info("  - Total functions: %d", stats["function_count"])
        logger.info("  - Total lines:     %d", stats["total_lines"])

        return True

    except Exception as e:
        logger.error("✗ Query functionality failed: %s", e, exc_info=True)
        return False


def test_incremental_update(integration: KuzuCodeGraph, temp_file: Path) -> bool:
    """Test incremental update of code graph."""
    logger.info("\nTEST 4: Incremental update")

    try:
        # Create updated sample data (add a new file)
        sample_data = create_sample_blarify_output()
        sample_data["files"].append(
            {
                "path": "src/amplihack/memory/kuzu/__init__.py",
                "language": "python",
                "lines_of_code": 27,
                "last_modified": "2025-01-02T00:00:00Z",
            }
        )

        # Write to temp file
        with open(temp_file, "w") as f:
            json.dump(sample_data, f, indent=2)

        # Incremental update
        counts = integration.incremental_update(temp_file)

        logger.info("✓ Incremental update successful:")
        logger.info("  - Files:         %d", counts["files"])

        # Verify new file was added
        stats = integration.get_code_stats()

        if stats["file_count"] == 4:  # 3 original + 1 new
            logger.info("✓ New file successfully added")
            return True
        logger.warning("⚠ File count unexpected: %d", stats["file_count"])
        return False

    except Exception as e:
        logger.error("✗ Incremental update failed: %s", e, exc_info=True)
        return False


def main():
    logger.info("=" * 60)
    logger.info("KUZU BLARIFY INTEGRATION TEST SUITE")
    logger.info("=" * 60)

    # Create temp file for sample data
    temp_file = Path(tempfile.gettempdir()) / f"kuzu_blarify_test_{uuid4()}.json"

    try:
        # Connect to Kuzu
        logger.info("\nConnecting to Kuzu...")
        db_path = Path(tempfile.gettempdir()) / f"kuzu_test_{uuid4()}.db"
        with KuzuConnector(db_path=str(db_path)) as conn:
            if not conn.verify_connectivity():
                logger.error("Cannot connect to Kuzu")
                return 1

            logger.info("✓ Connected to Kuzu: %s", db_path)

            # Initialize schema
            logger.info("\nInitializing schema...")
            if not initialize_schema(conn):
                logger.error("Schema initialization failed")
                return 1

            # Create instances
            integration = KuzuCodeGraph(conn)

            # Run tests
            results = []

            results.append(("Sample import", test_sample_import(integration, temp_file)))
            results.append(
                (
                    "Code-memory relationships",
                    test_code_memory_relationships(integration, conn),
                )
            )
            results.append(("Query functionality", test_query_functionality(integration, conn)))
            results.append(("Incremental update", test_incremental_update(integration, temp_file)))

            # Summary
            logger.info("\n" + "=" * 60)
            logger.info("TEST SUMMARY")
            logger.info("=" * 60)

            passed = sum(1 for _, result in results if result)
            total = len(results)

            for test_name, result in results:
                status = "✓ PASS" if result else "✗ FAIL"
                logger.info("%s: %s", status, test_name)

            logger.info("\nResults: %d/%d tests passed", passed, total)

            if passed == total:
                logger.info("\n🎉 All tests passed! Kuzu blarify integration is working.")
                return 0
            logger.warning("\n⚠ Some tests failed. Check logs above for details.")
            return 1

    except Exception as e:
        logger.error("Test suite failed: %s", e, exc_info=True)
        return 1

    finally:
        # Cleanup
        if temp_file.exists():
            temp_file.unlink()
            logger.debug("Cleaned up temp file: %s", temp_file)


if __name__ == "__main__":
    sys.exit(main())
