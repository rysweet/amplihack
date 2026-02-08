"""
Test suite for PM Daily Status Workflow

Tests verify the workflow configuration has required environment variables
for GitHub CLI authentication.

Following TDD: These tests define the contract and will FAIL before implementation.
"""

from pathlib import Path
from typing import Any

import yaml


def load_workflow_file() -> dict[str, Any]:
    """Load the PM Daily Status workflow YAML file."""
    workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "pm-daily-status.yml"

    with open(workflow_path, "r") as f:
        return yaml.safe_load(f)


def find_generate_status_step(workflow_data: dict[str, Any]) -> dict[str, Any]:
    """Find the 'Generate status report' step in the workflow."""
    jobs = workflow_data.get("jobs", {})
    daily_status = jobs.get("daily-status", {})
    steps = daily_status.get("steps", [])

    for step in steps:
        if isinstance(step, dict) and "Generate status report" in step.get("name", ""):
            return step

    raise AssertionError("'Generate status report' step not found in workflow")


class TestPMDailyStatusWorkflow:
    """Test suite for PM Daily Status workflow configuration."""

    def test_workflow_file_exists(self) -> None:
        """Test that the workflow file exists."""
        workflow_path = (
            Path(__file__).parent.parent / ".github" / "workflows" / "pm-daily-status.yml"
        )
        assert workflow_path.exists(), "PM Daily Status workflow file must exist"

    def test_workflow_has_generate_status_step(self) -> None:
        """Test that workflow has the 'Generate status report' step."""
        workflow_data = load_workflow_file()

        # This should not raise if the step exists
        find_generate_status_step(workflow_data)

    def test_generate_status_step_has_env_block(self) -> None:
        """Test that the generate status step has an env block."""
        workflow_data = load_workflow_file()
        status_step = find_generate_status_step(workflow_data)

        assert "env" in status_step, "Generate status step must have 'env' block"

    def test_gh_token_environment_variable_exists(self) -> None:
        """
        Test that GH_TOKEN environment variable is defined in generate status step.

        This is the critical test for Issue #3 Fix #1.
        Without GH_TOKEN, the gh CLI commands will fail with authentication errors.

        Expected: GH_TOKEN should be set to ${{ secrets.GITHUB_TOKEN }}
        """
        workflow_data = load_workflow_file()
        status_step = find_generate_status_step(workflow_data)

        env_vars = status_step.get("env", {})
        assert "GH_TOKEN" in env_vars, (
            "GH_TOKEN environment variable must be defined in 'Generate status report' step. "
            "This is required for GitHub CLI (gh) authentication. "
            "Without it, the workflow will fail with authentication errors."
        )

    def test_gh_token_uses_github_token_secret(self) -> None:
        """
        Test that GH_TOKEN is set to the correct GitHub token secret.

        Verifies the token source is ${{ secrets.GITHUB_TOKEN }}.
        """
        workflow_data = load_workflow_file()
        status_step = find_generate_status_step(workflow_data)

        env_vars = status_step.get("env", {})
        gh_token = env_vars.get("GH_TOKEN", "")

        assert "${{ secrets.GITHUB_TOKEN }}" in str(gh_token), (
            f"GH_TOKEN must be set to ${{{{ secrets.GITHUB_TOKEN }}}}. Current value: {gh_token}"
        )

    def test_anthropic_api_key_still_present(self) -> None:
        """
        Test that ANTHROPIC_API_KEY is still present after adding GH_TOKEN.

        Regression test: ensure we didn't accidentally remove existing env vars.
        """
        workflow_data = load_workflow_file()
        status_step = find_generate_status_step(workflow_data)

        env_vars = status_step.get("env", {})
        assert "ANTHROPIC_API_KEY" in env_vars, (
            "ANTHROPIC_API_KEY must still be present (regression test)"
        )

    def test_issue_number_still_present(self) -> None:
        """
        Test that ISSUE_NUMBER is still present after adding GH_TOKEN.

        Regression test: ensure we didn't accidentally remove existing env vars.
        """
        workflow_data = load_workflow_file()
        status_step = find_generate_status_step(workflow_data)

        env_vars = status_step.get("env", {})
        assert "ISSUE_NUMBER" in env_vars, "ISSUE_NUMBER must still be present (regression test)"

    def test_workflow_has_correct_permissions(self) -> None:
        """
        Test that workflow has minimal required permissions.

        Security test: verify principle of least privilege.
        """
        workflow_data = load_workflow_file()
        permissions = workflow_data.get("permissions", {})

        assert "contents" in permissions, "Must have contents permission"
        assert permissions["contents"] == "read", "Contents should be read-only"

        assert "issues" in permissions, "Must have issues permission"
        assert permissions["issues"] == "write", "Issues needs write for commenting"


class TestPMDailyStatusWorkflowIntegration:
    """Integration tests for the complete workflow behavior."""

    def test_all_required_env_vars_present(self) -> None:
        """
        Integration test: All three required environment variables are present.

        Tests the complete environment configuration for the generate status step.
        """
        workflow_data = load_workflow_file()
        status_step = find_generate_status_step(workflow_data)

        env_vars = status_step.get("env", {})

        required_vars = ["ANTHROPIC_API_KEY", "ISSUE_NUMBER", "GH_TOKEN"]
        for var in required_vars:
            assert var in env_vars, f"Required environment variable '{var}' must be present"

    def test_env_vars_use_correct_sources(self) -> None:
        """
        Integration test: Environment variables use appropriate secret/var sources.

        - ANTHROPIC_API_KEY should use secrets
        - ISSUE_NUMBER should use vars
        - GH_TOKEN should use secrets
        """
        workflow_data = load_workflow_file()
        status_step = find_generate_status_step(workflow_data)

        env_vars = status_step.get("env", {})

        # Check sources
        assert "secrets.ANTHROPIC_API_KEY" in str(env_vars.get("ANTHROPIC_API_KEY", "")), (
            "ANTHROPIC_API_KEY should come from secrets"
        )

        assert "vars.PM_STATUS_ISSUE_NUMBER" in str(env_vars.get("ISSUE_NUMBER", "")), (
            "ISSUE_NUMBER should come from vars"
        )

        assert "secrets.GITHUB_TOKEN" in str(env_vars.get("GH_TOKEN", "")), (
            "GH_TOKEN should come from secrets"
        )
