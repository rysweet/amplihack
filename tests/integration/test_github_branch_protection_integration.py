"""
Integration tests for applying GitHub branch protection to amplihack repository.

TDD Phase: RED - These tests should FAIL initially
- Branch protection not yet applied
- API calls haven't been made
- Verification will fail

Expected to PASS after:
- Phase 3: Protection applied to amplihack main branch
- All 5 settings configured
- Verification confirmed
"""

import json
import subprocess
from typing import Any

import pytest


class TestGitHubCLIAuthentication:
    """Test gh CLI is installed and authenticated."""

    def test_gh_cli_installed(self):
        """Test that gh CLI is installed and available."""
        result = subprocess.run(["gh", "--version"], capture_output=True, text=True, timeout=5)
        assert result.returncode == 0, "gh CLI not installed. Install with: https://cli.github.com/"
        assert "gh version" in result.stdout, f"Unexpected gh version output: {result.stdout}"

    def test_gh_authenticated(self):
        """Test that gh CLI is authenticated to GitHub."""
        result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=5)
        # gh auth status returns 0 if authenticated
        assert result.returncode == 0, (
            f"gh CLI not authenticated. Run: gh auth login\n{result.stderr}"
        )
        assert "Logged in" in result.stdout or "Logged in" in result.stderr, (
            f"gh auth status output unexpected: {result.stdout}\n{result.stderr}"
        )


class TestRepositoryAccess:
    """Test access to amplihack repository."""

    def test_can_access_amplihack_repo(self):
        """Test that we can access the amplihack repository."""
        result = subprocess.run(
            ["gh", "api", "repos/rysweet/amplihack"], capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, (
            f"Cannot access amplihack repository. Check permissions.\n{result.stderr}"
        )

        repo_data = json.loads(result.stdout)
        assert repo_data["full_name"] == "rysweet/amplihack", (
            f"Unexpected repository: {repo_data['full_name']}"
        )

    def test_user_has_admin_permissions(self):
        """Test that authenticated user has admin permissions on amplihack."""
        result = subprocess.run(
            ["gh", "api", "repos/rysweet/amplihack"], capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, f"Failed to fetch repo: {result.stderr}"

        repo_data = json.loads(result.stdout)
        permissions = repo_data.get("permissions", {})

        assert permissions.get("admin") is True, (
            f"User lacks admin permissions on amplihack. "
            f"Current permissions: {permissions}\n"
            f"Branch protection requires admin access."
        )


class TestBranchProtectionConfiguration:
    """Test branch protection configuration on amplihack main branch."""

    @pytest.fixture(scope="class")
    def protection_data(self) -> dict[str, Any]:
        """Fetch current branch protection configuration."""
        result = subprocess.run(
            ["gh", "api", "repos/rysweet/amplihack/branches/main/protection"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            # Protection might not exist yet - return empty dict
            return {}

        return json.loads(result.stdout)

    def test_branch_protection_exists(self, protection_data: dict):
        """Test that branch protection is configured on main branch."""
        assert len(protection_data) > 0, (
            "Branch protection not configured on main branch. "
            "Run protection configuration commands from skill."
        )
        assert "url" in protection_data, "Branch protection response missing URL field"

    def test_required_pull_request_reviews_enabled(self, protection_data: dict):
        """Test that pull request reviews are required."""
        assert "required_pull_request_reviews" in protection_data, (
            "Required pull request reviews not configured. Protection setting 1/5 missing."
        )

        reviews_config = protection_data["required_pull_request_reviews"]
        assert reviews_config is not None, "Reviews config is null"

        # Should require at least 1 review
        review_count = reviews_config.get("required_approving_review_count", 0)
        assert review_count >= 1, f"Expected at least 1 required review, got {review_count}"

    def test_required_status_checks_enabled(self, protection_data: dict):
        """Test that status checks are required."""
        assert "required_status_checks" in protection_data, (
            "Required status checks not configured. Protection setting 2/5 missing."
        )

        status_checks = protection_data["required_status_checks"]
        assert status_checks is not None, "Status checks config is null"

        # Should have contexts (CI checks)
        contexts = status_checks.get("contexts", [])
        assert len(contexts) > 0, (
            "No status check contexts configured. Expected at least CI checks."
        )

        # Verify expected CI checks for amplihack
        expected_checks = [
            "CI / Validate Code",
            "Version Check / Check Version Bump",
        ]

        # At least one expected check should be present
        found_checks = [check for check in expected_checks if check in contexts]
        assert len(found_checks) > 0, (
            f"Expected checks {expected_checks} not found in contexts: {contexts}"
        )

    def test_force_push_disabled(self, protection_data: dict):
        """Test that force pushes are blocked."""
        assert "allow_force_pushes" in protection_data, (
            "Force push setting not configured. Protection setting 3/5 missing."
        )

        force_push_config = protection_data["allow_force_pushes"]
        assert force_push_config is not None, "Force push config is null"

        # Should be disabled (enabled=false means force pushes are blocked)
        assert force_push_config.get("enabled") is False, (
            "Force pushes are not blocked. Expected enabled=false."
        )

    def test_deletion_disabled(self, protection_data: dict):
        """Test that branch deletion is blocked."""
        assert "allow_deletions" in protection_data, (
            "Branch deletion setting not configured. Protection setting 4/5 missing."
        )

        deletion_config = protection_data["allow_deletions"]
        assert deletion_config is not None, "Deletion config is null"

        # Should be disabled (enabled=false means deletions are blocked)
        assert deletion_config.get("enabled") is False, (
            "Branch deletion is not blocked. Expected enabled=false."
        )

    def test_enforce_admins_configuration(self, protection_data: dict):
        """Test that enforce_admins is configured (5/5 protection setting)."""
        assert "enforce_admins" in protection_data, (
            "Enforce admins setting not configured. Protection setting 5/5 missing."
        )

        enforce_config = protection_data["enforce_admins"]
        assert enforce_config is not None, "Enforce admins config is null"

        # Should be explicitly set (true or false)
        assert "enabled" in enforce_config, "Enforce admins config missing 'enabled' field"

        # For amplihack, we expect false to allow flexibility
        # (but test just confirms it's configured, not the specific value)
        assert isinstance(enforce_config["enabled"], bool), (
            f"Enforce admins enabled should be boolean, got {type(enforce_config['enabled'])}"
        )


class TestBranchProtectionEnforcement:
    """Test that branch protection actually blocks forbidden operations."""

    def test_direct_push_to_main_blocked(self):
        """Test that direct pushes to main are blocked by GitHub."""
        # This test requires actually attempting a push, which we can't do in CI
        # Instead, we verify the configuration exists that would block it
        result = subprocess.run(
            ["gh", "api", "repos/rysweet/amplihack/branches/main/protection"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, "Failed to fetch protection"

        protection_data = json.loads(result.stdout)

        # Required PR reviews + status checks = no direct push
        assert "required_pull_request_reviews" in protection_data, (
            "PR requirement missing - direct pushes might not be blocked"
        )
        assert "required_status_checks" in protection_data, (
            "Status checks missing - direct pushes might not be blocked"
        )

    def test_force_push_blocked_by_configuration(self):
        """Test that force push protection is configured."""
        result = subprocess.run(
            ["gh", "api", "repos/rysweet/amplihack/branches/main/protection"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, "Failed to fetch protection"

        protection_data = json.loads(result.stdout)
        force_push = protection_data.get("allow_force_pushes", {})

        # enabled=false means force pushes are blocked
        assert force_push.get("enabled") is False, (
            "Force pushes not blocked - configuration incorrect"
        )

    def test_branch_deletion_blocked_by_configuration(self):
        """Test that branch deletion protection is configured."""
        result = subprocess.run(
            ["gh", "api", "repos/rysweet/amplihack/branches/main/protection"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, "Failed to fetch protection"

        protection_data = json.loads(result.stdout)
        deletion = protection_data.get("allow_deletions", {})

        # enabled=false means deletions are blocked
        assert deletion.get("enabled") is False, (
            "Branch deletion not blocked - configuration incorrect"
        )


class TestVerificationCommands:
    """Test that verification commands from skill work correctly."""

    def test_get_protection_command_works(self):
        """Test gh api GET command for fetching protection."""
        result = subprocess.run(
            ["gh", "api", "repos/rysweet/amplihack/branches/main/protection"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, f"GET protection command failed: {result.stderr}"

        # Should return valid JSON
        try:
            protection_data = json.loads(result.stdout)
            assert isinstance(protection_data, dict), "Protection data should be a dict"
        except json.JSONDecodeError as e:
            pytest.fail(f"GET returned invalid JSON: {e}\n{result.stdout}")

    def test_jq_formatting_works(self):
        """Test that jq can format protection output."""
        # First check if jq is installed
        jq_check = subprocess.run(["which", "jq"], capture_output=True, timeout=5)

        if jq_check.returncode != 0:
            pytest.skip("jq not installed - optional but recommended for verification")

        # Test jq formatting of protection data
        # First get the protection data
        gh_result = subprocess.run(
            ["gh", "api", "repos/rysweet/amplihack/branches/main/protection"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if gh_result.returncode != 0:
            pytest.fail(f"gh api command failed: {gh_result.stderr}")

        # Then pipe to jq
        result = subprocess.run(
            ["jq", "."],
            input=gh_result.stdout,
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, f"jq formatting failed: {result.stderr}"

        # Should return valid formatted JSON
        try:
            json.loads(result.stdout)
        except json.JSONDecodeError as e:
            pytest.fail(f"jq output is not valid JSON: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
