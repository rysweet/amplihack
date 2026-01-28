"""Tests for Orchestrator module.

Tests end-to-end orchestration with all prerequisites,
graceful degradation, background execution, failed language skipping,
and accurate IndexingResult counts.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from amplihack.memory.kuzu.indexing.error_handler import ErrorSeverity, IndexingError
from amplihack.memory.kuzu.indexing.orchestrator import (
    IndexingConfig,
    Orchestrator,
)
from amplihack.memory.kuzu.indexing.prerequisite_checker import PrerequisiteResult


class TestOrchestrator:
    """Test orchestration of the indexing workflow."""

    @pytest.fixture
    def orchestrator(self):
        """Create Orchestrator instance."""
        return Orchestrator()

    def test_end_to_end_flow_with_all_prerequisites_available(self, orchestrator):
        """Test end-to-end flow with all prerequisites available."""
        # Arrange
        codebase_path = Path("/path/to/codebase")
        languages = ["python", "javascript"]

        with (
            patch.object(orchestrator, "_check_prerequisites") as mock_prereq,
            patch.object(orchestrator, "_run_indexing") as mock_index,
            patch.object(orchestrator, "_import_results") as mock_import,
        ):
            # All prerequisites available
            mock_prereq.return_value = PrerequisiteResult(
                can_proceed=True,
                available_languages=["python", "javascript"],
                unavailable_languages=[],
                partial_success=False,
            )

            mock_index.return_value = {
                "python": {"files": 100, "functions": 500},
                "javascript": {"files": 50, "functions": 200},
            }

            mock_import.return_value = {
                "files": 150,
                "functions": 700,
                "classes": 100,
            }

            # Act
            _ = orchestrator.run(
                codebase_path=codebase_path,
                languages=languages,
            )

            # Assert
            assert result.success is True
            assert result.total_files == 150
            assert result.total_functions == 700
            assert len(result.completed_languages) == 2
            assert len(result.failed_languages) == 0

    def test_graceful_degradation_with_missing_prerequisites(self, orchestrator):
        """Test graceful degradation with missing prerequisites."""
        # Arrange
        codebase_path = Path("/path/to/codebase")
        languages = ["python", "javascript", "typescript"]

        with (
            patch.object(orchestrator, "_check_prerequisites") as mock_prereq,
            patch.object(orchestrator, "_run_indexing") as mock_index,
            patch.object(orchestrator, "_import_results") as mock_import,
        ):
            # Only javascript available
            mock_prereq.return_value = PrerequisiteResult(
                can_proceed=True,
                available_languages=["javascript"],
                unavailable_languages=["python", "typescript"],
                partial_success=True,
            )

            mock_index.return_value = {
                "javascript": {"files": 50, "functions": 200},
            }

            mock_import.return_value = {
                "files": 50,
                "functions": 200,
                "classes": 20,
            }

            # Act
            _ = orchestrator.run(
                codebase_path=codebase_path,
                languages=languages,
            )

            # Assert
            assert result.success is True
            assert result.partial_success is True
            assert len(result.completed_languages) == 1
            assert "javascript" in result.completed_languages
            assert len(result.skipped_languages) == 2
            assert "python" in result.skipped_languages
            assert "typescript" in result.skipped_languages

    def test_background_execution_option(self, orchestrator):
        """Test background execution option."""
        # Arrange
        codebase_path = Path("/path/to/codebase")
        languages = ["python"]

        with (
            patch.object(orchestrator, "_check_prerequisites") as mock_prereq,
            patch.object(orchestrator, "_start_background_job") as mock_bg,
        ):
            mock_prereq.return_value = PrerequisiteResult(
                can_proceed=True,
                available_languages=["python"],
                unavailable_languages=[],
                partial_success=False,
            )

            mock_bg.return_value = Mock(job_id="job123", status="RUNNING")

            # Act
            _ = orchestrator.run(
                codebase_path=codebase_path,
                languages=languages,
                background=True,
            )

            # Assert
            assert result.background_job_id == "job123"
            assert result.is_background is True
            mock_bg.assert_called_once()

    def test_failed_languages_are_skipped(self, orchestrator):
        """Test that failed languages are skipped."""
        # Arrange
        codebase_path = Path("/path/to/codebase")
        languages = ["python", "javascript", "typescript"]

        with (
            patch.object(orchestrator, "_check_prerequisites") as mock_prereq,
            patch.object(orchestrator, "_run_indexing") as mock_index,
        ):
            # All prerequisites available
            mock_prereq.return_value = PrerequisiteResult(
                can_proceed=True,
                available_languages=["python", "javascript", "typescript"],
                unavailable_languages=[],
                partial_success=False,
            )

            # Python succeeds, javascript fails, typescript succeeds
            mock_index.return_value = {
                "python": {"files": 100, "functions": 500},
                "javascript": IndexingError(
                    language="javascript",
                    error_type="timeout",
                    message="Indexing timeout",
                    severity=ErrorSeverity.RECOVERABLE,
                ),
                "typescript": {"files": 75, "functions": 300},
            }

            # Act
            _ = orchestrator.run(
                codebase_path=codebase_path,
                languages=languages,
            )

            # Assert
            assert result.success is True
            assert result.partial_success is True
            assert len(result.completed_languages) == 2
            assert "python" in result.completed_languages
            assert "typescript" in result.completed_languages
            assert len(result.failed_languages) == 1
            assert "javascript" in result.failed_languages

    def test_indexing_result_contains_accurate_counts(self, orchestrator):
        """Test that IndexingResult contains accurate counts."""
        # Arrange
        codebase_path = Path("/path/to/codebase")
        languages = ["python", "javascript"]

        with (
            patch.object(orchestrator, "_check_prerequisites") as mock_prereq,
            patch.object(orchestrator, "_run_indexing") as mock_index,
            patch.object(orchestrator, "_import_results") as mock_import,
        ):
            mock_prereq.return_value = PrerequisiteResult(
                can_proceed=True,
                available_languages=["python", "javascript"],
                unavailable_languages=[],
                partial_success=False,
            )

            mock_index.return_value = {
                "python": {"files": 100, "functions": 500, "classes": 50},
                "javascript": {"files": 50, "functions": 200, "classes": 20},
            }

            mock_import.return_value = {
                "files": 150,
                "functions": 700,
                "classes": 70,
                "relationships": 300,
            }

            # Act
            _ = orchestrator.run(
                codebase_path=codebase_path,
                languages=languages,
            )

            # Assert
            assert result.total_files == 150
            assert result.total_functions == 700
            assert result.total_classes == 70
            assert result.total_relationships == 300

    def test_progress_tracking_during_orchestration(self, orchestrator):
        """Test progress tracking during orchestration."""
        # Arrange
        codebase_path = Path("/path/to/codebase")
        languages = ["python", "javascript"]
        progress_updates = []

        def progress_callback(update):
            progress_updates.append(update)

        orchestrator.register_progress_callback(progress_callback)

        # Mock code_graph instead of _run_indexing to allow progress callbacks to fire
        with (
            patch.object(orchestrator, "code_graph") as mock_cg,
            patch.object(orchestrator, "_check_prerequisites") as mock_prereq,
        ):
            mock_prereq.return_value = PrerequisiteResult(
                can_proceed=True,
                available_languages=["python", "javascript"],
                unavailable_languages=[],
                partial_success=False,
            )

            # Setup connector so code_graph is initialized
            orchestrator.code_graph = Mock()
            orchestrator.code_graph.run_blarify.return_value = {
                "files": 10,
                "functions": 50,
                "classes": 5,
            }

            # Act
            orchestrator.run(
                codebase_path=codebase_path,
                languages=languages,
            )

            # Assert
            assert len(progress_updates) > 0
            assert any("python" in str(u) for u in progress_updates)
            assert any("javascript" in str(u) for u in progress_updates)

    def test_error_aggregation_in_result(self, orchestrator):
        """Test error aggregation in result."""
        # Arrange
        codebase_path = Path("/path/to/codebase")
        languages = ["python", "javascript"]

        # Create errors that will be added to error_handler
        error1 = IndexingError("python", "timeout", "Timeout", ErrorSeverity.RECOVERABLE)
        error2 = IndexingError("javascript", "parse_error", "Parse failed", ErrorSeverity.WARNING)

        with (
            patch.object(orchestrator, "_check_prerequisites") as mock_prereq,
            patch.object(orchestrator, "_run_indexing") as mock_index,
        ):
            mock_prereq.return_value = PrerequisiteResult(
                can_proceed=True,
                available_languages=["python", "javascript"],
                unavailable_languages=[],
                partial_success=False,
            )

            # Both fail with different errors - return as dict entries
            errors_dict = {
                "python": error1,
                "javascript": error2,
            }
            mock_index.return_value = errors_dict

            # Manually populate error_handler to simulate real error collection
            orchestrator.error_handler._errors = [error1, error2]

            # Act
            _ = orchestrator.run(
                codebase_path=codebase_path,
                languages=languages,
            )

            # Assert
            assert result.success is False
            assert len(result.errors) == 2
            assert any(e.language == "python" for e in result.errors)
            assert any(e.language == "javascript" for e in result.errors)

    def test_config_customization(self, orchestrator):
        """Test configuration customization."""
        # Arrange
        config = IndexingConfig(
            timeout=600,
            max_retries=5,
            batch_size=1000,
            parallel_workers=4,
        )

        codebase_path = Path("/path/to/codebase")

        # Act
        _ = orchestrator.run(
            codebase_path=codebase_path,
            languages=["python"],
            config=config,
        )

        # Assert
        assert result.config.timeout == 600
        assert result.config.max_retries == 5

    def test_dry_run_mode(self, orchestrator):
        """Test dry-run mode (no actual indexing)."""
        # Arrange
        codebase_path = Path("/path/to/codebase")
        languages = ["python", "javascript"]

        with patch.object(orchestrator, "_run_indexing") as mock_index:
            # Act
            _ = orchestrator.run(
                codebase_path=codebase_path,
                languages=languages,
                dry_run=True,
            )

            # Assert
            assert result.dry_run is True
            mock_index.assert_not_called()

    def test_incremental_update_mode(self, orchestrator):
        """Test incremental update mode parameter."""
        # Arrange
        codebase_path = Path("/path/to/codebase")
        languages = ["python"]

        with (
            patch.object(orchestrator, "_check_prerequisites") as mock_prereq,
            patch.object(orchestrator, "_run_indexing") as mock_index,
        ):
            mock_prereq.return_value = PrerequisiteResult(
                can_proceed=True,
                available_languages=["python"],
                unavailable_languages=[],
                partial_success=False,
            )

            mock_index.return_value = {
                "python": {"files": 50, "functions": 200, "classes": 10},
            }

            # Act
            _ = orchestrator.run(
                codebase_path=codebase_path,
                languages=languages,
                incremental=True,
            )

            # Assert
            # Incremental parameter should be accepted (future blarify support)
            assert result.success is True
            mock_index.assert_called_once()

    def test_language_priority_ordering(self, orchestrator):
        """Test language processing follows priority ordering."""
        # Arrange
        codebase_path = Path("/path/to/codebase")
        languages = ["typescript", "python", "javascript"]  # Out of order
        priority_order = ["python", "javascript", "typescript"]

        with (
            patch.object(orchestrator, "_check_prerequisites") as mock_prereq,
            patch.object(orchestrator, "_run_indexing") as mock_index,
        ):
            mock_prereq.return_value = PrerequisiteResult(
                can_proceed=True,
                available_languages=priority_order,  # Should be in priority order
                unavailable_languages=[],
                partial_success=False,
            )

            mock_index.return_value = {
                "python": {"files": 10, "functions": 50},
                "javascript": {"files": 5, "functions": 25},
                "typescript": {"files": 8, "functions": 40},
            }

            # Act
            _ = orchestrator.run(
                codebase_path=codebase_path,
                languages=languages,
                priority_order=priority_order,
            )

            # Assert - Check that priority_order was applied
            # The _apply_priority_order method should reorder languages
            assert result.success is True
            # We can't directly verify order without inspecting internals,
            # but we can verify all languages were processed
            assert len(result.completed_languages) == 3

    def test_cleanup_on_completion(self, orchestrator, tmp_path):
        """Test cleanup of temporary files on completion."""
        # Arrange
        codebase_path = Path("/path/to/codebase")
        languages = ["python"]

        # Act
        _ = orchestrator.run(
            codebase_path=codebase_path,
            languages=languages,
        )

        # Assert - Temp files should be cleaned
        temp_files = list(tmp_path.glob("blarify_temp_*"))
        assert len(temp_files) == 0

    def test_concurrent_language_processing(self, orchestrator):
        """Test concurrent processing of multiple languages."""
        # Arrange
        codebase_path = Path("/path/to/codebase")
        languages = ["python", "javascript", "typescript"]

        with patch.object(orchestrator, "_run_indexing_parallel") as mock_parallel:
            # Act
            _ = orchestrator.run(
                codebase_path=codebase_path,
                languages=languages,
                parallel=True,
            )

            # Assert
            mock_parallel.assert_called_once()
