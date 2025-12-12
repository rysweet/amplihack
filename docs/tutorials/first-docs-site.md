# Your First Documentation Site

In this 30-minute tutorial, ye'll learn how to create and deploy yer first documentation site to GitHub Pages using amplihack's built-in tools.

## What You'll Build

By the end of this tutorial, ye'll have:

- A live documentation site on GitHub Pages
- Automatic navigation from yer docs structure
- Material theme with search and code highlighting
- Validated documentation that meets quality standards

## Prerequisites

**Ye'll need**:

- Python 3.8 or later
- Git installed and configured
- A GitHub repository
- 30 minutes

**Check yer setup**:

```bash
python --version   # Should be 3.8+
git --version      # Any recent version
```

## Step 1: Install Dependencies (2 minutes)

Install MkDocs and the Material theme:

```bash
pip install mkdocs mkdocs-material
```

Verify the installation:

```bash
mkdocs --version
# Output: mkdocs, version 1.5.0 or later
```

## Step 2: Create Documentation (5 minutes)

Create a basic documentation structure:

````bash
# Create docs directory
mkdir -p docs/tutorials
mkdir -p docs/howto
mkdir -p docs/reference

# Create index page
cat > docs/index.md << 'EOF'
# Welcome to My Project

This is yer documentation site, generated with amplihack.

## Quick Links

- [Getting Started Tutorial](tutorials/getting-started.md)
- [How to Deploy](howto/deploy.md)
- [API Reference](reference/api.md)

## About

This project demonstrates documentation site generation with MkDocs and GitHub Pages.
EOF

# Create a tutorial
cat > docs/tutorials/getting-started.md << 'EOF'
# Getting Started

This tutorial walks ye through the basics of using this project.

## Installation

Install the package:

```bash
pip install my-project
````

## Your First Example

Create a simple script:

```python
from my_project import hello

result = hello("World")
print(result)
# Output: Hello, World!
```

## Next Steps

- Read the [API Reference](../reference/api.md)
- Learn [How to Deploy](../howto/deploy.md)
  EOF

# Create a how-to guide

cat > docs/howto/deploy.md << 'EOF'

# How to Deploy

This guide shows how to deploy yer application.

## Deploy to Production

Run the deployment command:

```bash
my-project deploy --env production
```

## Verify Deployment

Check the deployment status:

```bash
my-project status
```

Expected output:

```
Status: Running
Version: 1.0.0
URL: https://example.com
```

EOF

# Create an API reference

cat > docs/reference/api.md << 'EOF'

# API Reference

Complete API documentation.

## Core Functions

### hello(name)

Greet someone by name.

```python
def hello(name: str) -> str:
    """Return a greeting.

    Args:
        name: Name to greet

    Returns:
        Greeting string
    """
    return f"Hello, {name}!"
```

Example:

```python
from my_project import hello

greeting = hello("Captain")
print(greeting)
# Output: Hello, Captain!
```

EOF

````

**Result**: Ye now have a documentation structure following the Diataxis framework (tutorials, how-to, reference).

## Step 3: Generate the Site (3 minutes)

Create a Python script to generate yer site:

```python
# generate_docs.py
from claude_skills.documentation_writing.github_pages import (
    SiteConfig,
    generate_site,
)

config = SiteConfig(
    project_name="My Amazing Project",
    project_url="https://github.com/YOUR_USERNAME/YOUR_REPO",  # ⚠️ Update this!
    docs_dir="docs",
    output_dir="site",
)

print("Generating documentation site...")
result = generate_site(config)

if result.success:
    print(f"✓ Success! Generated {len(result.pages)} pages")
    print(f"Site directory: {result.site_dir}")
    print(f"Configuration: {result.config_file}")

    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  - {warning}")
else:
    print("✗ Generation failed:")
    for error in result.errors:
        print(f"  - {error}")
````

**Important**: Update `project_url` with yer actual GitHub repository URL!

Run the script:

```bash
python generate_docs.py
```

**Expected output**:

```
Generating documentation site...
✓ Success! Generated 12 pages
Site directory: site
Configuration: mkdocs.yml
```

**What got created**:

- `site/` - HTML documentation
- `mkdocs.yml` - MkDocs configuration
- `site/.nojekyll` - Disables Jekyll on GitHub Pages

## Step 4: Preview Locally (2 minutes)

Start a local preview server:

```bash
mkdocs serve
```

**Expected output**:

```
INFO    -  Building documentation...
INFO    -  Cleaning site directory
INFO    -  Documentation built in 0.42 seconds
INFO    -  [00:00:00] Serving on http://127.0.0.1:8000
```

Open yer browser to http://127.0.0.1:8000 and ye'll see yer documentation site!

**What to check**:

- ✓ Home page loads
- ✓ Navigation works
- ✓ Code blocks have syntax highlighting
- ✓ Search box appears

Press `Ctrl+C` to stop the server.

## Step 5: Validate Documentation (3 minutes)

Create a validation script:

```python
# validate_docs.py
from claude_skills.documentation_writing.github_pages import validate_site

print("Running three-pass validation...\n")
validation = validate_site("site")

print(f"Overall: {'PASSED ✓' if validation.passed else 'FAILED ✗'}\n")

print("Scores:")
print(f"  Pass 1 - Coverage: {validation.pass1_coverage}% (target: 100%)")
print(f"  Pass 2 - Clarity: {validation.pass2_clarity_score}% (target: ≥80%)")
print(f"  Pass 3 - Grounded: {validation.pass3_grounded_pct}% (target: ≥95%)")

if validation.issues:
    print(f"\nIssues found: {len(validation.issues)}")

    # Group by severity
    errors = [i for i in validation.issues if i.severity == "error"]
    warnings = [i for i in validation.issues if i.severity == "warning"]
    info = [i for i in validation.issues if i.severity == "info"]

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for issue in errors:
            print(f"  - {issue.message}")
            if issue.suggestion:
                print(f"    Fix: {issue.suggestion}")

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for issue in warnings[:3]:  # Show first 3
            print(f"  - {issue.message}")

    if info:
        print(f"\nInfo ({len(info)}):")
        for issue in info[:3]:  # Show first 3
            print(f"  - {issue.message}")
else:
    print("\n✓ No issues found - excellent documentation!")
```

Run the validation:

```bash
python validate_docs.py
```

**Expected output**:

```
Running three-pass validation...

Overall: PASSED ✓

Scores:
  Pass 1 - Coverage: 100% (target: 100%)
  Pass 2 - Clarity: 85% (target: ≥80%)
  Pass 3 - Grounded: 100% (target: ≥95%)

✓ No issues found - excellent documentation!
```

## Step 6: Commit Your Work (3 minutes)

Before deploying, commit yer documentation:

```bash
# Add generated files to .gitignore
echo "site/" >> .gitignore
echo "mkdocs.yml" >> .gitignore

# Commit the docs source
git add docs/ generate_docs.py validate_docs.py .gitignore
git commit -m "Add documentation"
git push origin main
```

**Why ignore site/ and mkdocs.yml?**

- They're generated files
- They'll be built fresh on deployment
- Keeps yer repo clean

## Step 7: Deploy to GitHub Pages (5 minutes)

Create a deployment script:

```python
# deploy_docs.py
from claude_skills.documentation_writing.github_pages import (
    SiteConfig,
    DeploymentConfig,
    generate_site,
    deploy_site,
)

# Step 1: Generate fresh site
print("Generating site...")
site_config = SiteConfig(
    project_name="My Amazing Project",
    project_url="https://github.com/YOUR_USERNAME/YOUR_REPO",  # ⚠️ Update this!
    docs_dir="docs",
    output_dir="site",
)

result = generate_site(site_config)

if not result.success:
    print(f"✗ Generation failed: {result.errors}")
    exit(1)

print(f"✓ Generated {len(result.pages)} pages\n")

# Step 2: Deploy
print("Deploying to GitHub Pages...")
deploy_config = DeploymentConfig(
    site_dir="site",
    repo_path=".",
    commit_message="Update documentation [skip ci]",
)

deployment = deploy_site(deploy_config)

if deployment.success:
    print(f"✓ Deployment successful!\n")
    print(f"Branch: {deployment.branch}")
    print(f"Commit: {deployment.commit_sha}\n")
    print(f"Your site will be live at:")
    print(f"{deployment.url}")
    print(f"\nNote: It may take 1-2 minutes for GitHub to build the site.")
else:
    print(f"✗ Deployment failed:")
    for error in deployment.errors:
        print(f"  - {error}")
    exit(1)
```

**Important**: Update `project_url` with yer actual repository URL!

Run the deployment:

```bash
python deploy_docs.py
```

**Expected output**:

```
Generating site...
✓ Generated 12 pages

Deploying to GitHub Pages...
✓ Deployment successful!

Branch: gh-pages
Commit: a1b2c3d4e5f6...

Your site will be live at:
https://YOUR_USERNAME.github.io/YOUR_REPO/

Note: It may take 1-2 minutes for GitHub to build the site.
```

## Step 8: Enable GitHub Pages (2 minutes)

Configure yer repository to serve from the `gh-pages` branch:

1. Go to yer repository on GitHub
2. Click **Settings**
3. Scroll to **Pages** section
4. Under **Source**, select:
   - Branch: `gh-pages`
   - Folder: `/ (root)`
5. Click **Save**

GitHub will show: "Your site is live at https://YOUR_USERNAME.github.io/YOUR_REPO/"

## Step 9: Visit Your Site (1 minute)

Open the URL from GitHub Pages settings. Ye should see:

- ✓ Yer documentation with Material theme
- ✓ Navigation menu
- ✓ Search functionality
- ✓ Code syntax highlighting
- ✓ All yer pages accessible

## Congratulations! 🎉

Ye've successfully:

- Created a documentation structure
- Generated an MkDocs site
- Validated documentation quality
- Deployed to GitHub Pages
- Published a live documentation site

## Next Steps

Now that ye have a working docs site, explore these topics:

### Customize the Theme

Add custom colors and features:

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

### Custom Navigation

Define yer own navigation structure:

```python
config = SiteConfig(
    project_name="My Project",
    project_url="https://github.com/user/repo",
    nav_structure={
        "Home": "index.md",
        "Getting Started": [
            {"Installation": "tutorials/installation.md"},
            {"Quick Start": "tutorials/quick-start.md"},
        ],
        "Guides": [
            {"Deployment": "howto/deploy.md"},
            {"Configuration": "howto/configure.md"},
        ],
        "Reference": [
            {"API": "reference/api.md"},
            {"CLI": "reference/cli.md"},
        ],
    },
)
```

### Automatic Deployment

Set up GitHub Actions to auto-deploy on push:

```yaml
# .github/workflows/docs.yml
name: Deploy Docs

on:
  push:
    branches: [main]
    paths:
      - "docs/**"
      - "README.md"

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - run: pip install mkdocs mkdocs-material amplihack
      - run: python deploy_docs.py
```

### Add More Content

Expand yer documentation:

- **Tutorials**: Step-by-step learning guides
- **How-Tos**: Task-focused problem solutions
- **Reference**: Complete API and configuration docs
- **Concepts**: Explanations and background

## Troubleshooting

### Site Not Loading

**Problem**: GitHub Pages shows 404

**Solution**:

1. Check GitHub Pages settings (Settings → Pages)
2. Verify `gh-pages` branch exists
3. Wait 1-2 minutes for GitHub to build
4. Check branch contains HTML files (not just source)

### Deployment Failed: Permission Denied

**Problem**: `push failed: Permission denied (publickey)`

**Solution**:

```bash
# Check git remote
git remote get-url origin

# For SSH, test connection
ssh -T git@github.com

# Or switch to HTTPS
git remote set-url origin https://github.com/user/repo.git
```

### MkDocs Not Found

**Problem**: `FileNotFoundError: MkDocs not found`

**Solution**:

```bash
# Install MkDocs
pip install mkdocs mkdocs-material

# Verify installation
mkdocs --version
```

### Validation Failing

**Problem**: Documentation doesn't pass validation

**Solution**: Review the specific issues:

```bash
python validate_docs.py
```

Common issues:

- **Future tense**: Change "will be" to "is"
- **TODOs**: Complete them or move to `[PLANNED]` sections
- **Generic headings**: Use specific titles instead of "Overview"
- **Bad links**: Use descriptive link text instead of "click here"

## Summary

Ye've learned:

1. How to structure documentation (Diataxis framework)
2. How to generate an MkDocs site with amplihack
3. How to validate documentation quality (three-pass validation)
4. How to deploy to GitHub Pages
5. How to configure GitHub Pages settings

**Key Files Created**:

- `docs/` - Documentation source
- `generate_docs.py` - Site generation script
- `validate_docs.py` - Quality validation script
- `deploy_docs.py` - Deployment script

**Commands to Remember**:

```bash
python generate_docs.py   # Generate site
mkdocs serve              # Preview locally
python validate_docs.py   # Check quality
python deploy_docs.py     # Deploy to GitHub
```

## Learn More

- [GitHub Pages Generation How-To](../howto/github-pages-generation.md) - Detailed task guides
- [GitHub Pages API Reference](../reference/github-pages-api.md) - Complete API docs
- [Documentation Guidelines](../../DOCUMENTATION_GUIDELINES.md) - Eight rules for good docs
- [MkDocs Documentation](https://www.mkdocs.org/) - Official MkDocs docs
- [Material Theme](https://squidfunk.github.io/mkdocs-material/) - Material theme docs
