"""Tests for results persistence and formatting."""
# ggignore

import json
from datetime import datetime
from pathlib import Path
import sys

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import using relative path from project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude"))

from tools.benchmarking.results import ComparisonReport, ResultsManager
from tools.benchmarking.runner import (
    AggregatedTaskResult,
    BenchmarkResults,
)
from tools.benchmarking.docker_manager import TrialResult


@pytest.fixture
def results_dir(tmp_path):
    """Create temporary results directory."""
    return tmp_path / "results"


@pytest.fixture
def manager(results_dir):
    """Create ResultsManager instance."""
    return ResultsManager(results_dir)


@pytest.fixture
def mock_trial_result():
    """Create mock trial result."""
    return TrialResult(
        score=85,
        duration_seconds=120.5,
        timed_out=False,
        test_output="Test passed successfully",
        exit_code=0,
        error_message=None
    )


@pytest.fixture
def mock_aggregated_result(mock_trial_result):
    """Create mock aggregated result."""
    return AggregatedTaskResult(
        mean_score=85.0,
        median_score=85.0,
        std_dev=5.0,
        min_score=80,
        max_score=90,
        num_perfect_trials=0,
        total_trials=3,
        trial_results=[mock_trial_result] * 3
    )


@pytest.fixture
def mock_results(mock_aggregated_result):
    """Create mock benchmark results."""
    return BenchmarkResults(
        agent_task_results={
            ("agent1", "task1"): mock_aggregated_result
        },
        num_agents=1,
        num_tasks=1,
        total_trials=3,
        start_time=datetime(2025, 11, 17, 12, 0, 0),
        end_time=datetime(2025, 11, 17, 12, 10, 0),
        duration_seconds=600.0
    )


class TestResultsManager:
    """Test suite for ResultsManager."""

    def test_save_load_json_roundtrip(self, manager, mock_results, results_dir):
        """Should save results and load them back identically."""
        # Save
        filepath = manager.save(mock_results, format="json")

        # Verify file exists
        assert filepath.exists()
        assert filepath.parent == results_dir

        # Load
        loaded = manager.load(filepath)

        # Assert key fields match
        assert loaded.num_agents == mock_results.num_agents
        assert loaded.num_tasks == mock_results.num_tasks
        assert loaded.total_trials == mock_results.total_trials
        assert loaded.duration_seconds == mock_results.duration_seconds

        # Assert agent_task_results preserved
        assert ("agent1", "task1") in loaded.agent_task_results
        loaded_agg = loaded.agent_task_results[("agent1", "task1")]
        original_agg = mock_results.agent_task_results[("agent1", "task1")]

        assert loaded_agg.mean_score == original_agg.mean_score
        assert loaded_agg.median_score == original_agg.median_score
        assert loaded_agg.std_dev == original_agg.std_dev
        assert loaded_agg.min_score == original_agg.min_score
        assert loaded_agg.max_score == original_agg.max_score
        assert loaded_agg.num_perfect_trials == original_agg.num_perfect_trials
        assert loaded_agg.total_trials == original_agg.total_trials

        # Assert trial results preserved
        assert len(loaded_agg.trial_results) == len(original_agg.trial_results)
        for loaded_trial, original_trial in zip(loaded_agg.trial_results, original_agg.trial_results):
            assert loaded_trial.score == original_trial.score
            assert loaded_trial.duration_seconds == original_trial.duration_seconds
            assert loaded_trial.timed_out == original_trial.timed_out
            assert loaded_trial.exit_code == original_trial.exit_code

    def test_auto_generate_filename(self, manager, mock_results):
        """Should create timestamped filename if none provided."""
        filepath = manager.save(mock_results, format="json", filename=None)

        # Should match pattern: benchmark_YYYYMMDD_HHMMSS.json
        assert filepath.name.startswith("benchmark_")
        assert filepath.name.endswith(".json")
        assert filepath.exists()

        # Verify timestamp format
        name_without_ext = filepath.stem
        timestamp_part = name_without_ext.replace("benchmark_", "")
        # Should be YYYYMMDD_HHMMSS format (15 characters)
        assert len(timestamp_part) == 15
        assert timestamp_part[8] == "_"  # Separator between date and time

    def test_sanitize_secrets(self, manager):
        """Should replace secret values with [REDACTED]."""
        text = "Using API key test-fake-key-api03-secret123 to connect"
        secrets = ["test-fake-key-api03-secret123"]

        sanitized = manager.sanitize_output(text, secrets)

        assert "test-fake-key-api03-secret123" not in sanitized
        assert "[REDACTED]" in sanitized
        assert "Using API key" in sanitized
        assert "to connect" in sanitized

    def test_format_as_markdown(self, manager, mock_results):
        """Should format results as readable Markdown table."""
        markdown = manager.format_as_markdown(mock_results)

        # Check header
        assert "# Benchmark Results" in markdown
        assert "**Run Date**: 2025-11-17 12:00:00" in markdown
        assert "**Duration**: 600.0 seconds" in markdown
        assert "**Agents**: 1" in markdown
        assert "**Tasks**: 1" in markdown
        assert "**Total Trials**: 3" in markdown

        # Check table structure
        assert "| Agent | Task | Mean Score | Median | Std Dev | Min | Max | Perfect Trials | Total Trials |" in markdown
        assert "|-------|------|------------|--------|---------|-----|-----|----------------|--------------|" in markdown

        # Check data row
        assert "| agent1 | task1 | 85.0 | 85 | 5.0 | 80 | 90 | 0 | 3 |" in markdown

        # Check summary
        assert "## Summary" in markdown
        assert "Mean across all: 85.0" in markdown
        assert "Best performance: agent1 on task1 (90)" in markdown
        assert "Worst performance: agent1 on task1 (80)" in markdown

    def test_format_as_csv(self, manager, mock_results):
        """Should format results as valid CSV."""
        csv_text = manager.format_as_csv(mock_results)

        # Normalize line endings for cross-platform compatibility
        lines = csv_text.strip().replace('\r\n', '\n').split('\n')

        # Check header
        assert lines[0] == "agent,task,mean_score,median_score,std_dev,min,max,perfect_trials,total_trials"

        # Check data row
        assert lines[1] == "agent1,task1,85.0,85.0,5.0,80,90,0,3"

    def test_list_results(self, manager, results_dir):
        """Should list all JSON result files in directory."""
        results_dir.mkdir(parents=True, exist_ok=True)

        # Create multiple result files
        (results_dir / "benchmark_20251116_120000.json").write_text("{}")
        (results_dir / "benchmark_20251117_130000.json").write_text("{}")
        (results_dir / "other.txt").write_text("ignored")
        (results_dir / ".gitignore").write_text("*")

        files = manager.list_results(pattern="*.json")

        assert len(files) == 2
        assert all(f.suffix == ".json" for f in files)
        assert all("benchmark_" in f.name for f in files)

        # Should be sorted by modification time (newest first)
        assert files[0].name == "benchmark_20251117_130000.json"
        assert files[1].name == "benchmark_20251116_120000.json"

    def test_compare_results_improvements(self, manager, mock_aggregated_result):
        """Should identify improvements between runs."""
        # Create baseline with lower score
        baseline_agg = AggregatedTaskResult(
            mean_score=70.0,
            median_score=70.0,
            std_dev=5.0,
            min_score=65,
            max_score=75,
            num_perfect_trials=0,
            total_trials=3,
            trial_results=[]
        )
        baseline = BenchmarkResults(
            agent_task_results={("agent1", "task1"): baseline_agg},
            num_agents=1,
            num_tasks=1,
            total_trials=3,
            start_time=datetime(2025, 11, 16, 12, 0, 0),
            end_time=datetime(2025, 11, 16, 12, 10, 0),
            duration_seconds=600.0
        )

        # Current with higher score
        current = BenchmarkResults(
            agent_task_results={("agent1", "task1"): mock_aggregated_result},
            num_agents=1,
            num_tasks=1,
            total_trials=3,
            start_time=datetime(2025, 11, 17, 12, 0, 0),
            end_time=datetime(2025, 11, 17, 12, 10, 0),
            duration_seconds=600.0
        )

        baseline_path = manager.save(baseline, filename="baseline.json")
        current_path = manager.save(current, filename="current.json")

        comparison = manager.compare_results(baseline_path, current_path)

        assert ("agent1", "task1") in comparison.improvements
        assert comparison.improvements[("agent1", "task1")] == 15.0
        assert len(comparison.regressions) == 0
        assert len(comparison.unchanged) == 0
        assert "Improvements: 1" in comparison.summary
        assert "Average improvement: +15.0" in comparison.summary

    def test_compare_results_regressions(self, manager, mock_aggregated_result):
        """Should identify regressions between runs."""
        # Baseline with higher score
        baseline_agg = AggregatedTaskResult(
            mean_score=85.0,
            median_score=85.0,
            std_dev=5.0,
            min_score=80,
            max_score=90,
            num_perfect_trials=0,
            total_trials=3,
            trial_results=[]
        )
        baseline = BenchmarkResults(
            agent_task_results={("agent1", "task1"): baseline_agg},
            num_agents=1,
            num_tasks=1,
            total_trials=3,
            start_time=datetime(2025, 11, 16, 12, 0, 0),
            end_time=datetime(2025, 11, 16, 12, 10, 0),
            duration_seconds=600.0
        )

        # Current with lower score
        current_agg = AggregatedTaskResult(
            mean_score=70.0,
            median_score=70.0,
            std_dev=5.0,
            min_score=65,
            max_score=75,
            num_perfect_trials=0,
            total_trials=3,
            trial_results=[]
        )
        current = BenchmarkResults(
            agent_task_results={("agent1", "task1"): current_agg},
            num_agents=1,
            num_tasks=1,
            total_trials=3,
            start_time=datetime(2025, 11, 17, 12, 0, 0),
            end_time=datetime(2025, 11, 17, 12, 10, 0),
            duration_seconds=600.0
        )

        baseline_path = manager.save(baseline, filename="baseline.json")
        current_path = manager.save(current, filename="current.json")

        comparison = manager.compare_results(baseline_path, current_path)

        assert ("agent1", "task1") in comparison.regressions
        assert comparison.regressions[("agent1", "task1")] == -15.0
        assert len(comparison.improvements) == 0
        assert len(comparison.unchanged) == 0
        assert "Regressions: 1" in comparison.summary
        assert "Average regression: -15.0" in comparison.summary

    def test_compare_results_missing_combinations(self, manager, mock_aggregated_result):
        """Should handle when current run has different agent/task combos."""
        baseline = BenchmarkResults(
            agent_task_results={("agent1", "task1"): mock_aggregated_result},
            num_agents=1,
            num_tasks=1,
            total_trials=3,
            start_time=datetime(2025, 11, 16, 12, 0, 0),
            end_time=datetime(2025, 11, 16, 12, 10, 0),
            duration_seconds=600.0
        )

        # Different agent/task combination
        current = BenchmarkResults(
            agent_task_results={("agent2", "task2"): mock_aggregated_result},
            num_agents=1,
            num_tasks=1,
            total_trials=3,
            start_time=datetime(2025, 11, 17, 12, 0, 0),
            end_time=datetime(2025, 11, 17, 12, 10, 0),
            duration_seconds=600.0
        )

        baseline_path = manager.save(baseline, filename="baseline.json")
        current_path = manager.save(current, filename="current.json")

        comparison = manager.compare_results(baseline_path, current_path)

        assert len(comparison.improvements) == 0
        assert len(comparison.regressions) == 0
        assert len(comparison.unchanged) == 0
        assert "incompatible" in comparison.summary.lower()
        assert "No common agent-task combinations" in comparison.summary

    def test_sanitize_multiple_secrets(self, manager):
        """Should handle multiple different secrets in same text."""
        text = "API keys: test-fake-key-123 and test-fake-key-openai-456 and ghp_github_789"
        secrets = ["test-fake-key-123", "test-fake-key-openai-456", "ghp_github_789"]

        sanitized = manager.sanitize_output(text, secrets)

        assert "test-fake-key-123" not in sanitized
        assert "test-fake-key-openai-456" not in sanitized
        assert "ghp_github_789" not in sanitized
        assert sanitized.count("[REDACTED]") == 3
        assert "API keys:" in sanitized
        assert "and" in sanitized

    def test_save_unsupported_format(self, manager, mock_results):
        """Should raise ValueError for unsupported format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            manager.save(mock_results, format="xml")

    def test_save_invalid_filename(self, manager, mock_results):
        """Should raise ValueError for path traversal in filename."""
        with pytest.raises(ValueError, match="Invalid filename"):
            manager.save(mock_results, filename="../etc/passwd")

        with pytest.raises(ValueError, match="Invalid filename"):
            manager.save(mock_results, filename="subdir/file.json")

    def test_load_nonexistent_file(self, manager):
        """Should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            manager.load(Path("/nonexistent/file.json"))

    def test_save_markdown(self, manager, mock_results):
        """Should save results in Markdown format."""
        filepath = manager.save(mock_results, format="markdown", filename="test.md")

        assert filepath.suffix == ".md"
        content = filepath.read_text()
        assert "# Benchmark Results" in content
        assert "| agent1 | task1" in content

    def test_save_csv(self, manager, mock_results):
        """Should save results in CSV format."""
        filepath = manager.save(mock_results, format="csv", filename="test.csv")

        assert filepath.suffix == ".csv"
        content = filepath.read_text()
        assert "agent,task,mean_score" in content
        assert "agent1,task1,85.0" in content

    def test_gitignore_created(self, results_dir):
        """Should create .gitignore in results directory."""
        manager = ResultsManager(results_dir)

        gitignore_path = results_dir / ".gitignore"
        assert gitignore_path.exists()
        content = gitignore_path.read_text()
        assert "# Ignore benchmark results" in content
        assert "*" in content

    def test_comparison_report_to_markdown(self):
        """Should format comparison report as Markdown."""
        report = ComparisonReport(
            baseline_name="baseline.json",
            current_name="current.json",
            improvements={("agent1", "task1"): 15.0},
            regressions={("agent2", "task2"): -10.0},
            unchanged={("agent3", "task3"): 85.0},
            summary="Test comparison"
        )

        markdown = report.to_markdown()

        assert "# Benchmark Comparison" in markdown
        assert "**Baseline**: baseline.json" in markdown
        assert "**Current**: current.json" in markdown
        assert "Test comparison" in markdown
        assert "## Improvements (1)" in markdown
        assert "| agent1 | task1 | +15.0 |" in markdown
        assert "## Regressions (1)" in markdown
        assert "| agent2 | task2 | -10.0 |" in markdown
        assert "## Unchanged (1)" in markdown
        assert "| agent3 | task3 | 85.0 |" in markdown
