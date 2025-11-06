#!/usr/bin/env python3
"""Test blarify integration with Neo4j memory system.

Tests:
1. Schema initialization
2. Sample code import
3. Code-memory relationships
4. Query functionality
5. Incremental updates

Can run with or without actual blarify installation.
"""

import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

# Load .env if it exists
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key] = value

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.memory.neo4j.connector import Neo4jConnector
from amplihack.memory.neo4j.code_graph import BlarifyIntegration
from amplihack.memory.neo4j.memory_store import MemoryStore
from amplihack.memory.neo4j.schema import SchemaManager

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
                "path": "src/amplihack/memory/neo4j/connector.py",
                "language": "python",
                "lines_of_code": 438,
                "last_modified": "2025-01-01T00:00:00Z",
            },
            {
                "path": "src/amplihack/memory/neo4j/schema.py",
                "language": "python",
                "lines_of_code": 272,
                "last_modified": "2025-01-01T00:00:00Z",
            },
            {
                "path": "src/amplihack/memory/neo4j/memory_store.py",
                "language": "python",
                "lines_of_code": 578,
                "last_modified": "2025-01-01T00:00:00Z",
            },
        ],
        "classes": [
            {
                "id": "class:CircuitBreaker",
                "name": "CircuitBreaker",
                "file_path": "src/amplihack/memory/neo4j/connector.py",
                "line_number": 45,
                "docstring": "Circuit breaker for graceful degradation.",
                "is_abstract": False,
            },
            {
                "id": "class:Neo4jConnector",
                "name": "Neo4jConnector",
                "file_path": "src/amplihack/memory/neo4j/connector.py",
                "line_number": 166,
                "docstring": "Neo4j connection manager with connection pooling.",
                "is_abstract": False,
            },
            {
                "id": "class:SchemaManager",
                "name": "SchemaManager",
                "file_path": "src/amplihack/memory/neo4j/schema.py",
                "line_number": 17,
                "docstring": "Manages Neo4j schema for memory system.",
                "is_abstract": False,
            },
            {
                "id": "class:MemoryStore",
                "name": "MemoryStore",
                "file_path": "src/amplihack/memory/neo4j/memory_store.py",
                "line_number": 19,
                "docstring": "Neo4j-based memory store with agent type awareness.",
                "is_abstract": False,
            },
        ],
        "functions": [
            {
                "id": "func:Neo4jConnector.connect",
                "name": "connect",
                "file_path": "src/amplihack/memory/neo4j/connector.py",
                "line_number": 219,
                "docstring": "Establish connection to Neo4j.",
                "parameters": ["self"],
                "return_type": "Neo4jConnector",
                "is_async": False,
                "complexity": 3,
                "class_id": "class:Neo4jConnector",
            },
            {
                "id": "func:Neo4jConnector.execute_query",
                "name": "execute_query",
                "file_path": "src/amplihack/memory/neo4j/connector.py",
                "line_number": 249,
                "docstring": "Execute read query and return results with retry logic.",
                "parameters": ["self", "query", "parameters"],
                "return_type": "List[Dict[str, Any]]",
                "is_async": False,
                "complexity": 5,
                "class_id": "class:Neo4jConnector",
            },
            {
                "id": "func:SchemaManager.initialize_schema",
                "name": "initialize_schema",
                "file_path": "src/amplihack/memory/neo4j/schema.py",
                "line_number": 36,
                "docstring": "Initialize complete schema (idempotent).",
                "parameters": ["self"],
                "return_type": "bool",
                "is_async": False,
                "complexity": 4,
                "class_id": "class:SchemaManager",
            },
            {
                "id": "func:MemoryStore.create_memory",
                "name": "create_memory",
                "file_path": "src/amplihack/memory/neo4j/memory_store.py",
                "line_number": 38,
                "docstring": "Create a new memory linked to an agent type.",
                "parameters": ["self", "content", "agent_type", "category", "memory_type"],
                "return_type": "str",
                "is_async": False,
                "complexity": 8,
                "class_id": "class:MemoryStore",
            },
        ],
        "imports": [
            {
                "source_file": "src/amplihack/memory/neo4j/schema.py",
                "target_file": "src/amplihack/memory/neo4j/connector.py",
                "symbol": "Neo4jConnector",
                "alias": None,
            },
            {
                "source_file": "src/amplihack/memory/neo4j/memory_store.py",
                "target_file": "src/amplihack/memory/neo4j/connector.py",
                "symbol": "Neo4jConnector",
                "alias": None,
            },
        ],
        "relationships": [
            {
                "type": "CALLS",
                "source_id": "func:SchemaManager.initialize_schema",
                "target_id": "func:Neo4jConnector.execute_query",
            },
            {
                "type": "CALLS",
                "source_id": "func:MemoryStore.create_memory",
                "target_id": "func:Neo4jConnector.execute_query",
            },
        ],
    }


def test_schema_initialization(integration: BlarifyIntegration) -> bool:
    """Test code schema initialization."""
    logger.info("TEST 1: Schema initialization")

    success = integration.initialize_code_schema()

    if success:
        logger.info("✓ Code schema initialized successfully")
        return True
    else:
        logger.error("✗ Schema initialization failed")
        return False


def test_sample_import(integration: BlarifyIntegration, temp_file: Path) -> bool:
    """Test importing sample blarify output."""
    logger.info("\nTEST 2: Sample code import")

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
            "classes": 4,
            "functions": 4,
            "imports": 2,
            "relationships": 2,
        }

        all_match = all(counts[k] == expected[k] for k in expected)

        if all_match:
            logger.info("✓ All counts match expected values")
            return True
        else:
            logger.warning("⚠ Some counts don't match expected values")
            logger.warning("  Expected: %s", expected)
            logger.warning("  Got:      %s", counts)
            return False

    except Exception as e:
        logger.error("✗ Import failed: %s", e)
        return False


def test_code_memory_relationships(
    integration: BlarifyIntegration,
    memory_store: MemoryStore,
) -> bool:
    """Test creating relationships between code and memories."""
    logger.info("\nTEST 3: Code-memory relationships")

    try:
        # Create test memory with file reference
        memory_id = memory_store.create_memory(
            content="Use Neo4jConnector.execute_query for all database queries",
            agent_type="builder",
            category="best_practice",
            memory_type="procedural",
            metadata={"file": "connector.py"},
            tags=["neo4j", "database", "query"],
        )

        logger.info("Created test memory: %s", memory_id)

        # Link code to memories
        link_count = integration.link_code_to_memories()

        logger.info("✓ Created %d code-memory relationships", link_count)

        # Query code context for memory
        context = integration.query_code_context(memory_id)

        logger.info("Code context for memory:")
        logger.info("  - Files:     %d", len(context["files"]))
        logger.info("  - Functions: %d", len(context["functions"]))
        logger.info("  - Classes:   %d", len(context["classes"]))

        if context["files"] or context["functions"]:
            logger.info("✓ Memory successfully linked to code")
            return True
        else:
            logger.warning("⚠ Memory not linked to any code")
            return False

    except Exception as e:
        logger.error("✗ Code-memory linking failed: %s", e)
        return False


def test_query_functionality(integration: BlarifyIntegration, conn: Neo4jConnector) -> bool:
    """Test querying code graph."""
    logger.info("\nTEST 4: Query functionality")

    try:
        # Test 1: Query all files
        result = conn.execute_query("""
            MATCH (cf:CodeFile)
            RETURN cf.path as path, cf.language as language
            ORDER BY cf.path
        """)

        logger.info("✓ Found %d code files", len(result))
        for row in result[:3]:
            logger.info("  - %s (%s)", row["path"], row["language"])

        # Test 2: Query classes and their methods
        result = conn.execute_query("""
            MATCH (c:Class)<-[:METHOD_OF]-(f:Function)
            RETURN c.name as class_name, count(f) as method_count
            ORDER BY method_count DESC
        """)

        logger.info("✓ Found %d classes with methods", len(result))
        for row in result[:3]:
            logger.info("  - %s: %d methods", row["class_name"], row["method_count"])

        # Test 3: Query function call graph
        result = conn.execute_query("""
            MATCH (source:Function)-[:CALLS]->(target:Function)
            RETURN source.name as caller, target.name as callee
            LIMIT 5
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
        logger.error("✗ Query functionality failed: %s", e)
        return False


def test_incremental_update(integration: BlarifyIntegration, temp_file: Path) -> bool:
    """Test incremental update of code graph."""
    logger.info("\nTEST 5: Incremental update")

    try:
        # Create updated sample data (add a new file)
        sample_data = create_sample_blarify_output()
        sample_data["files"].append({
            "path": "src/amplihack/memory/neo4j/code_graph.py",
            "language": "python",
            "lines_of_code": 600,
            "last_modified": "2025-01-02T00:00:00Z",
        })

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
        else:
            logger.warning("⚠ File count unexpected: %d", stats["file_count"])
            return False

    except Exception as e:
        logger.error("✗ Incremental update failed: %s", e)
        return False


def main():
    logger.info("=" * 60)
    logger.info("BLARIFY INTEGRATION TEST SUITE")
    logger.info("=" * 60)

    # Create temp file for sample data
    temp_file = Path(tempfile.gettempdir()) / f"blarify_test_{uuid4()}.json"

    try:
        # Connect to Neo4j
        logger.info("\nConnecting to Neo4j...")
        with Neo4jConnector() as conn:
            if not conn.verify_connectivity():
                logger.error("Cannot connect to Neo4j")
                logger.error("Make sure Neo4j is running (see README)")
                return 1

            logger.info("✓ Connected to Neo4j")

            # Initialize schema
            logger.info("\nInitializing memory schema...")
            schema_mgr = SchemaManager(conn)
            schema_mgr.initialize_schema()
            logger.info("✓ Memory schema initialized")

            # Create instances
            integration = BlarifyIntegration(conn)
            memory_store = MemoryStore(conn)

            # Run tests
            results = []

            results.append(("Schema initialization", test_schema_initialization(integration)))
            results.append(("Sample import", test_sample_import(integration, temp_file)))
            results.append(
                ("Code-memory relationships", test_code_memory_relationships(integration, memory_store))
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
                logger.info("\n🎉 All tests passed! Blarify integration is working.")
                return 0
            else:
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
