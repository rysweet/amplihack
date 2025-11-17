"""Results persistence and formatting for benchmark results."""

import csv
import json
import logging
import re
import tempfile
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .runner import BenchmarkResults, AggregatedTaskResult, TrialResult

logger = logging.getLogger(__name__)


@dataclass
class ComparisonReport:
    """Comparison between two benchmark runs."""
    baseline_name: str
    current_name: str
    improvements: Dict[Tuple[str, str], float]  # (agent, task) -> delta
    regressions: Dict[Tuple[str, str], float]
    unchanged: Dict[Tuple[str, str], float]
    summary: str

    def to_markdown(self) -> str:
        """Format comparison as Markdown."""
        lines = [
            f"# Benchmark Comparison",
            f"",
            f"**Baseline**: {self.baseline_name}",
            f"**Current**: {self.current_name}",
            f"",
            f"## Summary",
            f"",
            self.summary,
            f"",
        ]

        if self.improvements:
            lines.extend([
                f"## Improvements ({len(self.improvements)})",
                f"",
                f"| Agent | Task | Delta |",
                f"|-------|------|-------|",
            ])
            for (agent, task), delta in sorted(self.improvements.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"| {agent} | {task} | +{delta:.1f} |")
            lines.append("")

        if self.regressions:
            lines.extend([
                f"## Regressions ({len(self.regressions)})",
                f"",
                f"| Agent | Task | Delta |",
                f"|-------|------|-------|",
            ])
            for (agent, task), delta in sorted(self.regressions.items(), key=lambda x: x[1]):
                lines.append(f"| {agent} | {task} | {delta:.1f} |")
            lines.append("")

        if self.unchanged:
            lines.extend([
                f"## Unchanged ({len(self.unchanged)})",
                f"",
                f"| Agent | Task | Score |",
                f"|-------|------|-------|",
            ])
            for (agent, task), score in sorted(self.unchanged.items()):
                lines.append(f"| {agent} | {task} | {score:.1f} |")
            lines.append("")

        return "\n".join(lines)


class ResultsManager:
    """Manage benchmark results persistence and formatting."""

    def __init__(self, results_dir: Path):
        """
        Initialize results manager.

        Args:
            results_dir: Directory to store results files
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Create .gitignore if it doesn't exist
        gitignore_path = self.results_dir / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text("# Ignore benchmark results\n*\n")

    def save(
        self,
        results: BenchmarkResults,
        format: str = "json",
        filename: Optional[str] = None
    ) -> Path:
        """
        Save benchmark results to file.

        Args:
            results: BenchmarkResults to save
            format: Output format ("json", "markdown", "csv")
            filename: Output filename (auto-generated if None)

        Returns:
            Path: Path to saved file

        Raises:
            ValueError: If format unsupported
            IOError: If write fails
        """
        if format not in ["json", "markdown", "csv"]:
            raise ValueError(f"Unsupported format: {format}. Must be one of: json, markdown, csv")

        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_{timestamp}.{format}"

        # Validate filename doesn't contain path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            raise ValueError(f"Invalid filename: {filename}")

        filepath = self.results_dir / filename

        # Format content based on format type
        if format == "json":
            content = self._to_json(results)
        elif format == "markdown":
            content = self.format_as_markdown(results)
        elif format == "csv":
            content = self.format_as_csv(results)

        # Write atomically (write to temp, then rename)
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                dir=self.results_dir,
                delete=False,
                suffix=f".tmp.{format}"
            ) as tmp_file:
                tmp_file.write(content)
                tmp_path = Path(tmp_file.name)

            # Atomic rename
            tmp_path.rename(filepath)
            logger.info(f"Saved results to {filepath}")
            return filepath

        except Exception as e:
            # Clean up temp file on error
            if 'tmp_path' in locals() and tmp_path.exists():
                tmp_path.unlink()
            raise IOError(f"Failed to save results: {e}")

    def load(self, filepath: Path) -> BenchmarkResults:
        """
        Load benchmark results from JSON file.

        Args:
            filepath: Path to results JSON file

        Returns:
            BenchmarkResults: Loaded results

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If JSON invalid
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Results file not found: {filepath}")

        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            # Reconstruct agent_task_results
            agent_task_results = {}
            for key, agg_data in data["agent_task_results"].items():
                # Key format is "agent__task"
                agent, task = key.split("__", 1)

                # Reconstruct trial results
                trial_results = []
                for trial_data in agg_data.get("trial_results", []):
                    trial = TrialResult(
                        score=trial_data["score"],
                        duration_seconds=trial_data["duration_seconds"],
                        timed_out=trial_data["timed_out"],
                        test_output=trial_data["test_output"],
                        exit_code=trial_data["exit_code"],
                        error_message=trial_data.get("error_message")
                    )
                    trial_results.append(trial)

                # Reconstruct aggregated result
                agg_result = AggregatedTaskResult(
                    mean_score=agg_data["mean_score"],
                    median_score=agg_data["median_score"],
                    std_dev=agg_data["std_dev"],
                    min_score=agg_data["min_score"],
                    max_score=agg_data["max_score"],
                    num_perfect_trials=agg_data["num_perfect_trials"],
                    total_trials=agg_data["total_trials"],
                    trial_results=trial_results
                )
                agent_task_results[(agent, task)] = agg_result

            # Reconstruct BenchmarkResults
            results = BenchmarkResults(
                agent_task_results=agent_task_results,
                num_agents=data["num_agents"],
                num_tasks=data["num_tasks"],
                total_trials=data["total_trials"],
                start_time=datetime.fromisoformat(data["start_time"]),
                end_time=datetime.fromisoformat(data["end_time"]),
                duration_seconds=data["duration_seconds"]
            )

            logger.info(f"Loaded results from {filepath}")
            return results

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in results file: {e}")
        except KeyError as e:
            raise ValueError(f"Missing required field in results file: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load results: {e}")

    def sanitize_output(self, text: str, secrets: List[str]) -> str:
        """
        Remove secrets from text output before saving.

        Args:
            text: Text to sanitize
            secrets: List of secret values to redact

        Returns:
            str: Sanitized text with secrets replaced by [REDACTED]
        """
        sanitized = text
        for secret in secrets:
            if secret:  # Skip empty strings
                # Escape regex special characters
                escaped_secret = re.escape(secret)
                # Replace all occurrences
                sanitized = re.sub(escaped_secret, "[REDACTED]", sanitized)
        return sanitized

    def format_as_markdown(self, results: BenchmarkResults) -> str:
        """
        Format results as Markdown table.

        Args:
            results: BenchmarkResults to format

        Returns:
            str: Markdown-formatted results
        """
        lines = [
            "# Benchmark Results",
            "",
            f"**Run Date**: {results.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Duration**: {results.duration_seconds:.1f} seconds",
            f"**Agents**: {results.num_agents}",
            f"**Tasks**: {results.num_tasks}",
            f"**Total Trials**: {results.total_trials}",
            "",
            "## Results Matrix",
            "",
            "| Agent | Task | Mean Score | Median | Std Dev | Min | Max | Perfect Trials | Total Trials |",
            "|-------|------|------------|--------|---------|-----|-----|----------------|--------------|",
        ]

        # Sort by agent name, then task name
        for (agent, task), agg in sorted(results.agent_task_results.items()):
            lines.append(
                f"| {agent} | {task} | {agg.mean_score:.1f} | {agg.median_score:.0f} | "
                f"{agg.std_dev:.1f} | {agg.min_score} | {agg.max_score} | "
                f"{agg.num_perfect_trials} | {agg.total_trials} |"
            )

        # Add summary statistics
        if results.agent_task_results:
            all_means = [agg.mean_score for agg in results.agent_task_results.values()]
            overall_mean = sum(all_means) / len(all_means)

            best_result = max(results.agent_task_results.items(), key=lambda x: x[1].max_score)
            worst_result = min(results.agent_task_results.items(), key=lambda x: x[1].min_score)

            lines.extend([
                "",
                "## Summary",
                "",
                f"- Mean across all: {overall_mean:.1f}",
                f"- Best performance: {best_result[0][0]} on {best_result[0][1]} ({best_result[1].max_score})",
                f"- Worst performance: {worst_result[0][0]} on {worst_result[0][1]} ({worst_result[1].min_score})",
            ])

        return "\n".join(lines)

    def format_as_csv(self, results: BenchmarkResults) -> str:
        """
        Format results as CSV.

        Args:
            results: BenchmarkResults to format

        Returns:
            str: CSV-formatted results
        """
        import io
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            "agent", "task", "mean_score", "median_score", "std_dev",
            "min", "max", "perfect_trials", "total_trials"
        ])

        # Write data rows
        for (agent, task), agg in sorted(results.agent_task_results.items()):
            writer.writerow([
                agent, task, agg.mean_score, agg.median_score, agg.std_dev,
                agg.min_score, agg.max_score, agg.num_perfect_trials, agg.total_trials
            ])

        return output.getvalue()

    def list_results(self, pattern: str = "*.json") -> List[Path]:
        """
        List all result files in results directory.

        Args:
            pattern: Glob pattern to filter files

        Returns:
            list: Sorted list of matching result files
        """
        files = list(self.results_dir.glob(pattern))
        # Filter out .gitignore and temp files
        files = [f for f in files if not f.name.startswith('.') and '.tmp.' not in f.name]
        # Sort by modification time (newest first)
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return files

    def compare_results(
        self,
        baseline_path: Path,
        current_path: Path
    ) -> ComparisonReport:
        """
        Compare two benchmark result files.

        Args:
            baseline_path: Path to baseline results
            current_path: Path to current results

        Returns:
            ComparisonReport: Statistical comparison

        Raises:
            ValueError: If results incompatible
        """
        baseline = self.load(baseline_path)
        current = self.load(current_path)

        improvements = {}
        regressions = {}
        unchanged = {}

        # Find common agent-task pairs
        baseline_keys = set(baseline.agent_task_results.keys())
        current_keys = set(current.agent_task_results.keys())
        common_keys = baseline_keys & current_keys

        if not common_keys:
            summary = f"Incompatible results: No common agent-task combinations found. " \
                     f"Baseline has {len(baseline_keys)} combinations, current has {len(current_keys)}."
            return ComparisonReport(
                baseline_name=baseline_path.name,
                current_name=current_path.name,
                improvements={},
                regressions={},
                unchanged={},
                summary=summary
            )

        # Compare common keys
        for key in common_keys:
            baseline_mean = baseline.agent_task_results[key].mean_score
            current_mean = current.agent_task_results[key].mean_score
            delta = current_mean - baseline_mean

            if delta > 0:
                improvements[key] = delta
            elif delta < 0:
                regressions[key] = delta
            else:
                unchanged[key] = current_mean

        # Generate summary
        total = len(common_keys)
        summary_parts = [
            f"Compared {total} agent-task combinations.",
            f"Improvements: {len(improvements)}",
            f"Regressions: {len(regressions)}",
            f"Unchanged: {len(unchanged)}",
        ]

        if improvements:
            avg_improvement = sum(improvements.values()) / len(improvements)
            summary_parts.append(f"Average improvement: +{avg_improvement:.1f}")

        if regressions:
            avg_regression = sum(regressions.values()) / len(regressions)
            summary_parts.append(f"Average regression: {avg_regression:.1f}")

        summary = " | ".join(summary_parts)

        return ComparisonReport(
            baseline_name=baseline_path.name,
            current_name=current_path.name,
            improvements=improvements,
            regressions=regressions,
            unchanged=unchanged,
            summary=summary
        )

    def _to_json(self, results: BenchmarkResults) -> str:
        """Convert BenchmarkResults to JSON string."""
        # Convert to serializable dict
        data = {
            "agent_task_results": {},
            "num_agents": results.num_agents,
            "num_tasks": results.num_tasks,
            "total_trials": results.total_trials,
            "start_time": results.start_time.isoformat(),
            "end_time": results.end_time.isoformat(),
            "duration_seconds": results.duration_seconds,
        }

        # Convert agent_task_results
        for (agent, task), agg in results.agent_task_results.items():
            # Use "__" as separator to allow reconstruction
            key = f"{agent}__{task}"

            # Convert trial results
            trial_results = []
            for trial in agg.trial_results:
                trial_dict = {
                    "score": trial.score,
                    "duration_seconds": trial.duration_seconds,
                    "timed_out": trial.timed_out,
                    "test_output": trial.test_output,
                    "exit_code": trial.exit_code,
                    "error_message": trial.error_message,
                }
                trial_results.append(trial_dict)

            # Convert aggregated result
            data["agent_task_results"][key] = {
                "mean_score": agg.mean_score,
                "median_score": agg.median_score,
                "std_dev": agg.std_dev,
                "min_score": agg.min_score,
                "max_score": agg.max_score,
                "num_perfect_trials": agg.num_perfect_trials,
                "total_trials": agg.total_trials,
                "trial_results": trial_results,
            }

        return json.dumps(data, indent=2)
