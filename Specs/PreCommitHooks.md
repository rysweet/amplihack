# Pre-Commit Hooks Specification

## Overview

Automated code quality enforcement system using the pre-commit framework to ensure consistent code standards across Python, JavaScript/TypeScript, and documentation files.

## Architecture

### Core Components

1. **Pre-commit Framework**: Python-based git hooks manager
2. **Language-specific Tools**: Isolated virtual environments per tool
3. **Configuration Files**: YAML and JSON configs for tools
4. **Custom Hooks**: Project-specific philosophy compliance

### Hook Execution Flow

```
git commit → pre-commit → parallel hook execution → pass/fail → commit/abort
```

## Hooks Configuration

### Performance Tiers

**Tier 1: Ultra-Fast (<50ms)**

- trailing-whitespace
- end-of-file-fixer
- check-merge-conflict
- detect-private-key
- mixed-line-ending

**Tier 2: Fast (<200ms)**

- check-yaml
- check-json
- ruff (Python format/lint)

**Tier 3: Moderate (<500ms)**

- prettier (JS/TS/MD formatting)
- markdownlint
- pyright (type checking)

**Tier 4: Variable (on-demand)**

- pytest-changed (only changed tests)
- philosophy-check (custom)

### Language Support

#### Python

- **Formatting**: ruff format
- **Linting**: ruff (E, W, F, I, B, C4, UP, ARG, SIM rules)
- **Type Checking**: pyright (standard mode)
- **Testing**: pytest (changed files only)

#### JavaScript/TypeScript

- **Formatting**: prettier
- **Linting**: eslint (optional, not configured)

#### Markdown

- **Formatting**: prettier
- **Linting**: markdownlint

#### JSON/YAML

- **Formatting**: prettier
- **Validation**: check-json, check-yaml

## Installation

### Quick Start

```bash
# Run the installation script
./scripts/install-hooks.sh
```

### Manual Installation

```bash
# Install pre-commit
pip3 install --user pre-commit

# Install hooks in repository
pre-commit install

# Update hooks to latest versions
pre-commit autoupdate

# Create secrets baseline
detect-secrets scan > .secrets.baseline
```

## Usage

### Normal Workflow

```bash
# Stage changes
git add .

# Commit (hooks run automatically)
git commit -m "feat: add new feature"

# If hooks fail, fix issues and retry
git add .
git commit -m "feat: add new feature"
```

### Bypass Options

```bash
# Skip all hooks (emergency only)
git commit --no-verify -m "emergency: critical fix"

# Skip specific hooks
SKIP=pyright,pytest-changed git commit -m "wip: experimental changes"
```

### Manual Execution

```bash
# Run on staged files
pre-commit run

# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff

# Run on specific files
pre-commit run --files src/main.py tests/test_main.py
```

## Performance Optimization

### Strategies Implemented

1. **Parallel Execution**: Hooks run in parallel where possible
2. **File Filtering**: Only check changed files
3. **Caching**: Pre-commit caches environments and results
4. **Selective Testing**: Only run tests for changed code
5. **Fast Tools**: Prefer ruff over multiple Python tools

### Expected Times

- **Typical commit** (3-5 files): 1-2 seconds
- **Large commit** (20+ files): 3-5 seconds
- **Full repository scan**: 10-30 seconds

### Performance Tips

1. Use `SKIP` for WIP commits
2. Run `pre-commit run` before staging to catch issues early
3. Use `.pre-commit-config.yaml` excludes for generated files
4. Configure IDE to run formatters on save

## Error Messages

### Common Errors and Solutions

#### "Files were modified by this hook"

**Cause**: Auto-formatting changed files
**Solution**: Stage the changes and commit again

```bash
git add .
git commit
```

#### "pyright: error: Import could not be resolved"

**Cause**: Missing type stubs or dependencies
**Solution**: Install dependencies or ignore with `# type: ignore`

#### "Philosophy check failed: Function too complex"

**Cause**: Function exceeds complexity limits
**Solution**: Refactor into smaller functions

## Configuration Files

### File Locations

```
/Users/ryan/src/hackathon/MicrosoftHackathon2025-AgenticCoding/
├── .pre-commit-config.yaml    # Main pre-commit configuration
├── pyproject.toml             # Python tools config (ruff, pyright, pytest)
├── .prettierrc.json           # JavaScript/TypeScript/Markdown formatting
├── .markdownlint.json         # Markdown linting rules
├── .secrets.baseline          # Detected secrets baseline
└── scripts/
    ├── install-hooks.sh       # Installation helper
    └── uninstall-hooks.sh     # Removal helper
```

### Customization

#### Disable a Hook

```yaml
# In .pre-commit-config.yaml
- id: hook-name
  stages: [manual] # Only run when explicitly called
```

#### Add File Exclusions

```yaml
# In .pre-commit-config.yaml
- id: hook-name
  exclude: ^(path/to/exclude|another/path)
```

#### Adjust Tool Settings

```toml
# In pyproject.toml
[tool.ruff]
line-length = 120  # Change line length

[tool.pyright]
typeCheckingMode = "strict"  # Stricter type checking
```

## Troubleshooting

### Pre-commit Not Found

```bash
# Add to PATH
export PATH="$HOME/.local/bin:$PATH"
```

### Hooks Not Running

```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install
```

### Slow Performance

```bash
# Clear cache and reinstall
pre-commit clean
pre-commit install --install-hooks
```

### Version Conflicts

```bash
# Update all hooks
pre-commit autoupdate
pre-commit install --install-hooks
```

## Philosophy Alignment

This setup follows the project's ruthless simplicity principles:

1. **Single Tool per Task**: ruff for Python, prettier for formatting
2. **Fast Feedback**: Quick checks run first
3. **Clear Contracts**: Explicit configuration files
4. **No Hidden Magic**: All hooks visible in `.pre-commit-config.yaml`
5. **Progressive Enhancement**: Can bypass when needed

## Maintenance

### Regular Updates

```bash
# Monthly: Update hook versions
pre-commit autoupdate

# Quarterly: Review and adjust rules
# - Check for new useful hooks
# - Remove unused hooks
# - Adjust performance settings
```

### Adding New Hooks

1. Research the hook in pre-commit registry
2. Add to `.pre-commit-config.yaml`
3. Test on sample files
4. Document in this specification

## Summary

The pre-commit hooks system provides:

- ✅ Automatic code quality enforcement
- ✅ Fast execution (<2 seconds typical)
- ✅ Clear error messages
- ✅ Easy bypass for emergencies
- ✅ Multi-language support
- ✅ Philosophy compliance checking

Installation: `./scripts/install-hooks.sh`
Usage: Automatic on `git commit`
Bypass: `git commit --no-verify`
