"""Tests for Kuzu code graph integration.

Tests blarify import logic ported from Neo4j to Kuzu.
Validates:
- File/class/function node creation
- Relationship creation
- Memory-code linking
- Query functionality
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from amplihack.memory.kuzu.code_graph import KuzuCodeGraph
from amplihack.memory.kuzu.connector import KUZU_AVAILABLE, KuzuConnector

# Skip all tests if Kuzu not available
pytestmark = pytest.mark.skipif(not KUZU_AVAILABLE, reason="Kuzu not installed")


@pytest.fixture
def kuzu_db(tmp_path):
    """Create temporary Kuzu database for testing."""
    db_path = tmp_path / "test_code_graph.db"
    conn = KuzuConnector(db_path=str(db_path))
    conn.connect()

    # Initialize schema (from kuzu_backend.py)
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

    # Create memory node tables (for linking tests)
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

    conn.execute_query("""
        CREATE NODE TABLE IF NOT EXISTS SemanticMemory(
            memory_id STRING,
            concept STRING,
            content STRING,
            category STRING,
            confidence_score DOUBLE,
            last_updated TIMESTAMP,
            version INT64,
            title STRING,
            metadata STRING,
            tags STRING,
            created_at TIMESTAMP,
            accessed_at TIMESTAMP,
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
        CREATE REL TABLE IF NOT EXISTS RELATES_TO_FILE_SEMANTIC(
            FROM SemanticMemory TO CodeFile,
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

    conn.execute_query("""
        CREATE REL TABLE IF NOT EXISTS RELATES_TO_FUNCTION_SEMANTIC(
            FROM SemanticMemory TO Function,
            relevance_score DOUBLE,
            context STRING,
            timestamp TIMESTAMP
        )
    """)

    yield conn

    conn.close()


@pytest.fixture
def code_graph(kuzu_db):
    """Create KuzuCodeGraph instance."""
    return KuzuCodeGraph(kuzu_db)


@pytest.fixture
def sample_blarify_data():
    """Sample blarify output for testing."""
    return {
        "files": [
            {
                "path": "src/example/module.py",
                "language": "python",
                "lines_of_code": 100,
                "last_modified": "2025-01-01T00:00:00Z",
            },
            {
                "path": "src/example/utils.py",
                "language": "python",
                "lines_of_code": 50,
                "last_modified": "2025-01-01T00:00:00Z",
            },
        ],
        "classes": [
            {
                "id": "class:Example",
                "name": "Example",
                "file_path": "src/example/module.py",
                "line_number": 10,
                "docstring": "Example class for testing.",
                "is_abstract": False,
            },
        ],
        "functions": [
            {
                "id": "func:Example.process",
                "name": "process",
                "file_path": "src/example/module.py",
                "line_number": 20,
                "docstring": "Process data.",
                "parameters": ["self", "data"],
                "return_type": "str",
                "is_async": False,
                "complexity": 3,
                "class_id": "class:Example",
            },
            {
                "id": "func:helper",
                "name": "helper",
                "file_path": "src/example/utils.py",
                "line_number": 5,
                "docstring": "Helper function.",
                "parameters": ["x"],
                "return_type": "int",
                "is_async": False,
                "complexity": 1,
                "class_id": None,
            },
        ],
        "imports": [
            {
                "source_file": "src/example/module.py",
                "target_file": "src/example/utils.py",
                "symbol": "helper",
                "alias": None,
            },
        ],
        "relationships": [
            {
                "type": "CALLS",
                "source_id": "func:Example.process",
                "target_id": "func:helper",
            },
        ],
    }


def test_import_files(code_graph, sample_blarify_data, tmp_path):
    """Test importing code files."""
    # Create temp JSON file
    json_path = tmp_path / "blarify.json"
    with open(json_path, "w") as f:
        json.dump(sample_blarify_data, f)

    # Import
    counts = code_graph.import_blarify_output(json_path)

    # Verify counts
    assert counts["files"] == 2
    assert counts["classes"] == 1
    assert counts["functions"] == 2
    assert counts["imports"] == 1
    assert counts["relationships"] == 1

    # Verify files exist in database
    result = code_graph.conn.execute_query(
        "MATCH (cf:CodeFile) RETURN count(cf) as cnt"
    )
    assert result[0]["cnt"] == 2

    # Verify file properties
    result = code_graph.conn.execute_query(
        """
        MATCH (cf:CodeFile {file_id: $file_id})
        RETURN cf.file_path, cf.language, cf.size_bytes
        """,
        {"file_id": "src/example/module.py"}
    )
    assert len(result) == 1
    assert result[0]["cf.file_path"] == "src/example/module.py"
    assert result[0]["cf.language"] == "python"
    assert result[0]["cf.size_bytes"] == 100


def test_import_classes(code_graph, sample_blarify_data, tmp_path):
    """Test importing classes."""
    json_path = tmp_path / "blarify.json"
    with open(json_path, "w") as f:
        json.dump(sample_blarify_data, f)

    counts = code_graph.import_blarify_output(json_path)
    assert counts["classes"] == 1

    # Verify class exists
    result = code_graph.conn.execute_query(
        """
        MATCH (c:Class {class_id: $class_id})
        RETURN c.class_name, c.docstring, c.is_abstract
        """,
        {"class_id": "class:Example"}
    )
    assert len(result) == 1
    assert result[0]["c.class_name"] == "Example"
    assert result[0]["c.docstring"] == "Example class for testing."
    assert result[0]["c.is_abstract"] is False

    # Verify DEFINED_IN relationship
    result = code_graph.conn.execute_query(
        """
        MATCH (c:Class {class_id: $class_id})-[r:DEFINED_IN]->(cf:CodeFile)
        RETURN cf.file_id, r.line_number
        """,
        {"class_id": "class:Example"}
    )
    assert len(result) == 1
    assert result[0]["cf.file_id"] == "src/example/module.py"
    assert result[0]["r.line_number"] == 10


def test_import_functions(code_graph, sample_blarify_data, tmp_path):
    """Test importing functions."""
    json_path = tmp_path / "blarify.json"
    with open(json_path, "w") as f:
        json.dump(sample_blarify_data, f)

    counts = code_graph.import_blarify_output(json_path)
    assert counts["functions"] == 2

    # Verify method function
    result = code_graph.conn.execute_query(
        """
        MATCH (f:Function {function_id: $function_id})
        RETURN f.function_name, f.signature, f.is_async, f.cyclomatic_complexity
        """,
        {"function_id": "func:Example.process"}
    )
    assert len(result) == 1
    assert result[0]["f.function_name"] == "process"
    assert result[0]["f.is_async"] is False
    assert result[0]["f.cyclomatic_complexity"] == 3

    # Verify METHOD_OF relationship
    result = code_graph.conn.execute_query(
        """
        MATCH (f:Function {function_id: $function_id})-[r:METHOD_OF]->(c:Class)
        RETURN c.class_id, r.method_type
        """,
        {"function_id": "func:Example.process"}
    )
    assert len(result) == 1
    assert result[0]["c.class_id"] == "class:Example"
    assert result[0]["r.method_type"] == "instance"

    # Verify standalone function
    result = code_graph.conn.execute_query(
        """
        MATCH (f:Function {function_id: $function_id})
        RETURN f.function_name
        """,
        {"function_id": "func:helper"}
    )
    assert len(result) == 1
    assert result[0]["f.function_name"] == "helper"


def test_import_relationships(code_graph, sample_blarify_data, tmp_path):
    """Test importing function call relationships."""
    json_path = tmp_path / "blarify.json"
    with open(json_path, "w") as f:
        json.dump(sample_blarify_data, f)

    counts = code_graph.import_blarify_output(json_path)
    assert counts["relationships"] == 1

    # Verify CALLS relationship
    result = code_graph.conn.execute_query(
        """
        MATCH (source:Function {function_id: $source_id})-[r:CALLS]->(target:Function {function_id: $target_id})
        RETURN r.call_count, r.context
        """,
        {"source_id": "func:Example.process", "target_id": "func:helper"}
    )
    assert len(result) == 1
    assert result[0]["r.call_count"] == 1


def test_import_imports(code_graph, sample_blarify_data, tmp_path):
    """Test importing file import relationships."""
    json_path = tmp_path / "blarify.json"
    with open(json_path, "w") as f:
        json.dump(sample_blarify_data, f)

    counts = code_graph.import_blarify_output(json_path)
    assert counts["imports"] == 1

    # Verify IMPORTS relationship
    result = code_graph.conn.execute_query(
        """
        MATCH (source:CodeFile {file_id: $source_id})-[r:IMPORTS]->(target:CodeFile {file_id: $target_id})
        RETURN r.import_type, r.alias
        """,
        {"source_id": "src/example/module.py", "target_id": "src/example/utils.py"}
    )
    assert len(result) == 1
    assert result[0]["r.import_type"] == "helper"


def test_incremental_update(code_graph, sample_blarify_data, tmp_path):
    """Test incremental updates don't create duplicates."""
    json_path = tmp_path / "blarify.json"
    with open(json_path, "w") as f:
        json.dump(sample_blarify_data, f)

    # First import
    counts1 = code_graph.import_blarify_output(json_path)
    assert counts1["files"] == 2

    # Second import (should update, not duplicate)
    counts2 = code_graph.import_blarify_output(json_path)
    assert counts2["files"] == 2

    # Verify no duplicates
    result = code_graph.conn.execute_query(
        "MATCH (cf:CodeFile) RETURN count(cf) as cnt"
    )
    assert result[0]["cnt"] == 2


def test_link_memories_to_files(code_graph, sample_blarify_data, tmp_path):
    """Test linking memories to code files."""
    # Import code
    json_path = tmp_path / "blarify.json"
    with open(json_path, "w") as f:
        json.dump(sample_blarify_data, f)
    code_graph.import_blarify_output(json_path)

    # Create test memory with file reference
    now = datetime.now()
    code_graph.conn.execute_write(
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
            "content": "Fixed bug in module.py",
            "event_type": "code_change",
            "emotional_valence": 0.5,
            "importance_score": 0.8,
            "title": "Bug fix",
            "metadata": json.dumps({"file": "module.py"}),
            "tags": "[]",
            "created_at": now,
            "accessed_at": now,
            "expires_at": None,
            "agent_id": "test-agent",
        }
    )

    # Link memories to code
    link_count = code_graph.link_code_to_memories()
    assert link_count > 0

    # Verify relationship created
    result = code_graph.conn.execute_query(
        """
        MATCH (m:EpisodicMemory {memory_id: $memory_id})-[r:RELATES_TO_FILE_EPISODIC]->(cf:CodeFile)
        RETURN cf.file_path, r.relevance_score, r.context
        """,
        {"memory_id": "mem-1"}
    )
    assert len(result) > 0
    assert result[0]["r.relevance_score"] == 1.0
    assert result[0]["r.context"] == "metadata_file_match"


def test_link_memories_to_functions(code_graph, sample_blarify_data, tmp_path):
    """Test linking memories to functions based on content."""
    # Import code
    json_path = tmp_path / "blarify.json"
    with open(json_path, "w") as f:
        json.dump(sample_blarify_data, f)
    code_graph.import_blarify_output(json_path)

    # Create test memory mentioning function name
    now = datetime.now()
    code_graph.conn.execute_write(
        """
        CREATE (m:SemanticMemory {
            memory_id: $memory_id,
            concept: $concept,
            content: $content,
            category: $category,
            confidence_score: $confidence_score,
            last_updated: $last_updated,
            version: $version,
            title: $title,
            metadata: $metadata,
            tags: $tags,
            created_at: $created_at,
            accessed_at: $accessed_at,
            agent_id: $agent_id
        })
        """,
        {
            "memory_id": "mem-2",
            "concept": "Helper pattern",
            "content": "The helper function is used for data transformation",
            "category": "pattern",
            "confidence_score": 0.9,
            "last_updated": now,
            "version": 1,
            "title": "Helper usage",
            "metadata": "{}",
            "tags": "[]",
            "created_at": now,
            "accessed_at": now,
            "agent_id": "test-agent",
        }
    )

    # Link memories to code
    link_count = code_graph.link_code_to_memories()
    assert link_count > 0

    # Verify relationship created
    result = code_graph.conn.execute_query(
        """
        MATCH (m:SemanticMemory {memory_id: $memory_id})-[r:RELATES_TO_FUNCTION_SEMANTIC]->(f:Function)
        RETURN f.function_name, r.relevance_score, r.context
        """,
        {"memory_id": "mem-2"}
    )
    assert len(result) > 0
    assert result[0]["f.function_name"] == "helper"
    assert result[0]["r.relevance_score"] == 0.8
    assert result[0]["r.context"] == "content_name_match"


def test_query_code_context(code_graph, sample_blarify_data, tmp_path):
    """Test querying code context for a memory."""
    # Import code
    json_path = tmp_path / "blarify.json"
    with open(json_path, "w") as f:
        json.dump(sample_blarify_data, f)
    code_graph.import_blarify_output(json_path)

    # Create and link memory
    now = datetime.now()
    code_graph.conn.execute_write(
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
            "memory_id": "mem-3",
            "timestamp": now,
            "content": "Updated process method",
            "event_type": "code_change",
            "emotional_valence": 0.5,
            "importance_score": 0.8,
            "title": "Method update",
            "metadata": "{}",
            "tags": "[]",
            "created_at": now,
            "accessed_at": now,
            "expires_at": None,
            "agent_id": "test-agent",
        }
    )

    code_graph.link_code_to_memories()

    # Query code context
    context = code_graph.query_code_context("mem-3")

    assert context["memory_id"] == "mem-3"
    assert len(context["functions"]) > 0
    assert any(f["name"] == "process" for f in context["functions"])


def test_get_code_stats(code_graph, sample_blarify_data, tmp_path):
    """Test getting code statistics."""
    json_path = tmp_path / "blarify.json"
    with open(json_path, "w") as f:
        json.dump(sample_blarify_data, f)

    code_graph.import_blarify_output(json_path)

    stats = code_graph.get_code_stats()

    assert stats["file_count"] == 2
    assert stats["class_count"] == 1
    assert stats["function_count"] == 2
    assert stats["total_lines"] == 150  # 100 + 50


def test_empty_import(code_graph, tmp_path):
    """Test importing empty blarify output."""
    json_path = tmp_path / "empty.json"
    with open(json_path, "w") as f:
        json.dump({"files": [], "classes": [], "functions": [], "imports": [], "relationships": []}, f)

    counts = code_graph.import_blarify_output(json_path)

    assert counts["files"] == 0
    assert counts["classes"] == 0
    assert counts["functions"] == 0
    assert counts["imports"] == 0
    assert counts["relationships"] == 0


def test_missing_file(code_graph):
    """Test error handling for missing file."""
    with pytest.raises(FileNotFoundError):
        code_graph.import_blarify_output(Path("/nonexistent/file.json"))


def test_inheritance_relationship(code_graph, tmp_path):
    """Test creating INHERITS relationships between classes."""
    data = {
        "files": [
            {
                "path": "test.py",
                "language": "python",
                "lines_of_code": 50,
                "last_modified": "2025-01-01T00:00:00Z",
            }
        ],
        "classes": [
            {
                "id": "class:Base",
                "name": "Base",
                "file_path": "test.py",
                "line_number": 1,
                "docstring": "Base class",
                "is_abstract": True,
            },
            {
                "id": "class:Derived",
                "name": "Derived",
                "file_path": "test.py",
                "line_number": 10,
                "docstring": "Derived class",
                "is_abstract": False,
            },
        ],
        "functions": [],
        "imports": [],
        "relationships": [
            {
                "type": "INHERITS",
                "source_id": "class:Derived",
                "target_id": "class:Base",
            }
        ],
    }

    json_path = tmp_path / "inherit.json"
    with open(json_path, "w") as f:
        json.dump(data, f)

    counts = code_graph.import_blarify_output(json_path)
    assert counts["relationships"] == 1

    # Verify INHERITS relationship
    result = code_graph.conn.execute_query(
        """
        MATCH (source:Class {class_id: $source_id})-[r:INHERITS]->(target:Class {class_id: $target_id})
        RETURN r.inheritance_type
        """,
        {"source_id": "class:Derived", "target_id": "class:Base"}
    )
    assert len(result) == 1
    assert result[0]["r.inheritance_type"] == "single"
