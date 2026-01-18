"""Integration tests for GitHub Pages module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from github_pages import (
    DeploymentConfig,
    DeploymentResult,
    GenerationResult,
    SiteConfig,
    ValidationResult,
    deploy_site,
    generate_site,
    validate_site,
)


class TestGenerateValidateWorkflow:
    """Integration tests for generate -> validate workflow."""

    @patch("github_pages.generator.subprocess.run")
    def test_generate_then_validate(
        self,
        mock_run: MagicMock,
        tmp_project_root: Path,
    ):
        """Test generating a site then validating it."""
        # Mock successful MkDocs build
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        # Create output directory with content
        site_dir = tmp_project_root / "site"
        site_dir.mkdir(exist_ok=True)
        (site_dir / "index.html").write_text("<html><body>Test</body></html>")
        (site_dir / "docs.md").write_text("# Documentation\n\nComplete guide.")

        # Generate
        gen_config = SiteConfig(
            project_name="Test Project",
            project_url="https://github.com/user/repo",
            docs_dir=str(tmp_project_root / "docs"),
            output_dir=str(site_dir),
        )

        gen_result = generate_site(gen_config)

        # Validate
        val_result = validate_site(site_dir)

        assert isinstance(gen_result, GenerationResult)
        assert isinstance(val_result, ValidationResult)

    @patch("github_pages.generator.subprocess.run")
    def test_validation_results_match_expectations(
        self,
        mock_run: MagicMock,
        tmp_project_root: Path,
    ):
        """Test that validation results contain expected data."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        site_dir = tmp_project_root / "site"
        site_dir.mkdir(exist_ok=True)

        # Create quality documentation
        (site_dir / "index.md").write_text("""
# Project Documentation

## Getting Started

This guide explains how to get started.

### Installation

Use pip to install the package.

### Configuration

Configure settings in config.yml.

## API Reference

See the [API documentation](api.md) for details.
""")

        val_result = validate_site(site_dir)

        # Should have all three pass scores
        assert val_result.pass1_coverage >= 0
        assert val_result.pass2_clarity_score >= 0
        assert val_result.pass3_grounded_pct >= 0


class TestFullWorkflow:
    """Integration tests for complete workflow."""

    @patch("github_pages.generator.subprocess.run")
    @patch("github_pages.deployer._run_git_command")
    @patch("github_pages.deployer._check_git_status")
    @patch("github_pages.deployer._get_current_branch")
    @patch("github_pages.deployer._get_repo_url")
    @patch("github_pages.deployer._branch_exists")
    def test_full_generate_validate_deploy(
        self,
        mock_branch_exists: MagicMock,
        mock_get_repo_url: MagicMock,
        mock_get_branch: MagicMock,
        mock_git_status: MagicMock,
        mock_git_cmd: MagicMock,
        mock_mkdocs: MagicMock,
        tmp_project_root: Path,
    ):
        """Test complete workflow: generate -> validate -> deploy."""
        # Setup mocks
        mock_mkdocs.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_git_status.return_value = True
        mock_get_branch.return_value = "main"
        mock_get_repo_url.return_value = "https://github.com/user/repo"
        mock_branch_exists.return_value = False
        mock_git_cmd.return_value = MagicMock(
            returncode=0,
            stdout="abc123\n",
            stderr="",
        )

        # Create site dir with content
        site_dir = tmp_project_root / "site"
        site_dir.mkdir(exist_ok=True)
        (site_dir / "index.html").write_text("<html></html>")
        (site_dir / "docs.md").write_text("# Docs\n\nContent here.")

        # Initialize git
        git_dir = tmp_project_root / ".git"
        git_dir.mkdir(exist_ok=True)

        # Step 1: Generate
        gen_config = SiteConfig(
            project_name="Test",
            project_url="https://github.com/user/repo",
            docs_dir=str(tmp_project_root / "docs"),
            output_dir=str(site_dir),
        )
        gen_result = generate_site(gen_config)

        # Step 2: Validate
        val_result = validate_site(site_dir)

        # Step 3: Deploy (only if validation passes thresholds)
        deploy_config = DeploymentConfig(
            site_dir=str(site_dir),
            repo_path=str(tmp_project_root),
        )
        deploy_result = deploy_site(deploy_config)

        # All should return results
        assert isinstance(gen_result, GenerationResult)
        assert isinstance(val_result, ValidationResult)
        assert isinstance(deploy_result, DeploymentResult)


class TestErrorHandling:
    """Integration tests for error handling."""

    def test_generate_with_invalid_docs_dir(self, tmp_path: Path):
        """Test error handling for invalid docs directory."""
        config = SiteConfig(
            project_name="Test",
            project_url="https://github.com/user/repo",
            docs_dir=str(tmp_path / "nonexistent"),
        )

        with pytest.raises(FileNotFoundError):
            generate_site(config)

    def test_validate_with_invalid_site_dir(self, tmp_path: Path):
        """Test error handling for invalid site directory."""
        with pytest.raises(FileNotFoundError):
            validate_site(tmp_path / "nonexistent")

    def test_deploy_with_invalid_site_dir(self, tmp_path: Path):
        """Test error handling for invalid site directory."""
        config = DeploymentConfig(
            site_dir=str(tmp_path / "nonexistent"),
        )

        with pytest.raises(ValueError):
            deploy_site(config)


class TestPublicAPI:
    """Tests for public API consistency."""

    def test_all_exports_available(self):
        """Test that all public exports are available."""
        from github_pages import (
            DeploymentConfig,
            DeploymentResult,
            GenerationResult,
            SiteConfig,
            ValidationIssue,
            ValidationResult,
            deploy_site,
            generate_site,
            preview_locally,
            validate_site,
        )

        # All should be importable
        assert SiteConfig is not None
        assert DeploymentConfig is not None
        assert GenerationResult is not None
        assert ValidationResult is not None
        assert ValidationIssue is not None
        assert DeploymentResult is not None
        assert callable(generate_site)
        assert callable(validate_site)
        assert callable(deploy_site)
        assert callable(preview_locally)

    def test_config_dataclasses_have_defaults(self):
        """Test that config dataclasses have sensible defaults."""
        site_config = SiteConfig(
            project_name="Test",
            project_url="https://github.com/user/repo",
        )

        assert site_config.docs_dir == "docs"
        assert site_config.output_dir == "site"
        assert site_config.theme == "material"

        deploy_config = DeploymentConfig(site_dir="/tmp/site")

        assert deploy_config.repo_path == "."
        assert deploy_config.force_push is False


class TestDataclasses:
    """Tests for result dataclasses."""

    def test_generation_result_fields(self):
        """Test GenerationResult has all required fields."""
        result = GenerationResult(
            success=True,
            site_dir=Path("/tmp/site"),
            pages=["index.html"],
            errors=[],
            warnings=[],
            config_file=Path("/tmp/mkdocs.yml"),
        )

        assert result.success is True
        assert isinstance(result.site_dir, Path)
        assert isinstance(result.pages, list)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)

    def test_validation_result_fields(self):
        """Test ValidationResult has all required fields."""
        result = ValidationResult(
            passed=True,
            issues=[],
            pass1_coverage=100.0,
            pass2_clarity_score=85.0,
            pass3_grounded_pct=98.0,
        )

        assert result.passed is True
        assert result.pass1_coverage == 100.0
        assert result.pass2_clarity_score == 85.0
        assert result.pass3_grounded_pct == 98.0

    def test_deployment_result_fields(self):
        """Test DeploymentResult has all required fields."""
        result = DeploymentResult(
            success=True,
            branch="gh-pages",
            commit_sha="abc123",
            url="https://user.github.io/repo/",
            errors=[],
        )

        assert result.success is True
        assert result.branch == "gh-pages"
        assert result.commit_sha is not None
        assert result.url is not None
