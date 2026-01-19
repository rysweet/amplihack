# GitHub Pages Documentation Generation

A complete solution for generating, validating, and deploying documentation sites to GitHub Pages using MkDocs with the Material theme.

## Philosophy

- **Single responsibility**: Each module handles one concern (generate, validate, deploy)
- **Standard library when possible**: External deps only where necessary (mkdocs, pyyaml)
- **Self-contained and regeneratable**: Module can be rebuilt from this specification
- **Zero-BS**: No stubs, no placeholders - everything works

## Module Structure

```
github_pages/
├── __init__.py         # Public API (dataclasses + function exports)
├── generator.py        # Site generation with MkDocs
├── validator.py        # Three-pass documentation validation
├── deployer.py         # GitHub Pages deployment via gh-pages branch
├── mkdocs_config.py    # MkDocs configuration builder
├── tests/              # Comprehensive test suite
│   ├── conftest.py     # Shared fixtures
│   ├── test_generator.py
│   ├── test_validator.py
│   ├── test_deployer.py
│   ├── test_mkdocs_config.py
│   └── test_integration.py
└── README.md           # This file
```

## Public API

### Configuration Dataclasses

```python
from github_pages import SiteConfig, DeploymentConfig

# Site generation configuration
site_config = SiteConfig(
    project_name="My Project",
    project_url="https://github.com/user/repo",
    docs_dir="docs",           # Default
    output_dir="site",         # Default
    theme="material",          # Default
    theme_features=None,       # Optional custom features
    nav_structure=None,        # Optional custom navigation
)

# Deployment configuration
deploy_config = DeploymentConfig(
    site_dir="site",
    repo_path=".",             # Default
    commit_message="Update docs",  # Default
    force_push=False,          # Default - NEVER force by default
)
```

### Result Dataclasses

```python
from github_pages import GenerationResult, ValidationResult, DeploymentResult

# GenerationResult fields:
# - success: bool
# - site_dir: Path
# - pages: list[str]
# - errors: list[str]
# - warnings: list[str]
# - config_file: Path | None

# ValidationResult fields:
# - passed: bool
# - issues: list[ValidationIssue]
# - pass1_coverage: float (target: 100%)
# - pass2_clarity_score: float (target: >= 80%)
# - pass3_grounded_pct: float (target: >= 95%)

# DeploymentResult fields:
# - success: bool
# - branch: str (always "gh-pages")
# - commit_sha: str | None
# - url: str | None (GitHub Pages URL)
# - errors: list[str]
```

### Main Functions

```python
from github_pages import generate_site, validate_site, deploy_site, preview_locally

# Generate documentation site
result = generate_site(site_config)
if not result.success:
    print(f"Generation failed: {result.errors}")

# Validate documentation quality
validation = validate_site("site")
if not validation.passed:
    for issue in validation.issues:
        print(f"[{issue.severity}] {issue.message}")
        if issue.suggestion:
            print(f"  Suggestion: {issue.suggestion}")

# Deploy to GitHub Pages
deployment = deploy_site(deploy_config)
if deployment.success:
    print(f"Deployed to {deployment.url}")

# Start local preview server (blocks)
preview_locally("mkdocs.yml", port=8000)
```

## Three-Pass Validation

The validator implements three distinct validation passes:

### Pass 1: Coverage (Target: 100%)

- Verifies all specified features are documented
- If no features specified, checks that content exists
- Creates issues for undocumented features

### Pass 2: Clarity (Target: >= 80%)

- **Navigation depth**: <= 3 levels recommended
- **Heading quality**: Descriptive headings score higher
- **Link quality**: Contextful links (not "click here")
- **Structure**: No walls of text (paragraphs > 300 words)

Scoring weights:

- Navigation: 20%
- Headings: 30%
- Links: 20%
- Structure: 30%

### Pass 3: Reality (Target: >= 95%)

- **No future tense**: "will be", "coming soon" (unless in [PLANNED] section)
- **No TODOs**: Unfinished work markers
- **No placeholders**: foo/bar examples in code blocks

Content marked with `[PLANNED]` is excluded from reality checks.

## Usage Example

```python
from github_pages import (
    SiteConfig,
    DeploymentConfig,
    generate_site,
    validate_site,
    deploy_site,
)

# 1. Generate
config = SiteConfig(
    project_name="My Project",
    project_url="https://github.com/myorg/myproject",
)

gen_result = generate_site(config)
if not gen_result.success:
    raise RuntimeError(f"Generation failed: {gen_result.errors}")

# 2. Validate
val_result = validate_site(gen_result.site_dir)
print(f"Coverage: {val_result.pass1_coverage}%")
print(f"Clarity: {val_result.pass2_clarity_score}%")
print(f"Grounded: {val_result.pass3_grounded_pct}%")

if not val_result.passed:
    print("Validation issues:")
    for issue in val_result.issues:
        print(f"  [{issue.pass_number}] {issue.message}")

# 3. Deploy (only if validation passes)
if val_result.passed:
    deploy_config = DeploymentConfig(
        site_dir=str(gen_result.site_dir),
    )
    deploy_result = deploy_site(deploy_config)

    if deploy_result.success:
        print(f"Deployed to: {deploy_result.url}")
    else:
        print(f"Deployment failed: {deploy_result.errors}")
```

## Dependencies

Required packages:

- `mkdocs>=1.5.0`
- `mkdocs-material>=9.5.0`
- `pyyaml`

Install with:

```bash
pip install mkdocs mkdocs-material pyyaml
```

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Deploy Docs

on:
  push:
    branches: [main]
    paths: ["docs/**", "README.md"]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install mkdocs mkdocs-material pyyaml

      - name: Generate and validate
        run: |
          python -c "
          from github_pages import SiteConfig, generate_site, validate_site

          config = SiteConfig(
              project_name='${{ github.repository }}',
              project_url='https://github.com/${{ github.repository }}',
          )

          result = generate_site(config)
          assert result.success, f'Generation failed: {result.errors}'

          validation = validate_site(result.site_dir)
          for issue in validation.issues:
              print(f'[{issue.severity}] {issue.message}')

          assert validation.passed, 'Validation failed'
          "

      - name: Deploy
        run: |
          git config user.name github-actions
          git config user.email github-actions@github.com
          mkdocs gh-deploy --force
```

## Testing

Run the test suite:

```bash
cd .claude/skills/documentation-writing
PYTHONPATH=. python -m pytest github_pages/tests/ -v
```

Test structure follows the testing pyramid:

- 60% unit tests (fast, mocked dependencies)
- 30% integration tests (multiple components)
- 10% end-to-end tests (complete workflows)

## Error Handling

All functions provide clear error handling:

- `generate_site`: Raises `TypeError` for None config, `FileNotFoundError` for missing docs
- `validate_site`: Raises `FileNotFoundError` for missing site directory
- `deploy_site`: Raises `TypeError` for None config, `ValueError` for missing/empty site

Results include error lists for non-fatal issues that don't prevent operation.

## Safety Features

- **Never force push by default**: `force_push=False` in DeploymentConfig
- **Branch switching with rollback**: Returns to original branch on failure
- **Uncommitted changes warning**: Detects dirty working directory
- **Safe subprocess handling**: Timeouts and error capture for external commands
