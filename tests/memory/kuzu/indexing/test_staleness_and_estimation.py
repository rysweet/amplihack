#!/usr/bin/env python3
"""TDD tests for blarify indexing staleness detection and time estimation.

Tests are written BEFORE implementation to define the contract.
Following SIMPLIFIED TDD approach: critical path only, fast execution (<5s).
"""

import time
from pathlib import Path

import pytest

# Import actual implementations and types
from src.amplihack.memory.kuzu.indexing.staleness_detector import (
    check_index_status,
)
from src.amplihack.memory.kuzu.indexing.time_estimator import (
    estimate_time,
)


# Test fixtures
@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Create temporary project directory with file structure."""
    project = tmp_path / "test_project"
    project.mkdir()

    # Create sample source files
    (project / "src").mkdir()
    (project / "src" / "main.py").write_text("def main():\n    pass\n")
    (project / "src" / "utils.py").write_text("def helper():\n    pass\n")

    return project


@pytest.fixture
def project_with_index(temp_project: Path) -> Path:
    """Create project with existing blarify index."""
    index_dir = temp_project / ".amplihack"
    index_dir.mkdir(exist_ok=True)

    # Create fake index.scip file
    index_file = index_dir / "index.scip"
    index_file.write_text("fake scip index content")

    # Set mtime (fresh index)
    index_file.touch()
    # Note: Implementation will check actual mtime vs source files

    return temp_project


@pytest.fixture
def project_with_stale_index(temp_project: Path) -> Path:
    """Create project with stale index (older than source files)."""
    index_dir = temp_project / ".amplihack"
    index_dir.mkdir(exist_ok=True)

    index_file = index_dir / "index.scip"
    index_file.write_text("old scip index content")

    # Make source files newer than index
    time.sleep(0.01)  # Ensure different mtime
    for src_file in (temp_project / "src").glob("*.py"):
        src_file.touch()

    return temp_project


@pytest.fixture
def multi_language_project(tmp_path: Path) -> Path:
    """Create project with multiple languages."""
    project = tmp_path / "multi_lang_project"
    project.mkdir()

    # Python files
    (project / "src").mkdir()
    for i in range(10):
        (project / "src" / f"module{i}.py").write_text(f"# Python file {i}\n")

    # TypeScript files
    (project / "src" / "ts").mkdir()
    for i in range(20):
        (project / "src" / "ts" / f"component{i}.ts").write_text(f"// TS file {i}\n")

    # JavaScript files
    (project / "src" / "js").mkdir()
    for i in range(15):
        (project / "src" / "js" / f"script{i}.js").write_text(f"// JS file {i}\n")

    return project


# Tests for check_index_status()
class TestCheckIndexStatus:
    """Tests for staleness detection (TDD - write tests first)."""

    def test_no_index_needs_indexing(self, temp_project: Path):
        """When .amplihack/index.scip doesn't exist, needs indexing."""
        status = check_index_status(temp_project)

        assert status.needs_indexing is True
        assert "missing" in status.reason.lower() or "no index" in status.reason.lower()
        assert status.estimated_files > 0  # Should find source files
        assert status.last_indexed is None

    def test_fresh_index_no_indexing_needed(self, project_with_index: Path):
        """When index is fresh (< 24 hours, source unchanged), no indexing needed."""
        status = check_index_status(project_with_index)

        assert status.needs_indexing is False
        assert "up-to-date" in status.reason.lower() or "current" in status.reason.lower()
        assert status.last_indexed is not None

    def test_stale_index_needs_indexing(self, project_with_stale_index: Path):
        """When source files modified after index, needs indexing."""
        status = check_index_status(project_with_stale_index)

        assert status.needs_indexing is True
        assert "stale" in status.reason.lower() or "modified" in status.reason.lower()
        assert status.estimated_files > 0
        assert status.last_indexed is not None

    def test_empty_project_no_indexing_needed(self, tmp_path: Path):
        """Empty project (no source files) doesn't need indexing."""
        empty_project = tmp_path / "empty"
        empty_project.mkdir()

        status = check_index_status(empty_project)

        assert status.needs_indexing is False
        assert status.estimated_files == 0
        assert "no files" in status.reason.lower() or "empty" in status.reason.lower()

    def test_counts_source_files_correctly(self, temp_project: Path):
        """Estimated files should match actual source file count."""
        # temp_project has 2 Python files in src/
        status = check_index_status(temp_project)

        assert status.estimated_files == 2

    def test_ignores_hidden_directories(self, temp_project: Path):
        """Should not count files in .git, .venv, __pycache__, etc."""
        # Add files in directories that should be ignored
        (temp_project / ".git").mkdir()
        (temp_project / ".git" / "config").write_text("fake git config")

        (temp_project / "__pycache__").mkdir()
        (temp_project / "__pycache__" / "cache.pyc").write_text("fake cache")

        status = check_index_status(temp_project)

        # Should still be 2 (only src/*.py files)
        assert status.estimated_files == 2


# Tests for estimate_time()
class TestEstimateTime:
    """Tests for time estimation (TDD - write tests first)."""

    def test_small_python_project_estimate(self, temp_project: Path):
        """Small Python project should estimate based on INDEXING_RATES."""
        # temp_project has 2 Python files
        estimate = estimate_time(temp_project, languages=["python"])

        assert estimate.total_seconds > 0
        assert estimate.total_seconds < 60  # Should be fast for 2 files
        assert "python" in estimate.by_language
        assert estimate.file_counts["python"] == 2

    def test_multi_language_estimate(self, multi_language_project: Path):
        """Multi-language project estimates each language separately."""
        # Project has 10 Python, 20 TypeScript, 15 JavaScript files
        estimate = estimate_time(
            multi_language_project, languages=["python", "typescript", "javascript"]
        )

        assert estimate.total_seconds > 0

        # Should have estimates for each language
        assert "python" in estimate.by_language
        assert "typescript" in estimate.by_language
        assert "javascript" in estimate.by_language

        # File counts should match
        assert estimate.file_counts["python"] == 10
        assert estimate.file_counts["typescript"] == 20
        assert estimate.file_counts["javascript"] == 15

        # Total should equal sum of language estimates
        language_sum = sum(estimate.by_language.values())
        assert abs(estimate.total_seconds - language_sum) < 0.1

    def test_empty_project_zero_estimate(self, tmp_path: Path):
        """Empty project should have zero time estimate."""
        empty = tmp_path / "empty"
        empty.mkdir()

        estimate = estimate_time(empty, languages=["python"])

        assert estimate.total_seconds == 0
        assert estimate.file_counts.get("python", 0) == 0

    def test_estimate_respects_language_rates(self, multi_language_project: Path):
        """Different languages should have different rates per file.

        From docs:
        - Average indexing speed: 300-600 files per minute with SCIP
        - This means roughly 0.1-0.2 seconds per file
        - Rates vary by language complexity
        """
        estimate = estimate_time(
            multi_language_project, languages=["python", "typescript", "javascript"]
        )

        # Calculate per-file rates
        py_rate = estimate.by_language["python"] / estimate.file_counts["python"]
        ts_rate = estimate.by_language["typescript"] / estimate.file_counts["typescript"]
        js_rate = estimate.by_language["javascript"] / estimate.file_counts["javascript"]

        # All rates should be in reasonable range (0.05-0.5 seconds per file)
        assert 0.05 <= py_rate <= 0.5
        assert 0.05 <= ts_rate <= 0.5
        assert 0.05 <= js_rate <= 0.5

        # Rates can differ (TypeScript typically slower than JavaScript)
        # Just verify they're not all identical
        assert not (py_rate == ts_rate == js_rate)

    def test_large_project_scales_linearly(self, tmp_path: Path):
        """Time estimate should scale linearly with file count."""
        small_project = tmp_path / "small"
        small_project.mkdir()
        for i in range(10):
            (small_project / f"file{i}.py").write_text("# Small\n")

        large_project = tmp_path / "large"
        large_project.mkdir()
        for i in range(100):
            (large_project / f"file{i}.py").write_text("# Large\n")

        small_estimate = estimate_time(small_project, languages=["python"])
        large_estimate = estimate_time(large_project, languages=["python"])

        # Large project should take roughly 10x longer (100 files vs 10 files)
        ratio = large_estimate.total_seconds / small_estimate.total_seconds
        assert 8 <= ratio <= 12  # Allow some variance

    def test_handles_mixed_extensions_for_language(self, tmp_path: Path):
        """Should recognize multiple file extensions for same language."""
        project = tmp_path / "mixed"
        project.mkdir()

        # TypeScript can be .ts or .tsx
        (project / "component.ts").write_text("// TS\n")
        (project / "app.tsx").write_text("// TSX\n")

        # JavaScript can be .js or .jsx
        (project / "script.js").write_text("// JS\n")
        (project / "ui.jsx").write_text("// JSX\n")

        estimate = estimate_time(project, languages=["typescript", "javascript"])

        # Should count both extensions for each language
        assert estimate.file_counts["typescript"] == 2  # .ts + .tsx
        assert estimate.file_counts["javascript"] == 2  # .js + .jsx


# Integration test (still fast, but tests both functions together)
class TestStalenessAndEstimationIntegration:
    """Integration tests combining staleness detection and estimation."""

    def test_workflow_new_project(self, temp_project: Path):
        """Full workflow: check status, then estimate time if needed."""
        # Step 1: Check if indexing needed
        status = check_index_status(temp_project)
        assert status.needs_indexing is True

        # Step 2: If needed, estimate time
        if status.needs_indexing:
            estimate = estimate_time(temp_project, languages=["python"])
            assert estimate.total_seconds > 0
            assert estimate.file_counts["python"] == status.estimated_files

    def test_workflow_indexed_project(self, project_with_index: Path):
        """Workflow for already-indexed project: no estimation needed."""
        status = check_index_status(project_with_index)

        if not status.needs_indexing:
            # No need to estimate - index is current
            pass
        else:
            # If somehow needed, estimate would be called
            estimate = estimate_time(project_with_index, languages=["python"])
            assert estimate is not None


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "--tb=short"])
