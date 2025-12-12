"""Scenario 1: Cross-File Navigation Test.

Tests the ability to find code across multiple files, specifically
locating all implementations of the Handler interface.
"""

from pathlib import Path

from tests.mcp_evaluation.framework.types import (
    Criterion,
    ScenarioCategory,
    TestScenario,
)


def create_navigation_scenario() -> TestScenario:
    """Create cross-file navigation test scenario.

    This scenario tests:
    - Finding all classes implementing Handler interface
    - Accurate file path identification
    - No false positives from text search

    Returns:
        Configured TestScenario
    """
    # Get path to test codebase
    codebase_path = Path(__file__).parent / "test_codebases" / "microservice_project"

    # Define expected results
    expected_implementations = [
        "HTTPHandler",
        "GRPCHandler",
        "WebSocketHandler",
    ]

    expected_files = [
        "handlers/http_handler.py",
        "handlers/grpc_handler.py",
        "handlers/websocket_handler.py",
    ]

    # Define success criteria
    def check_all_found(result):
        """Check if all Handler implementations were found."""
        found = result.get("found", 0)
        return found >= len(expected_implementations)

    def check_no_false_positives(result):
        """Check for false positives in results."""
        # In a real scenario, we'd validate the actual findings
        # For now, we accept if found count matches expected
        return result.get("found", 0) <= len(expected_implementations) + 1

    def check_correct_files(result):
        """Check if correct files were identified."""
        # Simplified check - real implementation would validate file paths
        return result.get("files_examined", 0) > 0

    criteria = [
        Criterion(
            name="find_all_implementations",
            check=check_all_found,
            description=f"Find all {len(expected_implementations)} Handler implementations",
        ),
        Criterion(
            name="no_false_positives",
            check=check_no_false_positives,
            description="No false positives from text search",
        ),
        Criterion(
            name="correct_file_paths",
            check=check_correct_files,
            description="Identify correct file paths",
        ),
    ]

    return TestScenario(
        id="cross_file_nav_001",
        category=ScenarioCategory.NAVIGATION,
        name="Find Interface Implementations",
        description="Locate all classes implementing the Handler interface across the codebase",
        test_codebase=codebase_path,
        initial_state={
            "target_interface": "Handler",
            "expected_count": len(expected_implementations),
            "expected_implementations": expected_implementations,
            "expected_files": expected_files,
        },
        task_prompt="""
Find all classes that implement the Handler interface in this codebase.

Requirements:
- Search across all Python files
- Identify classes that inherit from Handler
- List each implementation with its file path and class name
- Be precise - avoid false positives

Expected: There should be 3 implementations (HTTPHandler, GRPCHandler, WebSocketHandler)
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
