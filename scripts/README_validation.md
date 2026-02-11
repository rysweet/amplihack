# Documentation Validation Infrastructure

Comprehensive validation system for documentation quality, enforced automatically in CI/CD.

## Overview

This validation infrastructure ensures documentation quality through multiple complementary validators:

| Validator | Purpose | When It Runs |
|-----------|---------|--------------|
| **validate_docs_policy.py** | Enforces documentation standards (no stubs, proper placement, discoverability) | On PR |
| **validate_docs_examples.py** | Validates code blocks compile and optionally execute correctly | On PR |
| **validate_docs_navigation.py** | Ensures mkdocs navigation structure is correct | On PR |
| **validate_gh_pages_links.py** | Comprehensive link validation for deployed sites and local files | On PR (local mode) |
| **link_checker.py** (existing) | Simple link validation with GitHub issue creation | Weekly |

## Quick Start

### Local Validation

```bash
# Policy validation (no stubs, proper structure)
python scripts/validate_docs_policy.py docs/

# Code examples validation (syntax only)
python scripts/validate_docs_examples.py docs/ --skip-execution

# Code examples validation (with Docker execution)
python scripts/validate_docs_examples.py docs/

# Navigation validation
python scripts/validate_docs_navigation.py

# Link validation (local files)
python scripts/validate_gh_pages_links.py --local docs/ --pragmatic
```

### CI/CD Integration

The validation runs automatically on every PR that touches documentation:

- **Workflow**: `.github/workflows/docs-validation.yml`
- **Trigger**: Changes to `docs/`, `**/*.md`, `mkdocs.yml`, or validation scripts
- **Result**: PR blocked if any validation fails

## Validation Scripts

### 1. validate_docs_policy.py

Enforces amplihack documentation standards.

**Checks:**
- ✅ No stub content (TODO, FIXME, TBD, empty sections)
- ✅ Documentation in `docs/` directory (with allowed exceptions)
- ✅ All docs linked from discoverable entry points (README.md, docs/index.md)
- ✅ Proper formatting (no excessive whitespace)

**Usage:**
```bash
python scripts/validate_docs_policy.py docs/
python scripts/validate_docs_policy.py docs/README.md --verbose
```

**Exit Codes:**
- `0`: All checks passed
- `1`: Policy violations found

### 2. validate_docs_examples.py

Validates code blocks in documentation.

**Two-Tier Validation:**
1. **Syntax Validation** (always): Checks code compiles
2. **Execution Validation** (opt-in): Runs code in Docker sandbox

**Security:**
- Docker isolation with read-only filesystem
- No network access during execution
- Resource limits (memory, CPU, time)

**Usage:**
```bash
# Syntax validation only (fast)
python scripts/validate_docs_examples.py docs/ --skip-execution

# Full validation with execution (requires Docker)
python scripts/validate_docs_examples.py docs/

# Opt-in execution for specific code blocks
# Add <!-- runnable --> marker before code block
```

**Supported Languages:**
- Python (syntax + execution)
- JavaScript/TypeScript (syntax only)
- Bash (syntax only)

**Exit Codes:**
- `0`: All code blocks valid
- `1`: Validation failures found

### 3. validate_docs_navigation.py

Validates mkdocs navigation structure.

**Checks:**
- ✅ Landing pages exist (README.md in each section)
- ✅ index.md has all required sections
- ✅ Phase files have breadcrumb navigation
- ✅ No orphaned files (everything linked from nav)

**Usage:**
```bash
python scripts/validate_docs_navigation.py
```

**Exit Codes:**
- `0`: Navigation valid
- `1`: Structure issues found

### 4. validate_gh_pages_links.py

Advanced link validator with two modes.

**Mode 1: Web Crawling** (for deployed sites)
```bash
python scripts/validate_gh_pages_links.py \
  --site-url https://rysweet.github.io/amplihack/
```

**Mode 2: Local File Validation** (for PR checks)
```bash
# Strict mode (fail on warnings)
python scripts/validate_gh_pages_links.py --local docs/ --strict

# Pragmatic mode (errors only)
python scripts/validate_gh_pages_links.py --local docs/ --pragmatic
```

**Security Features:**
- SSRF prevention (blocks private IPs, AWS metadata, DNS rebinding)
- Path traversal protection
- Circuit breaker for external requests
- Rate limiting

**Exit Codes:**
- `0`: All links valid
- `1`: Broken links found

## CI/CD Workflow Details

### Workflow: docs-validation.yml

```yaml
# Triggers
on:
  pull_request:
    paths:
      - "docs/**"
      - "**/*.md"
      - "mkdocs.yml"
  workflow_dispatch:

# Jobs (parallel)
jobs:
  validate-policy:      # Documentation standards
  validate-examples:    # Code block validation
  validate-navigation:  # mkdocs structure
  validate-links-local: # Link validation
  validation-summary:   # Aggregate results
```

### Job Timeouts

- Policy: 10 minutes
- Examples: 15 minutes (Docker setup time)
- Navigation: 5 minutes
- Links: 15 minutes (external requests)

### Required Dependencies

Added to `pyproject.toml` under `dev` extras:

```toml
dev = [
    "beautifulsoup4>=4.9.0",  # HTML/XML parsing
    "lxml>=4.6.0",            # XML parsing
    "pyyaml>=6.0.0",          # mkdocs validation
    # ... other dev deps
]
```

Install with:
```bash
pip install -e ".[dev]"
```

## Comparison: New vs Existing

### validate_gh_pages_links.py vs link_checker.py

| Feature | validate_gh_pages_links.py | link_checker.py |
|---------|---------------------------|-----------------|
| **Lines** | 1,434 | 462 |
| **Web crawling** | ✅ Full site crawler | ❌ |
| **Local validation** | ✅ Markdown files | ✅ Markdown files |
| **SSRF protection** | ✅ Comprehensive | ✅ Basic |
| **Circuit breaker** | ✅ | ❌ |
| **Retry logic** | ✅ Exponential backoff | ❌ |
| **Path traversal** | ✅ Protected | ❌ |
| **When runs** | PR (local mode) | Weekly (web mode) |
| **GitHub integration** | ❌ | ✅ Creates issues |

**Verdict**: Complementary, not duplicative
- Use `link_checker.py` for weekly automated checks with issue creation
- Use `validate_gh_pages_links.py` for comprehensive PR validation

## Troubleshooting

### Docker Not Available

If Docker is not available, code execution validation is skipped:

```
::warning::Docker not available, skipping execution validation
```

Syntax validation still runs. Install Docker to enable execution validation.

### Policy Violations

Common violations and fixes:

**Empty sections:**
```markdown
## Configuration

<!-- Remove empty headings or add content -->
```

**Stub markers:**
```markdown
TODO: Add implementation guide

<!-- Replace with actual content -->
```

**Files not in docs/:**
```
✗ Documentation file should be in docs/ directory: GUIDE.md

# Move file to docs/ directory
mv GUIDE.md docs/GUIDE.md
```

### Navigation Validation Failures

**Missing landing page:**
```
✗ Memory landing page not found: docs/memory/README.md

# Create the landing page
touch docs/memory/README.md
```

**Missing breadcrumbs:**
```
✗ Missing breadcrumbs in docs/ddd/00_planning.md

# Add breadcrumb navigation at top of file
[← Back to DDD Guide](README.md) | [DDD Overview](../README.md)
```

## Philosophy Alignment

This validation infrastructure follows amplihack principles:

- **Zero-BS Implementation**: All validators are fully functional, no stubs
- **Ruthless Simplicity**: Direct validation, clear error messages
- **Working Code Only**: Scripts tested and proven in practice
- **CI-First Design**: Built for automation, with local dev support
- **Security by Default**: SSRF protection, path traversal prevention, sandboxing

## Future Enhancements

Potential improvements (not currently implemented):

- [ ] Parallel link checking for faster validation
- [ ] Historical tracking of documentation quality metrics
- [ ] Auto-fix mode for common violations
- [ ] Integration with GitHub Pull Request reviews
- [ ] Support for more code block languages (Go, Rust, Java)
- [ ] Playwright integration for JavaScript execution

## Contributing

When adding new validation rules:

1. Add check to appropriate validator script
2. Add test coverage in `tests/test_validate_*.py`
3. Update this README with the new check
4. Test locally before submitting PR

## Related Documentation

- [GitHub Pages Link Validator README](README_gh_pages_validator.md)
- [Weekly Link Checker Workflow](../.github/workflows/docs-link-checker.yml)
- [Documentation Deployment Workflow](../.github/workflows/docs.yml)
