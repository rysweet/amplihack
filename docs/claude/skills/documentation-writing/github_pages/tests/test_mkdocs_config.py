"""Tests for mkdocs_config.py module."""

from pathlib import Path

import pytest

from github_pages.mkdocs_config import (
    _construct_site_url,
    _extract_repo_info,
    _extract_repo_name,
    _format_page_name,
    _format_section_name,
    build_material_theme_config,
    build_mkdocs_config,
    generate_nav_structure,
    validate_config,
    write_mkdocs_yaml,
)


class TestBuildMkdocsConfig:
    """Tests for build_mkdocs_config function."""

    def test_basic_config(self, tmp_path: Path):
        """Test building basic configuration."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "index.md").write_text("# Home")

        config = build_mkdocs_config(
            project_name="Test Project",
            project_url="https://github.com/user/repo",
            docs_dir=str(docs_dir),
        )

        assert config["site_name"] == "Test Project"
        assert config["repo_url"] == "https://github.com/user/repo"
        assert "theme" in config
        assert "nav" in config
        assert "plugins" in config

    def test_config_with_custom_theme_features(self, tmp_path: Path):
        """Test configuration with custom theme features."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "index.md").write_text("# Home")

        custom_features = ["navigation.tabs", "search.suggest"]

        config = build_mkdocs_config(
            project_name="Test",
            project_url="https://github.com/user/repo",
            docs_dir=str(docs_dir),
            theme_features=custom_features,
        )

        assert config["theme"]["features"] == custom_features

    def test_config_with_custom_nav(self, tmp_path: Path):
        """Test configuration with custom navigation structure."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        custom_nav = [{"Home": "index.md"}, {"Guide": "guide.md"}]

        config = build_mkdocs_config(
            project_name="Test",
            project_url="https://github.com/user/repo",
            docs_dir=str(docs_dir),
            nav_structure=custom_nav,
        )

        assert config["nav"] == custom_nav

    def test_site_url_constructed_from_repo(self):
        """Test that site_url is properly constructed from repo URL."""
        config = build_mkdocs_config(
            project_name="Test",
            project_url="https://github.com/myuser/myrepo",
        )

        assert config["site_url"] == "https://myuser.github.io/myrepo/"

    def test_repo_name_extracted(self):
        """Test that repo name is extracted correctly."""
        config = build_mkdocs_config(
            project_name="Test",
            project_url="https://github.com/owner/repo-name",
        )

        assert config["repo_name"] == "owner/repo-name"


class TestBuildMaterialThemeConfig:
    """Tests for build_material_theme_config function."""

    def test_default_theme_config(self):
        """Test building default theme configuration."""
        config = build_material_theme_config()

        assert config["name"] == "material"
        assert "features" in config
        assert "palette" in config
        assert config["palette"]["primary"] == "indigo"

    def test_custom_features(self):
        """Test theme config with custom features."""
        features = ["navigation.tabs"]

        config = build_material_theme_config(features=features)

        assert config["features"] == features

    def test_default_features_included(self):
        """Test that default features are sensible."""
        config = build_material_theme_config()

        assert "navigation.tabs" in config["features"]
        assert "search.highlight" in config["features"]


class TestGenerateNavStructure:
    """Tests for generate_nav_structure function."""

    def test_empty_files_returns_default(self):
        """Test that empty file list returns default nav."""
        nav = generate_nav_structure([])

        assert nav == [{"Home": "index.md"}]

    def test_single_index_file(self, tmp_path: Path):
        """Test navigation with just index.md."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        index = docs_dir / "index.md"
        index.write_text("# Home")

        nav = generate_nav_structure([index])

        assert {"Home": "index.md"} in nav

    def test_files_in_subdirectories(self, sample_markdown_files: list[Path]):
        """Test navigation with files in subdirectories."""
        nav = generate_nav_structure(sample_markdown_files)

        # Should have Home
        home_items = [item for item in nav if "Home" in item]
        assert len(home_items) > 0

        # Should have sections
        nav_str = str(nav)
        assert "Tutorials" in nav_str or "tutorials" in nav_str.lower()

    def test_diataxis_ordering(self, tmp_path: Path):
        """Test that Diataxis sections are ordered correctly."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create sections in non-Diataxis order
        for section in ["concepts", "howto", "reference", "tutorials"]:
            section_dir = docs_dir / section
            section_dir.mkdir()
            (section_dir / "index.md").write_text(f"# {section}")

        files = list(docs_dir.rglob("*.md"))
        nav = generate_nav_structure(files)

        # Check order - Tutorials should come before Concepts
        nav_str = str(nav)
        tutorials_pos = nav_str.find("Tutorials")
        concepts_pos = nav_str.find("Concepts")

        # If both exist, Tutorials should come first
        if tutorials_pos >= 0 and concepts_pos >= 0:
            assert tutorials_pos < concepts_pos


class TestWriteMkdocsYaml:
    """Tests for write_mkdocs_yaml function."""

    def test_writes_valid_yaml(self, tmp_path: Path):
        """Test that valid YAML is written."""
        config = {
            "site_name": "Test",
            "theme": {"name": "material"},
        }

        output_path = tmp_path / "mkdocs.yml"
        result = write_mkdocs_yaml(config, output_path)

        assert result == output_path
        assert output_path.exists()

        content = output_path.read_text()
        assert "site_name: Test" in content
        assert "theme:" in content

    def test_preserves_key_order(self, tmp_path: Path):
        """Test that key order is preserved in YAML output."""
        config = {
            "first": "1",
            "second": "2",
            "third": "3",
        }

        output_path = tmp_path / "mkdocs.yml"
        write_mkdocs_yaml(config, output_path)

        content = output_path.read_text()
        first_pos = content.find("first")
        second_pos = content.find("second")
        third_pos = content.find("third")

        assert first_pos < second_pos < third_pos


class TestValidateConfig:
    """Tests for validate_config function."""

    def test_valid_config_passes(self):
        """Test that valid config passes validation."""
        config = {
            "site_name": "Test",
            "theme": {"name": "material"},
        }

        # Should not raise
        validate_config(config)

    def test_missing_site_name_raises(self):
        """Test that missing site_name raises ValueError."""
        config = {"theme": {"name": "material"}}

        with pytest.raises(ValueError, match="site_name"):
            validate_config(config)

    def test_missing_theme_raises(self):
        """Test that missing theme raises ValueError."""
        config = {"site_name": "Test"}

        with pytest.raises(ValueError, match="theme"):
            validate_config(config)

    def test_non_material_theme_raises(self):
        """Test that non-Material theme raises ValueError."""
        config = {
            "site_name": "Test",
            "theme": {"name": "readthedocs"},
        }

        with pytest.raises(ValueError, match="material"):
            validate_config(config)


class TestFormatSectionName:
    """Tests for _format_section_name function."""

    def test_basic_formatting(self):
        """Test basic section name formatting."""
        assert _format_section_name("getting-started") == "Getting Started"
        assert _format_section_name("user_guide") == "User Guide"

    def test_special_cases(self):
        """Test special case formatting."""
        assert _format_section_name("api") == "API"
        assert _format_section_name("api-reference") == "API Reference"
        assert _format_section_name("howto") == "How-To"
        assert _format_section_name("cli") == "CLI"


class TestFormatPageName:
    """Tests for _format_page_name function."""

    def test_basic_formatting(self):
        """Test basic page name formatting."""
        assert _format_page_name("getting-started.md") == "Getting Started"
        assert _format_page_name("user_guide.md") == "User Guide"

    def test_index_returns_home(self):
        """Test that index.md returns Home."""
        assert _format_page_name("index.md") == "Home"


class TestExtractRepoInfo:
    """Tests for _extract_repo_info function."""

    def test_https_url(self):
        """Test extracting from HTTPS URL."""
        owner, repo = _extract_repo_info("https://github.com/user/repo")

        assert owner == "user"
        assert repo == "repo"

    def test_https_url_with_git_extension(self):
        """Test extracting from HTTPS URL with .git extension."""
        owner, repo = _extract_repo_info("https://github.com/user/repo.git")

        assert owner == "user"
        assert repo == "repo"

    def test_ssh_url(self):
        """Test extracting from SSH URL."""
        owner, repo = _extract_repo_info("git@github.com:user/repo.git")

        assert owner == "user"
        assert repo == "repo"


class TestExtractRepoName:
    """Tests for _extract_repo_name function."""

    def test_returns_owner_slash_repo(self):
        """Test that owner/repo format is returned."""
        name = _extract_repo_name("https://github.com/myorg/myproject")

        assert name == "myorg/myproject"


class TestConstructSiteUrl:
    """Tests for _construct_site_url function."""

    def test_basic_url(self):
        """Test basic GitHub Pages URL construction."""
        url = _construct_site_url("https://github.com/user/repo")

        assert url == "https://user.github.io/repo/"

    def test_ssh_url(self):
        """Test URL construction from SSH format."""
        url = _construct_site_url("git@github.com:user/repo.git")

        assert url == "https://user.github.io/repo/"
