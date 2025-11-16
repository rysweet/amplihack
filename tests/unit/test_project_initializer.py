"""Tests for smart PROJECT.md initializer."""

import pytest

from amplihack.utils.project_initializer import (
    ActionTaken,
    GenerationMethod,
    InitMode,
    ProjectState,
    analyze_project_structure,
    detect_project_md_state,
    generate_from_template,
    initialize_project_md,
)


class TestStateDetection:
    """Test PROJECT.md state detection."""

    def test_detect_missing(self, tmp_path):
        """Test detection of missing PROJECT.md."""
        state, reason = detect_project_md_state(tmp_path)
        assert state == ProjectState.MISSING
        assert "not found" in reason.lower()

    def test_detect_amplihack_content(self, tmp_path):
        """Test detection of amplihack-describing PROJECT.md."""
        project_md = tmp_path / ".claude" / "context" / "PROJECT.md"
        project_md.parent.mkdir(parents=True)

        # Create file with multiple amplihack indicators
        content = """# Project: Microsoft Hackathon 2025 - Agentic Coding Framework

        We are building an advanced agentic coding framework that leverages AI agents
        to accelerate software development.
        """
        project_md.write_text(content)

        state, reason = detect_project_md_state(tmp_path)
        assert state == ProjectState.DESCRIBES_AMPLIHACK
        assert "amplihack indicators" in reason.lower()

    def test_detect_valid_user_content(self, tmp_path):
        """Test detection of valid user PROJECT.md."""
        project_md = tmp_path / ".claude" / "context" / "PROJECT.md"
        project_md.parent.mkdir(parents=True)

        # Create file with user's project info
        content = """# Project: My Awesome App

        This is a web application for managing tasks and projects.
        Built with React and Python FastAPI.
        """
        project_md.write_text(content)

        state, reason = detect_project_md_state(tmp_path)
        assert state == ProjectState.VALID_USER_CONTENT

    def test_detect_single_indicator_not_enough(self, tmp_path):
        """Test that single amplihack mention isn't flagged."""
        project_md = tmp_path / ".claude" / "context" / "PROJECT.md"
        project_md.parent.mkdir(parents=True)

        # Mention amplihack once (as a tool reference)
        content = """# Project: My App

        This project uses amplihack for development assistance.
        """
        project_md.write_text(content)

        state, reason = detect_project_md_state(tmp_path)
        assert state == ProjectState.VALID_USER_CONTENT


class TestProjectAnalysis:
    """Test project structure analysis."""

    def test_analyze_python_project(self, tmp_path):
        """Test analysis of Python project."""
        # Create Python files
        (tmp_path / "src" / "main.py").parent.mkdir(parents=True)
        (tmp_path / "src" / "main.py").write_text("print('hello')")
        (tmp_path / "pyproject.toml").write_text("[project]\nname='test'")

        info = analyze_project_structure(tmp_path)

        assert info["name"] == tmp_path.name
        assert "Python" in info["languages"]
        assert "pyproject.toml" in info["package_files"]

    def test_analyze_javascript_project(self, tmp_path):
        """Test analysis of JavaScript project."""
        (tmp_path / "src" / "index.js").parent.mkdir(parents=True)
        (tmp_path / "src" / "index.js").write_text("console.log('hello')")
        (tmp_path / "package.json").write_text('{"name":"test"}')

        info = analyze_project_structure(tmp_path)

        assert "JavaScript/TypeScript" in info["languages"]
        assert "package.json" in info["package_files"]

    def test_analyze_multi_language_project(self, tmp_path):
        """Test analysis of project with multiple languages."""
        (tmp_path / "backend.py").write_text("# python")
        (tmp_path / "frontend.js").write_text("// js")
        (tmp_path / "lib.rs").write_text("// rust")

        info = analyze_project_structure(tmp_path)

        assert len(info["languages"]) == 3
        assert "Python" in info["languages"]
        assert "JavaScript/TypeScript" in info["languages"]
        assert "Rust" in info["languages"]


class TestTemplateGeneration:
    """Test PROJECT.md template generation."""

    def test_generate_minimal_template(self):
        """Test template generation with minimal info."""
        info = {"name": "test-project"}

        content = generate_from_template(info)

        assert "# Project Context" in content
        assert "test-project" in content
        assert "amplihack" in content.lower()  # Reference to amplihack as tool

    def test_generate_with_readme(self):
        """Test template uses README content."""
        info = {
            "name": "my-app",
            "readme_preview": "# My App\n\nThis is a great application for managing tasks.",
        }

        content = generate_from_template(info)

        assert "my-app" in content
        # Should extract description from README
        assert "tasks" in content.lower() or "application" in content.lower()

    def test_generate_with_languages(self):
        """Test template includes detected languages."""
        info = {"name": "multi-lang", "languages": ["Python", "JavaScript/TypeScript"]}

        content = generate_from_template(info)

        assert "Python" in content
        assert "JavaScript/TypeScript" in content


class TestInitialization:
    """Test complete initialization flow."""

    def test_initialize_missing_file(self, tmp_path):
        """Test initialization when PROJECT.md missing."""
        # Ensure .claude/context exists
        (tmp_path / ".claude" / "context").mkdir(parents=True)

        result = initialize_project_md(tmp_path, mode=InitMode.AUTO)

        assert result.success
        assert result.action_taken == ActionTaken.INITIALIZED
        assert result.method == GenerationMethod.TEMPLATE
        assert (tmp_path / ".claude" / "context" / "PROJECT.md").exists()

    def test_skip_valid_user_content(self, tmp_path):
        """Test that valid user content is not overwritten."""
        project_md = tmp_path / ".claude" / "context" / "PROJECT.md"
        project_md.parent.mkdir(parents=True)

        user_content = "# My Project\n\nThis is my project."
        project_md.write_text(user_content)

        result = initialize_project_md(tmp_path, mode=InitMode.AUTO)

        assert result.action_taken == ActionTaken.SKIPPED
        assert result.state == ProjectState.VALID_USER_CONTENT
        # Verify user content not modified
        assert project_md.read_text() == user_content

    def test_offer_regeneration_for_amplihack_content(self, tmp_path):
        """Test that amplihack content triggers offer (not auto-regeneration)."""
        project_md = tmp_path / ".claude" / "context" / "PROJECT.md"
        project_md.parent.mkdir(parents=True)

        # Write amplihack-describing content
        project_md.write_text("""
        # Microsoft Hackathon 2025 - Agentic Coding Framework
        We are building an advanced agentic coding framework.
        """)

        result = initialize_project_md(tmp_path, mode=InitMode.AUTO)

        assert result.action_taken == ActionTaken.OFFERED
        assert result.state == ProjectState.DESCRIBES_AMPLIHACK
        assert "force" in result.message.lower()

    def test_force_mode_regenerates(self, tmp_path):
        """Test that FORCE mode regenerates regardless of content."""
        project_md = tmp_path / ".claude" / "context" / "PROJECT.md"
        project_md.parent.mkdir(parents=True)

        # Valid user content
        project_md.write_text("# My Project\n\nValid content")

        result = initialize_project_md(tmp_path, mode=InitMode.FORCE)

        assert result.success
        assert result.action_taken == ActionTaken.REGENERATED
        # Content should be replaced
        new_content = project_md.read_text()
        assert "Project Context" in new_content

    def test_check_mode_no_modifications(self, tmp_path):
        """Test that CHECK mode doesn't modify files."""
        result = initialize_project_md(tmp_path, mode=InitMode.CHECK)

        assert result.action_taken == ActionTaken.SKIPPED
        assert result.method == GenerationMethod.NONE
        # Verify no files created
        assert not (tmp_path / ".claude" / "context" / "PROJECT.md").exists()

    def test_creates_backup_before_regeneration(self, tmp_path):
        """Test that backup is created before overwriting."""
        project_md = tmp_path / ".claude" / "context" / "PROJECT.md"
        project_md.parent.mkdir(parents=True)

        original_content = "# Original\n\nOld content"
        project_md.write_text(original_content)

        result = initialize_project_md(tmp_path, mode=InitMode.FORCE)

        assert result.success
        # Check backup exists
        backup = project_md.with_suffix(".md.bak")
        assert backup.exists()
        assert backup.read_text() == original_content

    def test_handles_missing_claude_directory(self, tmp_path):
        """Test graceful handling when .claude directory doesn't exist."""
        result = initialize_project_md(tmp_path, mode=InitMode.AUTO)

        # Should create directory and file
        assert result.success
        assert (tmp_path / ".claude" / "context" / "PROJECT.md").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
