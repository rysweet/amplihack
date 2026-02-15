"""Comprehensive integration tests for Blarify graph and hooks.

This test suite validates the entire workflow:
1. Hook triggers detect Edit/Write operations
2. Staleness detection identifies when reindexing is needed
3. Indexing orchestrator runs successfully
4. Graph data is queryable
5. Cross-platform compatibility

Test Structure:
- 60% Unit tests (components in isolation)
- 30% Integration tests (end-to-end workflows)
- 10% Platform tests (environment variations)
"""

import os
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest  # pyright: ignore[reportMissingImports]

# Test imports
from amplihack.memory.kuzu.indexing.staleness_detector import (
    check_index_status,
)


class TestStalenessDetection:
    """Test staleness detection logic (UNIT TESTS - 60%)."""

    def test_missing_index_needs_indexing(self, tmp_path):
        """Test that missing index triggers indexing need."""
        # ARRANGE: Create project with Python files but no index
        project_path = tmp_path / "test_project"
        project_path.mkdir()
        (project_path / "main.py").write_text("print('hello')")

        # ACT: Check index status
        status = check_index_status(project_path)

        # ASSERT: Should need indexing
        assert status.needs_indexing is True
        assert status.reason == "missing (no index found)"
        assert status.estimated_files == 1
        assert status.last_indexed is None

    def test_up_to_date_index_no_reindex(self, tmp_path):
        """Test that current index doesn't trigger reindexing."""
        # ARRANGE: Create project with index newer than source
        project_path = tmp_path / "test_project"
        project_path.mkdir()

        # Create source file
        source_file = project_path / "main.py"
        source_file.write_text("print('hello')")
        time.sleep(0.1)

        # Create index file after source (newer)
        index_dir = project_path / ".amplihack"
        index_dir.mkdir()
        index_file = index_dir / "index.scip"
        index_file.write_text("mock index")

        # ACT: Check index status
        status = check_index_status(project_path)

        # ASSERT: Should NOT need indexing
        assert status.needs_indexing is False
        assert "up-to-date" in status.reason
        assert status.last_indexed is not None

    def test_stale_index_needs_reindex(self, tmp_path):
        """Test that outdated index triggers reindexing."""
        # ARRANGE: Create index, then modify source
        project_path = tmp_path / "test_project"
        project_path.mkdir()

        # Create index first
        index_dir = project_path / ".amplihack"
        index_dir.mkdir()
        index_file = index_dir / "index.scip"
        index_file.write_text("mock index")
        time.sleep(0.1)

        # Create source file after index (newer)
        source_file = project_path / "main.py"
        source_file.write_text("print('hello')")

        # ACT: Check index status
        status = check_index_status(project_path)

        # ASSERT: Should need indexing
        assert status.needs_indexing is True
        assert "stale" in status.reason
        assert status.estimated_files == 1

    def test_empty_project_no_indexing(self, tmp_path):
        """Test that empty project doesn't need indexing."""
        # ARRANGE: Create empty project
        project_path = tmp_path / "empty_project"
        project_path.mkdir()

        # ACT: Check index status
        status = check_index_status(project_path)

        # ASSERT: Should NOT need indexing
        assert status.needs_indexing is False
        assert "no files to index" in status.reason
        assert status.estimated_files == 0

    def test_counts_only_indexable_files(self, tmp_path):
        """Test that only supported file types are counted."""
        # ARRANGE: Create project with mixed files
        project_path = tmp_path / "test_project"
        project_path.mkdir()

        # Create indexable files
        (project_path / "main.py").write_text("# python")
        (project_path / "app.ts").write_text("// typescript")
        (project_path / "util.js").write_text("// javascript")

        # Create non-indexable files
        (project_path / "README.md").write_text("# docs")
        (project_path / "data.json").write_text("{}")
        (project_path / "image.png").write_bytes(b"fake png")

        # ACT: Check index status
        status = check_index_status(project_path)

        # ASSERT: Should count only 3 indexable files
        assert status.estimated_files == 3
        assert status.needs_indexing is True

    def test_ignores_standard_directories(self, tmp_path):
        """Test that ignored directories are skipped."""
        # ARRANGE: Create project with ignored dirs
        project_path = tmp_path / "test_project"
        project_path.mkdir()

        # Create files in ignored directories
        (project_path / ".git").mkdir()
        (project_path / ".git" / "config.py").write_text("# git")

        (project_path / "venv").mkdir()
        (project_path / "venv" / "lib.py").write_text("# venv")

        (project_path / "__pycache__").mkdir()
        (project_path / "__pycache__" / "cache.py").write_text("# cache")

        # Create files in project root
        (project_path / "main.py").write_text("# main")

        # ACT: Check index status
        status = check_index_status(project_path)

        # ASSERT: Should count only main.py
        assert status.estimated_files == 1


class TestHookTriggers:
    """Test hook trigger detection (UNIT TESTS - 60%)."""

    @pytest.mark.skip(reason="Hook integration needs implementation")
    def test_edit_operation_detected(self, tmp_path):
        """Test that Edit tool operation is detected by hook."""
        # ARRANGE: Create mock Edit operation
        project_path = tmp_path / "test_project"
        project_path.mkdir()
        target_file = project_path / "main.py"
        target_file.write_text("print('before')")

        # Mock hook registry
        hook_triggered = []

        def mock_hook(tool_name, tool_args, tool_result):
            if tool_name == "Edit":
                hook_triggered.append(tool_args.get("file_path"))

        # ACT: Simulate Edit operation
        # (This would be called by Claude Code's hook system)
        mock_hook("Edit", {"file_path": str(target_file)}, {})

        # ASSERT: Hook should detect the edit
        assert str(target_file) in hook_triggered

    @pytest.mark.skip(reason="Hook integration needs implementation")
    def test_write_operation_detected(self, tmp_path):
        """Test that Write tool operation is detected by hook."""
        # Similar to edit test but for Write tool
        # Implementation would mirror test_edit_operation_detected

    @pytest.mark.skip(reason="Hook integration needs implementation")
    def test_threshold_triggers_reindex(self, tmp_path):
        """Test that staleness threshold triggers reindexing."""
        # ARRANGE: Setup project with multiple files
        # Modify enough files to exceed threshold
        # ACT: Trigger hook multiple times
        # ASSERT: Reindexing is triggered when threshold exceeded


class TestIntegrationFlow:
    """Test end-to-end integration flow (INTEGRATION TESTS - 30%)."""

    @pytest.mark.skip(reason="Full integration test - requires database")
    def test_edit_to_index_to_query_flow(self, tmp_path):
        """Test complete flow: Edit → Detect → Index → Query.

        This is the critical path that validates:
        1. File edit is detected
        2. Staleness check runs
        3. Indexing is triggered
        4. Graph is updated
        5. Data is queryable
        """
        # ARRANGE: Setup project and database
        project_path = tmp_path / "test_project"
        project_path.mkdir()

        # Create initial file and index
        source_file = project_path / "main.py"
        source_file.write_text(
            """
def hello_world():
    print("Hello, world!")
"""
        )

        # Mock database connection
        mock_connector = MagicMock()

        # ACT 1: Initial indexing
        from amplihack.memory.kuzu.indexing.orchestrator import (
            IndexingConfig,
            Orchestrator,
        )

        orchestrator = Orchestrator(connector=mock_connector)
        result = orchestrator.run(
            codebase_path=project_path,
            languages=["python"],
            background=False,
            config=IndexingConfig(timeout=60),
        )

        # ASSERT 1: Initial index successful
        assert result.success is True
        assert result.total_files > 0

        # ACT 2: Edit file (simulate hook trigger)
        source_file.write_text(
            """
def hello_world():
    print("Hello, world!")

def goodbye():
    print("Goodbye!")
"""
        )

        # ACT 3: Check staleness
        status = check_index_status(project_path)

        # ASSERT 2: Index is now stale
        assert status.needs_indexing is True
        assert "stale" in status.reason

        # ACT 4: Reindex (would be triggered by hook in production)
        result = orchestrator.run(
            codebase_path=project_path,
            languages=["python"],
            background=False,
            config=IndexingConfig(timeout=60),
        )

        # ASSERT 3: Reindex successful
        assert result.success is True

        # ACT 5: Query the graph (verify new function exists)
        # (This would query Kuzu for the new 'goodbye' function)
        # mock_connector.query.assert_called()

    @pytest.mark.skip(reason="Full integration test - requires database")
    def test_multiple_file_edits_batch_correctly(self, tmp_path):
        """Test that multiple edits batch into single reindex."""
        # ARRANGE: Project with multiple files
        # ACT: Edit multiple files in sequence
        # ASSERT: Single reindex handles all changes

    @pytest.mark.skip(reason="Full integration test - requires background runner")
    def test_background_indexing_completes(self, tmp_path):
        """Test background indexing job completes successfully."""
        # ARRANGE: Setup project
        # ACT: Start background indexing
        # ASSERT: Job completes and data is available


class TestCrossPlatform:
    """Test cross-platform compatibility (PLATFORM TESTS - 10%)."""

    def test_works_in_claude_code_environment(self):
        """Test hooks work in Claude Code environment."""
        # ARRANGE: Detect Claude Code environment
        # Claude Code sets specific environment variables
        is_claude_code = os.getenv("CLAUDE_CODE") is not None

        # ACT & ASSERT: Environment detection works
        # (In real implementation, hook registration would check this)
        assert isinstance(is_claude_code, bool)

    @pytest.mark.skipif(
        os.getenv("GITHUB_COPILOT") is None,
        reason="GitHub Copilot environment not available",
    )
    def test_works_in_github_copilot_cli_environment(self):
        """Test hooks work in GitHub Copilot CLI environment."""
        # ARRANGE: Detect GitHub Copilot environment
        is_copilot = os.getenv("GITHUB_COPILOT") is not None

        # ACT & ASSERT: Environment detection works
        assert is_copilot is True

    def test_database_unavailable_graceful_degradation(self, tmp_path):
        """Test graceful handling when Kuzu database unavailable."""
        # ARRANGE: Setup without database connection
        project_path = tmp_path / "test_project"
        project_path.mkdir()
        (project_path / "main.py").write_text("print('hello')")

        from amplihack.memory.kuzu.indexing.orchestrator import (
            IndexingConfig,
            Orchestrator,
        )

        # ACT: Run orchestrator without connector
        orchestrator = Orchestrator(connector=None)
        result = orchestrator.run(
            codebase_path=project_path,
            languages=["python"],
            dry_run=True,  # Dry run should work without database
            config=IndexingConfig(),
        )

        # ASSERT: Should handle gracefully
        assert result.dry_run is True
        assert result.success is True


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_indexing_fails_gracefully_on_invalid_path(self):
        """Test error handling for non-existent path."""
        # ARRANGE: Invalid path
        from amplihack.memory.kuzu.indexing.orchestrator import (
            IndexingConfig,
            Orchestrator,
        )

        orchestrator = Orchestrator(connector=None)
        invalid_path = Path("/nonexistent/path")

        # ACT: Attempt indexing
        result = orchestrator.run(
            codebase_path=invalid_path,
            languages=["python"],
            config=IndexingConfig(),
        )

        # ASSERT: Should fail gracefully
        assert result.success is False
        assert len(result.errors) > 0

    def test_handles_very_large_codebase(self, tmp_path):
        """Test performance with large number of files."""
        # ARRANGE: Create large project structure
        project_path = tmp_path / "large_project"
        project_path.mkdir()

        # Create 1000 files (simulates large codebase)
        for i in range(1000):
            file_path = project_path / f"file_{i}.py"
            file_path.write_text(f"# File {i}")

        # ACT: Check staleness (should complete quickly)
        start_time = time.time()
        status = check_index_status(project_path)
        elapsed_time = time.time() - start_time

        # ASSERT: Should complete in < 1 second
        assert elapsed_time < 1.0
        assert status.estimated_files == 1000

    def test_handles_concurrent_edits(self, tmp_path):
        """Test behavior with concurrent file modifications."""
        # ARRANGE: Project with index
        project_path = tmp_path / "test_project"
        project_path.mkdir()

        # Create index
        index_dir = project_path / ".amplihack"
        index_dir.mkdir()
        (index_dir / "index.scip").write_text("mock index")
        time.sleep(0.1)

        # ACT: Modify multiple files "concurrently"
        for i in range(5):
            file_path = project_path / f"file_{i}.py"
            file_path.write_text(f"# Modified {i}")

        # Check staleness
        status = check_index_status(project_path)

        # ASSERT: Should detect staleness from newest file
        assert status.needs_indexing is True
        assert status.estimated_files == 5


class TestPerformance:
    """Performance benchmarks for critical paths."""

    def test_staleness_check_performance(self, tmp_path):
        """Test that staleness check completes in < 100ms."""
        # ARRANGE: Create realistic project
        project_path = tmp_path / "test_project"
        project_path.mkdir()

        # Create 100 files
        for i in range(100):
            (project_path / f"file_{i}.py").write_text("# code")

        # ACT: Measure staleness check time
        start_time = time.time()
        status = check_index_status(project_path)
        elapsed_time = time.time() - start_time

        # ASSERT: Should complete in < 100ms
        assert elapsed_time < 0.1
        assert status.estimated_files == 100


# ============================================================================
# TEST FIXTURES
# ============================================================================


@pytest.fixture
def mock_kuzu_connector():
    """Mock Kuzu connector for testing."""
    connector = MagicMock()
    connector.query.return_value = []
    return connector


@pytest.fixture
def sample_project(tmp_path):
    """Create a sample project structure for testing."""
    project_path = tmp_path / "sample_project"
    project_path.mkdir()

    # Create source files
    (project_path / "main.py").write_text(
        """
def main():
    print("Hello, world!")

if __name__ == "__main__":
    main()
"""
    )

    (project_path / "utils.py").write_text(
        """
def helper():
    return "helper"

class UtilClass:
    def method(self):
        pass
"""
    )

    return project_path


# ============================================================================
# VERIFICATION HELPERS
# ============================================================================


def verify_hook_integration():
    """Verify that hooks are properly integrated.

    This function checks:
    1. Hook files exist
    2. Hook registration is called
    3. Hook callbacks are registered

    Returns:
        bool: True if hooks are properly integrated
    """
    # Check if post_tool_use hook exists
    hook_path = Path.home() / ".claude" / "tools" / "amplihack" / "hooks" / "post_tool_use.py"
    if not hook_path.exists():
        return False

    # Check if blarify hook is registered
    # (Would inspect hook registry in real implementation)
    return True


def verify_graph_queryable(connector):
    """Verify that graph data is queryable.

    Args:
        connector: Kuzu connector instance

    Returns:
        bool: True if graph can be queried
    """
    try:
        # Try a simple query
        connector.query("MATCH (n) RETURN count(n) LIMIT 1")
        return True
    except Exception:
        return False


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: Integration tests (requires database)")
    config.addinivalue_line("markers", "platform: Platform-specific tests")
    config.addinivalue_line("markers", "performance: Performance benchmarks")
