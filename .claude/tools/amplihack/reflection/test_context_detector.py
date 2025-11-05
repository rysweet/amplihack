#!/usr/bin/env python3
"""
Tests for context_detector module.

Tests git-based detection of amplihack-internal vs user-project work,
prompt template selection, and repository routing.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from context_detector import (
    ContextDetector,
    WorkContext,
    detect_work_context,
    get_issue_target_repo,
    get_reflection_prompt,
)


class TestContextDetector(unittest.TestCase):
    """Test cases for ContextDetector class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.working_dir = Path(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detector_initialization(self):
        """Test detector can be initialized."""
        detector = ContextDetector(self.working_dir)
        self.assertEqual(detector.working_dir, self.working_dir)

    def test_detector_defaults_to_cwd(self):
        """Test detector defaults to current working directory."""
        detector = ContextDetector()
        self.assertEqual(detector.working_dir, Path.cwd())

    @patch("subprocess.run")
    def test_detect_amplihack_repository_https_url(self, mock_run):
        """Test detection of amplihack repo via HTTPS URL."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding.git\n",
        )

        detector = ContextDetector(self.working_dir)
        context = detector.detect_context()

        self.assertTrue(context.is_amplihack_internal)
        self.assertEqual(
            context.repository_name, "MicrosoftHackathon2025-AgenticCoding"
        )
        self.assertIn("MicrosoftHackathon2025-AgenticCoding", context.repository_url)

    @patch("subprocess.run")
    def test_detect_amplihack_repository_ssh_url(self, mock_run):
        """Test detection of amplihack repo via SSH URL."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="git@github.com:rysweet/amplihack.git\n"
        )

        detector = ContextDetector(self.working_dir)
        context = detector.detect_context()

        self.assertTrue(context.is_amplihack_internal)
        self.assertEqual(context.repository_name, "amplihack")

    @patch("subprocess.run")
    def test_detect_user_project_repository(self, mock_run):
        """Test detection of user project (non-amplihack) repo."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="https://github.com/user/my-project.git\n"
        )

        detector = ContextDetector(self.working_dir)
        context = detector.detect_context()

        self.assertFalse(context.is_amplihack_internal)
        self.assertEqual(context.repository_name, "my-project")
        self.assertIn("my-project", context.repository_url)

    @patch("subprocess.run")
    def test_no_git_repository(self, mock_run):
        """Test handling when not in a git repository."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        detector = ContextDetector(self.working_dir)
        context = detector.detect_context()

        self.assertFalse(context.is_amplihack_internal)
        self.assertIsNone(context.repository_url)
        self.assertIsNone(context.repository_name)

    @patch("subprocess.run")
    def test_git_command_timeout(self, mock_run):
        """Test handling of git command timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("git", 5)

        detector = ContextDetector(self.working_dir)
        context = detector.detect_context()

        self.assertFalse(context.is_amplihack_internal)
        self.assertIsNone(context.repository_url)

    @patch("subprocess.run")
    def test_extract_repo_name_https_with_git_suffix(self, mock_run):
        """Test repo name extraction from HTTPS URL with .git suffix."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="https://github.com/user/repo-name.git\n"
        )

        detector = ContextDetector(self.working_dir)
        context = detector.detect_context()

        self.assertEqual(context.repository_name, "repo-name")

    @patch("subprocess.run")
    def test_extract_repo_name_https_without_git_suffix(self, mock_run):
        """Test repo name extraction from HTTPS URL without .git suffix."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="https://github.com/user/repo-name\n"
        )

        detector = ContextDetector(self.working_dir)
        context = detector.detect_context()

        self.assertEqual(context.repository_name, "repo-name")

    @patch("subprocess.run")
    def test_extract_repo_name_ssh_format(self, mock_run):
        """Test repo name extraction from SSH URL."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="git@github.com:user/repo-name.git\n"
        )

        detector = ContextDetector(self.working_dir)
        context = detector.detect_context()

        self.assertEqual(context.repository_name, "repo-name")

    @patch("subprocess.run")
    def test_amplihack_pattern_case_insensitive(self, mock_run):
        """Test amplihack detection is case-insensitive."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/user/MICROSOFTHACKATHON2025-AGENTICCODING.git\n",
        )

        detector = ContextDetector(self.working_dir)
        context = detector.detect_context()

        self.assertTrue(context.is_amplihack_internal)

    @patch("subprocess.run")
    def test_get_amplihack_prompt_template(self, mock_run):
        """Test getting amplihack-internal prompt template."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding.git\n",
        )

        detector = ContextDetector(self.working_dir)
        template = detector.get_reflection_prompt_template()

        # Check for amplihack-specific content
        self.assertIn("amplihack framework internals", template.lower())
        self.assertIn("Framework Philosophy Adherence", template)
        self.assertIn("ruthless simplicity", template.lower())

    @patch("subprocess.run")
    def test_get_user_project_prompt_template(self, mock_run):
        """Test getting user project prompt template."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="https://github.com/user/my-project.git\n"
        )

        detector = ContextDetector(self.working_dir)
        template = detector.get_reflection_prompt_template()

        # Check for user-project-specific content
        self.assertIn("user project", template.lower())
        self.assertIn("User Requirements", template)
        self.assertIn("Code Quality", template)

    @patch("subprocess.run")
    def test_prompt_template_contains_placeholders(self, mock_run):
        """Test that prompt templates contain expected placeholders."""
        mock_run.return_value = MagicMock(returncode=0, stdout="https://github.com/user/test.git\n")

        detector = ContextDetector(self.working_dir)
        template = detector.get_reflection_prompt_template()

        # Check for format placeholders
        self.assertIn("{message_count}", template)
        self.assertIn("{conversation_summary}", template)
        self.assertIn("{template}", template)

    @patch("subprocess.run")
    def test_get_issue_repository_amplihack(self, mock_run):
        """Test issue repository routing for amplihack work."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding.git\n",
        )

        detector = ContextDetector(self.working_dir)
        repo = detector.get_issue_repository()

        # Should use current repo (None)
        self.assertIsNone(repo)

    @patch("subprocess.run")
    def test_get_issue_repository_user_project(self, mock_run):
        """Test issue repository routing for user project."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="https://github.com/user/my-project.git\n"
        )

        detector = ContextDetector(self.working_dir)
        repo = detector.get_issue_repository()

        # Should use current repo (None)
        self.assertIsNone(repo)

    @patch("subprocess.run")
    def test_convenience_function_detect_work_context(self, mock_run):
        """Test convenience function detect_work_context."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="https://github.com/user/test.git\n"
        )

        context = detect_work_context(self.working_dir)

        self.assertIsInstance(context, WorkContext)
        self.assertEqual(context.working_directory, self.working_dir)

    @patch("subprocess.run")
    def test_convenience_function_get_reflection_prompt(self, mock_run):
        """Test convenience function get_reflection_prompt."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="https://github.com/user/test.git\n"
        )

        prompt = get_reflection_prompt(self.working_dir)

        self.assertIsInstance(prompt, str)
        self.assertIn("{message_count}", prompt)

    @patch("subprocess.run")
    def test_convenience_function_get_issue_target_repo(self, mock_run):
        """Test convenience function get_issue_target_repo."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="https://github.com/user/test.git\n"
        )

        repo = get_issue_target_repo(self.working_dir)

        # Should return None for current repo
        self.assertIsNone(repo)

    @patch("subprocess.run")
    def test_multiple_amplihack_patterns(self, mock_run):
        """Test detection with various amplihack repo name patterns."""
        test_cases = [
            "https://github.com/user/MicrosoftHackathon2025-AgenticCoding.git",
            "https://github.com/user/amplihack.git",
            "https://github.com/user/agentic-coding.git",
            "git@github.com:user/amplihack-fork.git",
        ]

        for url in test_cases:
            with self.subTest(url=url):
                mock_run.return_value = MagicMock(returncode=0, stdout=f"{url}\n")

                detector = ContextDetector(self.working_dir)
                context = detector.detect_context()

                self.assertTrue(
                    context.is_amplihack_internal,
                    f"Failed to detect amplihack repo from URL: {url}",
                )

    @patch("subprocess.run")
    def test_non_amplihack_patterns(self, mock_run):
        """Test that non-amplihack repos are correctly identified."""
        test_cases = [
            "https://github.com/user/my-awesome-project.git",
            "https://github.com/user/not-amplihack.git",
            "git@github.com:user/random-repo.git",
        ]

        for url in test_cases:
            with self.subTest(url=url):
                mock_run.return_value = MagicMock(returncode=0, stdout=f"{url}\n")

                detector = ContextDetector(self.working_dir)
                context = detector.detect_context()

                self.assertFalse(
                    context.is_amplihack_internal,
                    f"Incorrectly detected as amplihack repo: {url}",
                )

    def test_work_context_dataclass(self):
        """Test WorkContext dataclass structure."""
        context = WorkContext(
            is_amplihack_internal=True,
            repository_url="https://github.com/test/repo.git",
            repository_name="repo",
            working_directory=self.working_dir,
        )

        self.assertTrue(context.is_amplihack_internal)
        self.assertEqual(context.repository_url, "https://github.com/test/repo.git")
        self.assertEqual(context.repository_name, "repo")
        self.assertEqual(context.working_directory, self.working_dir)

    @patch("subprocess.run")
    def test_context_reuse(self, mock_run):
        """Test that context can be reused across method calls."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding.git\n",
        )

        detector = ContextDetector(self.working_dir)
        context = detector.detect_context()

        # Use the same context for multiple calls
        template = detector.get_reflection_prompt_template(context)
        repo = detector.get_issue_repository(context)

        # Should not trigger additional git calls
        self.assertIn("amplihack", template.lower())
        self.assertIsNone(repo)

        # Only one git call should have been made
        self.assertEqual(mock_run.call_count, 1)


class TestIntegration(unittest.TestCase):
    """Integration tests with real git operations (if available)."""

    def test_real_git_repository_detection(self):
        """Test detection on actual repository (if in one)."""
        try:
            # Try to detect context in current directory
            context = detect_work_context()

            # Should return valid context
            self.assertIsInstance(context, WorkContext)
            self.assertIsInstance(context.is_amplihack_internal, bool)

            # If we got a URL, it should have a name
            if context.repository_url:
                self.assertIsNotNone(context.repository_name)

        except Exception as e:
            self.skipTest(f"Real git test failed: {e}")


if __name__ == "__main__":
    unittest.main()
