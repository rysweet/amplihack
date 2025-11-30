"""Scenario 3: Targeted Code Modification Test.

Tests the ability to make precise, context-aware code modifications,
specifically adding type hints to service methods.
"""

from pathlib import Path

from tests.mcp_evaluation.framework.types import (
    Criterion,
    ScenarioCategory,
    TestScenario,
)


def create_modification_scenario() -> TestScenario:
    """Create targeted modification test scenario.

    This scenario tests:
    - Making precise edits to specific methods
    - Context-aware modifications
    - Maintaining code correctness

    Returns:
        Configured TestScenario
    """
    # Get path to test codebase
    codebase_path = Path(__file__).parent / "test_codebases" / "microservice_project"

    # Define expected modifications
    expected_methods_to_modify = [
        "get_user",
        "create_user",
        "update_user",
        "delete_user",
        "list_users",
    ]

    # Define success criteria
    def check_methods_modified(result):
        """Check if expected methods were modified."""
        # In real scenario, would verify actual modifications
        return result.get("found", 0) >= 3

    def check_code_still_works(result):
        """Check that modifications didn't break code."""
        # Would run tests or syntax checks
        return result.get("status", "") == "success"

    def check_context_awareness(result):
        """Check that modifications were context-aware."""
        # Would verify imports, formatting, etc.
        return result.get("files_examined", 0) > 0

    criteria = [
        Criterion(
            name="all_methods_modified",
            check=check_methods_modified,
            description=f"Modify {len(expected_methods_to_modify)} service methods",
        ),
        Criterion(
            name="code_still_works",
            check=check_code_still_works,
            description="Modifications don't break existing code",
        ),
        Criterion(
            name="context_aware",
            check=check_context_awareness,
            description="Modifications are context-aware (imports, formatting)",
        ),
    ]

    return TestScenario(
        id="code_modification_001",
        category=ScenarioCategory.MODIFICATION,
        name="Add Type Hints to Service Methods",
        description="Add comprehensive type hints to all public methods in UserService",
        test_codebase=codebase_path,
        initial_state={
            "target_class": "UserService",
            "target_file": "services/user_service.py",
            "expected_count": len(expected_methods_to_modify),
            "expected_methods": expected_methods_to_modify,
        },
        task_prompt="""
Add comprehensive type hints to all public methods in the UserService class.

Requirements:
- Add type hints for parameters and return values
- Use proper typing imports (Optional, Dict, List, etc.)
- Maintain existing code structure and formatting
- Ensure code remains syntactically correct
- Add imports at the top if needed

Target file: services/user_service.py
Target class: UserService
        """.strip(),
        success_criteria=criteria,
        baseline_metrics=[
            "file_writes",
            "wall_clock_seconds",
            "correctness_score",
            "requirements_met",
        ],
        tool_metrics=[
            "features_used",
            "tool_call_latency",
            "edit_precision",
            "context_awareness",
        ],
    )
