# GitHub Pages API Reference

Complete Python API reference for generating, validating, and deploying documentation sites to GitHub Pages.

## Module

```python
from claude_skills.documentation_writing.github_pages import (
    # Configuration
    SiteConfig,
    DeploymentConfig,
    # Results
    GenerationResult,
    ValidationResult,
    ValidationIssue,
    DeploymentResult,
    # Functions
    generate_site,
    validate_site,
    deploy_site,
    preview_locally,
)
```

## Functions

### generate_site()

Generate a documentation site using MkDocs with Material theme.

```python
def generate_site(config: SiteConfig) -> GenerationResult:
    """Generate documentation site using MkDocs.

    Args:
        config: Site configuration

    Returns:
        GenerationResult with success status and details

    Raises:
        FileNotFoundError: If docs_dir doesn't exist
        PermissionError: If unable to write to output directory
        subprocess.CalledProcessError: If mkdocs build fails
    """
```

**Source**: [`~/.amplihack/.claude/skills/documentation-writing/github_pages/generator.py:23`](../claude/skills/documentation-writing/github_pages/generator.py#L23)

**Example**:

```python
from claude_skills.documentation_writing.github_pages import SiteConfig, generate_site

config = SiteConfig(
    project_name="amplihack",
    project_url="https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding",
    docs_dir="docs",
    output_dir="site",
)

result = generate_site(config)

if result.success:
    print(f"Generated {len(result.pages)} pages at {result.site_dir}")
    print(f"Configuration written to {result.config_file}")
else:
    print(f"Generation failed: {result.errors}")

# Check warnings (non-fatal issues)
for warning in result.warnings:
    print(f"Warning: {warning}")
```

**Content Discovery**:

The generator automatically discovers:

- All `*.md` files in `docs_dir` (recursive)
- `README.md` in project root (copied to `docs/index.md` if no index exists)
- CLI command help text (from `amplihack --help`)

**What It Creates**:

- `mkdocs.yml` - MkDocs configuration file
- `site/` - Generated HTML documentation
- `site/.nojekyll` - Disables Jekyll processing on GitHub Pages

---

### validate_site()

Run three-pass validation on generated documentation site.

```python
def validate_site(site_dir: Path | str) -> ValidationResult:
    """Run complete three-pass validation on documentation site.

    Args:
        site_dir: Path to generated site directory

    Returns:
        ValidationResult with scores from all three passes

    Raises:
        FileNotFoundError: If site_dir doesn't exist
    """
```

**Source**: [`~/.amplihack/.claude/skills/documentation-writing/github_pages/validator.py:53`](../claude/skills/documentation-writing/github_pages/validator.py#L53)

**Example**:

```python
from claude_skills.documentation_writing.github_pages import validate_site

validation = validate_site("site")

# Check overall pass/fail
if validation.passed:
    print("Documentation meets all quality standards")
else:
    print("Documentation needs improvement")

# Review individual pass scores
print(f"Pass 1 - Coverage: {validation.pass1_coverage}%")
print(f"Pass 2 - Clarity: {validation.pass2_clarity_score}%")
print(f"Pass 3 - Grounded: {validation.pass3_grounded_pct}%")

# Review all issues
for issue in validation.issues:
    print(f"\n[{issue.severity.upper()}] Pass {issue.pass_number}")
    print(f"Location: {issue.location}")
    print(f"Message: {issue.message}")
    if issue.suggestion:
        print(f"Suggestion: {issue.suggestion}")
```

**Validation Passes**:

1. **Pass 1 - Coverage** (target: 100%):
   - Checks that all features are documented
   - If no features list provided, verifies basic documentation exists

2. **Pass 2 - Clarity** (target: ≥ 80%):
   - Navigation depth (≤ 3 levels recommended)
   - Descriptive headings (not "Overview", "Introduction")
   - Contextful links (not "click here")
   - Content structure (no walls of text > 300 words)

3. **Pass 3 - Reality** (target: ≥ 95%):
   - No future tense ("will be", "coming soon")
   - No TODO markers
   - No placeholder examples (foo, bar, example.com)
   - Exception: `[PLANNED]` sections are allowed

**Overall Pass Criteria**:

```python
passed = (
    coverage >= 100.0
    and clarity >= 80.0
    and grounded >= 95.0
)
```

---

### deploy_site()

Deploy generated documentation site to GitHub Pages.

```python
def deploy_site(config: DeploymentConfig) -> DeploymentResult:
    """Deploy documentation site to GitHub Pages.

    Args:
        config: Deployment configuration

    Returns:
        DeploymentResult with deployment status

    Raises:
        TypeError: If config is None
        ValueError: If site_dir doesn't exist or is empty
        PermissionError: If unable to copy files
    """
```

**Source**: [`~/.amplihack/.claude/skills/documentation-writing/github_pages/deployer.py:20`](../claude/skills/documentation-writing/github_pages/deployer.py#L20)

**Example**:

```python
from claude_skills.documentation_writing.github_pages import DeploymentConfig, deploy_site

config = DeploymentConfig(
    site_dir="site",
    repo_path=".",
    commit_message="Update documentation [skip ci]",
    force_push=False,  # Never force push unless you know what you're doing
)

result = deploy_site(config)

if result.success:
    print(f"Deployed successfully")
    print(f"Branch: {result.branch}")
    print(f"Commit: {result.commit_sha}")
    print(f"URL: {result.url}")
else:
    print(f"Deployment failed")
    for error in result.errors:
        print(f"  Error: {error}")
```

**Deployment Process**:

1. Validates `site_dir` exists and has content
2. Checks git status (warns if uncommitted changes)
3. Saves current branch name
4. Creates or switches to `gh-pages` branch
5. Clears all files except `.git`
6. Copies site contents to repository root
7. Adds `.nojekyll` file
8. Commits changes
9. Pushes to remote
10. Returns to original branch

**Rollback on Failure**:

If deployment fails, the deployer automatically:

- Rolls back to the original branch
- Preserves local uncommitted changes
- Returns detailed error messages

**Safety Features**:

- Never force pushes by default (`force_push=False`)
- Validates branch names for security
- Validates GitHub URLs for security
- No auto-installation of dependencies

---

### preview_locally()

Start local preview server for documentation site.

```python
def preview_locally(config_path: Path | str = "mkdocs.yml", port: int = 8000) -> None:
    """Start local preview server for documentation site.

    Args:
        config_path: Path to mkdocs.yml configuration
        port: Port to serve on (default: 8000)

    Note:
        This function blocks until the server is stopped (Ctrl+C).
    """
```

**Source**: [`~/.amplihack/.claude/skills/documentation-writing/github_pages/generator.py:145`](../claude/skills/documentation-writing/github_pages/generator.py#L145)

**Example**:

```python
from claude_skills.documentation_writing.github_pages import preview_locally

# Starts server at http://127.0.0.1:8000
# Press Ctrl+C to stop
preview_locally(config_path="mkdocs.yml", port=8000)
```

**Preview Features**:

- Auto-reloads on file changes
- Watches `docs/` directory
- Live preview at `http://127.0.0.1:8000`
- Blocking function (use Ctrl+C to stop)

**Alternative** - Use MkDocs CLI directly:

```bash
mkdocs serve --dev-addr 127.0.0.1:8000
```

---

## Configuration Classes

### SiteConfig

Configuration for documentation site generation.

```python
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
```

**Source**: [`~/.amplihack/.claude/skills/documentation-writing/github_pages/__init__.py:31`](../claude/skills/documentation-writing/github_pages/__init__.py#L31)

**Example with Defaults**:

```python
from claude_skills.documentation_writing.github_pages import SiteConfig

config = SiteConfig(
    project_name="My Project",
    project_url="https://github.com/user/repo",
)
# Uses defaults: docs_dir="docs", output_dir="site", theme="material"
```

**Example with Custom Theme Features**:

```python
config = SiteConfig(
    project_name="My Project",
    project_url="https://github.com/user/repo",
    theme_features=[
        "navigation.tabs",
        "navigation.sections",
        "navigation.expand",
        "navigation.top",
        "search.highlight",
        "search.suggest",
        "search.share",
        "content.code.copy",
        "content.code.annotate",
    ],
)
```

**Example with Custom Navigation**:

```python
config = SiteConfig(
    project_name="My Project",
    project_url="https://github.com/user/repo",
    nav_structure={
        "Home": "index.md",
        "Getting Started": [
            {"Installation": "getting-started/install.md"},
            {"Quick Start": "getting-started/quick-start.md"},
        ],
        "API Reference": [
            {"Core API": "reference/core.md"},
            {"Advanced API": "reference/advanced.md"},
        ],
    },
)
```

**URL Validation**:

The `project_url` must be a valid GitHub URL:

- HTTPS: `https://github.com/user/repo`
- SSH: `git@github.com:user/repo.git`
- With `.git`: `https://github.com/user/repo.git`

Invalid URLs raise `ValueError`.

---

### DeploymentConfig

Configuration for GitHub Pages deployment.

```python
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
```

**Source**: [`~/.amplihack/.claude/skills/documentation-writing/github_pages/__init__.py:54`](../claude/skills/documentation-writing/github_pages/__init__.py#L54)

**Example**:

```python
from claude_skills.documentation_writing.github_pages import DeploymentConfig

config = DeploymentConfig(
    site_dir="site",
    repo_path=".",
    commit_message="Update documentation [skip ci]",
)
```

**⚠️ Force Push Warning**:

```python
# DANGEROUS - Only use if you know what you're doing
config = DeploymentConfig(
    site_dir="site",
    force_push=True,  # Overwrites remote history!
)
```

Force push should ONLY be used when:

- Remote `gh-pages` branch is corrupted
- Intentionally rebuilding from scratch
- Coordinated with all team members

---

## Result Classes

### GenerationResult

Result of documentation site generation.

```python
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
```

**Source**: [`~/.amplihack/.claude/skills/documentation-writing/github_pages/__init__.py:71`](../claude/skills/documentation-writing/github_pages/__init__.py#L71)

**Example**:

```python
result = generate_site(config)

if result.success:
    print(f"Success! Generated {len(result.pages)} pages")
    print(f"Site directory: {result.site_dir}")
    print(f"Configuration: {result.config_file}")

    # List all generated pages
    for page in result.pages:
        print(f"  - {page}")

    # Check for warnings
    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  - {warning}")
else:
    print("Generation failed:")
    for error in result.errors:
        print(f"  - {error}")
```

**Common Warnings**:

- "No markdown files found in docs directory"
- "No README.md or index.md found"
- "Could not copy README to index.md: ..."

---

### ValidationResult

Result of three-pass documentation validation.

```python
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
```

**Source**: [`~/.amplihack/.claude/skills/documentation-writing/github_pages/__init__.py:111`](../claude/skills/documentation-writing/github_pages/__init__.py#L111)

**Example**:

```python
validation = validate_site("site")

# Check overall pass
if validation.passed:
    print("✓ All validation passes succeeded")
else:
    print("✗ Validation failed - review issues below")

# Show scores
print(f"\nScores:")
print(f"  Coverage: {validation.pass1_coverage}% (target: 100%)")
print(f"  Clarity: {validation.pass2_clarity_score}% (target: ≥80%)")
print(f"  Grounded: {validation.pass3_grounded_pct}% (target: ≥95%)")

# Group issues by severity
errors = [i for i in validation.issues if i.severity == "error"]
warnings = [i for i in validation.issues if i.severity == "warning"]
info = [i for i in validation.issues if i.severity == "info"]

print(f"\nIssues: {len(errors)} errors, {len(warnings)} warnings, {len(info)} info")
```

---

### ValidationIssue

Single validation issue found during site validation.

```python
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
```

**Source**: [`~/.amplihack/.claude/skills/documentation-writing/github_pages/__init__.py:92`](../claude/skills/documentation-writing/github_pages/__init__.py#L92)

**Example**:

```python
validation = validate_site("site")

# Review all issues with suggestions
for issue in validation.issues:
    print(f"\n[{issue.severity.upper()}] Pass {issue.pass_number}")
    print(f"File: {issue.location}")
    print(f"Issue: {issue.message}")
    if issue.suggestion:
        print(f"Fix: {issue.suggestion}")

# Filter by pass number
pass3_issues = [i for i in validation.issues if i.pass_number == 3]
print(f"\nPass 3 (Reality) found {len(pass3_issues)} issues")

# Filter by severity
errors = [i for i in validation.issues if i.severity == "error"]
if errors:
    print("\nCritical errors that must be fixed:")
    for error in errors:
        print(f"  - {error.message}")
```

**Severity Levels**:

- `error`: Critical issues that prevent passing validation
- `warning`: Issues that should be fixed but don't prevent passing
- `info`: Suggestions for improvement

---

### DeploymentResult

Result of GitHub Pages deployment.

```python
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
```

**Source**: [`~/.amplihack/.claude/skills/documentation-writing/github_pages/__init__.py:130`](../claude/skills/documentation-writing/github_pages/__init__.py#L130)

**Example**:

```python
result = deploy_site(config)

if result.success:
    print(f"✓ Deployment successful")
    print(f"Branch: {result.branch}")
    print(f"Commit: {result.commit_sha}")
    print(f"URL: {result.url}")
    print(f"\nVisit: {result.url}")
else:
    print(f"✗ Deployment failed")
    for error in result.errors:
        print(f"  Error: {error}")

# Handle specific error cases
if "Permission denied" in str(result.errors):
    print("\nAction: Check git remote access (SSH keys or HTTPS credentials)")
elif "push failed" in str(result.errors):
    print("\nAction: Try pulling latest changes first")
```

**Success Case**:

```python
DeploymentResult(
    success=True,
    branch="gh-pages",
    commit_sha="a1b2c3d4e5f6...",
    url="https://user.github.io/repo/",
    errors=[],
)
```

**Failure Case**:

```python
DeploymentResult(
    success=False,
    branch="gh-pages",
    commit_sha=None,
    url=None,
    errors=["push failed: Permission denied (publickey)"],
)
```

**No Changes Case**:

```python
DeploymentResult(
    success=True,
    branch="gh-pages",
    commit_sha=None,
    url="https://user.github.io/repo/",
    errors=["No changes to deploy"],
)
```

---

## Environment Variables

Currently no environment variables are supported. All configuration is explicit via dataclasses.

---

## Complete Example

End-to-end workflow from generation to deployment:

```python
from claude_skills.documentation_writing.github_pages import (
    SiteConfig,
    DeploymentConfig,
    generate_site,
    validate_site,
    deploy_site,
)

# Step 1: Configure and generate
config = SiteConfig(
    project_name="My Amazing Project",
    project_url="https://github.com/user/repo",
    docs_dir="docs",
    output_dir="site",
)

print("Generating site...")
result = generate_site(config)

if not result.success:
    print(f"Generation failed: {result.errors}")
    exit(1)

print(f"✓ Generated {len(result.pages)} pages")

# Step 2: Validate
print("\nValidating site...")
validation = validate_site(result.site_dir)

print(f"Coverage: {validation.pass1_coverage}%")
print(f"Clarity: {validation.pass2_clarity_score}%")
print(f"Grounded: {validation.pass3_grounded_pct}%")

if not validation.passed:
    print(f"\n⚠️  Validation failed - {len(validation.issues)} issues found")
    for issue in validation.issues[:5]:  # Show first 5
        print(f"  - {issue.message}")

    # Continue anyway or exit based on your needs
    # exit(1)

# Step 3: Deploy
print("\nDeploying to GitHub Pages...")
deploy_config = DeploymentConfig(
    site_dir=str(result.site_dir),
    repo_path=".",
    commit_message="Update documentation [skip ci]",
)

deployment = deploy_site(deploy_config)

if deployment.success:
    print(f"✓ Deployed successfully")
    print(f"URL: {deployment.url}")
else:
    print(f"✗ Deployment failed: {deployment.errors}")
    exit(1)
```

---

## See Also

- [Generate GitHub Pages Sites How-To](../howto/github-pages-generation.md) - Task-oriented guide
- [First Documentation Site Tutorial](../tutorials/first-docs-site.md) - Beginner tutorial
- [Documentation Guidelines](../../DOCUMENTATION_GUIDELINES.md) - Eight rules for good docs
