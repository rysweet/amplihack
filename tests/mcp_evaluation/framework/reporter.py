"""Report generation for MCP evaluation framework.

This module generates human-readable markdown reports from evaluation results,
including executive summaries, detailed scenario breakdowns, and recommendations.
"""

from pathlib import Path
from typing import Dict, List

from .types import ComparisonResult, EvaluationReport


class ReportGenerator:
    """Generates markdown evaluation reports.

    Takes an EvaluationReport and produces:
    - Executive summary with key findings
    - Detailed scenario comparisons
    - Capability analysis
    - Integration recommendations
    """

    def __init__(self, report: EvaluationReport):
        """Initialize with evaluation results.

        Args:
            report: Complete evaluation report to generate from
        """
        self.report = report

    def generate_markdown(self) -> str:
        """Generate complete markdown report.

        Returns:
            Markdown-formatted report string
        """
        sections = [
            self._generate_header(),
            self._generate_executive_summary(),
            self._generate_detailed_results(),
            self._generate_capability_analysis(),
            self._generate_recommendations(),
        ]

        return "\n\n".join(sections)

    def save(self, path: Path) -> None:
        """Save report to file.

        Args:
            path: Path where report should be saved
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        markdown = self.generate_markdown()
        with open(path, "w") as f:
            f.write(markdown)

    def _generate_header(self) -> str:
        """Generate report header."""
        return f"""# MCP Tool Evaluation Report

**Tool**: {self.report.tool_config.tool_name} v{self.report.tool_config.version}
**Date**: {self.report.timestamp.strftime("%Y-%m-%d %H:%M:%S")}
**Scenarios**: {self.report.summary["total_scenarios"]} ({", ".join(set(r.scenario.category.value for r in self.report.results))})"""

    def _generate_executive_summary(self) -> str:
        """Generate executive summary section."""
        summary = self.report.summary
        time_improvement = summary.get("avg_time_improvement_percent", 0)
        quality_improvement = summary.get("avg_quality_improvement", 0)

        # Determine overall verdict
        integrate_pct = (
            (summary["integrate_recommended"] / summary["total_scenarios"] * 100)
            if summary["total_scenarios"] > 0
            else 0
        )

        verdict = (
            "INTEGRATE"
            if integrate_pct > 60
            else "CONSIDER"
            if integrate_pct > 30
            else "DON'T INTEGRATE"
        )

        return f"""## Executive Summary

- **Overall Verdict**: {verdict}
- **Performance**: {time_improvement:+.1f}% average time change
- **Quality**: {quality_improvement:+.1%} average correctness improvement
- **Scenarios Passed**: {summary["integrate_recommended"]}/{summary["total_scenarios"]} strongly recommend integration
- **Tool Capabilities**: {len(self.report.tool_config.capabilities)} features evaluated"""

    def _generate_detailed_results(self) -> str:
        """Generate detailed scenario results."""
        sections = ["## Detailed Results"]

        for i, result in enumerate(self.report.results, 1):
            sections.append(self._generate_scenario_details(result, i))

        return "\n\n".join(sections)

    def _generate_scenario_details(self, result: ComparisonResult, number: int) -> str:
        """Generate detailed results for a single scenario.

        Args:
            result: Comparison result for this scenario
            number: Scenario number for display

        Returns:
            Markdown section for this scenario
        """
        scenario = result.scenario
        baseline = result.baseline_result.metrics
        enhanced = result.enhanced_result.metrics

        # Build comparison table
        table = f"""### Scenario {number}: {scenario.name}

**Category**: {scenario.category.value}
**Task**: {scenario.description}

| Metric | Baseline | With Tool | Delta |
|--------|----------|-----------|-------|
| Time (s) | {baseline.efficiency.wall_clock_seconds:.1f} | {enhanced.efficiency.wall_clock_seconds:.1f} | {result.efficiency_delta["time_delta_percent"]:+.1f}% |
| Tokens | {baseline.efficiency.total_tokens:,} | {enhanced.efficiency.total_tokens:,} | {result.efficiency_delta["token_delta"]:+,} |
| File Reads | {baseline.efficiency.file_reads} | {enhanced.efficiency.file_reads} | {result.efficiency_delta["file_reads_delta"]:+d} |
| File Writes | {baseline.efficiency.file_writes} | {enhanced.efficiency.file_writes} | {result.efficiency_delta["file_writes_delta"]:+d} |
| Correctness | {baseline.quality.correctness_score:.1%} | {enhanced.quality.correctness_score:.1%} | {result.quality_delta["correctness_delta"]:+.1%} |
| Requirements Met | {baseline.quality.requirements_met}/{baseline.quality.requirements_total} | {enhanced.quality.requirements_met}/{enhanced.quality.requirements_total} | {result.quality_delta["requirements_delta"]:+d} |"""

        # Add tool usage if available
        if result.tool_value:
            tool_section = f"""

**Tool Usage**:
- Features Used: {", ".join(result.tool_value.get("features_used", []))}
- Success Rate: {result.tool_value.get("tool_success_rate", 0):.1%}
- Unique Insights: {result.tool_value.get("unique_insights", 0)}
- Estimated Time Saved: {result.tool_value.get("time_saved_estimate", 0):.1f}s"""
            table += tool_section

        # Add recommendation
        table += f"\n\n**Recommendation**: {result.recommendation}"

        return table

    def _generate_capability_analysis(self) -> str:
        """Generate analysis of tool capabilities."""
        sections = ["## Capability Analysis"]

        # Group results by which capabilities were used
        capability_usage: Dict[str, List[ComparisonResult]] = {}
        for result in self.report.results:
            if result.tool_value and "features_used" in result.tool_value:
                for feature in result.tool_value["features_used"]:
                    if feature not in capability_usage:
                        capability_usage[feature] = []
                    capability_usage[feature].append(result)

        # Analyze each capability
        for capability in self.report.tool_config.capabilities:
            results_using = capability_usage.get(capability.id, [])
            usage_count = len(results_using)

            if usage_count == 0:
                value = "NOT USED"
                description = "Capability was not utilized in any scenarios"
            else:
                # Calculate average improvement for this capability
                avg_time_delta = (
                    sum(r.efficiency_delta.get("time_delta_percent", 0) for r in results_using)
                    / usage_count
                )

                avg_quality_delta = (
                    sum(r.quality_delta.get("correctness_delta", 0) for r in results_using)
                    / usage_count
                )

                if avg_time_delta < -20 or avg_quality_delta > 0.1:
                    value = "HIGH"
                elif avg_time_delta < -10 or avg_quality_delta > 0.05:
                    value = "MEDIUM"
                else:
                    value = "LOW"

                description = (
                    f"Used in {usage_count}/{self.report.summary['total_scenarios']} scenarios"
                )
                if avg_time_delta < 0:
                    description += f", avg {-avg_time_delta:.1f}% faster"
                if avg_quality_delta > 0:
                    description += f", avg +{avg_quality_delta:.1%} quality"

            sections.append(f"""### {capability.name}

- **Value**: {value}
- **Usage**: {description}
- **Expected Improvement**: {capability.expected_improvement.value}
- **Description**: {capability.description}""")

        return "\n\n".join(sections)

    def _generate_recommendations(self) -> str:
        """Generate actionable recommendations."""
        sections = ["## Recommendations"]

        for i, rec in enumerate(self.report.recommendations, 1):
            sections.append(f"{i}. {rec}")

        # Add next steps based on overall recommendation
        verdict = (
            "INTEGRATE"
            if self.report.summary["integrate_recommended"]
            > self.report.summary["total_scenarios"] * 0.6
            else "DON'T INTEGRATE"
        )

        if verdict == "INTEGRATE":
            sections.extend(
                [
                    "",
                    "### Next Steps",
                    "",
                    "- [ ] Review tool setup requirements",
                    "- [ ] Plan integration into existing workflows",
                    "- [ ] Configure tool adapter in production",
                    "- [ ] Monitor real-world usage metrics",
                    "- [ ] Update agent workflows to leverage tool capabilities",
                ]
            )
        else:
            sections.extend(
                [
                    "",
                    "### Next Steps",
                    "",
                    "- [ ] Document reasons for not integrating",
                    "- [ ] Keep framework for evaluating other tools",
                    "- [ ] Consider alternative tools",
                    "- [ ] Re-evaluate if tool capabilities improve",
                ]
            )

        return "\n".join(sections)


def generate_comparison_report(
    baseline_report: EvaluationReport, enhanced_report: EvaluationReport, output_path: Path
) -> None:
    """Generate a side-by-side comparison report for two evaluations.

    Useful for comparing different tool versions or configurations.

    Args:
        baseline_report: First evaluation report
        enhanced_report: Second evaluation report
        output_path: Where to save comparison report
    """
    sections = [
        "# Evaluation Comparison Report",
        "",
        f"**Baseline**: {baseline_report.tool_config.tool_name} v{baseline_report.tool_config.version}",
        f"**Enhanced**: {enhanced_report.tool_config.tool_name} v{enhanced_report.tool_config.version}",
        f"**Date**: {enhanced_report.timestamp.strftime('%Y-%m-%d')}",
        "",
        "## Summary Comparison",
        "",
        "| Metric | Baseline | Enhanced | Delta |",
        "|--------|----------|----------|-------|",
    ]

    # Add summary comparisons
    b_sum = baseline_report.summary
    e_sum = enhanced_report.summary

    metrics = [
        ("Avg Time Improvement", "avg_time_improvement_percent", "%"),
        ("Avg Quality Improvement", "avg_quality_improvement", "%"),
        ("Integrate Recommended", "integrate_recommended", ""),
    ]

    for label, key, unit in metrics:
        b_val = b_sum.get(key, 0)
        e_val = e_sum.get(key, 0)
        delta = e_val - b_val
        sections.append(f"| {label} | {b_val:.1f}{unit} | {e_val:.1f}{unit} | {delta:+.1f}{unit} |")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(sections))
