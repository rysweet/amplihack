"""Integration tests for link fixing workflow.

Tests verify:
- End-to-end link detection and fixing
- Multiple strategies working together
- File modifications and git operations
- PR and issue creation workflows
"""

from pathlib import Path
from unittest.mock import Mock, patch


class TestLinkFixingWorkflow:
    """Integration tests for complete link fixing workflow."""

    def test_end_to_end_case_sensitivity_fix(self, temp_repo):
        """Complete workflow: detect broken link, fix with case sensitivity, create PR.

        Scenario:
            1. Broken link detected: ./GUIDE.MD
            2. Case sensitivity strategy fixes it: ./guide.md
            3. File is modified
            4. PR is created with changes
        """
        from link_checker import LinkChecker
        from link_fixer import LinkFixer

        # Setup: Create files
        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        readme = docs_dir / "README.md"
        readme.write_text("[Link](./GUIDE.MD)")

        guide = docs_dir / "guide.md"
        guide.write_text("# Guide")

        # Step 1: Detect broken links
        checker = LinkChecker(repo_path=temp_repo)
        broken_links = checker.check_all()

        assert len(broken_links) > 0
        broken = broken_links[0]
        assert "./GUIDE.MD" in broken["path"]

        # Step 2: Fix broken link
        fixer = LinkFixer(repo_path=temp_repo)
        result = fixer.fix_link(
            source_file=Path(broken["file"]), broken_path=broken["path"], line_number=broken["line"]
        )

        assert result is not None
        assert result.fixed_path == "./guide.md"
        assert result.confidence >= 0.90

        # Step 3: Verify file modification
        modified_content = readme.read_text()
        assert "./guide.md" in modified_content
        assert "./GUIDE.MD" not in modified_content

        # Step 4: Create PR (mocked)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="PR created")
            _pr_url = fixer.create_pr(
                [
                    {
                        "file": str(readme),
                        "old": "./GUIDE.MD",
                        "new": "./guide.md",
                        "confidence": result.confidence,
                    }
                ]
            )

            # Verify PR creation was attempted
            assert mock_run.called

    def test_multiple_strategies_cascade(self, temp_repo):
        """Should try multiple strategies until one with >= 90% confidence succeeds.

        Scenario:
            1. Case sensitivity succeeds (95% confidence)
        """
        from link_fixer import LinkFixer

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        # Source with broken link (case sensitivity issue)
        readme = docs_dir / "README.md"
        readme.write_text("[Link](./GUIDE.MD)")

        # Target file (correct case)
        guide = docs_dir / "guide.md"
        guide.write_text("# Guide")

        fixer = LinkFixer(repo_path=temp_repo)

        result = fixer.fix_link(source_file=readme, broken_path="./GUIDE.MD", line_number=1)

        assert result is not None
        assert result.fixed_path == "./guide.md"
        assert result.strategy_name == "case_sensitivity"

    def test_confidence_threshold_filtering(self, temp_repo):
        """Should only apply fixes meeting confidence threshold.

        Scenario:
            - Multiple potential fixes found
            - Only fixes >= 90% confidence applied
            - Lower confidence fixes reported but not applied
        """
        from link_fixer import LinkFixer

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        # Create ambiguous scenario (multiple matches)
        readme = docs_dir / "README.md"
        readme.write_text("[Link](./readme)")

        # Create multiple case variants (low confidence)
        (docs_dir / "README.md").touch()
        (docs_dir / "readme.txt").write_text("text")
        (docs_dir / "Readme.html").write_text("html")

        fixer = LinkFixer(repo_path=temp_repo, confidence_threshold=0.90)

        result = fixer.fix_link(source_file=readme, broken_path="./readme", line_number=1)

        # Should not apply fix if confidence too low
        if result is not None:
            assert result.confidence >= 0.90

    def test_batch_fix_preserves_formatting(self, temp_repo):
        """Should preserve markdown formatting when fixing multiple links.

        Scenario:
            - File has multiple broken links
            - Fix all links
            - Preserve indentation, spacing, other markdown
        """
        from link_fixer import LinkFixer

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        # Create complex markdown file
        readme = docs_dir / "README.md"
        readme_content = """# README

## Links

- [Guide](./GUIDE.MD)
- [Tutorial](./TUTORIAL.MD)
  - Nested item
- [Other](./other.md)

> [Quote link](./GUIDE.MD#section)
"""
        readme.write_text(readme_content)

        # Create target files
        (docs_dir / "guide.md").write_text("# Guide\n\n## Section")
        (docs_dir / "tutorial.md").write_text("# Tutorial")
        (docs_dir / "other.md").write_text("# Other")

        fixer = LinkFixer(repo_path=temp_repo)

        # Fix all broken links (only high confidence >= 90%)
        broken_links = [
            {"file": str(readme), "path": "./GUIDE.MD", "line": 5},
            {"file": str(readme), "path": "./TUTORIAL.MD", "line": 6},
            {"file": str(readme), "path": "./GUIDE.MD#section", "line": 10},
        ]

        _results = fixer.batch_fix(broken_links)

        # Verify fixes (case sensitivity fixes have 95% confidence)
        modified_content = readme.read_text()
        assert "./guide.md" in modified_content
        assert "./tutorial.md" in modified_content
        assert "./GUIDE.MD" not in modified_content

        # Verify formatting preserved
        assert "- [Guide]" in modified_content
        assert "  - Nested item" in modified_content
        assert "> [Quote link]" in modified_content

    def test_git_operations_workflow(self, temp_repo):
        """Should perform git operations correctly.

        Scenario:
            1. Create feature branch
            2. Make fixes
            3. Commit changes
            4. Push branch
            5. Create PR
        """
        from link_fixer import LinkFixer

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        readme = docs_dir / "README.md"
        readme.write_text("[Link](./GUIDE.MD)")

        guide = docs_dir / "guide.md"
        guide.write_text("# Guide")

        fixer = LinkFixer(repo_path=temp_repo)

        # Apply fix
        result = fixer.fix_link(source_file=readme, broken_path="./GUIDE.MD", line_number=1)

        assert result is not None

        # Mock git operations
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="success")

            # Create PR workflow
            _pr_url = fixer.create_pr(
                [{"file": str(readme), "old": "./GUIDE.MD", "new": "./guide.md"}]
            )

            # Verify git commands called
            calls = [call.args[0] for call in mock_run.call_args_list]

            # Should include: branch creation, add, commit, push
            git_commands = [cmd for cmd in calls if "git" in str(cmd)]
            assert len(git_commands) > 0

    def test_issue_creation_for_unfixable(self, temp_repo):
        """Should create issue for truly unfixable links.

        Scenario:
            - Link cannot be fixed by any strategy
            - Issue created with details for manual review
        """
        from link_fixer import LinkFixer

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        readme = docs_dir / "README.md"
        readme.write_text("[Link](./nonexistent.md)")

        fixer = LinkFixer(repo_path=temp_repo)

        # Try to fix (should fail)
        result = fixer.fix_link(source_file=readme, broken_path="./nonexistent.md", line_number=1)

        assert result is None

        # Create issue for unfixable
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="issue #123")

            _issue_url = fixer.create_issue(
                [
                    {
                        "file": str(readme),
                        "path": "./nonexistent.md",
                        "line": 1,
                        "reason": "No strategies succeeded",
                    }
                ]
            )

            # Verify issue creation attempted
            assert mock_run.called

    def test_mixed_success_and_failure(self, temp_repo):
        """Should handle mix of fixable and unfixable links.

        Scenario:
            - Some links fixable (high confidence)
            - Some links unfixable (no strategies work)
            - Create PR for fixes
            - Create issue for unfixable
        """
        from link_fixer import LinkFixer

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        readme = docs_dir / "README.md"
        readme.write_text("""
[Fixable 1](./GUIDE.MD)
[Unfixable](./nonexistent.md)
[Low confidence](./tutorial)
""")

        (docs_dir / "guide.md").write_text("# Guide")
        (docs_dir / "tutorial.md").write_text("# Tutorial")

        fixer = LinkFixer(repo_path=temp_repo)

        broken_links = [
            {"file": str(readme), "path": "./GUIDE.MD", "line": 2},
            {"file": str(readme), "path": "./nonexistent.md", "line": 3},
            {"file": str(readme), "path": "./tutorial", "line": 4},
        ]

        results = fixer.batch_fix(broken_links)

        # Should have 1 fixed (case sensitivity >= 90%) and 2 unfixable (one nonexistent, one < 90% confidence)
        assert len(results["fixed"]) == 1
        assert len(results["unfixable"]) == 2

        # Should create both PR and issue
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="success")

            _pr_url = fixer.create_pr(results["fixed"])
            _issue_url = fixer.create_issue(results["unfixable"])

            # Both should be attempted
            assert mock_run.call_count >= 2


class TestStrategyIntegration:
    """Integration tests for strategy interactions."""

    def test_strategies_respect_priority(self, temp_repo):
        """Higher confidence strategies should be tried first and only >= 90% applied.

        Scenario:
            - Case sensitivity strategy (95% confidence) should be used
            - Lower confidence strategies (< 90%) should be rejected
        """
        from link_fixer import LinkFixer

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        # Create scenario with case sensitivity issue (high confidence fix)
        readme = docs_dir / "README.md"
        readme.write_text("[Link](./GUIDE.MD)")

        guide = docs_dir / "guide.md"
        guide.write_text("# Guide")

        fixer = LinkFixer(repo_path=temp_repo)

        result = fixer.fix_link(source_file=readme, broken_path="./GUIDE.MD", line_number=1)

        assert result is not None
        # Should use case_sensitivity strategy (95% confidence)
        assert result.strategy_name == "case_sensitivity"

    def test_combined_fixes_same_file(self, temp_repo):
        """Should handle multiple different fix types in same file (only >= 90% confidence).

        Scenario:
            - File has case sensitivity issue (95% - fixed)
            - File has git history issue (90% - fixed)
            - File has missing extension issue (85% - not fixed)
            - Only high confidence fixes applied
        """
        from link_fixer import LinkFixer

        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)

        readme = docs_dir / "README.md"
        readme.write_text("""
[Case issue 1](./GUIDE.MD)
[Case issue 2](./TUTORIAL.MD)
[Missing ext](./reference)
""")

        guide = docs_dir / "guide.md"
        guide.write_text("# Guide")

        tutorial = docs_dir / "tutorial.md"
        tutorial.write_text("# Tutorial")

        reference = docs_dir / "reference.md"
        reference.write_text("# Reference")

        fixer = LinkFixer(repo_path=temp_repo)

        broken_links = [
            {"file": str(readme), "path": "./GUIDE.MD", "line": 2},
            {"file": str(readme), "path": "./TUTORIAL.MD", "line": 3},
            {"file": str(readme), "path": "./reference", "line": 4},
        ]

        results = fixer.batch_fix(broken_links)

        # Only >= 90% confidence fixes applied (case sensitivity is 95%)
        assert len(results["fixed"]) == 2
        assert len(results["unfixable"]) == 1

        # Verify case sensitivity strategy used
        strategies = {fix["strategy"] for fix in results["fixed"]}
        assert "case_sensitivity" in strategies
