"""
Test suite for platform-specific commands in SIMPLIFIED_WORKFLOW.md.

Tests validate:
- GitHub CLI commands (gh) for issue creation, PR creation, merge
- Azure DevOps CLI commands (az) for work item creation, PR creation, merge
- Command syntax correctness
- Security-safe command patterns
- Platform-agnostic guidance where applicable
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


def extract_step_content(workflow_content: str, step_num: int) -> str:
    """Extract content of a specific step"""
    pattern = rf"##\s+Step {step_num}:.*?(?=##\s+Step \d+:|##\s+[^S]|\Z)"
    match = re.search(pattern, workflow_content, re.DOTALL)
    assert match, f"Could not extract Step {step_num} content"
    return match.group(0)


class TestStep3IssueCreation:
    """Test Step 3: Create Tracking Issue - platform-specific commands"""

    def test_step3_includes_github_issue_command(self, workflow_content):
        """Step 3 must include GitHub issue creation command"""
        step3 = extract_step_content(workflow_content, 3)

        assert re.search(r"gh issue create", step3), "Step 3 must include 'gh issue create' command"

    def test_step3_includes_azure_devops_workitem_command(self, workflow_content):
        """Step 3 must include Azure DevOps work item creation command"""
        step3 = extract_step_content(workflow_content, 3)

        assert re.search(r"az boards work-item create", step3), (
            "Step 3 must include 'az boards work-item create' command"
        )

    def test_step3_github_command_has_required_flags(self, workflow_content):
        """GitHub issue command should have title and body flags"""
        step3 = extract_step_content(workflow_content, 3)

        gh_commands = re.findall(r"gh issue create[^\n]+", step3)
        assert len(gh_commands) > 0, "No gh issue create commands found"

        # Check at least one has --title or -t
        has_title = any(re.search(r"--title|-t", cmd) for cmd in gh_commands)
        assert has_title, "gh issue create should include --title or -t flag"

    def test_step3_azure_command_has_required_flags(self, workflow_content):
        """Azure DevOps work item command should have title and type"""
        step3 = extract_step_content(workflow_content, 3)

        az_commands = re.findall(r"az boards work-item create[^\n]+", step3)
        assert len(az_commands) > 0, "No az boards work-item create commands found"

        # Check for --title and --type flags
        has_title = any(re.search(r"--title", cmd) for cmd in az_commands)
        has_type = any(re.search(r"--type", cmd) for cmd in az_commands)

        assert has_title and has_type, (
            "az boards work-item create should include --title and --type flags"
        )


class TestStep11CommitAndPR:
    """Test Step 11: Commit Changes + Create PR - platform-specific commands"""

    def test_step11_includes_git_commit(self, workflow_content):
        """Step 11 must include git commit command"""
        step11 = extract_step_content(workflow_content, 11)

        assert re.search(r"git commit", step11), "Step 11 must include 'git commit' command"

    def test_step11_git_commit_uses_safe_patterns(self, workflow_content):
        """Step 11 git commit must use safe patterns (-F or quoted -m)"""
        step11 = extract_step_content(workflow_content, 11)

        git_commits = re.findall(r"git commit[^\n]+", step11)
        if git_commits:
            # Each commit should use -F flag or quoted message
            for cmd in git_commits:
                is_safe = bool(re.search(r'-F\s+|-m\s+"|-m\s+\'', cmd))
                assert is_safe, f"git commit must use -F flag or quoted message: {cmd}"

    def test_step11_includes_github_pr_command(self, workflow_content):
        """Step 11 must include GitHub PR creation command"""
        step11 = extract_step_content(workflow_content, 11)

        assert re.search(r"gh pr create", step11), "Step 11 must include 'gh pr create' command"

    def test_step11_includes_azure_devops_pr_command(self, workflow_content):
        """Step 11 must include Azure DevOps PR creation command"""
        step11 = extract_step_content(workflow_content, 11)

        assert re.search(r"az repos pr create", step11), (
            "Step 11 must include 'az repos pr create' command"
        )

    def test_step11_github_pr_has_required_flags(self, workflow_content):
        """GitHub PR command should have title and body flags"""
        step11 = extract_step_content(workflow_content, 11)

        gh_pr_commands = re.findall(r"gh pr create[^\n]+", step11)
        assert len(gh_pr_commands) > 0, "No gh pr create commands found"

        # Check for --title or -t
        has_title = any(re.search(r"--title|-t", cmd) for cmd in gh_pr_commands)
        assert has_title, "gh pr create should include --title or -t flag"

    def test_step11_azure_pr_has_required_flags(self, workflow_content):
        """Azure DevOps PR command should have title"""
        step11 = extract_step_content(workflow_content, 11)

        az_pr_commands = re.findall(r"az repos pr create[^\n]+", step11)
        assert len(az_pr_commands) > 0, "No az repos pr create commands found"

        # Check for --title
        has_title = any(re.search(r"--title", cmd) for cmd in az_pr_commands)
        assert has_title, "az repos pr create should include --title flag"


class TestStep15Merge:
    """Test Step 15: Final Verification and Merge - platform-specific commands"""

    def test_step15_includes_github_merge_command(self, workflow_content):
        """Step 15 must include GitHub merge command"""
        step15 = extract_step_content(workflow_content, 15)

        assert re.search(r"gh pr merge", step15), "Step 15 must include 'gh pr merge' command"

    def test_step15_includes_azure_devops_merge_command(self, workflow_content):
        """Step 15 must include Azure DevOps merge command"""
        step15 = extract_step_content(workflow_content, 15)

        # Azure uses "az repos pr update --status completed"
        assert re.search(r"az repos pr update.*completed|az repos pr update.*--status", step15), (
            "Step 15 must include Azure DevOps PR completion command"
        )

    def test_step15_github_merge_has_strategy_options(self, workflow_content):
        """GitHub merge should show merge strategy options"""
        step15 = extract_step_content(workflow_content, 15)

        # Should mention --merge, --squash, or --rebase options
        merge_strategies = [r"--merge", r"--squash", r"--rebase"]
        has_strategy = any(re.search(strategy, step15) for strategy in merge_strategies)

        assert has_strategy, (
            "gh pr merge should show merge strategy options (--merge, --squash, --rebase)"
        )

    def test_step15_azure_merge_sets_status_completed(self, workflow_content):
        """Azure DevOps merge must set status to completed"""
        step15 = extract_step_content(workflow_content, 15)

        az_merge_commands = re.findall(r"az repos pr update[^\n]+", step15)
        if az_merge_commands:
            has_completed = any(
                re.search(r"completed|--status\s+completed", cmd) for cmd in az_merge_commands
            )
            assert has_completed, "az repos pr update should set status to 'completed'"


class TestPlatformGuidance:
    """Test platform selection guidance"""

    def test_explains_platform_choice(self, workflow_content):
        """Workflow should explain how to choose between GitHub and Azure DevOps"""
        # Look for guidance in overview or steps about platform selection
        assert re.search(
            r"GitHub.*Azure DevOps|platform.*depend|choose.*platform",
            workflow_content,
            re.IGNORECASE,
        ), "Should explain platform choice guidance"

    def test_both_platforms_documented(self, workflow_content):
        """Both GitHub and Azure DevOps must be documented"""
        has_github = bool(re.search(r"GitHub|gh\s+", workflow_content))
        has_azure = bool(re.search(r"Azure DevOps|az boards|az repos", workflow_content))

        assert has_github, "GitHub CLI must be documented"
        assert has_azure, "Azure DevOps CLI must be documented"


class TestCommandSafety:
    """Test command safety patterns across all platform commands"""

    def test_no_unquoted_variables(self, workflow_content):
        """Platform commands must not use unquoted variables"""
        # Find all command examples (lines with gh, az, or git)
        command_lines = re.findall(r"^[^\n]*(?:gh|az|git)[^\n]+$", workflow_content, re.MULTILINE)

        for cmd in command_lines:
            # Skip comments and markdown formatting
            if re.match(r"^\s*[#*-]", cmd):
                continue

            # Check for unquoted variables like $VAR (but allow "$VAR")
            unquoted = re.findall(r'(?<!")(\$\w+)(?!")', cmd)
            # Filter out false positives in explanatory text
            if "example" not in cmd.lower() and "unsafe" not in cmd.lower():
                assert len(unquoted) == 0, f"Command has unquoted variables (security risk): {cmd}"

    def test_uses_double_dash_separator(self, workflow_content):
        """Git commands with file paths should use -- separator"""
        # Find git commands with file operations
        git_commands = re.findall(r"git (?:add|restore|checkout|diff)[^\n]+", workflow_content)

        for cmd in git_commands:
            # If command has file paths, should have -- separator
            if re.search(r"\.(md|py|txt|yml|yaml)", cmd):
                assert re.search(r"--\s+", cmd), (
                    f"git command with files should use -- separator: {cmd}"
                )


class TestCommandExamples:
    """Test that command examples are complete and runnable"""

    def test_github_commands_have_no_placeholders(self, workflow_content):
        """GitHub commands should minimize placeholder usage"""
        gh_commands = re.findall(r"gh [^\n]+", workflow_content)

        for cmd in gh_commands:
            # Check for common placeholder patterns
            has_placeholders = bool(re.search(r"<[A-Z_]+>|YOUR_|PLACEHOLDER", cmd))
            # If placeholders exist, they should be in examples/explanations
            if has_placeholders:
                # Context check: should be in example or explanation section
                context_start = max(0, workflow_content.find(cmd) - 100)
                context = workflow_content[context_start : workflow_content.find(cmd)]
                is_example_context = bool(
                    re.search(r"example|template|replace", context, re.IGNORECASE)
                )

                assert is_example_context, (
                    f"Command with placeholders should be marked as example: {cmd}"
                )

    def test_azure_commands_have_no_placeholders(self, workflow_content):
        """Azure DevOps commands should minimize placeholder usage"""
        az_commands = re.findall(r"az (?:boards|repos)[^\n]+", workflow_content)

        for cmd in az_commands:
            # Check for common placeholder patterns
            has_placeholders = bool(re.search(r"<[A-Z_]+>|YOUR_|PLACEHOLDER", cmd))
            # If placeholders exist, they should be in examples/explanations
            if has_placeholders:
                context_start = max(0, workflow_content.find(cmd) - 100)
                context = workflow_content[context_start : workflow_content.find(cmd)]
                is_example_context = bool(
                    re.search(r"example|template|replace", context, re.IGNORECASE)
                )

                assert is_example_context, (
                    f"Command with placeholders should be marked as example: {cmd}"
                )


class TestPlatformConsistency:
    """Test consistency between GitHub and Azure DevOps approaches"""

    def test_issue_creation_covered_for_both(self, workflow_content):
        """Step 3 must cover issue creation for both platforms"""
        step3 = extract_step_content(workflow_content, 3)

        has_gh_issue = bool(re.search(r"gh issue create", step3))
        has_az_workitem = bool(re.search(r"az boards work-item create", step3))

        assert has_gh_issue and has_az_workitem, (
            "Step 3 must cover issue creation for both GitHub and Azure DevOps"
        )

    def test_pr_creation_covered_for_both(self, workflow_content):
        """Step 11 must cover PR creation for both platforms"""
        step11 = extract_step_content(workflow_content, 11)

        has_gh_pr = bool(re.search(r"gh pr create", step11))
        has_az_pr = bool(re.search(r"az repos pr create", step11))

        assert has_gh_pr and has_az_pr, (
            "Step 11 must cover PR creation for both GitHub and Azure DevOps"
        )

    def test_merge_covered_for_both(self, workflow_content):
        """Step 15 must cover merge for both platforms"""
        step15 = extract_step_content(workflow_content, 15)

        has_gh_merge = bool(re.search(r"gh pr merge", step15))
        has_az_merge = bool(re.search(r"az repos pr update.*completed", step15))

        assert has_gh_merge and has_az_merge, (
            "Step 15 must cover merge for both GitHub and Azure DevOps"
        )
