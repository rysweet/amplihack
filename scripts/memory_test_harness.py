#!/usr/bin/env python3
"""Memory System A/B Test Harness

Automated testing framework for comparing memory system effectiveness:
- Control (no memory)
- SQLite memory
- Neo4j memory

Usage:
    # Run full test suite
    python scripts/memory_test_harness.py --full

    # Run specific phase
    python scripts/memory_test_harness.py --phase baseline
    python scripts/memory_test_harness.py --phase sqlite
    python scripts/memory_test_harness.py --phase neo4j

    # Run specific scenarios
    python scripts/memory_test_harness.py --scenarios 1,2,3

    # Analyze existing results
    python scripts/memory_test_harness.py --analyze

Design: docs/memory/EFFECTIVENESS_TEST_DESIGN.md
"""

import argparse
import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.power import tt_ind_solve_power


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class TimeMetrics:
    """Time-based metrics for test run."""

    execution_time: float  # Total task execution time (seconds)
    time_to_first_action: float  # Time until agent takes first action
    decision_time: float  # Time spent in decision-making
    implementation_time: float  # Time spent writing code


@dataclass
class QualityMetrics:
    """Quality metrics for test run."""

    test_pass_rate: float  # Percentage of tests passing (0-1)
    code_complexity: int  # Cyclomatic complexity
    error_count: int  # Number of errors during execution
    revision_cycles: int  # Number of code revision iterations
    pylint_score: float  # Automated code quality score (0-10)


@dataclass
class MemoryMetrics:
    """Memory usage metrics for test run."""

    memory_retrievals: int  # Number of memory queries
    memory_hits: int  # Number of relevant memories found
    memory_applied: int  # Number of memories actually used
    retrieval_time: float  # Time spent retrieving memories (ms)


@dataclass
class OutputMetrics:
    """Output metrics for test run."""

    lines_of_code: int  # LOC generated
    files_modified: int  # Number of files changed
    test_coverage: float  # Test coverage percentage (0-100)
    documentation_completeness: float  # Doc completeness score (0-1)


@dataclass
class TestRun:
    """Complete metrics for a single test run."""

    scenario_id: str
    config: str  # "control", "sqlite", "neo4j"
    iteration: int
    timestamp: str
    time: TimeMetrics
    quality: QualityMetrics
    memory: MemoryMetrics
    output: OutputMetrics
    error_occurred: bool = False
    error_message: Optional[str] = None


@dataclass
class Scenario:
    """Test scenario definition."""

    id: str
    name: str
    type: str  # learning_from_repetition, pattern_transfer, etc.
    expected_benefit: str  # high, medium, low
    description: str
    task: str
    success_criteria: List[str]
    metrics: List[str]


# ============================================================================
# Metrics Collection
# ============================================================================


class MetricsCollector:
    """Collect metrics during test execution."""

    def __init__(self, scenario_id: str, config: str, iteration: int):
        self.scenario_id = scenario_id
        self.config = config
        self.iteration = iteration
        self.start_time = None
        self.time_metrics = {}
        self.quality_metrics = {}
        self.memory_metrics = {}
        self.output_metrics = {}
        self.error_occurred = False
        self.error_message = None

    def start_collection(self):
        """Begin metric collection for a test run."""
        self.start_time = time.time()

    def record_time_metric(self, name: str, value: float):
        """Record a time-based metric."""
        self.time_metrics[name] = value

    def record_quality_metric(self, name: str, value: float):
        """Record a quality metric."""
        self.quality_metrics[name] = value

    def record_memory_metric(self, name: str, value: float):
        """Record a memory usage metric."""
        self.memory_metrics[name] = value

    def record_output_metric(self, name: str, value: float):
        """Record an output metric."""
        self.output_metrics[name] = value

    def record_error(self, error_message: str):
        """Record an error during test run."""
        self.error_occurred = True
        self.error_message = error_message

    def finalize(self) -> TestRun:
        """Finalize and return collected metrics."""
        execution_time = time.time() - self.start_time

        # Create metrics objects with defaults
        time_obj = TimeMetrics(
            execution_time=execution_time,
            time_to_first_action=self.time_metrics.get("time_to_first_action", 0.0),
            decision_time=self.time_metrics.get("decision_time", 0.0),
            implementation_time=self.time_metrics.get("implementation_time", 0.0),
        )

        quality_obj = QualityMetrics(
            test_pass_rate=self.quality_metrics.get("test_pass_rate", 0.0),
            code_complexity=self.quality_metrics.get("code_complexity", 0),
            error_count=self.quality_metrics.get("error_count", 0),
            revision_cycles=self.quality_metrics.get("revision_cycles", 0),
            pylint_score=self.quality_metrics.get("pylint_score", 0.0),
        )

        memory_obj = MemoryMetrics(
            memory_retrievals=self.memory_metrics.get("memory_retrievals", 0),
            memory_hits=self.memory_metrics.get("memory_hits", 0),
            memory_applied=self.memory_metrics.get("memory_applied", 0),
            retrieval_time=self.memory_metrics.get("retrieval_time", 0.0),
        )

        output_obj = OutputMetrics(
            lines_of_code=self.output_metrics.get("lines_of_code", 0),
            files_modified=self.output_metrics.get("files_modified", 0),
            test_coverage=self.output_metrics.get("test_coverage", 0.0),
            documentation_completeness=self.output_metrics.get("documentation_completeness", 0.0),
        )

        return TestRun(
            scenario_id=self.scenario_id,
            config=self.config,
            iteration=self.iteration,
            timestamp=datetime.now().isoformat(),
            time=time_obj,
            quality=quality_obj,
            memory=memory_obj,
            output=output_obj,
            error_occurred=self.error_occurred,
            error_message=self.error_message,
        )


# ============================================================================
# Statistical Analysis
# ============================================================================


class StatisticalAnalyzer:
    """Perform statistical analysis on test results."""

    @staticmethod
    def compare_configurations(
        baseline_values: List[float], treatment_values: List[float]
    ) -> Dict[str, Any]:
        """Compare two configurations using paired t-test.

        Args:
            baseline_values: Metric values from baseline configuration
            treatment_values: Metric values from treatment configuration

        Returns:
            Dictionary with statistical test results
        """
        # Paired t-test (same scenarios, different conditions)
        t_statistic, p_value = stats.ttest_rel(baseline_values, treatment_values)

        # Calculate effect size (Cohen's d for paired data)
        diff = np.array(treatment_values) - np.array(baseline_values)
        effect_size = np.mean(diff) / np.std(diff) if np.std(diff) > 0 else 0.0

        # Calculate confidence interval
        conf_interval = stats.t.interval(
            0.95, len(diff) - 1, loc=np.mean(diff), scale=stats.sem(diff)
        )

        # Calculate percentage improvement
        mean_baseline = np.mean(baseline_values)
        mean_treatment = np.mean(treatment_values)
        pct_improvement = ((mean_treatment - mean_baseline) / mean_baseline) * 100

        return {
            "t_statistic": float(t_statistic),
            "p_value": float(p_value),
            "effect_size": float(effect_size),
            "mean_baseline": float(mean_baseline),
            "mean_treatment": float(mean_treatment),
            "mean_diff": float(np.mean(diff)),
            "pct_improvement": float(pct_improvement),
            "conf_interval_95": [float(conf_interval[0]), float(conf_interval[1])],
            "significant": p_value < 0.05,
        }

    @staticmethod
    def analyze_multiple_metrics(
        baseline_data: List[TestRun], treatment_data: List[TestRun], metrics: List[str]
    ) -> Dict[str, Any]:
        """Analyze multiple metrics with Bonferroni correction.

        Args:
            baseline_data: Test runs from baseline
            treatment_data: Test runs from treatment
            metrics: List of metric names to analyze

        Returns:
            Dictionary with results for each metric
        """
        results = {}
        p_values = []

        for metric in metrics:
            baseline_values = [StatisticalAnalyzer._extract_metric(run, metric) for run in baseline_data]
            treatment_values = [StatisticalAnalyzer._extract_metric(run, metric) for run in treatment_data]

            result = StatisticalAnalyzer.compare_configurations(baseline_values, treatment_values)
            results[metric] = result
            p_values.append(result["p_value"])

        # Apply Bonferroni correction for multiple comparisons
        corrected = multipletests(p_values, alpha=0.05, method="bonferroni")

        for i, metric in enumerate(metrics):
            results[metric]["corrected_p_value"] = float(corrected[1][i])
            results[metric]["significant_corrected"] = bool(corrected[0][i])

        return results

    @staticmethod
    def _extract_metric(run: TestRun, metric_name: str) -> float:
        """Extract a specific metric value from a test run."""
        # Parse metric name (e.g., "time.execution_time" or "quality.error_count")
        parts = metric_name.split(".")
        if len(parts) == 2:
            category, field = parts
            if category == "time":
                return getattr(run.time, field)
            if category == "quality":
                return getattr(run.quality, field)
            if category == "memory":
                return getattr(run.memory, field)
            if category == "output":
                return getattr(run.output, field)

        raise ValueError(f"Invalid metric name: {metric_name}")

    @staticmethod
    def calculate_power(effect_size: float, n: int, alpha: float = 0.05) -> float:
        """Calculate statistical power for given parameters.

        Args:
            effect_size: Cohen's d effect size
            n: Sample size per group
            alpha: Significance level

        Returns:
            Statistical power (0-1)
        """
        try:
            power = tt_ind_solve_power(
                effect_size=effect_size, nobs1=n, alpha=alpha, ratio=1.0, alternative="two-sided"
            )
            return float(power)
        except Exception:
            return 0.0


# ============================================================================
# Configuration Management
# ============================================================================


class Configuration:
    """Base class for test configurations."""

    def __init__(self, name: str):
        self.name = name

    def run_scenario(self, scenario: Scenario) -> Dict[str, Any]:
        """Run a scenario with this configuration."""
        raise NotImplementedError


class ControlConfiguration(Configuration):
    """Configuration with no memory system."""

    def __init__(self):
        super().__init__("control")

    def run_scenario(self, scenario: Scenario) -> Dict[str, Any]:
        """Run scenario without memory."""
        # TODO: Implement actual scenario execution
        # For now, return mock data
        return {"success": True, "output": "Mock output"}


class SQLiteConfiguration(Configuration):
    """Configuration with SQLite-based memory."""

    def __init__(self):
        super().__init__("sqlite")

    def run_scenario(self, scenario: Scenario) -> Dict[str, Any]:
        """Run scenario with SQLite memory."""
        # TODO: Implement actual scenario execution with SQLite memory
        return {"success": True, "output": "Mock output"}


class Neo4jConfiguration(Configuration):
    """Configuration with Neo4j-based memory."""

    def __init__(self):
        super().__init__("neo4j")

    def run_scenario(self, scenario: Scenario) -> Dict[str, Any]:
        """Run scenario with Neo4j memory."""
        # TODO: Implement actual scenario execution with Neo4j memory
        return {"success": True, "output": "Mock output"}


# ============================================================================
# Test Harness
# ============================================================================


class MemoryTestHarness:
    """Automated A/B test harness for memory systems."""

    def __init__(self, output_dir: str = "test_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.scenarios = self._load_scenarios()
        self.configurations = {
            "control": ControlConfiguration(),
            "sqlite": SQLiteConfiguration(),
            "neo4j": Neo4jConfiguration(),
        }

    def _load_scenarios(self) -> List[Scenario]:
        """Load test scenarios from definitions."""
        # TODO: Load from YAML files
        # For now, create mock scenarios
        return [
            Scenario(
                id="repeat_authentication",
                name="Repeat Authentication Implementation",
                type="learning_from_repetition",
                expected_benefit="high",
                description="Implement JWT authentication, should reuse pattern on second attempt",
                task="Implement JWT authentication for REST API with user login endpoint",
                success_criteria=["Tests pass", "JWT generation works", "Token validation works"],
                metrics=["time.execution_time", "quality.error_count", "memory.memory_applied"],
            )
        ]

    def run_full_test_suite(self):
        """Run complete A/B test suite."""
        print("=" * 70)
        print("MEMORY SYSTEM A/B TEST SUITE")
        print("=" * 70)

        # Phase 1: Baseline
        print("\n[Phase 1] Establishing baseline (no memory)...")
        baseline_results = self.run_configuration("control")
        self._save_results(baseline_results, "baseline")

        # Phase 2: SQLite
        print("\n[Phase 2] Testing SQLite memory...")
        sqlite_results = self.run_configuration("sqlite")
        self._save_results(sqlite_results, "sqlite")

        # Analyze Phase 2
        comparison_2 = self._compare_configurations(baseline_results, sqlite_results)
        self._save_comparison(comparison_2, "baseline_vs_sqlite")

        if comparison_2["proceed_recommendation"]:
            # Phase 3: Neo4j (only if Phase 2 successful)
            print("\n[Phase 3] Testing Neo4j memory...")
            neo4j_results = self.run_configuration("neo4j")
            self._save_results(neo4j_results, "neo4j")

            # Analyze Phase 3
            comparison_3 = self._compare_configurations(sqlite_results, neo4j_results)
            self._save_comparison(comparison_3, "sqlite_vs_neo4j")
        else:
            print("\n[Phase 3] SKIPPED - Phase 2 results did not meet criteria")

        # Phase 4: Final Analysis
        print("\n[Phase 4] Generating final report...")
        self._generate_final_report()

    def run_configuration(self, config_name: str, iterations: int = 5) -> List[TestRun]:
        """Run all scenarios for a configuration.

        Args:
            config_name: Configuration to test ("control", "sqlite", "neo4j")
            iterations: Number of iterations per scenario

        Returns:
            List of test run results
        """
        config = self.configurations[config_name]
        results = []

        for scenario in self.scenarios:
            print(f"\n  Scenario: {scenario.name}")

            for iteration in range(iterations):
                print(f"    Iteration {iteration + 1}/{iterations}...", end="", flush=True)

                # Run scenario
                result = self._run_single_test(config, scenario, iteration)
                results.append(result)

                print(f" Done ({result.time.execution_time:.1f}s)")

        return results

    def _run_single_test(
        self, config: Configuration, scenario: Scenario, iteration: int
    ) -> TestRun:
        """Run a single test iteration."""
        # Initialize metrics collector
        collector = MetricsCollector(scenario.id, config.name, iteration)
        collector.start_collection()

        try:
            # Run scenario with configuration
            output = config.run_scenario(scenario)

            # TODO: Collect metrics from actual output
            # For now, record mock metrics
            collector.record_time_metric("time_to_first_action", 5.0)
            collector.record_time_metric("decision_time", 10.0)
            collector.record_time_metric("implementation_time", 30.0)

            collector.record_quality_metric("test_pass_rate", 0.95)
            collector.record_quality_metric("code_complexity", 5)
            collector.record_quality_metric("error_count", 1)
            collector.record_quality_metric("revision_cycles", 2)
            collector.record_quality_metric("pylint_score", 8.5)

            collector.record_memory_metric("memory_retrievals", 3)
            collector.record_memory_metric("memory_hits", 2)
            collector.record_memory_metric("memory_applied", 1)
            collector.record_memory_metric("retrieval_time", 15.0)

            collector.record_output_metric("lines_of_code", 120)
            collector.record_output_metric("files_modified", 3)
            collector.record_output_metric("test_coverage", 85.0)
            collector.record_output_metric("documentation_completeness", 0.8)

        except Exception as e:
            # Record failure
            collector.record_error(str(e))

        # Finalize and return metrics
        return collector.finalize()

    def _compare_configurations(
        self, baseline: List[TestRun], treatment: List[TestRun]
    ) -> Dict[str, Any]:
        """Compare two configurations statistically."""
        analyzer = StatisticalAnalyzer()

        # Define metrics to compare
        metrics = [
            "time.execution_time",
            "quality.error_count",
            "quality.pylint_score",
        ]

        # Run statistical analysis
        comparison = analyzer.analyze_multiple_metrics(baseline, treatment, metrics)

        # Determine recommendation
        comparison["proceed_recommendation"] = self._should_proceed(comparison)

        return comparison

    def _should_proceed(self, comparison: Dict[str, Any]) -> bool:
        """Determine if results justify proceeding."""
        # Check execution time improvement
        exec_time = comparison.get("time.execution_time", {})

        # Check if statistically significant
        significant = exec_time.get("significant", False)

        # Check if effect size is meaningful (medium or larger)
        effect_size = abs(exec_time.get("effect_size", 0.0))
        meaningful = effect_size > 0.5

        # Check if improvement is substantial (>20%)
        pct_improvement = exec_time.get("pct_improvement", 0.0)
        substantial = pct_improvement < -20  # Negative = time reduction

        return significant and meaningful and substantial

    def _save_results(self, results: List[TestRun], name: str):
        """Save test results to file."""
        output_file = self.output_dir / f"{name}_results.json"

        # Convert to JSON-serializable format
        data = [asdict(run) for run in results]

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

        print(f"  Saved results to: {output_file}")

    def _save_comparison(self, comparison: Dict[str, Any], name: str):
        """Save comparison results to file."""
        output_file = self.output_dir / f"{name}_comparison.json"

        with open(output_file, "w") as f:
            json.dump(comparison, f, indent=2)

        print(f"  Saved comparison to: {output_file}")

    def _generate_final_report(self):
        """Generate comprehensive comparison report."""
        # TODO: Implement full report generation
        print(f"\n{'=' * 70}")
        print("Final report generation not yet implemented")
        print(f"{'=' * 70}")


# ============================================================================
# CLI Interface
# ============================================================================


def main():
    """Main entry point for test harness."""
    parser = argparse.ArgumentParser(description="Memory System A/B Test Harness")

    parser.add_argument("--full", action="store_true", help="Run full test suite")
    parser.add_argument(
        "--phase",
        choices=["baseline", "sqlite", "neo4j"],
        help="Run specific test phase",
    )
    parser.add_argument("--scenarios", help="Comma-separated list of scenario IDs")
    parser.add_argument("--analyze", action="store_true", help="Analyze existing results")
    parser.add_argument("--output-dir", default="test_results", help="Output directory for results")

    args = parser.parse_args()

    # Initialize test harness
    harness = MemoryTestHarness(output_dir=args.output_dir)

    if args.full:
        # Run full test suite
        harness.run_full_test_suite()

    elif args.phase:
        # Run specific phase
        config_name = "control" if args.phase == "baseline" else args.phase
        results = harness.run_configuration(config_name)
        harness._save_results(results, args.phase)

    elif args.analyze:
        # Analyze existing results
        print("Analysis of existing results not yet implemented")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
