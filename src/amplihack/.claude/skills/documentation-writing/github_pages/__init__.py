"""GitHub Pages Documentation Site Generation.

A complete solution for generating, validating, and deploying documentation
sites to GitHub Pages using MkDocs with the Material theme.

Philosophy:
- Single responsibility: Generate docs -> Validate docs -> Deploy docs
- Standard library when possible, external deps only where necessary (mkdocs, pyyaml)
- Self-contained and regeneratable
- Zero-BS: No stubs, no placeholders - everything works

Public API (the "studs"):
    SiteConfig: Configuration for site generation
    DeploymentConfig: Configuration for deployment
    GenerationResult: Result of site generation
    ValidationResult: Result of three-pass validation
    ValidationIssue: Single validation issue
    DeploymentResult: Result of deployment

    generate_site: Generate documentation site from docs/
    validate_site: Run three-pass validation
    deploy_site: Deploy to GitHub Pages
    preview_locally: Start local preview server
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class SiteConfig:
    """Configuration for site generation.

    Attributes:
        project_name: Name of the project (used in site title)
        project_url: GitHub repository URL
        docs_dir: Path to documentation directory (default: "docs")
        output_dir: Path for generated site output (default: "site")
        theme: MkDocs theme to use (default: "material")
        theme_features: List of Material theme features to enable
        nav_structure: Custom navigation structure (auto-generated if None)
    """

    project_name: str
    project_url: str
    docs_dir: str | Path = "docs"
    output_dir: str | Path = "site"
    theme: str = "material"
    theme_features: list[str] | None = None
    nav_structure: dict | None = None


@dataclass
class DeploymentConfig:
    """Configuration for deployment.

    Attributes:
        site_dir: Path to generated site directory
        repo_path: Path to git repository root (default: ".")
        commit_message: Commit message for deployment (default: "Update docs")
        force_push: Whether to force push (DANGEROUS - default: False)
    """

    site_dir: str | Path
    repo_path: str | Path = "."
    commit_message: str = "Update docs"
    force_push: bool = False


@dataclass
class GenerationResult:
    """Result of site generation.

    Attributes:
        success: Whether generation succeeded
        site_dir: Path to generated site directory
        pages: List of generated page paths
        errors: List of error messages
        warnings: List of warning messages
        config_file: Path to generated mkdocs.yml
    """

    success: bool
    site_dir: Path
    pages: list[str]
    errors: list[str]
    warnings: list[str]
    config_file: Path | None


@dataclass
class ValidationIssue:
    """Single validation issue.

    Attributes:
        severity: Issue severity level ("error", "warning", "info")
        pass_number: Which validation pass found this (1, 2, or 3)
        location: File path and optionally line number
        message: Description of the issue
        suggestion: Optional suggestion for fixing the issue
    """

    severity: Literal["error", "warning", "info"]
    pass_number: int
    location: str
    message: str
    suggestion: str | None = None


@dataclass
class ValidationResult:
    """Result of three-pass validation.

    Attributes:
        passed: Whether validation passed all thresholds
        issues: List of all validation issues found
        pass1_coverage: Coverage percentage (target: 100%)
        pass2_clarity_score: Clarity score (target: >= 80%)
        pass3_grounded_pct: Percentage of grounded content (target: >= 95%)
    """

    passed: bool
    issues: list[ValidationIssue]
    pass1_coverage: float
    pass2_clarity_score: float
    pass3_grounded_pct: float


@dataclass
class DeploymentResult:
    """Result of deployment.

    Attributes:
        success: Whether deployment succeeded
        branch: Branch deployed to (usually "gh-pages")
        commit_sha: SHA of the deployment commit (None if failed)
        url: GitHub Pages URL (None if failed)
        errors: List of error messages
    """

    success: bool
    branch: str
    commit_sha: str | None
    url: str | None
    errors: list[str]


# Import implementations after dataclasses are defined
from .deployer import deploy_site
from .generator import generate_site, preview_locally
from .validator import validate_site

__all__ = [
    # Configuration classes
    "SiteConfig",
    "DeploymentConfig",
    # Result classes
    "GenerationResult",
    "ValidationResult",
    "ValidationIssue",
    "DeploymentResult",
    # Main functions
    "generate_site",
    "validate_site",
    "deploy_site",
    "preview_locally",
]
