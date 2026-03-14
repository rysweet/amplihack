"""
Test suite for Link Checker Exit Code Behavior

Tests verify that the link checker script returns exit code 0 even when
broken links are found, allowing the workflow to complete and create issues.

Following TDD: These tests define the contract and will FAIL before implementation.
"""

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest  # type: ignore[import-not-found]


@pytest.fixture
def link_checker_path() -> Path:
    """Return the path to the link checker script."""
    script_path = Path(__file__).parent.parent / ".github" / "scripts" / "link_checker.py"
    return script_path


class TestLinkCheckerExitCode:
    """Test suite for link checker exit code behavior."""

    def test_link_checker_script_exists(self, link_checker_path: Path) -> None:
        """Test that the link checker script exists."""
        assert link_checker_path.exists(), "Link checker script must exist"

    def test_link_checker_returns_zero_on_success(self, link_checker_path: Path) -> None:
        """
        Test that link checker returns 0 when no broken links are found.

        This is the baseline behavior - should work before and after fix.
        """
        # Import the script as a module
        sys.path.insert(0, str(link_checker_path.parent))

        try:
            import link_checker  # type: ignore[import-not-found]

            # Mock check_all_links to return no broken links
            mock_result = MagicMock()
            mock_result.total_links = 10
            mock_result.valid_links = 10
            mock_result.broken_links = []
            mock_result.warnings = []

            with patch.object(link_checker, "check_all_links", return_value=mock_result):
                with patch.object(link_checker.Path, "cwd", return_value=Path(__file__).parent):
                    exit_code = link_checker.main()

            assert exit_code == 0, "Link checker should return 0 when no broken links found"
        finally:
            sys.path.remove(str(link_checker_path.parent))
            if "link_checker" in sys.modules:
                del sys.modules["link_checker"]

    def test_link_checker_returns_zero_with_broken_links(self, link_checker_path: Path) -> None:
        """
        Test that link checker returns 0 even when broken links are found.

        THIS IS THE CRITICAL TEST FOR ISSUE #3 FIX #2.

        Before fix: Returns 1 when broken links found (workflow fails)
        After fix: Returns 0 always (workflow succeeds, issue gets created)

        This test will FAIL before implementation and PASS after.
        """
        # Import the script as a module
        sys.path.insert(0, str(link_checker_path.parent))

        try:
            import link_checker  # type: ignore[import-not-found]

            # Mock check_all_links to return broken links
            mock_result = MagicMock()
            mock_result.total_links = 10
            mock_result.valid_links = 5
            # Create proper BrokenLink objects instead of dicts
            broken_link = link_checker.BrokenLink(
                file="test.md",
                line=1,
                link_text="broken link",
                link_url="https://broken.example.com",
                error="404 Not Found",
                severity="error",
            )
            mock_result.broken_links = [broken_link]
            mock_result.warnings = []

            with patch.object(link_checker, "check_all_links", return_value=mock_result):
                with patch.object(link_checker.Path, "cwd", return_value=Path(__file__).parent):
                    with patch.object(link_checker.Path, "write_text"):  # Mock file writing
                        exit_code = link_checker.main()

            assert exit_code == 0, (
                "Link checker MUST return 0 even when broken links are found. "
                "This allows the workflow to complete and create a GitHub issue. "
                "Without this fix, the workflow fails and the issue creation step never runs."
            )
        finally:
            sys.path.remove(str(link_checker_path.parent))
            if "link_checker" in sys.modules:
                del sys.modules["link_checker"]

    def test_link_checker_returns_zero_with_warnings(self, link_checker_path: Path) -> None:
        """
        Test that link checker returns 0 when warnings are found.

        Warnings should not cause workflow failure.
        """
        # Import the script as a module
        sys.path.insert(0, str(link_checker_path.parent))

        try:
            import link_checker  # type: ignore[import-not-found]

            # Mock check_all_links to return warnings
            mock_result = MagicMock()
            mock_result.total_links = 10
            mock_result.valid_links = 10
            mock_result.broken_links = []
            # Create proper BrokenLink object for warning
            warning_link = link_checker.BrokenLink(
                file="test.md",
                line=1,
                link_text="slow link",
                link_url="https://slow.example.com",
                error="Slow response time",
                severity="warning",
            )
            mock_result.warnings = [warning_link]

            with patch.object(link_checker, "check_all_links", return_value=mock_result):
                with patch.object(link_checker.Path, "cwd", return_value=Path(__file__).parent):
                    with patch.object(link_checker.Path, "write_text"):  # Mock file writing
                        exit_code = link_checker.main()

            assert exit_code == 0, "Link checker should return 0 when only warnings found"
        finally:
            sys.path.remove(str(link_checker_path.parent))
            if "link_checker" in sys.modules:
                del sys.modules["link_checker"]

    def test_link_checker_returns_zero_with_broken_and_warnings(
        self, link_checker_path: Path
    ) -> None:
        """
        Test that link checker returns 0 with both broken links and warnings.

        Combined case: broken links + warnings should still return 0.
        """
        # Import the script as a module
        sys.path.insert(0, str(link_checker_path.parent))

        try:
            import link_checker  # type: ignore[import-not-found]

            # Mock check_all_links to return both broken links and warnings
            mock_result = MagicMock()
            mock_result.total_links = 10
            mock_result.valid_links = 5
            # Create proper BrokenLink objects
            broken_link = link_checker.BrokenLink(
                file="test.md",
                line=1,
                link_text="broken link",
                link_url="https://broken.example.com",
                error="404 Not Found",
                severity="error",
            )
            warning_link = link_checker.BrokenLink(
                file="test.md",
                line=2,
                link_text="slow link",
                link_url="https://slow.example.com",
                error="Slow response time",
                severity="warning",
            )
            mock_result.broken_links = [broken_link]
            mock_result.warnings = [warning_link]

            with patch.object(link_checker, "check_all_links", return_value=mock_result):
                with patch.object(link_checker.Path, "cwd", return_value=Path(__file__).parent):
                    with patch.object(link_checker.Path, "write_text"):  # Mock file writing
                        exit_code = link_checker.main()

            assert exit_code == 0, (
                "Link checker must return 0 even with both broken links and warnings"
            )
        finally:
            sys.path.remove(str(link_checker_path.parent))
            if "link_checker" in sys.modules:
                del sys.modules["link_checker"]


class TestLinkCheckerReportGeneration:
    """Test that report generation still works after exit code change."""

    def test_report_generated_when_broken_links_found(self, link_checker_path: Path) -> None:
        """
        Test that broken_links_report.md is still generated when broken links found.

        Regression test: changing exit code shouldn't break report generation.
        """
        sys.path.insert(0, str(link_checker_path.parent))

        try:
            import link_checker  # type: ignore[import-not-found]

            mock_result = MagicMock()
            mock_result.total_links = 10
            mock_result.valid_links = 5
            # Create proper BrokenLink object
            broken_link = link_checker.BrokenLink(
                file="test.md",
                line=1,
                link_text="broken link",
                link_url="https://broken.example.com",
                error="404 Not Found",
                severity="error",
            )
            mock_result.broken_links = [broken_link]
            mock_result.warnings = []

            mock_write = MagicMock()

            with patch.object(link_checker, "check_all_links", return_value=mock_result):
                with patch.object(link_checker.Path, "cwd", return_value=Path(__file__).parent):
                    with patch.object(link_checker, "generate_report", return_value="# Report"):
                        with patch.object(link_checker.Path, "write_text", mock_write):
                            link_checker.main()

            # Verify report was written
            assert mock_write.called, "Report must be generated when broken links are found"
        finally:
            sys.path.remove(str(link_checker_path.parent))
            if "link_checker" in sys.modules:
                del sys.modules["link_checker"]

    def test_results_printed_to_stdout(self, link_checker_path: Path, capsys: Any) -> None:
        """
        Test that results are printed to stdout.

        Regression test: ensure output is still visible in workflow logs.
        """
        sys.path.insert(0, str(link_checker_path.parent))

        try:
            import link_checker  # type: ignore[import-not-found]

            mock_result = MagicMock()
            mock_result.total_links = 10
            mock_result.valid_links = 5
            # Create proper BrokenLink object
            broken_link = link_checker.BrokenLink(
                file="test.md",
                line=1,
                link_text="broken link",
                link_url="https://broken.example.com",
                error="404 Not Found",
                severity="error",
            )
            mock_result.broken_links = [broken_link]
            mock_result.warnings = []

            with patch.object(link_checker, "check_all_links", return_value=mock_result):
                with patch.object(link_checker.Path, "cwd", return_value=Path(__file__).parent):
                    with patch.object(link_checker.Path, "write_text"):
                        link_checker.main()

            captured = capsys.readouterr()
            assert "Total: 10" in captured.out, "Total links must be printed"
            assert "Valid: 5" in captured.out, "Valid links must be printed"
            assert "Broken:" in captured.out, "Broken links count must be printed"
        finally:
            sys.path.remove(str(link_checker_path.parent))
            if "link_checker" in sys.modules:
                del sys.modules["link_checker"]


class TestLinkCheckerBehaviorContract:
    """Test the complete behavior contract of the link checker."""

    def test_main_function_signature(self, link_checker_path: Path) -> None:
        """
        Test that main() function exists and returns int.

        Contract test: ensures the function interface is stable.
        """
        sys.path.insert(0, str(link_checker_path.parent))

        try:
            import link_checker  # type: ignore[import-not-found]

            # Check function exists
            assert hasattr(link_checker, "main"), "main() function must exist"

            # Check it's callable
            assert callable(link_checker.main), "main() must be callable"

            # Mock dependencies and verify return type
            mock_result = MagicMock()
            mock_result.total_links = 0
            mock_result.valid_links = 0
            mock_result.broken_links = []
            mock_result.warnings = []

            with patch.object(link_checker, "check_all_links", return_value=mock_result):
                with patch.object(link_checker.Path, "cwd", return_value=Path(__file__).parent):
                    result = link_checker.main()

            assert isinstance(result, int), "main() must return an integer exit code"
        finally:
            sys.path.remove(str(link_checker_path.parent))
            if "link_checker" in sys.modules:
                del sys.modules["link_checker"]

    def test_exit_code_is_always_zero(self, link_checker_path: Path) -> None:
        """
        Test the fundamental contract: exit code is ALWAYS 0.

        This is the key behavior change for Issue #3 Fix #2.
        The script should always return 0 regardless of findings.
        """
        sys.path.insert(0, str(link_checker_path.parent))

        try:
            import link_checker  # type: ignore[import-not-found]

            # Test multiple scenarios
            scenarios = [
                # (total, valid, broken_count, warnings_count, description)
                (0, 0, 0, 0, "no links"),
                (10, 10, 0, 0, "all valid"),
                (10, 5, 5, 0, "some broken"),
                (10, 0, 10, 0, "all broken"),
                (10, 10, 0, 5, "warnings only"),
                (10, 5, 5, 5, "broken and warnings"),
            ]

            for total, valid, broken_count, warn_count, desc in scenarios:
                mock_result = MagicMock()
                mock_result.total_links = total
                mock_result.valid_links = valid
                # Create proper BrokenLink objects
                mock_result.broken_links = [
                    link_checker.BrokenLink(
                        file=f"test{i}.md",
                        line=i + 1,
                        link_text=f"link {i}",
                        link_url=f"https://test{i}.example.com",
                        error="404 Not Found",
                        severity="error",
                    )
                    for i in range(broken_count)
                ]
                mock_result.warnings = [
                    link_checker.BrokenLink(
                        file=f"test{i}.md",
                        line=i + 1,
                        link_text=f"warning link {i}",
                        link_url=f"https://warning{i}.example.com",
                        error=f"warning{i}",
                        severity="warning",
                    )
                    for i in range(warn_count)
                ]

                with patch.object(link_checker, "check_all_links", return_value=mock_result):
                    with patch.object(link_checker.Path, "cwd", return_value=Path(__file__).parent):
                        with patch.object(link_checker.Path, "write_text"):
                            exit_code = link_checker.main()

                assert exit_code == 0, (
                    f"Exit code must be 0 for scenario: {desc} "
                    f"(total={total}, valid={valid}, broken={broken_count}, warnings={warn_count})"
                )
        finally:
            sys.path.remove(str(link_checker_path.parent))
            if "link_checker" in sys.modules:
                del sys.modules["link_checker"]
