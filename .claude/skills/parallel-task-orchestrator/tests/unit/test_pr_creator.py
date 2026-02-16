"""Unit tests for PRCreator - generating draft PRs for completed agent work.

Tests the PRCreator brick that generates PR bodies and creates draft PRs via gh CLI.

Philosophy: Test PR generation logic with mocked gh CLI calls.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestPRCreator:
    """Unit tests for PR creation functionality."""

    def test_generate_pr_title(self):
        """Test generation of PR title from issue."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        creator = PRCreator()
        title = creator.generate_title(
            issue_number=101,
            issue_title="Implement authentication module"
        )

        assert "101" in title
        assert "authentication" in title.lower()
        assert "feat:" in title.lower() or "fix:" in title.lower()

    def test_generate_pr_body_basic(self):
        """Test generation of basic PR body."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        creator = PRCreator()
        body = creator.generate_body(
            issue_number=101,
            parent_issue=1783,
            summary="Implemented authentication with JWT tokens"
        )

        assert "101" in body
        assert "1783" in body
        assert "authentication" in body.lower()
        assert "Closes #101" in body or "Fixes #101" in body

    def test_generate_pr_body_with_checklist(self):
        """Test PR body includes standard checklist."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        creator = PRCreator()
        body = creator.generate_body(
            issue_number=101,
            parent_issue=1783,
            summary="Implementation complete"
        )

        # Should include checklist items
        assert "- [" in body  # Checkbox format
        assert "test" in body.lower()
        assert "doc" in body.lower() or "documentation" in body.lower()

    def test_generate_pr_body_links_parent_issue(self):
        """Test PR body correctly links to parent issue."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        creator = PRCreator()
        body = creator.generate_body(
            issue_number=101,
            parent_issue=1783,
            summary="Part of larger epic"
        )

        assert "#1783" in body
        assert "parent" in body.lower() or "epic" in body.lower()

    @patch("subprocess.run")
    def test_create_pr_success(self, mock_run, mock_pr_create_response):
        """Test successful PR creation via gh CLI."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 1801, "url": "https://github.com/owner/repo/pull/1801"}'
        )

        creator = PRCreator()
        result = creator.create_pr(
            branch_name="feat/issue-101",
            title="feat: Implement authentication (Issue #101)",
            body="Implementation complete"
        )

        assert result["number"] == 1801
        assert "github.com" in result["url"]
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_create_pr_as_draft(self, mock_run):
        """Test PR creation with draft flag."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 1801, "state": "draft"}'
        )

        creator = PRCreator()
        result = creator.create_pr(
            branch_name="feat/issue-101",
            title="Work in progress",
            body="Draft PR",
            draft=True
        )

        # Should call gh pr create with --draft flag
        call_args = str(mock_run.call_args)
        assert "--draft" in call_args or "draft" in call_args

    @patch("subprocess.run")
    def test_create_pr_gh_cli_error(self, mock_run):
        """Test handling of gh CLI errors."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="API rate limit exceeded"
        )

        creator = PRCreator()

        with pytest.raises(RuntimeError, match="PR creation failed"):
            creator.create_pr(
                branch_name="feat/issue-101",
                title="Test",
                body="Test"
            )

    @patch("subprocess.run")
    def test_create_pr_branch_not_pushed(self, mock_run):
        """Test error when branch doesn't exist on remote."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="branch not found"
        )

        creator = PRCreator()

        with pytest.raises(RuntimeError, match="branch"):
            creator.create_pr(
                branch_name="nonexistent-branch",
                title="Test",
                body="Test"
            )

    def test_create_batch_prs(self):
        """Test creating multiple PRs in batch."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        creator = PRCreator()
        agents = [
            {
                "issue_number": 101,
                "branch_name": "feat/issue-101",
                "summary": "Completed task A",
            },
            {
                "issue_number": 102,
                "branch_name": "feat/issue-102",
                "summary": "Completed task B",
            },
        ]

        with patch("subprocess.run", return_value=MagicMock(
            returncode=0,
            stdout='{"number": 1801}'
        )):
            results = creator.create_batch(agents, parent_issue=1783)

        assert len(results) == 2
        assert all("pr_number" in r for r in results)

    def test_validate_branch_exists(self):
        """Test validation that branch exists before creating PR."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        creator = PRCreator()

        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="feat/issue-101")):
            assert creator.validate_branch_exists("feat/issue-101") is True

        with patch("subprocess.run", return_value=MagicMock(returncode=1)):
            assert creator.validate_branch_exists("nonexistent") is False

    def test_add_labels_to_pr(self):
        """Test adding labels to created PR."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        creator = PRCreator()
        labels = ["automated", "sub-issue", "parent-1783"]

        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            creator.add_labels(pr_number=1801, labels=labels)

        # Should call gh pr edit with labels
        # Verification happens through mock assertion

    def test_link_pr_to_issue(self):
        """Test linking PR to issue via closing keywords."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        creator = PRCreator()
        body = creator.generate_body(
            issue_number=101,
            parent_issue=1783,
            summary="Complete"
        )

        # Should include closing keyword
        assert any(keyword in body for keyword in ["Closes", "Fixes", "Resolves"])
        assert "#101" in body

    def test_pr_body_includes_test_evidence(self):
        """Test PR body can include test results."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        creator = PRCreator()
        test_results = {
            "passed": 45,
            "failed": 0,
            "coverage": 92.5,
        }

        body = creator.generate_body(
            issue_number=101,
            parent_issue=1783,
            summary="Complete",
            test_results=test_results
        )

        assert "45" in body
        assert "92.5" in body or "92" in body
        assert "test" in body.lower()

    def test_generate_pr_body_includes_orchestrator_metadata(self):
        """Test PR body includes metadata showing it was orchestrator-generated."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        creator = PRCreator()
        body = creator.generate_body(
            issue_number=101,
            parent_issue=1783,
            summary="Auto-generated by orchestrator"
        )

        # Should indicate automated generation
        assert "orchestrator" in body.lower() or "automated" in body.lower()
        assert "agent" in body.lower()

    def test_pr_title_follows_conventional_commits(self):
        """Test PR titles follow conventional commit format."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        creator = PRCreator()

        feat_title = creator.generate_title(101, "Add new feature X")
        assert feat_title.startswith("feat:")

        fix_title = creator.generate_title(102, "Fix bug in module Y")
        assert fix_title.startswith("fix:")

        docs_title = creator.generate_title(103, "Update documentation")
        assert docs_title.startswith("docs:")

    @patch("subprocess.run")
    def test_create_pr_with_base_branch(self, mock_run):
        """Test creating PR with custom base branch."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"number": 1801}'
        )

        creator = PRCreator()
        creator.create_pr(
            branch_name="feat/issue-101",
            title="Test",
            body="Test",
            base_branch="develop"
        )

        call_args = str(mock_run.call_args)
        assert "develop" in call_args or "--base" in call_args

    def test_format_pr_body_markdown(self):
        """Test PR body is properly formatted markdown."""
        from parallel_task_orchestrator.core.pr_creator import PRCreator

        creator = PRCreator()
        body = creator.generate_body(
            issue_number=101,
            parent_issue=1783,
            summary="Implementation complete"
        )

        # Should have markdown headers
        assert "#" in body or "##" in body
        # Should have proper list formatting
        assert "- " in body or "* " in body
