"""Tests for ADO provider support in default-workflow steps 03 and 16.

Verifies that:
- step-03-create-issue detects ADO remotes and uses az boards work-item create
- step-03-create-issue on GitHub remotes still uses gh issue create (unchanged)
- step-03b-extract-issue-number regex matches both GitHub and ADO URL patterns
- step-16-create-draft-pr detects ADO remotes and uses az repos pr create
- Provider detection function (detect_git_provider) is defined in both steps

Fixes #4205.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def workflow_steps():
    """Load and return step commands from default-workflow.yaml."""
    workflow_path = Path("amplifier-bundle/recipes/default-workflow.yaml")
    if not workflow_path.exists():
        pytest.skip("default-workflow.yaml not found")

    with open(workflow_path) as f:
        data = yaml.safe_load(f)

    return {s["id"]: s for s in data["steps"]}


# ============================================================================
# YAML Structure Tests — Provider Detection
# ============================================================================


class TestProviderDetectionInYaml:
    """Verify both step-03 and step-16 contain the provider detection function."""

    def test_step_03_has_detect_git_provider(self, workflow_steps):
        cmd = workflow_steps["step-03-create-issue"]["command"]
        assert "detect_git_provider" in cmd, "step-03 must define detect_git_provider()"

    def test_step_16_has_detect_git_provider(self, workflow_steps):
        cmd = workflow_steps["step-16-create-draft-pr"]["command"]
        assert "detect_git_provider" in cmd, "step-16 must define detect_git_provider()"

    def test_provider_detection_checks_dev_azure_com(self, workflow_steps):
        for step_id in ("step-03-create-issue", "step-16-create-draft-pr"):
            cmd = workflow_steps[step_id]["command"]
            assert "dev.azure.com" in cmd, f"{step_id} must check for dev.azure.com in remote URL"

    def test_provider_detection_checks_visualstudio_com(self, workflow_steps):
        for step_id in ("step-03-create-issue", "step-16-create-draft-pr"):
            cmd = workflow_steps[step_id]["command"]
            assert "visualstudio.com" in cmd, (
                f"{step_id} must check for visualstudio.com in remote URL"
            )

    def test_both_steps_branch_on_ado_provider(self, workflow_steps):
        for step_id in ("step-03-create-issue", "step-16-create-draft-pr"):
            cmd = workflow_steps[step_id]["command"]
            assert (
                'GIT_PROVIDER" = "ado"' in cmd or "GIT_PROVIDER = ado" in cmd or '"ado"' in cmd
            ), f"{step_id} must branch on ado provider"


# ============================================================================
# YAML Structure Tests — step-03 ADO Path
# ============================================================================


class TestStep03AdoPath:
    """Verify step-03 contains the ADO work item creation path."""

    def test_step_03_uses_az_boards_work_item_create(self, workflow_steps):
        cmd = workflow_steps["step-03-create-issue"]["command"]
        assert "az boards work-item create" in cmd, (
            "step-03 must use az boards work-item create for ADO remotes"
        )

    def test_step_03_creates_task_type(self, workflow_steps):
        cmd = workflow_steps["step-03-create-issue"]["command"]
        assert '--type "Task"' in cmd or "--type Task" in cmd, (
            "step-03 ADO path must create work items of type Task"
        )

    def test_step_03_emits_workitems_edit_url(self, workflow_steps):
        cmd = workflow_steps["step-03-create-issue"]["command"]
        assert "_workitems/edit/" in cmd, (
            "step-03 ADO path must emit _workitems/edit/ID for step-03b to parse"
        )

    def test_step_03_ado_idempotency_guard1_checks_existing_item(self, workflow_steps):
        cmd = workflow_steps["step-03-create-issue"]["command"]
        assert "az boards work-item show" in cmd, (
            "step-03 ADO path must check for existing work item (idempotency guard 1)"
        )

    def test_step_03_github_path_still_uses_gh_issue_create(self, workflow_steps):
        cmd = workflow_steps["step-03-create-issue"]["command"]
        assert "gh issue create" in cmd, "step-03 GitHub path must still use gh issue create"

    def test_step_03_label_creation_is_github_only(self, workflow_steps):
        cmd = workflow_steps["step-03-create-issue"]["command"]
        assert "gh label create" in cmd, "Label creation should still exist in GitHub path"
        # Label creation must not appear before the else block (i.e., in ADO path)
        ado_section_end = cmd.find("else")
        label_pos = cmd.find("gh label create")
        assert ado_section_end < label_pos, (
            "gh label create must appear only in the GitHub (else) path, not in ADO path"
        )


# ============================================================================
# YAML Structure Tests — step-03b ADO URL Pattern
# ============================================================================


class TestStep03bAdoUrlPattern:
    """Verify step-03b regex matches both GitHub and ADO URL formats."""

    def test_step_03b_regex_matches_workitems_edit(self, workflow_steps):
        cmd = workflow_steps["step-03b-extract-issue-number"]["command"]
        assert "_workitems/edit" in cmd, (
            "step-03b regex must match ADO _workitems/edit/NNNN pattern"
        )

    def test_step_03b_still_matches_github_issues(self, workflow_steps):
        cmd = workflow_steps["step-03b-extract-issue-number"]["command"]
        # The regex is (issues|_workitems/edit)/[0-9]+ — check for the 'issues' alternative
        assert "issues" in cmd, "step-03b regex must still match GitHub issues/NNNN pattern"

    def test_step_03b_extracts_number_from_ado_url(self):
        """Bash regex extracts numeric ID from ADO work item path."""
        script = r"""
        ISSUE_CREATION="_workitems/edit/4205"
        EXTRACTED=$(printf '%s' "$ISSUE_CREATION" \
            | grep -oE '(issues|_workitems/edit)/[0-9]+' \
            | grep -oE '[0-9]+' | head -1)
        printf '%s' "$EXTRACTED"
        """
        result = subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "4205"

    def test_step_03b_extracts_number_from_github_url(self):
        """Bash regex still extracts numeric ID from GitHub issue URL."""
        script = r"""
        ISSUE_CREATION="https://github.com/org/repo/issues/123"
        EXTRACTED=$(printf '%s' "$ISSUE_CREATION" \
            | grep -oE '(issues|_workitems/edit)/[0-9]+' \
            | grep -oE '[0-9]+' | head -1)
        printf '%s' "$EXTRACTED"
        """
        result = subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "123"

    def test_step_03b_extracts_number_from_full_ado_url(self):
        """Bash regex extracts ID from a full ADO work item URL."""
        script = r"""
        ISSUE_CREATION="https://dev.azure.com/myorg/myproject/_workitems/edit/4205"
        EXTRACTED=$(printf '%s' "$ISSUE_CREATION" \
            | grep -oE '(issues|_workitems/edit)/[0-9]+' \
            | grep -oE '[0-9]+' | head -1)
        printf '%s' "$EXTRACTED"
        """
        result = subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "4205"


# ============================================================================
# YAML Structure Tests — step-16 ADO Path
# ============================================================================


class TestStep16AdoPath:
    """Verify step-16 contains the ADO PR creation path."""

    def test_step_16_uses_az_repos_pr_create(self, workflow_steps):
        cmd = workflow_steps["step-16-create-draft-pr"]["command"]
        assert "az repos pr create" in cmd, "step-16 must use az repos pr create for ADO remotes"

    def test_step_16_ado_pr_uses_draft_flag(self, workflow_steps):
        cmd = workflow_steps["step-16-create-draft-pr"]["command"]
        assert "az repos pr create --draft" in cmd, "step-16 ADO path must create draft PRs"

    def test_step_16_ado_idempotency_checks_existing_pr(self, workflow_steps):
        cmd = workflow_steps["step-16-create-draft-pr"]["command"]
        assert "az repos pr list" in cmd, (
            "step-16 ADO path must check for existing PRs (idempotency guard)"
        )

    def test_step_16_github_path_still_uses_gh_pr_create(self, workflow_steps):
        cmd = workflow_steps["step-16-create-draft-pr"]["command"]
        assert "gh pr create --draft" in cmd, (
            "step-16 GitHub path must still use gh pr create --draft"
        )

    def test_step_16_ado_specifies_source_and_target_branch(self, workflow_steps):
        cmd = workflow_steps["step-16-create-draft-pr"]["command"]
        assert "--source-branch" in cmd, "step-16 ADO path must specify --source-branch"
        assert "--target-branch" in cmd, "step-16 ADO path must specify --target-branch"


# ============================================================================
# Bash logic tests — Provider Detection Function
# ============================================================================


class TestProviderDetectionLogic:
    """Test the detect_git_provider function behavior."""

    DETECT_FUNC = r"""
    detect_git_provider() {
      local remote_url
      remote_url=$(git remote get-url origin 2>/dev/null || echo '')
      if [[ "$remote_url" == *"dev.azure.com"* ]] || [[ "$remote_url" == *"visualstudio.com"* ]]; then
        echo "ado"
      else
        echo "github"
      fi
    }
    """

    def _run(self, script: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_dev_azure_com_remote_returns_ado(self, tmp_path):
        """A remote containing dev.azure.com returns 'ado'."""
        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(tmp_path),
                "remote",
                "add",
                "origin",
                "https://dev.azure.com/myorg/myproject/_git/myrepo",
            ],
            check=True,
            capture_output=True,
        )
        script = f"cd {tmp_path}\n{self.DETECT_FUNC}\ndetect_git_provider"
        result = self._run(script)
        assert result.returncode == 0
        assert result.stdout.strip() == "ado"

    def test_visualstudio_com_remote_returns_ado(self, tmp_path):
        """A remote containing visualstudio.com returns 'ado'."""
        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(tmp_path),
                "remote",
                "add",
                "origin",
                "https://myorg.visualstudio.com/myproject/_git/myrepo",
            ],
            check=True,
            capture_output=True,
        )
        script = f"cd {tmp_path}\n{self.DETECT_FUNC}\ndetect_git_provider"
        result = self._run(script)
        assert result.returncode == 0
        assert result.stdout.strip() == "ado"

    def test_github_com_remote_returns_github(self, tmp_path):
        """A remote containing github.com returns 'github'."""
        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(tmp_path), "remote", "add", "origin", "https://github.com/org/repo"],
            check=True,
            capture_output=True,
        )
        script = f"cd {tmp_path}\n{self.DETECT_FUNC}\ndetect_git_provider"
        result = self._run(script)
        assert result.returncode == 0
        assert result.stdout.strip() == "github"

    def test_no_remote_returns_github(self, tmp_path):
        """A repo with no remote defaults to 'github'."""
        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        script = f"cd {tmp_path}\n{self.DETECT_FUNC}\ndetect_git_provider"
        result = self._run(script)
        assert result.returncode == 0
        assert result.stdout.strip() == "github"
