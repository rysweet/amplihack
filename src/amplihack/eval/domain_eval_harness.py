"""Generic evaluation harness for domain-specific agents.

Runs eval levels for any DomainAgent, grades results, and produces reports.
Philosophy: Generic harness that works with any domain - agents provide their own eval levels.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from amplihack.agents.domain_agents.base import DomainAgent, EvalLevel, EvalScenario

logger = logging.getLogger(__name__)


@dataclass
class ScenarioResult:
    """Result of evaluating a single scenario.

    Attributes:
        scenario_id: Scenario identifier
        scenario_name: Human-readable name
        level_id: Which eval level this belongs to
        score: Grade from 0.0 to 1.0
        passed: Whether score meets threshold
        agent_output: What the agent produced
        grading_details: How the grade was determined
    """

    scenario_id: str
    scenario_name: str
    level_id: str
    score: float
    passed: bool
    agent_output: Any
    grading_details: str


@dataclass
class LevelResult:
    """Aggregated results for one evaluation level.

    Attributes:
        level_id: Level identifier (L1-L4)
        level_name: Human-readable name
        scenarios: Individual scenario results
        average_score: Mean score across scenarios
        passed: Whether average meets threshold
        passing_threshold: Required minimum score
    """

    level_id: str
    level_name: str
    scenarios: list[ScenarioResult]
    average_score: float
    passed: bool
    passing_threshold: float


@dataclass
class EvalReport:
    """Complete evaluation report for a domain agent.

    Attributes:
        agent_name: Agent being evaluated
        domain: Domain name
        levels: Results per level
        overall_score: Weighted overall score
        overall_passed: Whether agent passed overall
        metadata: Additional info
    """

    agent_name: str
    domain: str
    levels: list[LevelResult]
    overall_score: float
    overall_passed: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""
        return {
            "agent_name": self.agent_name,
            "domain": self.domain,
            "overall_score": round(self.overall_score, 3),
            "overall_passed": self.overall_passed,
            "levels": [
                {
                    "level_id": level.level_id,
                    "level_name": level.level_name,
                    "average_score": round(level.average_score, 3),
                    "passed": level.passed,
                    "passing_threshold": level.passing_threshold,
                    "scenario_count": len(level.scenarios),
                    "scenarios": [
                        {
                            "scenario_id": s.scenario_id,
                            "scenario_name": s.scenario_name,
                            "score": round(s.score, 3),
                            "passed": s.passed,
                            "grading_details": s.grading_details,
                        }
                        for s in level.scenarios
                    ],
                }
                for level in self.levels
            ],
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert report to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class DomainEvalHarness:
    """Generic evaluation harness for domain-specific agents.

    Runs each eval level's scenarios against the agent, grades results,
    and produces an EvalReport.

    Example:
        >>> agent = CodeReviewAgent("test_reviewer")
        >>> harness = DomainEvalHarness(agent)
        >>> report = harness.run()
        >>> print(f"Overall: {report.overall_score:.0%}")
        >>> print(report.to_json())
    """

    def __init__(self, agent: DomainAgent):
        """Initialize harness for a domain agent.

        Args:
            agent: The domain agent to evaluate
        """
        self.agent = agent
        self.eval_levels = agent.get_eval_levels()

    def run(self, levels: list[str] | None = None) -> EvalReport:
        """Run evaluation across all (or specified) levels.

        Args:
            levels: Optional list of level IDs to run (e.g. ["L1", "L2"]).
                    If None, runs all levels.

        Returns:
            EvalReport with results
        """
        target_levels = self.eval_levels
        if levels:
            target_levels = [lv for lv in self.eval_levels if lv.level_id in levels]

        level_results = []
        for level in target_levels:
            level_result = self._run_level(level)
            level_results.append(level_result)

        # Calculate overall score (weighted equally across levels)
        if level_results:
            overall_score = sum(lr.average_score for lr in level_results) / len(level_results)
        else:
            overall_score = 0.0

        # Pass if all levels pass
        overall_passed = all(lr.passed for lr in level_results) if level_results else False

        return EvalReport(
            agent_name=self.agent.agent_name,
            domain=self.agent.domain,
            levels=level_results,
            overall_score=overall_score,
            overall_passed=overall_passed,
            metadata={
                "levels_evaluated": len(level_results),
                "total_scenarios": sum(len(lr.scenarios) for lr in level_results),
            },
        )

    def _run_level(self, level: EvalLevel) -> LevelResult:
        """Run all scenarios for one evaluation level.

        Args:
            level: The eval level to run

        Returns:
            LevelResult with aggregated scores
        """
        scenario_results = []

        for scenario in level.scenarios:
            result = self._run_scenario(scenario, level)
            scenario_results.append(result)

        # Calculate average
        if scenario_results:
            avg_score = sum(r.score for r in scenario_results) / len(scenario_results)
        else:
            avg_score = 0.0

        return LevelResult(
            level_id=level.level_id,
            level_name=level.name,
            scenarios=scenario_results,
            average_score=avg_score,
            passed=avg_score >= level.passing_threshold,
            passing_threshold=level.passing_threshold,
        )

    def _run_scenario(self, scenario: EvalScenario, level: EvalLevel) -> ScenarioResult:
        """Run a single scenario and grade the result.

        Args:
            scenario: The scenario to run
            level: The level this scenario belongs to

        Returns:
            ScenarioResult with score and details
        """
        # Execute agent on scenario input
        try:
            task_result = self.agent.execute_task(scenario.input_data)
        except Exception as e:
            logger.exception("Scenario %s execution failed", scenario.scenario_id)
            return ScenarioResult(
                scenario_id=scenario.scenario_id,
                scenario_name=scenario.name,
                level_id=level.level_id,
                score=0.0,
                passed=False,
                agent_output=None,
                grading_details=f"Agent execution failed: {type(e).__name__}",
            )

        if not task_result.success:
            return ScenarioResult(
                scenario_id=scenario.scenario_id,
                scenario_name=scenario.name,
                level_id=level.level_id,
                score=0.0,
                passed=False,
                agent_output=task_result.error,
                grading_details=f"Task failed: {task_result.error}",
            )

        # Grade the result
        score, details = self._grade_output(
            agent_output=task_result.output,
            expected=scenario.expected_output,
            rubric=scenario.grading_rubric,
        )

        return ScenarioResult(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.name,
            level_id=level.level_id,
            score=score,
            passed=score >= level.passing_threshold,
            agent_output=task_result.output,
            grading_details=details,
        )

    def _grade_output(
        self,
        agent_output: Any,
        expected: dict[str, Any],
        rubric: str,
    ) -> tuple[float, str]:
        """Grade agent output against expected output.

        Uses deterministic checks based on expected output criteria.
        Does not require LLM for grading (keeping harness self-contained).

        Args:
            agent_output: What the agent produced
            expected: Expected output criteria
            rubric: Grading rubric text

        Returns:
            Tuple of (score, details_text)
        """
        if agent_output is None:
            return 0.0, "No output produced"

        checks_passed = 0
        checks_total = 0
        details_parts = []

        # Check minimum counts
        for key, min_val in expected.items():
            if key.startswith("min_"):
                checks_total += 1
                actual_key = key[4:]  # Remove "min_" prefix
                actual_val = _deep_get(agent_output, actual_key)
                if actual_val is not None:
                    if isinstance(actual_val, (list, tuple)):
                        actual_count = len(actual_val)
                    elif isinstance(actual_val, (int, float)):
                        actual_count = actual_val
                    else:
                        actual_count = 0

                    if actual_count >= min_val:
                        checks_passed += 1
                        details_parts.append(
                            f"PASS: {actual_key} >= {min_val} (got {actual_count})"
                        )
                    else:
                        details_parts.append(f"FAIL: {actual_key} < {min_val} (got {actual_count})")
                else:
                    details_parts.append(f"FAIL: {actual_key} not found in output")

        # Check expected values that should be present
        for key, expected_val in expected.items():
            if key.startswith("expected_"):
                checks_total += 1
                check_key = key[9:]  # Remove "expected_" prefix

                if isinstance(expected_val, list):
                    # Check that all expected values are found somewhere in output
                    output_str = json.dumps(agent_output).lower()
                    found = sum(1 for v in expected_val if str(v).lower() in output_str)
                    ratio = found / len(expected_val) if expected_val else 1.0
                    if ratio >= 0.5:
                        checks_passed += ratio
                        details_parts.append(f"PASS: {check_key} found {found}/{len(expected_val)}")
                    else:
                        checks_passed += ratio
                        details_parts.append(
                            f"PARTIAL: {check_key} found {found}/{len(expected_val)}"
                        )

        # Check "must_mention" items
        if "must_mention" in expected:
            checks_total += 1
            output_str = json.dumps(agent_output).lower()
            mentions = expected["must_mention"]
            found = sum(1 for m in mentions if m.lower() in output_str)
            ratio = found / len(mentions) if mentions else 1.0
            checks_passed += ratio
            details_parts.append(f"Mentions: {found}/{len(mentions)}")

        # Check boolean flags
        for key, expected_val in expected.items():
            if isinstance(expected_val, bool) and key.startswith("must_"):
                checks_total += 1
                check_key = key[5:]
                output_str = json.dumps(agent_output).lower()
                if check_key.replace("_", " ") in output_str or check_key in output_str:
                    if expected_val:
                        checks_passed += 1
                        details_parts.append(f"PASS: {check_key} present")
                    else:
                        details_parts.append(f"FAIL: {check_key} should not be present")
                else:
                    if not expected_val:
                        checks_passed += 1
                        details_parts.append(f"PASS: {check_key} absent as expected")
                    else:
                        details_parts.append(f"FAIL: {check_key} not found")

        # Check specific issue patterns
        if "issues" in expected:
            for issue_pattern in expected["issues"]:
                checks_total += 1
                output_issues = (
                    agent_output.get("issues", []) if isinstance(agent_output, dict) else []
                )
                found = False
                for actual_issue in output_issues:
                    match = True
                    for pk, pv in issue_pattern.items():
                        if pk == "message_contains":
                            if pv.lower() not in str(actual_issue.get("message", "")).lower():
                                match = False
                        elif actual_issue.get(pk) != pv:
                            match = False
                    if match:
                        found = True
                        break

                if found:
                    checks_passed += 1
                    details_parts.append(f"PASS: Found issue matching {issue_pattern}")
                else:
                    details_parts.append(f"FAIL: No issue matching {issue_pattern}")

        # Calculate score
        if checks_total > 0:
            score = checks_passed / checks_total
        else:
            # No specific checks defined - give partial credit if output exists
            score = 0.5

        details = " | ".join(details_parts) if details_parts else "No specific checks defined"
        return round(min(1.0, max(0.0, score)), 3), details


def _deep_get(obj: Any, key: str) -> Any:
    """Get a value from a nested dict/list structure.

    Args:
        obj: The object to search
        key: Key to find (supports dot notation)

    Returns:
        The found value or None
    """
    if obj is None:
        return None

    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        # Try nested access
        for k, v in obj.items():
            if k == key:
                return v
            result = _deep_get(v, key)
            if result is not None:
                return result

    if isinstance(obj, (list, tuple)):
        return obj  # Return the list itself for counting

    return None
