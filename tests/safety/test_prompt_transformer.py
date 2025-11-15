"""Unit tests for PromptTransformer module.

Tests all scenarios from the architecture specification:
1. No temp used - return original prompt
2. Simple prompt with no slash commands
3. Single slash command
4. Multiple slash commands
5. Slash command with colons
"""

import unittest
from pathlib import Path

from amplihack.safety.prompt_transformer import PromptTransformer


class TestPromptTransformer(unittest.TestCase):
    """Test suite for PromptTransformer."""

    def setUp(self):
        """Set up test fixtures."""
        self.transformer = PromptTransformer()
        self.target_directory = Path("/home/user/project")

    def test_no_temp_used_returns_original(self):
        """Test Case 1: No temp used - return original prompt unchanged.

        Expected behavior:
        - Prompt returned unchanged when used_temp=False
        """
        original_prompt = "Fix the bug in the authentication module"

        result = self.transformer.transform_prompt(
            original_prompt=original_prompt,
            target_directory=self.target_directory,
            used_temp=False
        )

        self.assertEqual(result, original_prompt)

    def test_simple_prompt_no_slash_commands(self):
        """Test Case 2: Simple prompt with no slash commands.

        Expected behavior:
        - Directory change inserted at start
        - Format: "Change your working directory to <dir>. <prompt>"
        """
        original_prompt = "Fix the bug in the authentication module"

        result = self.transformer.transform_prompt(
            original_prompt=original_prompt,
            target_directory=self.target_directory,
            used_temp=True
        )

        # Verify structure instead of exact path (path resolution varies by OS)
        self.assertIn("Change your working directory to", result)
        self.assertIn("Fix the bug in the authentication module", result)
        self.assertIn(str(self.target_directory.resolve()), result)

    def test_single_slash_command(self):
        """Test Case 3: Single slash command.

        Expected behavior:
        - Directory change inserted after slash command
        - Format: "/cmd Change your working directory to <dir>. <rest>"
        """
        original_prompt = "/amplihack:ultrathink Fix the bug"

        result = self.transformer.transform_prompt(
            original_prompt=original_prompt,
            target_directory=self.target_directory,
            used_temp=True
        )

        # Verify structure
        self.assertTrue(result.startswith("/amplihack:ultrathink"))
        self.assertIn("Change your working directory to", result)
        self.assertIn("Fix the bug", result)
        self.assertIn(str(self.target_directory.resolve()), result)

    def test_multiple_slash_commands(self):
        """Test Case 4: Multiple slash commands.

        Expected behavior:
        - Directory change inserted after all slash commands
        - Format: "/cmd1 /cmd2 Change your working directory to <dir>. <rest>"
        """
        original_prompt = "/analyze /improve Fix stuff"

        result = self.transformer.transform_prompt(
            original_prompt=original_prompt,
            target_directory=self.target_directory,
            used_temp=True
        )

        # Verify structure
        self.assertTrue(result.startswith("/analyze /improve"))
        self.assertIn("Change your working directory to", result)
        self.assertIn("Fix stuff", result)

    def test_slash_command_with_colons(self):
        """Test Case 5: Slash command with colons.

        Expected behavior:
        - Correctly parse slash commands with : separators
        - Format: "/cmd:sub:cmd Change your working directory to <dir>. <rest>"
        """
        original_prompt = "/amplihack:ddd:1-plan Feature X"

        result = self.transformer.transform_prompt(
            original_prompt=original_prompt,
            target_directory=self.target_directory,
            used_temp=True
        )

        # Verify structure
        self.assertTrue(result.startswith("/amplihack:ddd:1-plan"))
        self.assertIn("Change your working directory to", result)
        self.assertIn("Feature X", result)

    def test_slash_command_only_no_remaining_text(self):
        """Test slash command with no remaining text after it."""
        original_prompt = "/amplihack:status"

        result = self.transformer.transform_prompt(
            original_prompt=original_prompt,
            target_directory=self.target_directory,
            used_temp=True
        )

        # Verify structure
        self.assertTrue(result.startswith("/amplihack:status"))
        self.assertIn("Change your working directory to", result)

    def test_whitespace_handling(self):
        """Test proper handling of leading/trailing whitespace."""
        original_prompt = "  /amplihack:ultrathink   Fix the bug  "

        result = self.transformer.transform_prompt(
            original_prompt=original_prompt,
            target_directory=self.target_directory,
            used_temp=True
        )

        # Should strip whitespace appropriately
        self.assertIn("/amplihack:ultrathink", result)
        self.assertIn("Fix the bug", result)
        self.assertIn(str(self.target_directory), result)

    def test_complex_slash_command_with_hyphens(self):
        """Test slash commands with hyphens in the name."""
        original_prompt = "/amplihack:ci-diagnostic-workflow Check PR #123"

        result = self.transformer.transform_prompt(
            original_prompt=original_prompt,
            target_directory=self.target_directory,
            used_temp=True
        )

        # Verify structure
        self.assertTrue(result.startswith("/amplihack:ci-diagnostic-workflow"))
        self.assertIn("Change your working directory to", result)
        self.assertIn("Check PR #123", result)

    def test_target_directory_path_resolution(self):
        """Test that target directory is resolved to absolute path."""
        relative_path = "./some/relative/path"

        result = self.transformer.transform_prompt(
            original_prompt="Fix bug",
            target_directory=relative_path,
            used_temp=True
        )

        # Should contain absolute path
        self.assertIn(str(Path(relative_path).resolve()), result)

    def test_three_consecutive_slash_commands(self):
        """Test three consecutive slash commands."""
        original_prompt = "/analyze /improve /test Run comprehensive checks"

        result = self.transformer.transform_prompt(
            original_prompt=original_prompt,
            target_directory=self.target_directory,
            used_temp=True
        )

        # Verify structure
        self.assertTrue(result.startswith("/analyze /improve /test"))
        self.assertIn("Change your working directory to", result)
        self.assertIn("Run comprehensive checks", result)

    def test_slash_in_remaining_text_not_treated_as_command(self):
        """Test that slash in remaining text is not treated as command."""
        original_prompt = "/analyze Check the src/test.py file"

        result = self.transformer.transform_prompt(
            original_prompt=original_prompt,
            target_directory=self.target_directory,
            used_temp=True
        )

        # src/test.py should be in remaining text, not treated as command
        self.assertTrue(result.startswith("/analyze"))
        self.assertIn("Change your working directory to", result)
        self.assertIn("Check the src/test.py file", result)

    def test_empty_prompt(self):
        """Test behavior with empty prompt."""
        original_prompt = ""

        result = self.transformer.transform_prompt(
            original_prompt=original_prompt,
            target_directory=self.target_directory,
            used_temp=True
        )

        # Should just add directory change
        self.assertIn("Change your working directory to", result)

    def test_prompt_with_only_whitespace(self):
        """Test behavior with whitespace-only prompt."""
        original_prompt = "   \n  \t  "

        result = self.transformer.transform_prompt(
            original_prompt=original_prompt,
            target_directory=self.target_directory,
            used_temp=True
        )

        # Should just add directory change
        self.assertIn("Change your working directory to", result)

    def test_slash_command_with_underscores(self):
        """Test slash commands with underscores in the name."""
        original_prompt = "/amplihack:n_version Implement JWT validation"

        result = self.transformer.transform_prompt(
            original_prompt=original_prompt,
            target_directory=self.target_directory,
            used_temp=True
        )

        # Verify structure
        self.assertTrue(result.startswith("/amplihack:n_version"))
        self.assertIn("Change your working directory to", result)
        self.assertIn("Implement JWT validation", result)

    def test_directory_with_spaces(self):
        """Test target directory path with spaces."""
        dir_with_spaces = Path("/home/user/My Documents/project")

        result = self.transformer.transform_prompt(
            original_prompt="Fix bug",
            target_directory=dir_with_spaces,
            used_temp=True
        )

        # Should include full path with spaces
        self.assertIn(str(dir_with_spaces.resolve()), result)

    def test_extract_slash_commands_regex_patterns(self):
        """Test _extract_slash_commands method with various patterns."""
        test_cases = [
            ("/cmd text", ("/cmd", "text")),
            ("/cmd1 /cmd2 text", ("/cmd1 /cmd2", "text")),
            ("no commands", ("", "no commands")),
            ("/cmd", ("/cmd", "")),
            ("/cmd:sub text", ("/cmd:sub", "text")),
            ("/cmd-name text", ("/cmd-name", "text")),
            ("/cmd_name text", ("/cmd_name", "text")),
        ]

        for prompt, expected in test_cases:
            slash_commands, remaining = self.transformer._extract_slash_commands(prompt)
            self.assertEqual((slash_commands, remaining), expected,
                           f"Failed for input: {prompt}")


if __name__ == '__main__':
    unittest.main()
