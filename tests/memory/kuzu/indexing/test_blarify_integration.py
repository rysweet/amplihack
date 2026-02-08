"""Integration tests for blarify indexing enhancements.

Tests full workflow from launcher through Kuzu import,
missing tools scenario, and background execution end-to-end.
"""

import time
from unittest.mock import patch

import pytest

from amplihack.memory.kuzu.code_graph import KuzuCodeGraph
from amplihack.memory.kuzu.connector import KuzuConnector
from amplihack.memory.kuzu.indexing.orchestrator import Orchestrator


class TestBlarifyIntegration:
    """Integration tests for complete blarify indexing workflow."""

    @pytest.fixture
    def temp_kuzu_db(self, tmp_path):
        """Create temporary Kuzu database."""
        db_path = tmp_path / "test_kuzu.db"
        connector = KuzuConnector(str(db_path))
        yield connector
        connector.close()

    @pytest.fixture
    def test_codebase(self, tmp_path):
        """Create test codebase."""
        codebase = tmp_path / "test_codebase"
        codebase.mkdir()

        # Create sample Python file
        python_file = codebase / "sample.py"
        python_file.write_text("""
def hello_world():
    '''Sample function.'''
    return "Hello, World!"

class SampleClass:
    '''Sample class.'''
    def method(self):
        return 42
""")

        # Create sample JavaScript file
        js_file = codebase / "sample.js"
        js_file.write_text("""
function helloWorld() {
    return "Hello, World!";
}

class SampleClass {
    method() {
        return 42;
    }
}
""")

        return codebase

    def test_full_workflow_launcher_to_kuzu_import(self, test_codebase, temp_kuzu_db):
        """Test full workflow from launcher through Kuzu import."""
        # Arrange
        orchestrator = Orchestrator(connector=temp_kuzu_db)
        code_graph = KuzuCodeGraph(temp_kuzu_db)

        # Act - Run complete indexing workflow
        _ = orchestrator.run(
            codebase_path=test_codebase,
            languages=["python", "javascript"],
        )

        # Import results into Kuzu
        if result.success:
            import_counts = code_graph.import_blarify_output(
                blarify_json_path=result.output_file,
                project_id="test_project",
            )

        # Assert
        assert result.success is True
        assert result.total_files >= 2
        assert import_counts["files"] >= 2
        assert import_counts["functions"] >= 2
        assert import_counts["classes"] >= 2

    def test_missing_tools_scenario(self, test_codebase, temp_kuzu_db):
        """Test handling of missing tools scenario."""
        # Arrange
        orchestrator = Orchestrator(connector=temp_kuzu_db)

        with patch("shutil.which") as mock_which:
            # Simulate missing scip-python
            def which_side_effect(cmd):
                if cmd == "scip-python":
                    return None
                return "/usr/bin/node"

            mock_which.side_effect = which_side_effect

            # Act
            _ = orchestrator.run(
                codebase_path=test_codebase,
                languages=["python", "javascript"],
            )

        # Assert - Should gracefully degrade
        assert result.partial_success is True
        assert "python" in result.skipped_languages
        assert "javascript" in result.completed_languages
        assert result.total_files > 0  # JavaScript files indexed

    def test_background_execution_end_to_end(self, test_codebase, temp_kuzu_db):
        """Test background execution end-to-end."""
        # Arrange
        orchestrator = Orchestrator(connector=temp_kuzu_db)

        # Act - Start background job
        _ = orchestrator.run(
            codebase_path=test_codebase,
            languages=["python"],
            background=True,
        )

        # Wait for completion
        timeout = 30
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = orchestrator.get_job_status(result.background_job_id)
            if status in ["COMPLETED", "FAILED"]:
                break
            time.sleep(0.5)

        final_result = orchestrator.get_job_result(result.background_job_id)

        # Assert
        assert result.is_background is True
        assert result.background_job_id is not None
        assert final_result.success is True
        assert final_result.total_files > 0

    def test_prerequisite_check_integration(self, test_codebase):
        """Test prerequisite checking integration."""
        # Arrange
        orchestrator = Orchestrator()

        # Act
        prereq_result = orchestrator.check_prerequisites(["python", "javascript", "typescript"])

        # Assert
        assert prereq_result.can_proceed is True or prereq_result.partial_success is True
        assert len(prereq_result.available_languages) > 0

    def test_progress_tracking_integration(self, test_codebase, temp_kuzu_db):
        """Test progress tracking throughout workflow."""
        # Arrange
        orchestrator = Orchestrator(connector=temp_kuzu_db)
        progress_updates = []

        def capture_progress(update):
            progress_updates.append(update)

        orchestrator.register_progress_callback(capture_progress)

        # Act
        _ = orchestrator.run(
            codebase_path=test_codebase,
            languages=["python"],
        )

        # Assert
        assert len(progress_updates) > 0
        assert any("python" in str(u) for u in progress_updates)

    def test_error_handling_integration(self, test_codebase, temp_kuzu_db):
        """Test error handling integration."""
        # Arrange
        orchestrator = Orchestrator(connector=temp_kuzu_db)

        with patch.object(orchestrator.code_graph, "run_blarify") as mock_blarify:
            # Simulate indexing error
            mock_blarify.side_effect = RuntimeError("Indexing failed")

            # Act
            _ = orchestrator.run(
                codebase_path=test_codebase,
                languages=["python"],
            )

        # Assert
        assert result.success is False
        assert len(result.errors) > 0

    def test_kuzu_import_with_relationships(self, test_codebase, temp_kuzu_db):
        """Test Kuzu import with relationships."""
        # Arrange
        orchestrator = Orchestrator(connector=temp_kuzu_db)
        code_graph = KuzuCodeGraph(temp_kuzu_db)

        # Act
        _ = orchestrator.run(
            codebase_path=test_codebase,
            languages=["python"],
        )

        import_counts = code_graph.import_blarify_output(
            blarify_json_path=result.output_file,
            project_id="test_project",
        )

        # Query relationships
        files = temp_kuzu_db.execute_query("MATCH (f:CodeFile) RETURN count(f) as cnt")
        functions = temp_kuzu_db.execute_query("MATCH (fn:CodeFunction) RETURN count(fn) as cnt")
        relationships = temp_kuzu_db.execute_query(
            "MATCH (fn:CodeFunction)-[r:DEFINED_IN]->(f:CodeFile) RETURN count(r) as cnt"
        )

        # Assert
        assert files[0]["cnt"] > 0
        assert functions[0]["cnt"] > 0
        assert relationships[0]["cnt"] > 0

    def test_multi_language_indexing(self, test_codebase, temp_kuzu_db):
        """Test indexing multiple languages."""
        # Arrange
        orchestrator = Orchestrator(connector=temp_kuzu_db)
        code_graph = KuzuCodeGraph(temp_kuzu_db)

        # Act
        _ = orchestrator.run(
            codebase_path=test_codebase,
            languages=["python", "javascript"],
        )

        import_counts = code_graph.import_blarify_output(
            blarify_json_path=result.output_file,
            project_id="test_project",
        )

        # Assert
        assert result.success is True
        assert len(result.completed_languages) >= 1
        assert import_counts["files"] >= 2

    def test_incremental_update_integration(self, test_codebase, temp_kuzu_db):
        """Test incremental update workflow."""
        # Arrange
        orchestrator = Orchestrator(connector=temp_kuzu_db)
        code_graph = KuzuCodeGraph(temp_kuzu_db)

        # Initial indexing
        result1 = orchestrator.run(
            codebase_path=test_codebase,
            languages=["python"],
        )
        import_counts1 = code_graph.import_blarify_output(
            blarify_json_path=result1.output_file,
            project_id="test_project",
        )

        # Add new file
        new_file = test_codebase / "new_module.py"
        new_file.write_text("""
def new_function():
    return "New"
""")

        # Incremental update
        result2 = orchestrator.run(
            codebase_path=test_codebase,
            languages=["python"],
            incremental=True,
        )
        import_counts2 = code_graph.incremental_update(
            blarify_json_path=result2.output_file,
            project_id="test_project",
        )

        # Assert
        assert import_counts2["files"] >= import_counts1["files"]
        assert import_counts2["functions"] >= import_counts1["functions"]

    def test_large_codebase_performance(self, tmp_path, temp_kuzu_db):
        """Test performance with larger codebase."""
        # Arrange
        large_codebase = tmp_path / "large_codebase"
        large_codebase.mkdir()

        # Create 100 Python files
        for i in range(100):
            file = large_codebase / f"module_{i}.py"
            file.write_text(f"""
def function_{i}():
    return {i}

class Class_{i}:
    def method_{i}(self):
        return {i}
""")

        orchestrator = Orchestrator(connector=temp_kuzu_db)

        # Act
        start_time = time.time()
        _ = orchestrator.run(
            codebase_path=large_codebase,
            languages=["python"],
        )
        elapsed = time.time() - start_time

        # Assert
        assert result.success is True
        assert result.total_files >= 100
        # Should complete in reasonable time (< 60 seconds for 100 files)
        assert elapsed < 60

    def test_error_recovery_and_retry(self, test_codebase, temp_kuzu_db):
        """Test error recovery and retry logic."""
        # Arrange
        orchestrator = Orchestrator(connector=temp_kuzu_db)
        attempt_count = 0

        def flaky_indexing(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise RuntimeError("Transient failure")
            return {"files": 10, "functions": 50, "classes": 5}

        with patch.object(orchestrator.code_graph, "run_blarify", side_effect=flaky_indexing):
            # Act
            _ = orchestrator.run(
                codebase_path=test_codebase,
                languages=["python"],
                max_retries=3,
            )

        # Assert
        assert result.success is True
        assert attempt_count == 3

    def test_concurrent_language_processing(self, test_codebase, temp_kuzu_db):
        """Test concurrent processing of multiple languages."""
        # Arrange
        orchestrator = Orchestrator(connector=temp_kuzu_db)

        # Act
        start_time = time.time()
        _ = orchestrator.run(
            codebase_path=test_codebase,
            languages=["python", "javascript"],
            parallel=True,
        )
        parallel_time = time.time() - start_time

        # Compare with sequential
        start_time = time.time()
        result_seq = orchestrator.run(
            codebase_path=test_codebase,
            languages=["python", "javascript"],
            parallel=False,
        )
        sequential_time = time.time() - start_time

        # Assert - Parallel should be faster (or similar)
        assert result.success is True
        assert parallel_time <= sequential_time * 1.2  # Allow 20% overhead

    def test_cleanup_on_error(self, test_codebase, tmp_path, temp_kuzu_db):
        """Test cleanup of temporary files on error."""
        # Arrange
        orchestrator = Orchestrator(connector=temp_kuzu_db)

        with patch.object(orchestrator.code_graph, "run_blarify") as mock_blarify:
            mock_blarify.side_effect = RuntimeError("Fatal error")

            # Act
            _ = orchestrator.run(
                codebase_path=test_codebase,
                languages=["python"],
            )

        # Assert - Temp files should be cleaned up
        temp_files = list(tmp_path.glob("blarify_temp_*"))
        assert len(temp_files) == 0
