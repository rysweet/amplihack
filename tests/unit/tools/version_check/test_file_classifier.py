"""
Unit tests for file_classifier module.

Tests file classification into update strategies:
- ALWAYS_UPDATE: Core framework files
- PRESERVE_IF_MODIFIED: User-customizable files
- NEVER_UPDATE: User-generated content
- Path normalization and edge cases
"""

import sys
from pathlib import Path

# Add .claude/tools/amplihack to path for imports
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent.parent.parent / ".claude" / "tools" / "amplihack")
)

from file_classifier import (
    FileCategory,
    classify_file,
    get_category_description,
)


class TestAlwaysUpdateFiles:
    """Test suite for ALWAYS_UPDATE file classification."""

    def test_always_update_framework_agent(self):
        """Test that framework agent files are always updated."""
        assert classify_file("agents/amplihack/architect.md") == FileCategory.ALWAYS_UPDATE
        assert classify_file("agents/amplihack/builder.md") == FileCategory.ALWAYS_UPDATE
        assert classify_file("agents/amplihack/tester.md") == FileCategory.ALWAYS_UPDATE

    def test_always_update_framework_tools(self):
        """Test that framework tool files are always updated."""
        assert classify_file("tools/amplihack/version_checker.py") == FileCategory.ALWAYS_UPDATE
        assert classify_file("tools/amplihack/file_classifier.py") == FileCategory.ALWAYS_UPDATE
        assert classify_file("tools/amplihack/update_engine.py") == FileCategory.ALWAYS_UPDATE

    def test_always_update_core_context_files(self):
        """Test that core context files are always updated."""
        assert classify_file("context/PHILOSOPHY.md") == FileCategory.ALWAYS_UPDATE
        assert classify_file("context/PATTERNS.md") == FileCategory.ALWAYS_UPDATE
        assert classify_file("context/TRUST.md") == FileCategory.ALWAYS_UPDATE
        assert classify_file("context/AGENT_INPUT_VALIDATION.md") == FileCategory.ALWAYS_UPDATE

    def test_always_update_workflow_files(self):
        """Test that workflow files are always updated (except DEFAULT_WORKFLOW.md)."""
        assert classify_file("workflow/N_VERSION_WORKFLOW.md") == FileCategory.ALWAYS_UPDATE
        assert classify_file("workflow/DEBATE_WORKFLOW.md") == FileCategory.ALWAYS_UPDATE
        assert classify_file("workflow/CASCADE_WORKFLOW.md") == FileCategory.ALWAYS_UPDATE

    def test_always_update_with_claude_prefix(self):
        """Test that files with .claude/ prefix are properly classified."""
        assert classify_file(".claude/agents/amplihack/architect.md") == FileCategory.ALWAYS_UPDATE
        assert (
            classify_file(".claude/tools/amplihack/version_checker.py")
            == FileCategory.ALWAYS_UPDATE
        )
        assert classify_file(".claude/context/PHILOSOPHY.md") == FileCategory.ALWAYS_UPDATE

    def test_always_update_subdirectories(self):
        """Test that subdirectories within framework paths are handled."""
        assert (
            classify_file("agents/amplihack/specialized/knowledge-archaeologist.md")
            == FileCategory.ALWAYS_UPDATE
        )
        assert classify_file("tools/amplihack/memory/storage.py") == FileCategory.ALWAYS_UPDATE


class TestPreserveIfModifiedFiles:
    """Test suite for PRESERVE_IF_MODIFIED file classification."""

    def test_preserve_if_modified_default_workflow(self):
        """Test that DEFAULT_WORKFLOW.md is preserved if modified."""
        assert classify_file("workflow/DEFAULT_WORKFLOW.md") == FileCategory.PRESERVE_IF_MODIFIED
        assert (
            classify_file(".claude/workflow/DEFAULT_WORKFLOW.md")
            == FileCategory.PRESERVE_IF_MODIFIED
        )

    def test_preserve_if_modified_user_preferences(self):
        """Test that user preferences are preserved."""
        assert classify_file("context/USER_PREFERENCES.md") == FileCategory.PRESERVE_IF_MODIFIED
        assert (
            classify_file("context/USER_REQUIREMENT_PRIORITY.md")
            == FileCategory.PRESERVE_IF_MODIFIED
        )

    def test_preserve_if_modified_custom_commands(self):
        """Test that custom commands are preserved."""
        assert classify_file("commands/custom.md") == FileCategory.PRESERVE_IF_MODIFIED
        assert classify_file("commands/my-command.md") == FileCategory.PRESERVE_IF_MODIFIED
        assert classify_file(".claude/commands/ultrathink.md") == FileCategory.PRESERVE_IF_MODIFIED

    def test_preserve_if_modified_hooks(self):
        """Test that hook files are preserved if modified."""
        assert classify_file("tools/amplihack/hooks/start.py") == FileCategory.PRESERVE_IF_MODIFIED
        assert classify_file("tools/amplihack/hooks/stop.py") == FileCategory.PRESERVE_IF_MODIFIED
        assert (
            classify_file(".claude/tools/amplihack/hooks/pre_compact.py")
            == FileCategory.PRESERVE_IF_MODIFIED
        )


class TestNeverUpdateFiles:
    """Test suite for NEVER_UPDATE file classification."""

    def test_never_update_discoveries(self):
        """Test that DISCOVERIES.md is never updated."""
        assert classify_file("context/DISCOVERIES.md") == FileCategory.NEVER_UPDATE
        assert classify_file(".claude/context/DISCOVERIES.md") == FileCategory.NEVER_UPDATE

    def test_never_update_project_info(self):
        """Test that PROJECT.md is never updated."""
        assert classify_file("context/PROJECT.md") == FileCategory.NEVER_UPDATE
        assert classify_file(".claude/context/PROJECT.md") == FileCategory.NEVER_UPDATE

    def test_never_update_docs(self):
        """Test that documentation files are never updated."""
        assert classify_file("docs/README.md") == FileCategory.NEVER_UPDATE
        assert classify_file("docs/api/endpoints.md") == FileCategory.NEVER_UPDATE
        assert (
            classify_file(".claude/docs/document_driven_development/overview.md")
            == FileCategory.NEVER_UPDATE
        )

    def test_never_update_runtime(self):
        """Test that runtime files are never updated."""
        assert classify_file("runtime/logs/session.log") == FileCategory.NEVER_UPDATE
        assert classify_file("runtime/metrics/performance.json") == FileCategory.NEVER_UPDATE
        assert (
            classify_file(".claude/runtime/logs/20251116_test/DECISIONS.md")
            == FileCategory.NEVER_UPDATE
        )

    def test_never_update_ai_working(self):
        """Test that experimental tools are never updated."""
        assert classify_file("ai_working/experiment.py") == FileCategory.NEVER_UPDATE
        assert classify_file("ai_working/tool-name/implementation.py") == FileCategory.NEVER_UPDATE

    def test_never_update_scenarios(self):
        """Test that scenario tools are never updated."""
        assert classify_file("scenarios/analyze-codebase/tool.py") == FileCategory.NEVER_UPDATE
        assert classify_file("scenarios/my-tool/README.md") == FileCategory.NEVER_UPDATE

    def test_never_update_skills(self):
        """Test that user skills are never updated."""
        assert classify_file("skills/custom-skill/skill.md") == FileCategory.NEVER_UPDATE
        assert (
            classify_file(".claude/skills/my-skill/implementation.py") == FileCategory.NEVER_UPDATE
        )


class TestPathNormalization:
    """Test suite for path normalization and handling."""

    def test_path_normalization_forward_slashes(self):
        """Test that paths with forward slashes are handled correctly."""
        assert classify_file("agents/amplihack/architect.md") == FileCategory.ALWAYS_UPDATE

    def test_path_normalization_backslashes(self):
        """Test that paths with backslashes are normalized to forward slashes."""
        # Windows-style paths should be normalized
        assert classify_file("agents\\amplihack\\architect.md") == FileCategory.ALWAYS_UPDATE

    def test_path_normalization_with_path_object(self):
        """Test that Path objects are handled correctly."""
        assert classify_file(Path("agents/amplihack/architect.md")) == FileCategory.ALWAYS_UPDATE
        assert classify_file(Path("context/DISCOVERIES.md")) == FileCategory.NEVER_UPDATE

    def test_path_normalization_leading_claude_removed(self):
        """Test that leading .claude/ is removed for consistent matching."""
        # Both should match the same pattern
        assert classify_file("agents/amplihack/architect.md") == classify_file(
            ".claude/agents/amplihack/architect.md"
        )
        assert classify_file("context/PHILOSOPHY.md") == classify_file(
            ".claude/context/PHILOSOPHY.md"
        )

    def test_path_normalization_relative_paths(self):
        """Test that relative paths are handled correctly."""
        assert classify_file("./agents/amplihack/architect.md") == FileCategory.ALWAYS_UPDATE


class TestEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    def test_edge_case_empty_string(self):
        """Test handling of empty string path."""
        # Empty path should default to PRESERVE_IF_MODIFIED for safety
        result = classify_file("")
        assert result == FileCategory.PRESERVE_IF_MODIFIED

    def test_edge_case_root_file(self):
        """Test handling of file at root level."""
        # File not matching any specific pattern should be preserved
        result = classify_file("random_file.txt")
        assert result == FileCategory.PRESERVE_IF_MODIFIED

    def test_edge_case_hooks_not_in_tools(self):
        """Test that hooks/ pattern only matches within tools/amplihack/."""
        # Should not match hooks in other locations
        result = classify_file("hooks/custom.py")
        assert result == FileCategory.PRESERVE_IF_MODIFIED

    def test_edge_case_similar_directory_names(self):
        """Test that similar directory names don't cause false matches."""
        # "documentation/" should not match "docs/"
        result = classify_file("documentation/guide.md")
        assert result == FileCategory.PRESERVE_IF_MODIFIED

        # "agents/custom/" should not match "agents/amplihack/"
        result = classify_file("agents/custom/my-agent.md")
        assert result == FileCategory.PRESERVE_IF_MODIFIED

    def test_edge_case_file_extension_variations(self):
        """Test that file extensions are handled correctly."""
        assert classify_file("agents/amplihack/architect.md") == FileCategory.ALWAYS_UPDATE
        assert classify_file("tools/amplihack/version_checker.py") == FileCategory.ALWAYS_UPDATE
        assert classify_file("docs/README.rst") == FileCategory.NEVER_UPDATE

    def test_edge_case_deep_nesting(self):
        """Test that deeply nested paths are handled correctly."""
        assert (
            classify_file("agents/amplihack/very/deep/nested/path/file.md")
            == FileCategory.ALWAYS_UPDATE
        )
        assert classify_file("docs/very/deep/nested/path/file.md") == FileCategory.NEVER_UPDATE

    def test_edge_case_partial_matches(self):
        """Test that partial path matches are handled correctly."""
        # "agents/amplihack2/" should not match "agents/amplihack/"
        result = classify_file("agents/amplihack2/custom.md")
        assert result == FileCategory.PRESERVE_IF_MODIFIED

        # "context/PHILOSOPHY.md.bak" should not match "context/PHILOSOPHY.md"
        result = classify_file("context/PHILOSOPHY.md.bak")
        assert result == FileCategory.PRESERVE_IF_MODIFIED

    def test_edge_case_security_path_traversal_attempt(self):
        """Test that path traversal attempts are handled safely."""
        # These should still be classified based on their effective path
        result = classify_file("../agents/amplihack/architect.md")
        assert result == FileCategory.ALWAYS_UPDATE

        result = classify_file("../../docs/README.md")
        assert result == FileCategory.NEVER_UPDATE


class TestGetCategoryDescription:
    """Test suite for get_category_description function."""

    def test_get_category_description_always_update(self):
        """Test description for ALWAYS_UPDATE category."""
        desc = get_category_description(FileCategory.ALWAYS_UPDATE)
        assert "Core framework file" in desc
        assert "always updated" in desc

    def test_get_category_description_preserve_if_modified(self):
        """Test description for PRESERVE_IF_MODIFIED category."""
        desc = get_category_description(FileCategory.PRESERVE_IF_MODIFIED)
        assert "User-customizable" in desc
        assert "preserved if locally modified" in desc

    def test_get_category_description_never_update(self):
        """Test description for NEVER_UPDATE category."""
        desc = get_category_description(FileCategory.NEVER_UPDATE)
        assert "User content" in desc
        assert "never touched" in desc

    def test_get_category_description_all_categories(self):
        """Test that all categories have descriptions."""
        for category in FileCategory:
            desc = get_category_description(category)
            assert isinstance(desc, str)
            assert len(desc) > 0


class TestCategoryEnum:
    """Test suite for FileCategory enum."""

    def test_category_enum_values(self):
        """Test that FileCategory enum has expected values."""
        assert FileCategory.ALWAYS_UPDATE.value == "always"
        assert FileCategory.PRESERVE_IF_MODIFIED.value == "preserve"
        assert FileCategory.NEVER_UPDATE.value == "never"

    def test_category_enum_members(self):
        """Test that FileCategory enum has all expected members."""
        members = list(FileCategory)
        assert len(members) == 3
        assert FileCategory.ALWAYS_UPDATE in members
        assert FileCategory.PRESERVE_IF_MODIFIED in members
        assert FileCategory.NEVER_UPDATE in members
