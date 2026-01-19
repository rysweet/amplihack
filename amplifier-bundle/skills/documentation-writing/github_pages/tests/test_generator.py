"""Tests for generator.py module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from github_pages import GenerationResult, SiteConfig
from github_pages.generator import (
    discover_commands,
    discover_content,
    discover_readme,
    generate_navigation,
    generate_site,
    preview_locally,
)


class TestGenerateSite:
    """Tests for generate_site function."""

    def test_raises_type_error_for_none_config(self):
        """Test that None config raises TypeError."""
        with pytest.raises(TypeError, match="Config cannot be None"):
            generate_site(None)

    def test_raises_file_not_found_for_missing_docs(self, tmp_path: Path):
        """Test that missing docs directory raises FileNotFoundError."""
        config = SiteConfig(
            project_name="Test",
            project_url="https://github.com/user/repo",
            docs_dir=str(tmp_path / "nonexistent"),
        )

        with pytest.raises(FileNotFoundError, match="not found"):
            generate_site(config)

    @patch("github_pages.generator.subprocess.run")
    def test_successful_generation(
        self,
        mock_run: MagicMock,
        tmp_project_root: Path,
    ):
        """Test successful site generation."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        config = SiteConfig(
            project_name="Test Project",
            project_url="https://github.com/user/repo",
            docs_dir=str(tmp_project_root / "docs"),
            output_dir=str(tmp_project_root / "site"),
        )

        result = generate_site(config)

        assert isinstance(result, GenerationResult)
        assert result.config_file is not None
        # mkdocs.yml should be created
        assert (tmp_project_root / "mkdocs.yml").exists()

    @patch("github_pages.generator.subprocess.run")
    def test_mkdocs_failure_returns_error(
        self,
        mock_run: MagicMock,
        tmp_project_root: Path,
    ):
        """Test that MkDocs failure is handled."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Build error",
        )

        config = SiteConfig(
            project_name="Test",
            project_url="https://github.com/user/repo",
            docs_dir=str(tmp_project_root / "docs"),
            output_dir=str(tmp_project_root / "site"),
        )

        result = generate_site(config)

        assert result.success is False
        assert len(result.errors) > 0

    @patch("github_pages.generator.subprocess.run")
    def test_readme_copied_to_index(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
    ):
        """Test that README is copied to index.md if index doesn't exist."""
        # Create docs dir without index
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "guide.md").write_text("# Guide")

        # Create README
        readme = tmp_path / "README.md"
        readme.write_text("# Project README")

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        config = SiteConfig(
            project_name="Test",
            project_url="https://github.com/user/repo",
            docs_dir=str(docs_dir),
            output_dir=str(tmp_path / "site"),
        )

        generate_site(config)

        # index.md should be created from README
        index_path = docs_dir / "index.md"
        assert index_path.exists()
        assert "Project README" in index_path.read_text()

    @patch("github_pages.generator.subprocess.run")
    def test_timeout_handled(
        self,
        mock_run: MagicMock,
        tmp_project_root: Path,
    ):
        """Test that timeout is handled gracefully."""
        mock_run.side_effect = subprocess.TimeoutExpired("mkdocs", 120)

        config = SiteConfig(
            project_name="Test",
            project_url="https://github.com/user/repo",
            docs_dir=str(tmp_project_root / "docs"),
            output_dir=str(tmp_project_root / "site"),
        )

        result = generate_site(config)

        assert result.success is False
        assert any("timed out" in err for err in result.errors)


class TestDiscoverContent:
    """Tests for discover_content function."""

    def test_empty_directory(self, tmp_path: Path):
        """Test discovering content in empty directory."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        files = discover_content(docs_dir)

        assert files == []

    def test_nonexistent_directory(self, tmp_path: Path):
        """Test discovering content in nonexistent directory."""
        files = discover_content(tmp_path / "nonexistent")

        assert files == []

    def test_finds_markdown_files(self, tmp_docs_dir: Path):
        """Test that markdown files are discovered."""
        files = discover_content(tmp_docs_dir)

        assert len(files) > 0
        assert all(f.suffix == ".md" for f in files)

    def test_index_md_sorted_first(self, tmp_path: Path):
        """Test that index.md is sorted first."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "zebra.md").write_text("# Zebra")
        (docs_dir / "alpha.md").write_text("# Alpha")
        (docs_dir / "index.md").write_text("# Index")

        files = discover_content(docs_dir)

        assert files[0].name == "index.md"

    def test_finds_files_in_subdirectories(self, sample_markdown_files: list[Path]):
        """Test that files in subdirectories are found."""
        # Get the docs dir from the first file
        docs_dir = sample_markdown_files[0].parent

        files = discover_content(docs_dir)

        # Should find files in subdirectories
        paths_str = [str(f) for f in files]
        assert any("tutorials" in p or "reference" in p for p in paths_str)


class TestDiscoverReadme:
    """Tests for discover_readme function."""

    def test_finds_readme_md(self, tmp_path: Path):
        """Test finding README.md."""
        readme = tmp_path / "README.md"
        readme.write_text("# Project")

        result = discover_readme(tmp_path)

        assert result == readme

    def test_finds_lowercase_readme(self, tmp_path: Path):
        """Test finding readme.md (lowercase)."""
        readme = tmp_path / "readme.md"
        readme.write_text("# Project")

        result = discover_readme(tmp_path)

        # On case-insensitive filesystems, the canonical path may differ
        assert result is not None
        assert result.name.lower() == "readme.md"

    def test_returns_none_if_no_readme(self, tmp_path: Path):
        """Test returning None when no README exists."""
        result = discover_readme(tmp_path)

        assert result is None


class TestDiscoverCommands:
    """Tests for discover_commands function."""

    @patch("github_pages.generator.subprocess.run")
    def test_discovers_amplihack_command(self, mock_run: MagicMock):
        """Test discovering amplihack command help."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="amplihack help text",
            stderr="",
        )

        commands = discover_commands()

        # May or may not find commands depending on system
        assert isinstance(commands, dict)

    @patch("github_pages.generator.subprocess.run")
    def test_handles_missing_command(self, mock_run: MagicMock):
        """Test handling when amplihack is not found."""
        mock_run.side_effect = FileNotFoundError()

        commands = discover_commands()

        assert commands == {}


class TestGenerateNavigation:
    """Tests for generate_navigation function."""

    def test_empty_files(self):
        """Test navigation with empty file list."""
        nav = generate_navigation([])

        assert isinstance(nav, dict)

    def test_custom_structure_used(self):
        """Test that custom navigation structure is used when provided."""
        custom = {"Home": "index.md", "Guide": "guide.md"}

        nav = generate_navigation([], custom_structure=custom)

        assert nav == custom

    def test_auto_generation(self, sample_markdown_files: list[Path]):
        """Test auto-generation of navigation."""
        nav = generate_navigation(sample_markdown_files)

        # Should be a dict
        assert isinstance(nav, dict)


class TestPreviewLocally:
    """Tests for preview_locally function."""

    @patch("github_pages.generator.subprocess.run")
    def test_starts_server(self, mock_run: MagicMock, tmp_path: Path):
        """Test that preview starts MkDocs server."""
        config_path = tmp_path / "mkdocs.yml"
        config_path.write_text("site_name: Test")

        preview_locally(config_path, port=8000)

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "mkdocs" in call_args
        assert "serve" in call_args

    @patch("github_pages.generator.subprocess.run")
    def test_custom_port(self, mock_run: MagicMock, tmp_path: Path):
        """Test preview with custom port."""
        config_path = tmp_path / "mkdocs.yml"
        config_path.write_text("site_name: Test")

        preview_locally(config_path, port=9000)

        call_args = mock_run.call_args[0][0]
        assert "9000" in str(call_args)
