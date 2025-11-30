# Generate GitHub Pages Sites

This guide shows ye how to generate, validate, and deploy documentation sites to GitHub Pages using amplihack's built-in MkDocs integration.

## Prerequisites

Install MkDocs and the Material theme:

```bash
pip install mkdocs mkdocs-material
```

## Quick Start

Generate and deploy a documentation site in three steps:

```python
from claude_skills.documentation_writing.github_pages import (
    SiteConfig,
    generate_site,
    validate_site,
    deploy_site,
    DeploymentConfig,
)

# Step 1: Generate the site
config = SiteConfig(
    project_name="My Project",
    project_url="https://github.com/user/repo",
    docs_dir="docs",
    output_dir="site",
)
result = generate_site(config)

# Step 2: Validate the site
validation = validate_site(result.site_dir)
print(f"Coverage: {validation.pass1_coverage}%")
print(f"Clarity: {validation.pass2_clarity_score}%")
print(f"Grounded: {validation.pass3_grounded_pct}%")

# Step 3: Deploy to GitHub Pages
deploy_config = DeploymentConfig(
    site_dir="site",
    repo_path=".",
    commit_message="Update documentation",
)
deployment = deploy_site(deploy_config)
print(f"Deployed to: {deployment.url}")
```

## How to Generate a Site

### Basic Generation

The simplest way to generate a site:

```python
from claude_skills.documentation_writing.github_pages import SiteConfig, generate_site

config = SiteConfig(
    project_name="amplihack",
    project_url="https://github.com/amplihack/amplihack",
)

result = generate_site(config)

if result.success:
    print(f"Site generated at {result.site_dir}")
    print(f"Generated {len(result.pages)} pages")
else:
    print(f"Errors: {result.errors}")
```

### What Gets Generated

The generator automatically discovers and includes:

1. **All markdown files in docs/**: Recursively scans for `*.md` files
2. **README.md**: Copies to `docs/index.md` if no index exists
3. **Command help text**: Auto-generates CLI reference from `amplihack --help`

### Custom Configuration

Configure theme features and navigation:

```python
config = SiteConfig(
    project_name="My Project",
    project_url="https://github.com/user/repo",
    docs_dir="docs",
    output_dir="site",
    theme_features=[
        "navigation.tabs",
        "navigation.sections",
        "navigation.expand",
        "search.highlight",
        "search.suggest",
        "content.code.copy",
    ],
    nav_structure={
        "Home": "index.md",
        "Getting Started": [
            {"Installation": "getting-started/installation.md"},
            {"Quick Start": "getting-started/quick-start.md"},
        ],
        "Tutorials": "tutorials/",
    },
)

result = generate_site(config)
```

## How to Validate a Site

Run three-pass validation to ensure documentation quality:

```python
from claude_skills.documentation_writing.github_pages import validate_site

validation = validate_site("site")

print(f"Passed: {validation.passed}")
print(f"Pass 1 (Coverage): {validation.pass1_coverage}%")
print(f"Pass 2 (Clarity): {validation.pass2_clarity_score}%")
print(f"Pass 3 (Grounded): {validation.pass3_grounded_pct}%")

# Review issues
for issue in validation.issues:
    print(f"{issue.severity.upper()}: {issue.message}")
    if issue.suggestion:
        print(f"  Suggestion: {issue.suggestion}")
```

### Validation Passes

**Pass 1: Coverage** - Every feature must be documented (target: 100%)

- Checks that all features are mentioned in documentation
- If no feature list provided, checks for basic documentation presence

**Pass 2: Clarity** - Organization and readability (target: >= 80%)

- Navigation depth (≤ 3 levels recommended)
- Descriptive headings (not just "Overview", "Introduction")
- Contextful links (not "click here")
- No walls of text (paragraphs ≤ 300 words)

**Pass 3: Reality** - No future tense, no placeholders (target: >= 95%)

- No "will be", "coming soon", "to be implemented"
- No TODO markers in documentation
- No foo/bar placeholder examples
- Exception: Content in `[PLANNED]` sections is allowed

### Validation Thresholds

```python
# Validation passes when:
# - Coverage >= 100%
# - Clarity >= 80%
# - Grounded >= 95%

if validation.passed:
    print("Documentation meets all quality standards")
else:
    print("Documentation needs improvement:")
    for issue in validation.issues:
        print(f"  - {issue.message}")
```

## How to Deploy to GitHub Pages

### Basic Deployment

Deploy to the `gh-pages` branch:

```python
from claude_skills.documentation_writing.github_pages import DeploymentConfig, deploy_site

config = DeploymentConfig(
    site_dir="site",
    repo_path=".",
    commit_message="Update documentation",
)

result = deploy_site(config)

if result.success:
    print(f"Deployed to: {result.url}")
    print(f"Commit: {result.commit_sha}")
else:
    print(f"Deployment failed: {result.errors}")
```

### Deployment Process

The deployer handles the git workflow automatically:

1. Validates site directory exists and has content
2. Checks git status (warns if uncommitted changes)
3. Creates or switches to `gh-pages` branch
4. Clears all files except `.git`
5. Copies site contents to repo root
6. Adds `.nojekyll` file (disables Jekyll processing)
7. Commits changes with your message
8. Pushes to remote
9. Returns to original branch

### Force Push (Dangerous)

Force push overwrites remote history - use with caution:

```python
config = DeploymentConfig(
    site_dir="site",
    repo_path=".",
    commit_message="Rebuild documentation",
    force_push=True,  # ⚠️ DANGEROUS - overwrites remote
)

result = deploy_site(config)
```

**Warning**: Force push should only be used when:

- You know the remote `gh-pages` branch is corrupted
- You're intentionally rebuilding from scratch
- You've coordinated with all team members

## How to Preview Locally

Start a local server to preview changes:

```python
from claude_skills.documentation_writing.github_pages import preview_locally

# Starts server at http://127.0.0.1:8000
preview_locally(config_path="mkdocs.yml", port=8000)
```

Or use MkDocs directly:

```bash
mkdocs serve
```

The preview server:

- Watches for file changes
- Auto-reloads the browser
- Shows the site at http://127.0.0.1:8000
- Press Ctrl+C to stop

## Troubleshooting

### MkDocs Not Found

**Error**: `FileNotFoundError: MkDocs not found`

**Solution**: Install MkDocs and Material theme:

```bash
pip install mkdocs mkdocs-material
```

### Site Directory is Empty

**Error**: `ValueError: Site directory is empty`

**Solution**: Generate the site before deploying:

```python
# Generate first
generation_result = generate_site(config)

# Then deploy
deployment_result = deploy_site(DeploymentConfig(
    site_dir=generation_result.site_dir,
))
```

### Git Push Failed

**Error**: `push failed: Permission denied`

**Solution**: Verify git remote access:

```bash
# Check remote URL
git remote get-url origin

# Test SSH connection (for SSH URLs)
ssh -T git@github.com

# Or use HTTPS with credentials
git remote set-url origin https://github.com/user/repo.git
```

### Navigation Not Showing

**Problem**: Navigation structure looks wrong

**Solution**: Check your `nav_structure` or let it auto-generate:

```python
# Let it auto-generate based on directory structure
config = SiteConfig(
    project_name="My Project",
    project_url="https://github.com/user/repo",
    nav_structure=None,  # Auto-generate
)
```

The auto-generated navigation follows Diataxis order:

1. Home (index.md)
2. Tutorials
3. How-To
4. Reference
5. Concepts
6. Other sections (alphabetically)

### Validation Failing

**Problem**: Validation fails but you're not sure why

**Solution**: Review the specific issues:

```python
validation = validate_site("site")

# Group issues by pass
pass1_issues = [i for i in validation.issues if i.pass_number == 1]
pass2_issues = [i for i in validation.issues if i.pass_number == 2]
pass3_issues = [i for i in validation.issues if i.pass_number == 3]

print(f"Coverage issues: {len(pass1_issues)}")
print(f"Clarity issues: {len(pass2_issues)}")
print(f"Reality issues: {len(pass3_issues)}")

# Show detailed suggestions
for issue in validation.issues:
    print(f"\n{issue.severity.upper()}: {issue.message}")
    print(f"Location: {issue.location}")
    if issue.suggestion:
        print(f"Fix: {issue.suggestion}")
```

## Configuration Options

### SiteConfig Options

```python
SiteConfig(
    project_name="My Project",           # Required: Project name
    project_url="https://github.com/...",  # Required: GitHub URL
    docs_dir="docs",                     # Optional: Source directory
    output_dir="site",                   # Optional: Output directory
    theme="material",                    # Optional: MkDocs theme
    theme_features=[...],                # Optional: Theme features
    nav_structure={...},                 # Optional: Custom navigation
)
```

### DeploymentConfig Options

```python
DeploymentConfig(
    site_dir="site",                     # Required: Generated site path
    repo_path=".",                       # Optional: Repository root
    commit_message="Update docs",        # Optional: Commit message
    force_push=False,                    # Optional: Force push (DANGEROUS)
)
```

### Environment Variables

None currently supported. All configuration is explicit via dataclasses.

## See Also

- [First Documentation Site Tutorial](../tutorials/first-docs-site.md) - Step-by-step beginner guide
- [GitHub Pages API Reference](../reference/github-pages-api.md) - Complete API documentation
- [Documentation Guidelines](../../DOCUMENTATION_GUIDELINES.md) - Eight rules for good docs
