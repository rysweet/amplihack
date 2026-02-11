"""
Integration tests for CI workflow fixes

Tests verify that the complete workflow configurations are correct
and will work end-to-end.

Following TDD: These tests define the integration contract and will FAIL before implementation.
"""

from pathlib import Path
from typing import Any

import yaml


def load_pm_workflow() -> dict[str, Any]:
    """Load PM Daily Status workflow."""
    workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "pm-daily-status.yml"
    with open(workflow_path) as f:
        return yaml.safe_load(f)


def load_link_checker_workflow() -> dict[str, Any]:
    """Load Docs Weekly Link Checker workflow."""
    workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "docs-link-checker.yml"
    with open(workflow_path) as f:
        return yaml.safe_load(f)


class TestPMDailyStatusIntegration:
    """Integration tests for PM Daily Status workflow end-to-end behavior."""

    def test_workflow_can_authenticate_to_github(self) -> None:
        """
        Integration test: Workflow has all components needed for GitHub CLI authentication.

        Tests the complete authentication flow:
        1. Permissions allow API access
        2. GH_TOKEN environment variable is set
        3. Token source is GITHUB_TOKEN secret
        """
        workflow = load_pm_workflow()

        # Check permissions
        permissions = workflow.get("permissions", {})
        assert "contents" in permissions, "Must have contents permission for API"
        assert "issues" in permissions, "Must have issues permission for API"

        # Check GH_TOKEN is set in generate status step
        jobs = workflow.get("jobs", {})
        daily_status = jobs.get("daily-status", {})
        steps = daily_status.get("steps", [])

        status_step = None
        for step in steps:
            if isinstance(step, dict) and "Generate status report" in step.get("name", ""):
                status_step = step
                break

        assert status_step is not None, "Must have generate status step"

        env_vars = status_step.get("env", {})
        assert "GH_TOKEN" in env_vars, "Must have GH_TOKEN for gh CLI"
        assert "${{ secrets.GITHUB_TOKEN }}" in str(env_vars.get("GH_TOKEN")), (
            "GH_TOKEN must use built-in GITHUB_TOKEN secret"
        )

    def test_workflow_can_call_anthropic_api(self) -> None:
        """
        Integration test: Workflow has API key for Claude API calls.

        Regression test: ensure API key is still configured.
        """
        workflow = load_pm_workflow()

        jobs = workflow.get("jobs", {})
        daily_status = jobs.get("daily-status", {})
        steps = daily_status.get("steps", [])

        status_step = None
        for step in steps:
            if isinstance(step, dict) and "Generate status report" in step.get("name", ""):
                status_step = step
                break

        assert status_step is not None, "Must have generate status step"
        env_vars = status_step.get("env", {})
        assert "ANTHROPIC_API_KEY" in env_vars, "Must have ANTHROPIC_API_KEY"

    def test_workflow_has_issue_number_for_posting(self) -> None:
        """
        Integration test: Workflow knows which issue to post to.

        Regression test: ensure issue number variable is configured.
        """
        workflow = load_pm_workflow()

        jobs = workflow.get("jobs", {})
        daily_status = jobs.get("daily-status", {})
        steps = daily_status.get("steps", [])

        status_step = None
        for step in steps:
            if isinstance(step, dict) and "Generate status report" in step.get("name", ""):
                status_step = step
                break

        assert status_step is not None, "Must have generate status step"
        env_vars = status_step.get("env", {})
        assert "ISSUE_NUMBER" in env_vars, "Must have ISSUE_NUMBER"

    def test_workflow_can_post_to_issue(self) -> None:
        """
        Integration test: Workflow has step to post report to GitHub issue.

        Tests the complete reporting flow:
        1. Report is generated
        2. Report is posted to issue
        3. Post step has correct configuration
        """
        workflow = load_pm_workflow()

        jobs = workflow.get("jobs", {})
        daily_status = jobs.get("daily-status", {})
        steps = daily_status.get("steps", [])

        # Find post to issue step
        post_step = None
        for step in steps:
            if isinstance(step, dict) and "Post report to tracking issue" in step.get("name", ""):
                post_step = step
                break

        assert post_step is not None, "Must have step to post to issue"

        # Check it uses the correct action
        assert "uses" in post_step, "Post step must use an action"
        assert "create-or-update-comment" in post_step["uses"], "Must use comment creation action"

        # Check it has correct configuration
        with_config = post_step.get("with", {})
        assert "issue-number" in with_config, "Must specify issue number"
        assert "body-path" in with_config, "Must specify report file path"


class TestLinkCheckerIntegration:
    """Integration tests for Link Checker workflow end-to-end behavior."""

    def test_workflow_calls_link_checker_script(self) -> None:
        """
        Integration test: Workflow has step to run link checker script.
        """
        workflow = load_link_checker_workflow()

        jobs = workflow.get("jobs", {})
        # The job name might vary, find it
        job_name = None
        for name in jobs.keys():
            if "link" in name.lower() or "check" in name.lower():
                job_name = name
                break

        assert job_name is not None, "Must have link checking job"

        steps = jobs[job_name].get("steps", [])

        # Find step that runs link checker
        checker_step = None
        for step in steps:
            if isinstance(step, dict):
                run_cmd = step.get("run", "")
                if "link_checker" in run_cmd:
                    checker_step = step
                    break

        assert checker_step is not None, "Must have step that runs link_checker.py"

    def test_workflow_creates_issue_for_broken_links(self) -> None:
        """
        Integration test: Workflow has step to create/update issue with broken links.

        This is the critical integration for Issue #3 Fix #2.
        The workflow must be able to complete and run the issue creation step.
        """
        workflow = load_link_checker_workflow()

        jobs = workflow.get("jobs", {})
        job_name = None
        for name in jobs.keys():
            if "link" in name.lower() or "check" in name.lower():
                job_name = name
                break

        steps = jobs[job_name].get("steps", [])

        # Find step that creates/updates issue
        issue_step = None
        for step in steps:
            if isinstance(step, dict):
                name = step.get("name", "")
                if "issue" in name.lower():
                    issue_step = step
                    break

        assert issue_step is not None, (
            "Must have step to create/update issue. "
            "This step reports broken links to GitHub issues."
        )

    def test_workflow_succeeds_even_with_broken_links(self) -> None:
        """
        Integration test: Workflow configuration allows success with broken links.

        Key integration point: The link checker script must return 0,
        allowing subsequent steps (like issue creation) to run.

        This test verifies the workflow doesn't have continue-on-error or
        other configurations that would mask the exit code issue.
        """
        workflow = load_link_checker_workflow()

        jobs = workflow.get("jobs", {})
        job_name = None
        for name in jobs.keys():
            if "link" in name.lower() or "check" in name.lower():
                job_name = name
                break

        steps = jobs[job_name].get("steps", [])

        # Find link checker step
        checker_step = None
        for step in steps:
            if isinstance(step, dict):
                run_cmd = step.get("run", "")
                if "link_checker" in run_cmd:
                    checker_step = step
                    break

        # Verify the step doesn't have continue-on-error: true
        # (which would indicate we're papering over the exit code issue)
        continue_on_error = checker_step.get("continue-on-error", False) if checker_step else False

        assert not continue_on_error, (
            "Link checker step should NOT have 'continue-on-error: true'. "
            "Instead, the script itself should return exit code 0. "
            "Using continue-on-error would paper over the real fix."
        )


class TestBothWorkflowsIntegration:
    """Integration tests that both workflows work correctly together."""

    def test_both_workflows_exist(self) -> None:
        """
        Integration test: Both workflow files exist.
        """
        pm_workflow = Path(__file__).parent.parent / ".github" / "workflows" / "pm-daily-status.yml"
        link_workflow = (
            Path(__file__).parent.parent / ".github" / "workflows" / "docs-link-checker.yml"
        )

        assert pm_workflow.exists(), "PM Daily Status workflow must exist"
        assert link_workflow.exists(), "Docs Link Checker workflow must exist"

    def test_both_workflows_use_minimal_permissions(self) -> None:
        """
        Security integration test: Both workflows follow principle of least privilege.
        """
        pm_workflow = load_pm_workflow()
        link_workflow = load_link_checker_workflow()

        # PM workflow permissions
        pm_perms = pm_workflow.get("permissions", {})
        assert pm_perms.get("contents") == "read", "PM workflow: contents should be read"
        assert pm_perms.get("issues") == "write", "PM workflow: issues needs write"

        # Link checker workflow permissions
        link_perms = link_workflow.get("permissions", {})
        assert link_perms.get("contents") == "read", "Link checker: contents should be read"
        # Link checker needs issues:write to create/update issues
        assert link_perms.get("issues") == "write", "Link checker: issues needs write"

    def test_both_workflows_have_manual_triggers(self) -> None:
        """
        Integration test: Both workflows can be manually triggered for testing.
        """
        pm_workflow = load_pm_workflow()
        link_workflow = load_link_checker_workflow()

        # Check workflow_dispatch is in the 'on' triggers
        # Note: YAML parses "on:" as boolean True, not string "on"
        pm_triggers: dict[str, Any] = pm_workflow.get("on") or pm_workflow.get(True) or {}  # type: ignore[misc]
        link_triggers: dict[str, Any] = link_workflow.get("on") or link_workflow.get(True) or {}  # type: ignore[misc]

        assert "workflow_dispatch" in pm_triggers, (
            "PM workflow must support workflow_dispatch for manual testing"
        )

        assert "workflow_dispatch" in link_triggers, (
            "Link checker must support workflow_dispatch for manual testing"
        )

    def test_both_workflows_have_scheduled_runs(self) -> None:
        """
        Integration test: Both workflows run on their defined schedules.
        """
        pm_workflow = load_pm_workflow()
        link_workflow = load_link_checker_workflow()

        # Note: YAML parses "on:" as boolean True, not string "on"
        pm_triggers: dict[str, Any] = pm_workflow.get("on") or pm_workflow.get(True) or {}  # type: ignore[misc]
        link_triggers: dict[str, Any] = link_workflow.get("on") or link_workflow.get(True) or {}  # type: ignore[misc]

        assert "schedule" in pm_triggers, "PM workflow must have scheduled runs"
        assert "schedule" in link_triggers, "Link checker must have scheduled runs"


class TestWorkflowSecurity:
    """Security integration tests for both workflows."""

    def test_pm_workflow_masks_api_key(self) -> None:
        """
        Security test: PM workflow masks ANTHROPIC_API_KEY in logs.
        """
        workflow = load_pm_workflow()

        jobs = workflow.get("jobs", {})
        daily_status = jobs.get("daily-status", {})
        steps = daily_status.get("steps", [])

        # Find mask step
        mask_step = None
        for step in steps:
            if isinstance(step, dict) and "Mask API key" in step.get("name", ""):
                mask_step = step
                break

        assert mask_step is not None, "Must have step to mask API key"
        assert "add-mask" in mask_step.get("run", ""), "Must use add-mask command"

    def test_pm_workflow_disables_command_echo(self) -> None:
        """
        Security test: PM workflow disables command echo to prevent secret leakage.
        """
        workflow = load_pm_workflow()

        jobs = workflow.get("jobs", {})
        daily_status = jobs.get("daily-status", {})
        steps = daily_status.get("steps", [])

        # Find generate status step
        status_step = None
        for step in steps:
            if isinstance(step, dict) and "Generate status report" in step.get("name", ""):
                status_step = step
                break

        # Check that the run command includes 'set +x'
        run_cmd = status_step.get("run", "") if status_step else ""
        assert "set +x" in run_cmd, "Must disable command echo with 'set +x'"

    def test_workflows_have_timeout_limits(self) -> None:
        """
        Security test: Both workflows have timeout limits to prevent runaway execution.
        """
        pm_workflow = load_pm_workflow()
        link_workflow = load_link_checker_workflow()

        pm_jobs = pm_workflow.get("jobs", {})
        link_jobs = link_workflow.get("jobs", {})

        # Check PM workflow
        for job_name, job_config in pm_jobs.items():
            assert "timeout-minutes" in job_config, (
                f"PM workflow job '{job_name}' must have timeout-minutes"
            )

        # Check Link checker workflow
        for job_name, job_config in link_jobs.items():
            assert "timeout-minutes" in job_config, (
                f"Link checker job '{job_name}' must have timeout-minutes"
            )
