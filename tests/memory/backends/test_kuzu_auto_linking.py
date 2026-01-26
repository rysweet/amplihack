"""Tests for automated memory-code linking in Kuzu backend.

Tests Week 3 functionality:
- Auto-linking memories to code files based on metadata
- Auto-linking memories to functions based on content
- Relevance scoring (1.0 for metadata, 0.8 for content)
- Link deduplication
- Performance requirements

Philosophy:
- Test behavior, not implementation
- Focus on integration: store_memory() should auto-link
- Validate link quality (correct relevance scores, no duplicates)
"""

import tempfile
from datetime import datetime
from unittest.mock import Mock, patch

from src.amplihack.memory.models import MemoryEntry, MemoryType


class TestAutoLinkingBasics:
    """Test basic auto-linking functionality."""

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_store_memory_with_file_metadata_creates_file_link(self, mock_kuzu):
        """Test that storing a memory with file metadata auto-creates file link."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        # Mock result for file path query (return one matching file)
        mock_file_result = Mock()
        mock_file_result.has_next.side_effect = [True, False]  # One result
        mock_file_result.get_next.return_value = ["src/test.py"]

        # Mock result for existing relationship check (no existing links)
        mock_check_result = Mock()
        mock_check_result.has_next.return_value = True
        mock_check_result.get_next.return_value = [0]  # No existing relationships

        # Setup execute to return appropriate mocks
        def execute_side_effect(query, params=None):
            if "CodeFile" in query and "CONTAINS" in query:
                return mock_file_result
            if "COUNT(r)" in query:
                return mock_check_result
            return Mock(has_next=Mock(return_value=False))

        mock_conn.execute.side_effect = execute_side_effect

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db", enable_auto_linking=True)
            backend.initialize()

            memory = MemoryEntry(
                id="test-1",
                session_id="session-1",
                agent_id="agent-1",
                memory_type=MemoryType.EPISODIC,
                title="Test Event",
                content="Modified file",
                metadata={"file": "src/test.py"},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )

            mock_conn.execute.reset_mock()
            mock_conn.execute.side_effect = execute_side_effect

            result = backend.store_memory(memory)

            assert result is True, "store_memory() failed"

            # Check that file link was created with correct relevance score
            calls = [str(call) for call in mock_conn.execute.call_args_list]
            relates_to_file_calls = [c for c in calls if "RELATES_TO_FILE" in str(c)]

            assert len(relates_to_file_calls) > 0, "No RELATES_TO_FILE link created"

            # Verify relevance score is 1.0 for metadata match
            file_link_create = [c for c in relates_to_file_calls if "CREATE" in str(c)]
            assert len(file_link_create) > 0, "File link not created"
            assert "relevance_score" in str(file_link_create[0]), "Missing relevance_score"
            assert "1.0" in str(file_link_create[0]), "Relevance score should be 1.0 for metadata"

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_store_memory_with_function_in_content_creates_function_link(self, mock_kuzu):
        """Test that storing a memory mentioning a function auto-creates function link."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        # Mock result for function name query (return one matching function)
        mock_func_result = Mock()
        mock_func_result.has_next.side_effect = [True, False]
        mock_func_result.get_next.return_value = ["func_123", "process_data"]

        # Mock result for existing relationship check
        mock_check_result = Mock()
        mock_check_result.has_next.return_value = True
        mock_check_result.get_next.return_value = [0]

        def execute_side_effect(query, params=None):
            if "Function" in query and "CONTAINS" in query:
                return mock_func_result
            if "COUNT(r)" in query:
                return mock_check_result
            return Mock(has_next=Mock(return_value=False))

        mock_conn.execute.side_effect = execute_side_effect

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db", enable_auto_linking=True)
            backend.initialize()

            memory = MemoryEntry(
                id="test-2",
                session_id="session-1",
                agent_id="agent-1",
                memory_type=MemoryType.SEMANTIC,
                title="Function Knowledge",
                content="The process_data function handles input validation",
                metadata={},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )

            mock_conn.execute.reset_mock()
            mock_conn.execute.side_effect = execute_side_effect

            result = backend.store_memory(memory)

            assert result is True, "store_memory() failed"

            # Check that function link was created
            calls = [str(call) for call in mock_conn.execute.call_args_list]
            relates_to_func_calls = [c for c in calls if "RELATES_TO_FUNCTION" in str(c)]

            assert len(relates_to_func_calls) > 0, "No RELATES_TO_FUNCTION link created"

            # Verify relevance score is 0.8 for content match
            func_link_create = [c for c in relates_to_func_calls if "CREATE" in str(c)]
            assert len(func_link_create) > 0, "Function link not created"
            assert "relevance_score" in str(func_link_create[0]), "Missing relevance_score"
            assert "0.8" in str(func_link_create[0]), "Relevance score should be 0.8 for content"

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_auto_linking_can_be_disabled(self, mock_kuzu):
        """Test that auto-linking can be disabled via constructor parameter."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db", enable_auto_linking=False)
            backend.initialize()

            memory = MemoryEntry(
                id="test-3",
                session_id="session-1",
                agent_id="agent-1",
                memory_type=MemoryType.EPISODIC,
                title="Test Event",
                content="Modified file",
                metadata={"file": "src/test.py"},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )

            mock_conn.execute.reset_mock()
            result = backend.store_memory(memory)

            assert result is True, "store_memory() failed"

            # Should NOT query for code files or functions
            calls = [str(call) for call in mock_conn.execute.call_args_list]
            code_queries = [c for c in calls if "CodeFile" in str(c) or "Function" in str(c)]

            # Should have no code queries (only memory creation)
            assert len(code_queries) == 0, f"Auto-linking ran when disabled: {code_queries}"


class TestAutoLinkingRelevanceScoring:
    """Test relevance scoring logic."""

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_metadata_file_match_scores_1_0(self, mock_kuzu):
        """Test that file path from metadata gets relevance score 1.0."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        mock_file_result = Mock()
        mock_file_result.has_next.side_effect = [True, False]
        mock_file_result.get_next.return_value = ["src/test.py"]

        mock_check_result = Mock()
        mock_check_result.has_next.return_value = True
        mock_check_result.get_next.return_value = [0]

        def execute_side_effect(query, params=None):
            if "CodeFile" in query and "CONTAINS" in query:
                return mock_file_result
            if "COUNT(r)" in query:
                return mock_check_result
            return Mock(has_next=Mock(return_value=False))

        mock_conn.execute.side_effect = execute_side_effect

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            memory = MemoryEntry(
                id="test-4",
                session_id="session-1",
                agent_id="agent-1",
                memory_type=MemoryType.EPISODIC,
                title="File Change",
                content="Updated logic",
                metadata={"file": "src/test.py"},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )

            mock_conn.execute.reset_mock()
            mock_conn.execute.side_effect = execute_side_effect
            backend.store_memory(memory)

            # Find CREATE statement for file link
            calls = [str(call) for call in mock_conn.execute.call_args_list]
            create_calls = [c for c in calls if "RELATES_TO_FILE" in str(c) and "CREATE" in str(c)]

            assert len(create_calls) > 0, "No file link created"
            # Verify relevance_score: 1.0 appears in CREATE statement
            assert "relevance_score" in str(create_calls[0])
            assert "1.0" in str(create_calls[0])

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_content_function_match_scores_0_8(self, mock_kuzu):
        """Test that function name from content gets relevance score 0.8."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        mock_func_result = Mock()
        mock_func_result.has_next.side_effect = [True, False]
        mock_func_result.get_next.return_value = ["func_456", "calculate"]

        mock_check_result = Mock()
        mock_check_result.has_next.return_value = True
        mock_check_result.get_next.return_value = [0]

        def execute_side_effect(query, params=None):
            if "Function" in query and "CONTAINS" in query:
                return mock_func_result
            if "COUNT(r)" in query:
                return mock_check_result
            return Mock(has_next=Mock(return_value=False))

        mock_conn.execute.side_effect = execute_side_effect

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            memory = MemoryEntry(
                id="test-5",
                session_id="session-1",
                agent_id="agent-1",
                memory_type=MemoryType.SEMANTIC,
                title="Function Info",
                content="The calculate function performs computations",
                metadata={},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )

            mock_conn.execute.reset_mock()
            mock_conn.execute.side_effect = execute_side_effect
            backend.store_memory(memory)

            # Find CREATE statement for function link
            calls = [str(call) for call in mock_conn.execute.call_args_list]
            create_calls = [
                c for c in calls if "RELATES_TO_FUNCTION" in str(c) and "CREATE" in str(c)
            ]

            assert len(create_calls) > 0, "No function link created"
            assert "relevance_score" in str(create_calls[0])
            assert "0.8" in str(create_calls[0])


class TestAutoLinkingDeduplication:
    """Test that duplicate links are not created."""

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_duplicate_file_links_not_created(self, mock_kuzu):
        """Test that storing memory twice doesn't create duplicate file links."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        mock_file_result = Mock()
        mock_file_result.has_next.side_effect = [True, False]
        mock_file_result.get_next.return_value = ["src/test.py"]

        # First call: no existing links (return 0)
        # Second call: existing link found (return 1)
        call_count = [0]

        def get_check_result():
            call_count[0] += 1
            mock_result = Mock()
            mock_result.has_next.return_value = True
            if call_count[0] == 1:
                mock_result.get_next.return_value = [0]  # No existing
            else:
                mock_result.get_next.return_value = [1]  # Already exists
            return mock_result

        def execute_side_effect(query, params=None):
            if "CodeFile" in query and "CONTAINS" in query:
                return mock_file_result
            if "COUNT(r)" in query:
                return get_check_result()
            return Mock(has_next=Mock(return_value=False))

        mock_conn.execute.side_effect = execute_side_effect

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            memory = MemoryEntry(
                id="test-6",
                session_id="session-1",
                agent_id="agent-1",
                memory_type=MemoryType.EPISODIC,
                title="Event",
                content="Content",
                metadata={"file": "src/test.py"},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )

            # First storage - should create link
            mock_conn.execute.reset_mock()
            mock_conn.execute.side_effect = execute_side_effect
            backend.store_memory(memory)

            first_calls = [str(c) for c in mock_conn.execute.call_args_list]
            first_creates = [
                c for c in first_calls if "RELATES_TO_FILE" in str(c) and "CREATE" in str(c)
            ]
            assert len(first_creates) > 0, "First link not created"

            # Second storage - should NOT create duplicate
            mock_conn.execute.reset_mock()
            mock_conn.execute.side_effect = execute_side_effect
            backend.store_memory(memory)

            second_calls = [str(c) for c in mock_conn.execute.call_args_list]
            second_creates = [
                c for c in second_calls if "RELATES_TO_FILE" in str(c) and "CREATE" in str(c)
            ]
            assert len(second_creates) == 0, "Duplicate link created"


class TestAutoLinkingContextMetadata:
    """Test that link context metadata is properly set."""

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_file_link_has_metadata_context(self, mock_kuzu):
        """Test that file links include context='metadata_file_match'."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        mock_file_result = Mock()
        mock_file_result.has_next.side_effect = [True, False]
        mock_file_result.get_next.return_value = ["src/test.py"]

        mock_check_result = Mock()
        mock_check_result.has_next.return_value = True
        mock_check_result.get_next.return_value = [0]

        def execute_side_effect(query, params=None):
            if "CodeFile" in query and "CONTAINS" in query:
                return mock_file_result
            if "COUNT(r)" in query:
                return mock_check_result
            return Mock(has_next=Mock(return_value=False))

        mock_conn.execute.side_effect = execute_side_effect

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            memory = MemoryEntry(
                id="test-7",
                session_id="session-1",
                agent_id="agent-1",
                memory_type=MemoryType.EPISODIC,
                title="Event",
                content="Content",
                metadata={"file": "src/test.py"},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )

            mock_conn.execute.reset_mock()
            mock_conn.execute.side_effect = execute_side_effect
            backend.store_memory(memory)

            calls = [str(c) for c in mock_conn.execute.call_args_list]
            create_calls = [c for c in calls if "RELATES_TO_FILE" in str(c) and "CREATE" in str(c)]

            assert len(create_calls) > 0, "No file link created"
            assert "context" in str(create_calls[0])
            assert "metadata_file_match" in str(create_calls[0])

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_function_link_has_content_context(self, mock_kuzu):
        """Test that function links include context='content_name_match'."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        mock_func_result = Mock()
        mock_func_result.has_next.side_effect = [True, False]
        mock_func_result.get_next.return_value = ["func_789", "helper"]

        mock_check_result = Mock()
        mock_check_result.has_next.return_value = True
        mock_check_result.get_next.return_value = [0]

        def execute_side_effect(query, params=None):
            if "Function" in query and "CONTAINS" in query:
                return mock_func_result
            if "COUNT(r)" in query:
                return mock_check_result
            return Mock(has_next=Mock(return_value=False))

        mock_conn.execute.side_effect = execute_side_effect

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            memory = MemoryEntry(
                id="test-8",
                session_id="session-1",
                agent_id="agent-1",
                memory_type=MemoryType.SEMANTIC,
                title="Knowledge",
                content="The helper function assists with validation",
                metadata={},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )

            mock_conn.execute.reset_mock()
            mock_conn.execute.side_effect = execute_side_effect
            backend.store_memory(memory)

            calls = [str(c) for c in mock_conn.execute.call_args_list]
            create_calls = [
                c for c in calls if "RELATES_TO_FUNCTION" in str(c) and "CREATE" in str(c)
            ]

            assert len(create_calls) > 0, "No function link created"
            assert "context" in str(create_calls[0])
            assert "content_name_match" in str(create_calls[0])


class TestAutoLinkingErrorHandling:
    """Test that auto-linking failures don't break memory storage."""

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_linking_failure_does_not_fail_storage(self, mock_kuzu):
        """Test that memory storage succeeds even if linking fails."""
        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        call_counter = [0]

        # Make code file query raise an exception ONLY during store_memory
        def execute_side_effect(query, params=None):
            call_counter[0] += 1
            # Let initialization succeed (first ~38 calls)
            if call_counter[0] <= 40:
                return Mock(has_next=Mock(return_value=False))
            # Then fail on code file queries during auto-linking
            if "CodeFile" in query and "CONTAINS" in query:
                raise Exception("Database error")
            return Mock(has_next=Mock(return_value=False))

        mock_conn.execute.side_effect = execute_side_effect

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            memory = MemoryEntry(
                id="test-9",
                session_id="session-1",
                agent_id="agent-1",
                memory_type=MemoryType.EPISODIC,
                title="Event",
                content="Content",
                metadata={"file": "src/test.py"},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )

            # Should succeed despite linking failure
            result = backend.store_memory(memory)
            assert result is True, "Memory storage failed when linking failed"


class TestAutoLinkingPerformance:
    """Test performance characteristics of auto-linking."""

    @patch("src.amplihack.memory.backends.kuzu_backend.kuzu")
    def test_auto_linking_completes_quickly(self, mock_kuzu):
        """Test that auto-linking adds minimal overhead to store_memory()."""
        import time

        from src.amplihack.memory.backends.kuzu_backend import KuzuBackend

        mock_conn = Mock()
        mock_kuzu.Database.return_value = Mock()
        mock_kuzu.Connection.return_value = mock_conn

        # Mock fast responses
        mock_result = Mock()
        mock_result.has_next.return_value = False

        mock_conn.execute.return_value = mock_result

        with tempfile.TemporaryDirectory() as tmpdir:
            backend = KuzuBackend(db_path=f"{tmpdir}/test_db")
            backend.initialize()

            memory = MemoryEntry(
                id="test-10",
                session_id="session-1",
                agent_id="agent-1",
                memory_type=MemoryType.EPISODIC,
                title="Event",
                content="Content",
                metadata={"file": "src/test.py"},
                created_at=datetime.now(),
                accessed_at=datetime.now(),
            )

            mock_conn.execute.reset_mock()

            start = time.time()
            backend.store_memory(memory)
            elapsed = time.time() - start

            # Should complete in <100ms (mostly mock overhead)
            assert elapsed < 0.5, f"Auto-linking too slow: {elapsed:.2f}s"
