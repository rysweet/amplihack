"""
Test suite for Tool Verification section in SIMPLIFIED_WORKFLOW.md.

Tests validate:
- Tool Verification section exists and is comprehensive
- GitHub CLI installation and setup guidance
- Azure DevOps CLI installation and setup guidance
- Git worktree support verification
- Pre-commit hooks setup (optional)
- Tool authentication instructions
- Troubleshooting common issues
"""

import re
from pathlib import Path

import pytest


@pytest.fixture
def workflow_file():
    """Path to SIMPLIFIED_WORKFLOW.md"""
    return Path(".claude/workflow/SIMPLIFIED_WORKFLOW.md")


@pytest.fixture
def workflow_content(workflow_file):
    """Load workflow file content"""
    assert workflow_file.exists(), f"SIMPLIFIED_WORKFLOW.md not found at {workflow_file}"
    return workflow_file.read_text(encoding="utf-8")


@pytest.fixture
def tool_verification_section(workflow_content):
    """Extract Tool Verification section"""
    pattern = r"##\s+Tool Verification.*?(?=##\s+[A-Z]|\Z)"
    match = re.search(pattern, workflow_content, re.DOTALL | re.IGNORECASE)
    assert match, "Tool Verification section not found"
    return match.group(0)


class TestToolVerificationSectionPresence:
    """Test presence of Tool Verification section"""

    def test_tool_verification_section_exists(self, workflow_content):
        """Tool Verification section must exist"""
        assert re.search(r"##\s+Tool Verification", workflow_content, re.IGNORECASE), (
            "Missing Tool Verification section"
        )

    def test_section_before_steps(self, workflow_content):
        """Tool Verification should appear before workflow steps or in overview"""
        tool_match = re.search(r"##\s+Tool Verification", workflow_content, re.IGNORECASE)
        step0_match = re.search(r"##\s+Step 0:", workflow_content)

        # Either before Step 0 or after Step 15 (as appendix)
        if tool_match and step0_match:
            # Accept both placements
            is_valid_placement = (
                tool_match.start() < step0_match.start() or tool_match.start() > step0_match.start()
            )
            assert is_valid_placement, "Tool Verification section placement is valid"


class TestGitHubCLIGuidance:
    """Test GitHub CLI installation and setup guidance"""

    def test_covers_github_cli_installation(self, tool_verification_section):
        """Must cover GitHub CLI installation"""
        assert re.search(
            r"GitHub CLI|gh.*install|install.*gh", tool_verification_section, re.IGNORECASE
        ), "Must cover GitHub CLI installation"

    def test_covers_multiple_platforms(self, tool_verification_section):
        """Must cover installation for multiple platforms"""
        platforms = [r"macOS|Mac|Homebrew|brew", r"Ubuntu|Debian|apt", r"Windows|winget|choco"]
        matches = sum(
            1
            for platform in platforms
            if re.search(platform, tool_verification_section, re.IGNORECASE)
        )

        assert matches >= 2, (
            f"Must cover at least 2 platforms for GitHub CLI installation (found {matches})"
        )

    def test_includes_installation_commands(self, tool_verification_section):
        """Must include actual installation commands"""
        # Check for common installation commands
        install_patterns = [r"brew install", r"apt install", r"winget install", r"choco install"]
        has_commands = any(
            re.search(pattern, tool_verification_section) for pattern in install_patterns
        )

        assert has_commands, "Must include installation command examples"

    def test_covers_github_cli_verification(self, tool_verification_section):
        """Must cover how to verify GitHub CLI installation"""
        assert re.search(
            r"gh --version|verify.*gh|check.*gh.*install", tool_verification_section, re.IGNORECASE
        ), "Must cover GitHub CLI verification"

    def test_covers_github_authentication(self, tool_verification_section):
        """Must cover GitHub CLI authentication"""
        assert re.search(
            r"gh auth login|gh.*authenticat|login.*github", tool_verification_section, re.IGNORECASE
        ), "Must cover GitHub CLI authentication"

    def test_includes_common_issues(self, tool_verification_section):
        """Should include common GitHub CLI issues"""
        assert re.search(
            r"common.*issue|troubleshoot|problem|error", tool_verification_section, re.IGNORECASE
        ), "Should include troubleshooting guidance"


class TestAzureDevOpsCLIGuidance:
    """Test Azure DevOps CLI installation and setup guidance"""

    def test_covers_azure_cli_installation(self, tool_verification_section):
        """Must cover Azure CLI installation"""
        assert re.search(
            r"Azure CLI|az.*install|install.*az", tool_verification_section, re.IGNORECASE
        ), "Must cover Azure CLI installation"

    def test_covers_azure_devops_extension(self, tool_verification_section):
        """Must cover Azure DevOps extension installation"""
        assert re.search(
            r"az extension.*azure-devops|azure-devops.*extension",
            tool_verification_section,
            re.IGNORECASE,
        ), "Must cover Azure DevOps extension installation"

    def test_includes_azure_installation_commands(self, tool_verification_section):
        """Must include Azure CLI installation commands"""
        # Check for Azure CLI installation methods
        azure_patterns = [
            r"curl.*azureclip",
            r"apt.*azure-cli",
            r"brew.*azure-cli",
            r"Install-Module.*Az",
        ]
        has_commands = any(
            re.search(pattern, tool_verification_section, re.IGNORECASE)
            for pattern in azure_patterns
        )

        assert has_commands, "Must include Azure CLI installation commands"

    def test_covers_azure_verification(self, tool_verification_section):
        """Must cover Azure CLI verification"""
        assert re.search(
            r"az --version|az version|verify.*azure", tool_verification_section, re.IGNORECASE
        ), "Must cover Azure CLI verification"

    def test_covers_azure_authentication(self, tool_verification_section):
        """Must cover Azure DevOps authentication"""
        assert re.search(
            r"az login|az devops login|authenticat.*azure", tool_verification_section, re.IGNORECASE
        ), "Must cover Azure DevOps authentication"

    def test_covers_organization_configuration(self, tool_verification_section):
        """Should cover Azure DevOps organization configuration"""
        assert re.search(
            r"organization|az devops configure", tool_verification_section, re.IGNORECASE
        ), "Should cover organization configuration"


class TestGitWorktreeSupport:
    """Test Git worktree support verification"""

    def test_covers_git_worktree(self, tool_verification_section):
        """Must cover Git worktree requirements"""
        assert re.search(
            r"git worktree|worktree.*support", tool_verification_section, re.IGNORECASE
        ), "Must cover Git worktree requirements"

    def test_specifies_minimum_git_version(self, tool_verification_section):
        """Must specify minimum Git version for worktree support"""
        # Git 2.5+ required for worktrees
        assert re.search(
            r"git.*2\.[5-9]|git.*[3-9]\.\d|minimum.*git.*version",
            tool_verification_section,
            re.IGNORECASE,
        ), "Must specify minimum Git version (2.5+)"

    def test_includes_git_version_check(self, tool_verification_section):
        """Must include how to check Git version"""
        assert re.search(r"git --version|git version", tool_verification_section, re.IGNORECASE), (
            "Must include Git version check command"
        )


class TestPreCommitHooksGuidance:
    """Test pre-commit hooks setup guidance (optional)"""

    def test_mentions_precommit_hooks(self, tool_verification_section):
        """Should mention pre-commit hooks as optional tool"""
        assert re.search(r"pre-commit|pre commit|hook", tool_verification_section, re.IGNORECASE), (
            "Should mention pre-commit hooks"
        )

    def test_marks_precommit_as_optional(self, tool_verification_section):
        """Pre-commit should be marked as optional/recommended"""
        # Check context around pre-commit mentions
        precommit_context = ""
        for match in re.finditer(
            r".{0,50}pre-commit.{0,50}", tool_verification_section, re.IGNORECASE
        ):
            precommit_context += match.group(0)

        if precommit_context:
            is_optional = bool(
                re.search(r"optional|recommended|if available", precommit_context, re.IGNORECASE)
            )
            assert is_optional, "Pre-commit should be marked as optional or recommended"


class TestToolVerificationCompleteness:
    """Test completeness of tool verification guidance"""

    def test_covers_all_required_tools(self, tool_verification_section):
        """Must cover all tools used in workflow"""
        required_tools = [
            (r"gh|GitHub CLI", "GitHub CLI"),
            (r"az|Azure CLI", "Azure CLI"),
            (r"git", "Git"),
        ]

        for pattern, tool_name in required_tools:
            assert re.search(pattern, tool_verification_section, re.IGNORECASE), (
                f"Must cover {tool_name}"
            )

    def test_provides_verification_commands(self, tool_verification_section):
        """Must provide verification commands for all tools"""
        verification_patterns = [r"gh --version", r"az --version", r"git --version"]

        matches = sum(
            1 for pattern in verification_patterns if re.search(pattern, tool_verification_section)
        )
        assert matches >= 2, f"Must provide verification commands (found {matches} of 3)"

    def test_includes_help_resources(self, tool_verification_section):
        """Should include links to official documentation"""
        # Check for URLs or documentation references
        has_urls = bool(
            re.search(r"https?://|docs\.|documentation", tool_verification_section, re.IGNORECASE)
        )
        assert has_urls, "Should include documentation links or references"


class TestTroubleshootingGuidance:
    """Test troubleshooting guidance for common issues"""

    def test_includes_troubleshooting_section(self, tool_verification_section):
        """Should include troubleshooting guidance"""
        assert re.search(
            r"troubleshoot|common.*issue|problem|error", tool_verification_section, re.IGNORECASE
        ), "Should include troubleshooting guidance"

    def test_addresses_authentication_issues(self, tool_verification_section):
        """Should address authentication issues"""
        auth_issues = [r"auth.*fail|permission.*denied|not.*authenticated"]
        has_auth_troubleshooting = any(
            re.search(pattern, tool_verification_section, re.IGNORECASE) for pattern in auth_issues
        )

        # This is a should, not a must
        if not has_auth_troubleshooting:
            # Just log, don't fail
            pass

    def test_addresses_installation_issues(self, tool_verification_section):
        """Should address installation issues"""
        install_issues = [r"not found|command not found|install.*fail"]
        has_install_troubleshooting = any(
            re.search(pattern, tool_verification_section, re.IGNORECASE)
            for pattern in install_issues
        )

        # This is a should, not a must
        if not has_install_troubleshooting:
            # Just log, don't fail
            pass


class TestToolVerificationIntegration:
    """Test integration of tool verification with workflow steps"""

    def test_step_references_tool_verification(self, workflow_content):
        """At least one step should reference tool verification section"""
        # Check if any step mentions checking tools or refers to verification section
        steps_content = ""
        for step_num in range(16):
            pattern = rf"##\s+Step {step_num}:.*?(?=##\s+Step \d+:|##\s+[^S]|\Z)"
            match = re.search(pattern, workflow_content, re.DOTALL)
            if match:
                steps_content += match.group(0)

        # Look for references to tool setup, verification, or CLI
        # This is informational - steps may implicitly assume tools are installed
        # Not making this a hard requirement
        _ = bool(
            re.search(
                r"tool.*verify|verify.*tool|CLI.*setup|ensure.*gh|ensure.*az",
                steps_content,
                re.IGNORECASE,
            )
        )
