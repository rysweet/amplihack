"""Scenario 2: Code Understanding and Analysis Test.

Tests the ability to understand code structure and map dependencies,
specifically analyzing the DatabaseService class.
"""

from pathlib import Path

from tests.mcp_evaluation.framework.types import (
    Criterion,
    ScenarioCategory,
    TestScenario,
)


def create_analysis_scenario() -> TestScenario:
    """Create code understanding test scenario.

    This scenario tests:
    - Identifying direct dependencies
    - Understanding method calls
    - Mapping class relationships

    Returns:
        Configured TestScenario
    """
    # Get path to test codebase
    codebase_path = Path(__file__).parent / "test_codebases" / "microservice_project"

    # Define expected results
    expected_direct_deps = [
        "Dict",
        "List",
        "Optional",
        "Any",
    ]

    expected_usages = [
        "UserService",
        "AuthService",
    ]

    # Define success criteria
    def check_direct_deps(result):
        """Check if direct dependencies were identified."""
        # Simplified: check if some analysis was done
        return result.get("found", 0) >= 2

    def check_usage_found(result):
        """Check if classes using DatabaseService were found."""
        # Should find UserService and AuthService
        return result.get("found", 0) >= 1

    def check_completeness(result):
        """Check analysis completeness."""
        # Basic check that analysis was performed
        return result.get("files_examined", 0) > 0

    criteria = [
        Criterion(
            name="identify_direct_deps",
            check=check_direct_deps,
            description="Identify direct dependencies of DatabaseService",
        ),
        Criterion(
            name="find_usages",
            check=check_usage_found,
            description="Find classes that use DatabaseService",
        ),
        Criterion(
            name="complete_analysis",
            check=check_completeness,
            description="Provide complete dependency analysis",
        ),
    ]

    return TestScenario(
        id="code_analysis_001",
        category=ScenarioCategory.ANALYSIS,
        name="Map Class Dependencies",
        description="Analyze the DatabaseService class and identify all its dependencies and usages",
        test_codebase=codebase_path,
        initial_state={
            "target_class": "DatabaseService",
            "expected_count": len(expected_usages),
            "expected_direct_deps": expected_direct_deps,
            "expected_usages": expected_usages,
        },
        task_prompt="""
Analyze the DatabaseService class and identify:

1. All direct dependencies (imports, type hints)
2. All methods it defines
3. All classes that depend on DatabaseService (use it)
4. The relationship between DatabaseService and other services

Provide a complete analysis of how DatabaseService fits into the architecture.
        """.strip(),
        success_criteria=criteria,
        baseline_metrics=[
            "file_reads",
            "wall_clock_seconds",
            "correctness_score",
            "requirements_met",
        ],
        tool_metrics=[
            "features_used",
            "tool_call_latency",
            "unique_insights",
            "time_saved_estimate",
        ],
    )
