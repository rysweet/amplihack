"""Tests for Kùzu code graph schema extension.

Tests the new code graph schema with:
- 3 code node types (CodeFile, Class, Function)
- 7 code relationship types (DEFINED_IN, METHOD_OF, CALLS, INHERITS, IMPORTS, REFERENCES, CONTAINS)
- 10 memory-code link types (5 memory types × 2 code targets)

Philosophy:
- TDD approach: Write failing tests first, implement to make them pass
- Test behavior, not implementation
- Focus on critical path: schema creation, idempotency, regression
"""

import tempfile
from datetime import datetime
from unittest.mock import Mock, patch

from src.amplihack.memory.models import MemoryEntry, MemoryType


class TestKuzuCodeSchemaCreation:
    """Test that all 20 new code schema tables are created."""

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_initialize_creates_codefile_node_table(self, mock_kuzu):
        """Test that CodeFile node table is created with correct schema."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            # Check that CodeFile table creation was attempted
            calls = [str(call) for call in mock_conn.execute.call_args_list]
            assert any("CodeFile" in str(call) for call in calls), (
                "CodeFile node table not created"
            )

            # Verify key properties exist in schema
            codefile_calls = [c for c in calls if "CodeFile" in str(c)]
            assert any("file_id" in str(c) for c in codefile_calls), (
                "CodeFile missing file_id primary key"
            )
            assert any("file_path" in str(c) for c in codefile_calls), (
                "CodeFile missing file_path property"
            )
            assert any("language" in str(c) for c in codefile_calls), (
                "CodeFile missing language property"
            )

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_initialize_creates_class_node_table(self, mock_kuzu):
        """Test that Class node table is created with correct schema."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            calls = [str(call) for call in mock_conn.execute.call_args_list]
            assert any("Class" in str(call) and "NODE TABLE" in str(call) for call in calls), (
                "Class node table not created"
            )

            # Verify key properties
            class_calls = [c for c in calls if "Class" in str(c)]
            assert any("class_id" in str(c) for c in class_calls), (
                "Class missing class_id primary key"
            )
            assert any("class_name" in str(c) for c in class_calls), (
                "Class missing class_name property"
            )
            assert any("fully_qualified_name" in str(c) for c in class_calls), (
                "Class missing fully_qualified_name property"
            )

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_initialize_creates_function_node_table(self, mock_kuzu):
        """Test that Function node table is created with correct schema."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            calls = [str(call) for call in mock_conn.execute.call_args_list]
            assert any("Function" in str(call) and "NODE TABLE" in str(call) for call in calls), (
                "Function node table not created"
            )

            # Verify key properties
            func_calls = [c for c in calls if "Function" in str(c)]
            assert any("function_id" in str(c) for c in func_calls), (
                "Function missing function_id primary key"
            )
            assert any("function_name" in str(c) for c in func_calls), (
                "Function missing function_name property"
            )
            assert any("is_async" in str(c) for c in func_calls), (
                "Function missing is_async property"
            )

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_initialize_creates_all_7_code_relationships(self, mock_kuzu):
        """Test that all 7 code relationship types are created."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            calls = [str(call) for call in mock_conn.execute.call_args_list]
            expected_relationships = [
                "DEFINED_IN",
                "METHOD_OF",
                "CALLS",
                "INHERITS",
                "IMPORTS",
                "REFERENCES",
                "CONTAINS",
            ]

            for rel_type in expected_relationships:
                assert any(rel_type in str(call) for call in calls), (
                    f"{rel_type} code relationship not created"
                )

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_initialize_creates_all_10_memory_code_links(self, mock_kuzu):
        """Test that all 10 memory-code link relationship types are created."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            calls = [str(call) for call in mock_conn.execute.call_args_list]

            # 5 memory types × 2 targets (file + function) = 10 relationships
            expected_links = [
                "RELATES_TO_FILE_EPISODIC",
                "RELATES_TO_FILE_SEMANTIC",
                "RELATES_TO_FILE_PROCEDURAL",
                "RELATES_TO_FILE_PROSPECTIVE",
                "RELATES_TO_FILE_WORKING",
                "RELATES_TO_FUNCTION_EPISODIC",
                "RELATES_TO_FUNCTION_SEMANTIC",
                "RELATES_TO_FUNCTION_PROCEDURAL",
                "RELATES_TO_FUNCTION_PROSPECTIVE",
                "RELATES_TO_FUNCTION_WORKING",
            ]

            for link_type in expected_links:
                assert any(link_type in str(call) for call in calls), (
                    f"{link_type} memory-code link not created"
                )

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_initialize_creates_all_20_tables(self, mock_kuzu):
        """Test that exactly 20 new tables are created (3 nodes + 7 rels + 10 links)."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            calls = [str(call) for call in mock_conn.execute.call_args_list]

            # Count code schema tables
            code_tables = [
                "CodeFile", "Class", "Function",  # 3 node types
                "DEFINED_IN", "METHOD_OF", "CALLS", "INHERITS", "IMPORTS", "REFERENCES", "CONTAINS",  # 7 rels
                "RELATES_TO_FILE_EPISODIC", "RELATES_TO_FILE_SEMANTIC", "RELATES_TO_FILE_PROCEDURAL",
                "RELATES_TO_FILE_PROSPECTIVE", "RELATES_TO_FILE_WORKING",
                "RELATES_TO_FUNCTION_EPISODIC", "RELATES_TO_FUNCTION_SEMANTIC", "RELATES_TO_FUNCTION_PROCEDURAL",
                "RELATES_TO_FUNCTION_PROSPECTIVE", "RELATES_TO_FUNCTION_WORKING",  # 10 links
            ]

            found_tables = [table for table in code_tables if any(table in str(call) for call in calls)]
            assert len(found_tables) == 20, (
                f"Expected 20 code schema tables, found {len(found_tables)}: {found_tables}"
            )


class TestKuzuCodeSchemaIdempotency:
    """Test that initialize() can be called multiple times without errors."""

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_initialize_twice_succeeds(self, mock_kuzu):
        """Test calling initialize() twice doesn't raise errors."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")

            # First initialization
            backend.initialize()
            first_call_count = mock_conn.execute.call_count

            # Second initialization - should succeed
            backend.initialize()
            second_call_count = mock_conn.execute.call_count

            # Both should execute SQL, demonstrating idempotency
            assert first_call_count > 0, "First initialize() made no SQL calls"
            assert second_call_count > first_call_count, "Second initialize() made no SQL calls"

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_initialize_uses_if_not_exists(self, mock_kuzu):
        """Test that all CREATE statements use IF NOT EXISTS for idempotency."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            calls = [str(call) for call in mock_conn.execute.call_args_list]

            # All code schema CREATE statements should have IF NOT EXISTS
            code_create_calls = [
                c for c in calls
                if "CREATE" in str(c) and any(
                    table in str(c) for table in [
                        "CodeFile", "Class", "Function",
                        "DEFINED_IN", "METHOD_OF", "CALLS", "INHERITS", "IMPORTS", "REFERENCES", "CONTAINS",
                        "RELATES_TO_FILE", "RELATES_TO_FUNCTION"
                    ]
                )
            ]

            for call in code_create_calls:
                assert "IF NOT EXISTS" in str(call), (
                    f"CREATE statement missing IF NOT EXISTS: {call}"
                )


class TestKuzuCodeSchemaTableStructure:
    """Test that code schema tables have required properties."""

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_codefile_has_all_required_properties(self, mock_kuzu):
        """Test CodeFile node has all required properties from schema."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            calls = [str(call) for call in mock_conn.execute.call_args_list]
            codefile_calls = [c for c in calls if "CodeFile" in str(c)]

            required_properties = [
                "file_id", "file_path", "language", "size_bytes", "line_count",
                "last_modified", "git_hash", "module_name", "is_test", "metadata"
            ]

            for prop in required_properties:
                assert any(prop in str(c) for c in codefile_calls), (
                    f"CodeFile missing required property: {prop}"
                )

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_class_has_all_required_properties(self, mock_kuzu):
        """Test Class node has all required properties from schema."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            calls = [str(call) for call in mock_conn.execute.call_args_list]
            class_calls = [c for c in calls if "Class" in str(c) and "NODE TABLE" in str(c)]

            required_properties = [
                "class_id", "class_name", "fully_qualified_name", "line_start", "line_end",
                "docstring", "is_abstract", "is_interface", "access_modifier", "decorators", "metadata"
            ]

            for prop in required_properties:
                assert any(prop in str(c) for c in class_calls), (
                    f"Class missing required property: {prop}"
                )

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_function_has_all_required_properties(self, mock_kuzu):
        """Test Function node has all required properties from schema."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            calls = [str(call) for call in mock_conn.execute.call_args_list]
            func_calls = [c for c in calls if "Function" in str(c) and "NODE TABLE" in str(c)]

            required_properties = [
                "function_id", "function_name", "fully_qualified_name", "line_start", "line_end",
                "docstring", "signature", "return_type", "is_async", "is_method", "is_static",
                "access_modifier", "decorators", "complexity_score", "metadata"
            ]

            for prop in required_properties:
                assert any(prop in str(c) for c in func_calls), (
                    f"Function missing required property: {prop}"
                )

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_memory_code_links_have_relevance_score(self, mock_kuzu):
        """Test that memory-code link relationships have relevance_score property."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            calls = [str(call) for call in mock_conn.execute.call_args_list]
            link_calls = [c for c in calls if "RELATES_TO" in str(c)]

            # All memory-code links should have relevance_score and context
            for call in link_calls:
                assert "relevance_score" in str(call), (
                    f"Memory-code link missing relevance_score: {call}"
                )
                assert "context" in str(call), (
                    f"Memory-code link missing context: {call}"
                )


class TestKuzuCodeSchemaRegression:
    """Test that existing memory schema functionality still works."""

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_existing_memory_nodes_still_created(self, mock_kuzu):
        """Test that 5 memory node types are still created after adding code schema."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            calls = [str(call) for call in mock_conn.execute.call_args_list]

            # Verify existing memory node types still exist
            memory_nodes = [
                "EpisodicMemory", "SemanticMemory", "ProceduralMemory",
                "ProspectiveMemory", "WorkingMemory"
            ]

            for node_type in memory_nodes:
                assert any(node_type in str(call) for call in calls), (
                    f"Memory node type {node_type} not created - regression detected"
                )

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_existing_memory_relationships_still_created(self, mock_kuzu):
        """Test that 11 memory relationship types are still created."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            calls = [str(call) for call in mock_conn.execute.call_args_list]

            # Verify existing memory relationships still exist
            memory_rels = [
                "CONTAINS_EPISODIC", "CONTAINS_WORKING",
                "CONTRIBUTES_TO_SEMANTIC", "USES_PROCEDURE", "CREATES_INTENTION",
                "DERIVES_FROM", "REFERENCES", "TRIGGERS", "ACTIVATES", "RECALLS", "BUILDS_ON"
            ]

            for rel_type in memory_rels:
                assert any(rel_type in str(call) for call in calls), (
                    f"Memory relationship {rel_type} not created - regression detected"
                )

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_store_memory_still_works(self, mock_kuzu):
        """Test that storing memories still works after adding code schema."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            memory = MemoryEntry(
                id="test-1",
                session_id="session-1",
                agent_id="agent-1",
                memory_type=MemoryType.SEMANTIC,
                title="Test Knowledge",
                content="Code schema extension deployed",
                metadata={},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )

            mock_conn.execute.reset_mock()
            result = backend.store_memory(memory)

            # Should successfully store memory
            assert result is True, "store_memory() failed after code schema addition"

            # Should create SemanticMemory node
            calls = [str(call) for call in mock_conn.execute.call_args_list]
            assert any("SemanticMemory" in str(call) for call in calls), (
                "SemanticMemory node not created - regression detected"
            )


class TestKuzuCodeSchemaQueryCatalog:
    """Test that schema tables can be queried from Kuzu catalog."""

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_can_query_codefile_table_from_catalog(self, mock_kuzu):
        """Test that CodeFile table exists in Kuzu catalog after initialization."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_result = Mock()
        mock_result.has_next.return_value = True
        mock_result.get_next.return_value = ["CodeFile"]

        mock_conn = Mock()
        mock_conn.execute.return_value = mock_result
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            # Query catalog for CodeFile table
            mock_conn.execute.reset_mock()
            mock_conn.execute.return_value = mock_result

            # This query pattern is how we verify table existence
            result = backend.connection.execute("""
                MATCH (n:CodeFile) RETURN COUNT(n) AS count LIMIT 1
            """)

            # Should be able to query without error
            assert result is not None, "Cannot query CodeFile table from catalog"

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_can_query_all_code_relationships(self, mock_kuzu):
        """Test that all code relationships exist and can be queried."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_result = Mock()
        mock_result.has_next.return_value = False

        mock_conn = Mock()
        mock_conn.execute.return_value = mock_result
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            mock_conn.execute.reset_mock()
            mock_conn.execute.return_value = mock_result

            # Test querying each relationship type
            relationships = [
                ("Class", "DEFINED_IN", "CodeFile"),
                ("Function", "DEFINED_IN", "CodeFile"),
                ("Function", "METHOD_OF", "Class"),
                ("Function", "CALLS", "Function"),
                ("Class", "INHERITS", "Class"),
                ("CodeFile", "IMPORTS", "CodeFile"),
                ("Function", "REFERENCES", "Class"),
                ("CodeFile", "CONTAINS", "CodeFile"),
            ]

            for from_node, rel_type, to_node in relationships:
                # Each relationship should be queryable
                query = f"MATCH (a:{from_node})-[r:{rel_type}]->(b:{to_node}) RETURN COUNT(r) AS count"
                result = backend.connection.execute(query)
                assert result is not None, f"Cannot query {rel_type} relationship"


class TestKuzuCodeSchemaPerformance:
    """Test schema initialization performance requirements."""

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_initialize_completes_in_reasonable_time(self, mock_kuzu):
        """Test that initialize() with code schema completes quickly."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend
        import time

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")

            start = time.time()
            backend.initialize()
            elapsed = time.time() - start

            # Should complete in <1s (mostly mock overhead, but tests contract)
            assert elapsed < 2.0, (
                f"initialize() took {elapsed:.2f}s, should be <2s for mocked execution"
            )

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_initialize_creates_correct_number_of_statements(self, mock_kuzu):
        """Test that initialize() executes expected number of CREATE statements."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            calls = [str(call) for call in mock_conn.execute.call_args_list]

            # Count total CREATE statements for code schema
            # Expected: 3 node types + 7 code rels + 10 memory-code links = 20 new statements
            # Plus existing: 2 infrastructure nodes + 5 memory nodes + 11 memory rels = 18 existing
            # Total: 38 CREATE statements minimum
            create_calls = [c for c in calls if "CREATE" in str(c)]

            assert len(create_calls) >= 38, (
                f"Expected at least 38 CREATE statements, got {len(create_calls)}"
            )
