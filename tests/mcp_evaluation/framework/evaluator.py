"""Core evaluation orchestration for MCP framework.

This module provides the MCPEvaluationFramework class that orchestrates
the entire evaluation process: running scenarios, collecting metrics,
comparing results, and generating reports.
"""

import importlib
from datetime import datetime
from typing import Any, Dict, List

from .adapter import ToolAdapter
from .metrics import MetricsCollector
from .types import (
    ComparisonResult,
    EvaluationReport,
    ScenarioResult,
    TestScenario,
    ToolConfiguration,
)


class MCPEvaluationFramework:
    """Generic framework for evaluating MCP tool integrations.

    This is the main entry point for running evaluations. It:
    1. Loads tool adapter based on configuration
    2. Runs scenarios with and without tool
    3. Collects metrics for comparison
    4. Generates evaluation reports
    """

    def __init__(self, tool_config: ToolConfiguration):
        """Initialize framework with tool-specific configuration.

        Args:
            tool_config: Configuration describing the tool to evaluate
        """
        self.tool_config = tool_config
        self.adapter = self._load_adapter()

    def _load_adapter(self) -> ToolAdapter:
        """Load tool adapter based on configuration.

        Returns:
            Instantiated tool adapter

        Raises:
            ImportError: If adapter class cannot be loaded
            ValueError: If adapter class doesn't implement ToolAdapter
        """
        # Try to load from tools directory
        module_name = f"tests.mcp_evaluation.tools.{self.tool_config.tool_id}_adapter"
        try:
            module = importlib.import_module(module_name)
            adapter_class = getattr(module, self.tool_config.adapter_class)

            if not issubclass(adapter_class, ToolAdapter):
                raise ValueError(f"{self.tool_config.adapter_class} must inherit from ToolAdapter")

            return adapter_class(self.tool_config)

        except (ImportError, AttributeError) as e:
            raise ImportError(
                f"Failed to load adapter {self.tool_config.adapter_class} from {module_name}: {e}"
            )

    def run_evaluation(
        self, scenarios: List[TestScenario], mode: str = "with_vs_without"
    ) -> EvaluationReport:
        """Run full evaluation suite.

        Args:
            scenarios: Test scenarios to run
            mode: "with_vs_without" or "before_vs_after"

        Returns:
            Complete evaluation report with all metrics
        """
        results = []

        for scenario in scenarios:
            print(f"\nRunning scenario: {scenario.name}")
            print(f"  Category: {scenario.category.value}")

            # Run baseline (without tool)
            print("  Executing baseline (no tool)...")
            baseline_result = self._run_scenario(scenario, use_tool=False)

            # Run enhanced (with tool)
            print("  Executing with tool...")
            enhanced_result = self._run_scenario(scenario, use_tool=True)

            # Compare and collect metrics
            print("  Comparing results...")
            comparison = self._compare_results(baseline_result, enhanced_result, scenario)

            results.append(comparison)
            print(f"  Recommendation: {comparison.recommendation}")

        # Generate report
        return self._generate_report(results)

    def _run_scenario(self, scenario: TestScenario, use_tool: bool) -> ScenarioResult:
        """Execute a single test scenario.

        Args:
            scenario: The test scenario to execute
            use_tool: Whether to enable the tool

        Returns:
            Captured execution data and results
        """
        # Configure tool availability
        if use_tool:
            if not self.adapter.is_available():
                print("    Warning: Tool not available, using fallback behavior")
                if self.tool_config.fallback_behavior.value == "fail":
                    raise RuntimeError(f"Tool {self.tool_config.tool_id} not available")
                if self.tool_config.fallback_behavior.value == "skip":
                    return None
                # Otherwise fall back to baseline
                use_tool = False

            if use_tool:
                self.adapter.enable()
        else:
            self.adapter.disable()

        # Create metrics collector
        metrics_collector = MetricsCollector(adapter=self.adapter if use_tool else None)

        # Start metrics collection
        metrics_collector.start()

        # Execute scenario
        # NOTE: This is a simplified placeholder. Real implementation would
        # integrate with Claude Code SDK or subprocess execution
        result = self._execute_task(scenario, metrics_collector)

        # Collect metrics
        metrics = metrics_collector.stop()

        return ScenarioResult(
            scenario=scenario,
            use_tool=use_tool,
            output=result,
            metrics=metrics,
        )

    def _execute_task(
        self, scenario: TestScenario, metrics_collector: MetricsCollector
    ) -> Dict[str, Any]:
        """Execute the actual task.

        This is a placeholder for the real execution logic.
        In production, this would:
        1. Set up test environment
        2. Invoke Claude Code with the task prompt
        3. Monitor execution and capture metrics
        4. Validate results against success criteria

        Args:
            scenario: Scenario to execute
            metrics_collector: Collector to record metrics

        Returns:
            Execution result data
        """
        # Placeholder implementation
        # Real implementation would integrate with Claude Code SDK
        import random

        # Simulate some file operations
        for i in range(random.randint(5, 20)):
            metrics_collector.record_file_read(f"file_{i}.py")

        # Simulate token usage
        metrics_collector.record_tokens(random.randint(1000, 5000))

        # Simulate quality assessment
        requirements_met = random.randint(
            scenario.initial_state.get("expected_count", 5) - 1,
            scenario.initial_state.get("expected_count", 5),
        )
        metrics_collector.set_requirements(
            met=requirements_met, total=scenario.initial_state.get("expected_count", 5)
        )
        metrics_collector.set_correctness(
            requirements_met / scenario.initial_state.get("expected_count", 5)
        )

        return {
            "status": "success",
            "found": requirements_met,
            "files_examined": len(metrics_collector.file_reads),
        }

    def _compare_results(
        self, baseline: ScenarioResult, enhanced: ScenarioResult, scenario: TestScenario
    ) -> ComparisonResult:
        """Compare baseline vs tool-enhanced execution.

        Args:
            baseline: Baseline execution result
            enhanced: Tool-enhanced execution result
            scenario: Test scenario

        Returns:
            Comparison result with deltas and recommendation
        """
        # Calculate quality deltas
        quality_delta = {
            "correctness_delta": enhanced.metrics.quality.correctness_score
            - baseline.metrics.quality.correctness_score,
            "test_failures_delta": enhanced.metrics.quality.test_failures
            - baseline.metrics.quality.test_failures,
            "requirements_delta": enhanced.metrics.quality.requirements_met
            - baseline.metrics.quality.requirements_met,
        }

        # Calculate efficiency deltas
        time_delta = (
            enhanced.metrics.efficiency.wall_clock_seconds
            - baseline.metrics.efficiency.wall_clock_seconds
        )
        time_percent = (
            (time_delta / baseline.metrics.efficiency.wall_clock_seconds * 100)
            if baseline.metrics.efficiency.wall_clock_seconds > 0
            else 0
        )

        efficiency_delta = {
            "time_delta_seconds": time_delta,
            "time_delta_percent": time_percent,
            "token_delta": enhanced.metrics.efficiency.total_tokens
            - baseline.metrics.efficiency.total_tokens,
            "file_reads_delta": enhanced.metrics.efficiency.file_reads
            - baseline.metrics.efficiency.file_reads,
            "file_writes_delta": enhanced.metrics.efficiency.file_writes
            - baseline.metrics.efficiency.file_writes,
        }

        # Calculate tool value
        tool_value = {}
        if enhanced.metrics.tool:
            tool_value = {
                "features_used": enhanced.metrics.tool.features_used,
                "unique_insights": enhanced.metrics.tool.unique_insights,
                "time_saved_estimate": enhanced.metrics.tool.time_saved_estimate,
                "tool_success_rate": 1.0
                - (
                    enhanced.metrics.tool.tool_failures
                    / max(1, enhanced.metrics.efficiency.tool_invocations)
                ),
            }

        # Generate recommendation
        recommendation = self._make_recommendation(quality_delta, efficiency_delta, tool_value)

        return ComparisonResult(
            scenario=scenario,
            baseline_result=baseline,
            enhanced_result=enhanced,
            quality_delta=quality_delta,
            efficiency_delta=efficiency_delta,
            tool_value=tool_value,
            recommendation=recommendation,
        )

    def _make_recommendation(
        self,
        quality_delta: Dict[str, Any],
        efficiency_delta: Dict[str, Any],
        tool_value: Dict[str, Any],
    ) -> str:
        """Make integrate/don't-integrate recommendation.

        Args:
            quality_delta: Quality improvements
            efficiency_delta: Efficiency improvements
            tool_value: Tool-specific value metrics

        Returns:
            Recommendation string
        """
        # Simple heuristic: recommend if quality improved or time decreased significantly
        quality_improved = quality_delta.get("correctness_delta", 0) > 0
        faster = efficiency_delta.get("time_delta_percent", 0) < -10  # >10% faster
        much_faster = efficiency_delta.get("time_delta_percent", 0) < -30  # >30% faster

        if much_faster or (faster and quality_improved):
            return "INTEGRATE - Significant measurable value"
        if faster or quality_improved:
            return "CONSIDER - Some value demonstrated"
        return "DON'T INTEGRATE - No clear advantage"

    def _generate_report(self, results: List[ComparisonResult]) -> EvaluationReport:
        """Generate comprehensive evaluation report.

        Args:
            results: List of comparison results

        Returns:
            Complete evaluation report
        """
        # Calculate summary statistics
        total_scenarios = len(results)
        integrate_count = sum(1 for r in results if "INTEGRATE" in r.recommendation)
        consider_count = sum(1 for r in results if "CONSIDER" in r.recommendation)

        avg_time_delta = (
            sum(r.efficiency_delta.get("time_delta_percent", 0) for r in results) / total_scenarios
            if total_scenarios > 0
            else 0
        )

        avg_quality_delta = (
            sum(r.quality_delta.get("correctness_delta", 0) for r in results) / total_scenarios
            if total_scenarios > 0
            else 0
        )

        summary = {
            "total_scenarios": total_scenarios,
            "integrate_recommended": integrate_count,
            "consider_recommended": consider_count,
            "avg_time_improvement_percent": avg_time_delta,
            "avg_quality_improvement": avg_quality_delta,
        }

        # Generate recommendations
        recommendations = []
        if integrate_count > total_scenarios * 0.6:
            recommendations.append(
                f"INTEGRATE: {integrate_count}/{total_scenarios} scenarios show clear value"
            )
        elif integrate_count + consider_count > total_scenarios * 0.5:
            recommendations.append("CONSIDER: Mixed results, evaluate specific use cases")
        else:
            recommendations.append("DON'T INTEGRATE: Insufficient value demonstrated")

        if avg_time_delta < -20:
            recommendations.append(
                f"Tool provides significant speed improvements (avg {-avg_time_delta:.1f}% faster)"
            )

        if avg_quality_delta > 0.1:
            recommendations.append(f"Tool improves correctness (avg +{avg_quality_delta:.1%})")

        return EvaluationReport(
            tool_config=self.tool_config,
            timestamp=datetime.now(),
            results=results,
            summary=summary,
            recommendations=recommendations,
        )
