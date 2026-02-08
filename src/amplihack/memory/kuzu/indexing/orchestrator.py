"""Orchestrator for Blarify indexing operations.

Coordinates all components for end-to-end indexing workflow.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..code_graph import KuzuCodeGraph
from ..connector import KuzuConnector
from .background_indexer import BackgroundIndexer, IndexingJob
from .error_handler import ErrorAction, ErrorHandler, ErrorSeverity, IndexingError
from .prerequisite_checker import PrerequisiteChecker, PrerequisiteResult
from .progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


@dataclass
class IndexingConfig:
    """Configuration for indexing operations."""

    timeout: int = 300
    max_retries: int = 3
    batch_size: int = 100
    parallel_workers: int = 1


@dataclass
class IndexingResult:
    """Result of an indexing operation."""

    success: bool
    total_files: int
    total_functions: int
    total_classes: int
    total_relationships: int
    completed_languages: list[str]
    failed_languages: list[str]
    skipped_languages: list[str]
    partial_success: bool
    errors: list[IndexingError]
    background_job_id: str | None = None
    is_background: bool = False
    config: IndexingConfig | None = None
    dry_run: bool = False
    output_file: Path | None = None


class Orchestrator:
    """Orchestrate the Blarify indexing workflow."""

    def __init__(self, connector: KuzuConnector | None = None):
        """Initialize orchestrator.

        Args:
            connector: Optional KuzuConnector for real blarify integration.
                      If not provided, orchestrator can still run prerequisites,
                      background jobs, and dry runs.
        """
        self.prerequisite_checker = PrerequisiteChecker()
        self.error_handler = ErrorHandler()
        self.background_indexer = BackgroundIndexer()
        self._progress_callbacks: list[Callable] = []
        self.connector = connector
        self.code_graph = KuzuCodeGraph(connector) if connector else None

    def run(
        self,
        codebase_path: Path,
        languages: list[str],
        background: bool = False,
        config: IndexingConfig | None = None,
        dry_run: bool = False,
        priority_order: list[str] | None = None,
        parallel: bool = False,
        max_retries: int | None = None,
        incremental: bool = False,
    ) -> IndexingResult:
        """Run the indexing workflow.

        Args:
            codebase_path: Path to codebase to index
            languages: Languages to index
            background: Run in background
            config: Optional configuration
            dry_run: Perform dry run without actual indexing
            priority_order: Optional language priority order
            parallel: Process languages in parallel
            max_retries: Override config max_retries
            incremental: Use incremental update mode if blarify supports it

        Returns:
            IndexingResult with operation details
        """
        if config is None:
            config = IndexingConfig()

        # Apply max_retries override
        if max_retries is not None:
            config.max_retries = max_retries

        # Handle dry run
        if dry_run:
            return IndexingResult(
                success=True,
                total_files=0,
                total_functions=0,
                total_classes=0,
                total_relationships=0,
                completed_languages=[],
                failed_languages=[],
                skipped_languages=[],
                partial_success=False,
                errors=[],
                config=config,
                dry_run=True,
            )

        # Check prerequisites
        prereq_result = self._check_prerequisites(languages)

        if not prereq_result.can_proceed:
            return IndexingResult(
                success=False,
                total_files=0,
                total_functions=0,
                total_classes=0,
                total_relationships=0,
                completed_languages=[],
                failed_languages=[],
                skipped_languages=languages,
                partial_success=False,
                errors=[],
                config=config,
            )

        # Handle background execution
        if background:
            # Start background job with available languages (or requested languages if prerequisites weren't checked)
            langs_to_index = (
                prereq_result.available_languages
                if prereq_result.available_languages
                else languages
            )
            job = self._start_background_job(
                codebase_path,
                langs_to_index,
                config,
            )
            job_id = job.job_id

            return IndexingResult(
                success=prereq_result.can_proceed or len(langs_to_index) > 0,
                total_files=0,
                total_functions=0,
                total_classes=0,
                total_relationships=0,
                completed_languages=[],
                failed_languages=[],
                skipped_languages=prereq_result.unavailable_languages,
                partial_success=prereq_result.partial_success,
                errors=[],
                background_job_id=job_id,
                is_background=True,
                config=config,
            )

        # Apply priority ordering
        if priority_order:
            languages = self._apply_priority_order(languages, priority_order)

        # Run indexing
        try:
            if parallel:
                indexing_results = self._run_indexing_parallel(
                    codebase_path,
                    prereq_result.available_languages,
                    config,
                )
            else:
                indexing_results = self._run_indexing(
                    codebase_path,
                    prereq_result.available_languages,
                    config,
                )
        except IndexingError as e:
            # Handle case where indexing raises an error
            self.error_handler.handle_error(e)
            indexing_results = {}

        # Import results
        import_results = self._import_results(indexing_results, codebase_path)

        # Build final result
        completed = []
        failed = []

        for lang in prereq_result.available_languages:
            if lang in indexing_results and not isinstance(indexing_results[lang], IndexingError):
                completed.append(lang)
            else:
                failed.append(lang)

        success = len(completed) > 0
        partial = success and (len(failed) > 0 or len(prereq_result.unavailable_languages) > 0)

        # Set output file path (SCIP index file)
        output_file = codebase_path / "index.scip"

        return IndexingResult(
            success=success,
            total_files=import_results.get("files", 0),
            total_functions=import_results.get("functions", 0),
            total_classes=import_results.get("classes", 0),
            total_relationships=import_results.get("relationships", 0),
            completed_languages=completed,
            failed_languages=failed,
            skipped_languages=prereq_result.unavailable_languages,
            partial_success=partial,
            errors=self.error_handler._errors,
            config=config,
            output_file=output_file,
        )

    def _check_prerequisites(self, languages: list[str]) -> PrerequisiteResult:
        """Check prerequisites for languages."""
        return self.prerequisite_checker.check_all(languages)

    def _start_background_job(
        self,
        codebase_path: Path,
        languages: list[str],
        config: IndexingConfig,
    ) -> IndexingJob:
        """Start background indexing job."""
        return self.background_indexer.start_background_job(
            codebase_path=codebase_path,
            languages=languages,
            timeout=config.timeout,
        )

    def _run_indexing(
        self,
        codebase_path: Path,
        languages: list[str],
        config: IndexingConfig,
    ) -> dict:
        """Run indexing for all languages using real blarify integration.

        Args:
            codebase_path: Path to codebase
            languages: Languages to index
            config: Indexing configuration

        Returns:
            Dictionary of results per language (or IndexingError objects)
        """
        results = {}
        progress_tracker = ProgressTracker(languages)

        for language in languages:
            # Notify progress callbacks
            for callback in self._progress_callbacks:
                callback(f"Starting {language}")

            # Start progress tracking
            progress_tracker.start_language(language, estimated_files=100)

            # Check if codebase path exists
            if not codebase_path.exists():
                error = IndexingError(
                    language=language,
                    error_type="path_error",
                    message=f"Codebase path does not exist: {codebase_path}",
                    severity=ErrorSeverity.RECOVERABLE,
                )
                action = self.error_handler.handle_error(error, max_retries=config.max_retries)
                results[language] = error

                if action.action_type == ErrorAction.ABORT:
                    break
                continue

            # Real blarify integration via KuzuCodeGraph
            if not self.code_graph:
                error = IndexingError(
                    language=language,
                    error_type="config_error",
                    message="No KuzuConnector provided - cannot run blarify",
                    severity=ErrorSeverity.FATAL,
                )
                self.error_handler.handle_error(error, max_retries=config.max_retries)
                results[language] = error
                break

            try:
                # Call real blarify through KuzuCodeGraph
                logger.info("Running blarify for %s on %s", language, codebase_path)
                counts = self.code_graph.run_blarify(
                    codebase_path=str(codebase_path),
                    languages=[language],
                )

                result = {
                    "files": counts.get("files", 0),
                    "functions": counts.get("functions", 0),
                    "classes": counts.get("classes", 0),
                }

                progress_tracker.complete_language(language, final_count=counts.get("files", 0))
                results[language] = result

                # Notify progress
                for callback in self._progress_callbacks:
                    callback(f"Completed {language}")

            except Exception as e:
                # Handle blarify execution errors
                error = IndexingError(
                    language=language,
                    error_type="execution_error",
                    message=f"Blarify execution failed: {e!s}",
                    severity=ErrorSeverity.RECOVERABLE,
                )
                action = self.error_handler.handle_error(error, max_retries=config.max_retries)
                results[language] = error

                if action.action_type == ErrorAction.ABORT:
                    break

        return results

    def _run_indexing_parallel(
        self,
        codebase_path: Path,
        languages: list[str],
        config: IndexingConfig,
    ) -> dict:
        """Run indexing in parallel for multiple languages.

        Args:
            codebase_path: Path to codebase
            languages: Languages to index
            config: Indexing configuration

        Returns:
            Dictionary of results per language
        """
        # For now, delegate to sequential implementation
        # In production, this would use multiprocessing
        return self._run_indexing(codebase_path, languages, config)

    def _import_results(self, indexing_results: dict, codebase_path: Path) -> dict:
        """Import indexing results into database.

        Now actually imports the SCIP index into Kuzu!

        Args:
            indexing_results: Results from indexing (currently unused, kept for compatibility)
            codebase_path: Path to the codebase where index.scip was created

        Returns:
            Import statistics from SCIP index
        """
        # Try to import SCIP index if it exists
        if not self.code_graph or not self.connector:
            # No database connection - return empty stats
            logger.warning("No Kuzu connection - cannot import SCIP index")
            return {
                "files": 0,
                "functions": 0,
                "classes": 0,
                "relationships": 0,
            }

        try:
            from .scip_importer import ScipImporter

            # Check if SCIP index exists in the codebase root
            # The output_file was set in the run() method
            index_path = codebase_path / "index.scip"
            if not index_path.exists():
                logger.warning(f"SCIP index not found at {index_path}")
                return {
                    "files": 0,
                    "functions": 0,
                    "classes": 0,
                    "relationships": 0,
                }

            # Import the SCIP index into Kuzu
            importer = ScipImporter(self.connector)
            stats = importer.import_from_file(
                scip_index_path=str(index_path),
                project_root=str(codebase_path),
                language="python",  # TODO: Make this dynamic based on available_languages
            )

            logger.info(
                "Successfully imported SCIP index: %d files, %d functions, %d classes",
                stats.get("files", 0),
                stats.get("functions", 0),
                stats.get("classes", 0),
            )

            return stats

        except Exception as e:
            logger.error(f"Failed to import SCIP index: {e}")
            import traceback

            traceback.print_exc()
            # Return empty stats on error
            return {
                "files": 0,
                "functions": 0,
                "classes": 0,
                "relationships": 0,
            }

    def _apply_priority_order(
        self,
        languages: list[str],
        priority_order: list[str],
    ) -> list[str]:
        """Apply priority ordering to languages.

        Args:
            languages: Languages to order
            priority_order: Desired order

        Returns:
            Ordered language list
        """
        ordered = []
        remaining = list(languages)

        for lang in priority_order:
            if lang in remaining:
                ordered.append(lang)
                remaining.remove(lang)

        # Add any remaining languages
        ordered.extend(remaining)

        return ordered

    def register_progress_callback(self, callback: Callable) -> None:
        """Register callback for progress updates.

        Args:
            callback: Function to call with progress updates
        """
        self._progress_callbacks.append(callback)

    def check_prerequisites(self, languages: list[str]) -> PrerequisiteResult:
        """Public API to check prerequisites.

        Args:
            languages: Languages to check

        Returns:
            PrerequisiteResult
        """
        return self._check_prerequisites(languages)

    def get_job_status(self, job_id: str):
        """Get status of a background job.

        Args:
            job_id: Job identifier

        Returns:
            Job status
        """
        return self.background_indexer.get_job_status(job_id)
