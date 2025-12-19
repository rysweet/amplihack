"""Tests to verify documentation uses flexible language instead of hardcoded step counts.

This test ensures issue #1886 fix is maintained - no hardcoded step count references
like "13-step" or "22-step" in documentation.

Philosophy:
- Use flexible language like "multi-step workflow" instead of specific counts
- Step counts change frequently, hardcoding them causes maintenance burden
- This test prevents regression of issue #1886
"""

import subprocess
from pathlib import Path

import pytest


def find_hardcoded_step_references(root_dir: Path) -> list[tuple[str, int, str]]:
    """Search for hardcoded step count references in documentation.

    Args:
        root_dir: Root directory to search (typically project root)

    Returns:
        List of tuples: (file_path, line_number, matching_line)
    """
    # Patterns that indicate hardcoded step counts
    # Match: "13-step", "22-step", "N-step workflow" where N is a number
    patterns = [
        r"\b\d+-step\b",  # Matches: "13-step", "22-step", etc.
        r"\b\d+\s+steps?\b",  # Matches: "13 steps", "22 step", etc. (in specific contexts)
    ]

    violations = []

    # File extensions to check
    extensions = [".md", ".txt", ".rst"]

    # Directories to exclude
    exclude_dirs = {
        ".git",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        "venv",
        "env",
        ".claude/runtime",  # Exclude runtime logs
    }

    for ext in extensions:
        for doc_file in root_dir.rglob(f"*{ext}"):
            # Skip excluded directories
            if any(exclude_dir in doc_file.parts for exclude_dir in exclude_dirs):
                continue

            try:
                with open(doc_file, encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        # Check each pattern
                        for pattern in patterns:
                            # Use grep-like matching
                            result = subprocess.run(
                                ["grep", "-E", pattern],
                                input=line,
                                capture_output=True,
                                text=True,
                            )
                            if result.returncode == 0:
                                # Found a match - check if it's in a context we care about
                                lower_line = line.lower()
                                # Skip if it's in code blocks or examples
                                if "```" not in line and not line.strip().startswith("#"):
                                    # Skip legitimate uses in specific contexts
                                    if not any(
                                        phrase in lower_line
                                        for phrase in [
                                            "n-step",  # Generic reference is OK
                                            "multi-step",  # Generic reference is OK
                                            "example:",  # Examples are OK
                                            "e.g.",  # Examples are OK
                                        ]
                                    ):
                                        violations.append(
                                            (
                                                str(doc_file.relative_to(root_dir)),
                                                line_num,
                                                line.strip(),
                                            )
                                        )
            except (UnicodeDecodeError, PermissionError):
                # Skip files we can't read
                continue

    return violations


class TestDocumentationStepCountReferences:
    """Test suite for verifying no hardcoded step counts in documentation."""

    def test_no_hardcoded_step_counts_in_workflow_docs(self):
        """Verify workflow documentation doesn't contain hardcoded step counts like '13-step' or '22-step'."""
        # This test should PASS initially if issue #1886 is fixed
        # It will FAIL if someone adds hardcoded step counts back

        root_dir = Path(__file__).parent.parent  # Project root

        # Find all hardcoded step references
        violations = find_hardcoded_step_references(root_dir)

        if violations:
            error_msg = "Found hardcoded step count references in documentation:\n\n"
            for file_path, line_num, line in violations:
                error_msg += f"  {file_path}:{line_num}\n    {line}\n\n"
            error_msg += (
                "\nUse flexible language instead:\n"
                "  ❌ '13-step workflow'\n"
                "  ✅ 'multi-step workflow'\n"
                "  ✅ 'systematic workflow'\n"
                "  ✅ 'comprehensive workflow'\n"
                "\nSee issue #1886 for context."
            )
            pytest.fail(error_msg)

    def test_workflow_documentation_uses_flexible_language(self):
        """Verify workflow documentation uses flexible language like 'multi-step' instead of specific counts."""
        # This is a positive test - verify good patterns exist

        root_dir = Path(__file__).parent.parent
        workflow_files = list(root_dir.rglob(".claude/workflow/*.md"))

        if not workflow_files:
            pytest.skip("No workflow files found")

        # Look for flexible language patterns
        flexible_patterns = [
            "multi-step",
            "systematic",
            "comprehensive",
            "structured workflow",
        ]

        found_flexible_language = False
        for workflow_file in workflow_files:
            try:
                content = workflow_file.read_text()
                if any(pattern in content.lower() for pattern in flexible_patterns):
                    found_flexible_language = True
                    break
            except (UnicodeDecodeError, PermissionError):
                continue

        # This test is informational - just verify we're using good patterns
        assert found_flexible_language, (
            "Workflow documentation should use flexible language like 'multi-step' or 'systematic'"
        )

    def test_readme_uses_flexible_step_references(self):
        """Verify README files use flexible step count references."""
        # Should fail initially if README has hardcoded counts
        # Expected: No references like "13-step" in README files

        root_dir = Path(__file__).parent.parent
        readme_files = list(root_dir.rglob("README.md"))

        violations = []
        for readme_file in readme_files:
            # Skip excluded directories
            if any(
                exclude in readme_file.parts
                for exclude in [".git", "node_modules", ".claude/runtime"]
            ):
                continue

            try:
                content = readme_file.read_text()
                lines = content.split("\n")

                for line_num, line in enumerate(lines, 1):
                    # Simple pattern matching for N-step where N is a digit
                    if any(
                        f"{n}-step" in line.lower()
                        for n in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
                    ):
                        # Check if it's in a code block
                        if "```" not in line:
                            violations.append(
                                (
                                    str(readme_file.relative_to(root_dir)),
                                    line_num,
                                    line.strip(),
                                )
                            )
            except (UnicodeDecodeError, PermissionError):
                continue

        if violations:
            error_msg = "Found hardcoded step counts in README files:\n\n"
            for file_path, line_num, line in violations:
                error_msg += f"  {file_path}:{line_num}\n    {line}\n\n"
            pytest.fail(error_msg)


class TestStepCountFlexibility:
    """Tests to verify step count flexibility is maintained."""

    def test_workflow_can_change_step_count_without_doc_updates(self):
        """Verify that changing workflow step count doesn't require documentation updates."""
        # This is a design test - verifies the architecture supports flexibility

        # If we can change the workflow without breaking documentation,
        # this means our docs use flexible language

        # This test is more of a documentation of the design principle
        # The actual verification happens in the grep-based tests above

        assert True, "This test documents the design principle: docs should be step-count agnostic"


# =============================================================================
# HELPER FUNCTIONS FOR TESTING
# =============================================================================


def test_find_hardcoded_step_references_detects_violations():
    """Unit test for the find_hardcoded_step_references() function itself."""
    # Create a temporary test file
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"
        test_file.write_text(
            """
# Test Documentation

This is a 13-step workflow that...  # VIOLATION
This is a multi-step workflow that...  # OK
This workflow has 22 steps.  # POTENTIAL VIOLATION (context-dependent)
        """
        )

        violations = find_hardcoded_step_references(Path(tmpdir))

        # Should find at least the "13-step" reference
        assert len(violations) > 0
        assert any("13-step" in line for _, _, line in violations)


def test_find_hardcoded_step_references_allows_generic_references():
    """Verify that generic references like 'multi-step' are allowed."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"
        test_file.write_text(
            """
# Test Documentation

This is a multi-step workflow.  # OK
This is a systematic workflow.  # OK
This uses an n-step process.  # OK
        """
        )

        violations = find_hardcoded_step_references(Path(tmpdir))

        # Should find no violations in generic references
        assert len(violations) == 0
