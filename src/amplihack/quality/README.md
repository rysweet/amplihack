# Quality Checking Module

Post-tool-use quality validation for various file types.

## Overview

The quality module provides automatic quality checking for files modified by Write/Edit operations in Claude Code. It integrates with the PostToolUse hook to run linters and validators immediately after file modifications.

## Features

- **Multiple Validators**: Support for Python (Ruff), Shell (ShellCheck), Markdown (markdownlint), YAML (yamllint), and JSON
- **Graceful Degradation**: Works even when external tools are not installed
- **Fast Mode**: Quick checks with configurable timeouts (< 5s default)
- **Configurable**: Via pyproject.toml and environment variables
- **Exclusion Patterns**: Skip unwanted directories (e.g., __pycache__, .venv)

## Configuration

### pyproject.toml

```toml
[tool.amplihack.quality]
enabled = true
fast_mode = true
fast_mode_timeout = 5
full_mode_timeout = 30
validators = ["python", "shell", "markdown", "yaml", "json"]
exclude = [
    "**/__pycache__/**",
    "**/.venv/**",
    "**/venv/**",
    "**/.git/**",
]
severity = ["error", "warning"]
```

### Environment Variables

Override configuration at runtime:

```bash
export AMPLIHACK_QUALITY_ENABLED=true
export AMPLIHACK_QUALITY_FAST_MODE=true
export AMPLIHACK_QUALITY_FAST_TIMEOUT=5
export AMPLIHACK_QUALITY_FULL_TIMEOUT=30
export AMPLIHACK_QUALITY_VALIDATORS=python,json
```

## Usage

### Programmatic Usage

```python
from amplihack.quality import QualityChecker, QualityConfig

# Use default configuration
checker = QualityChecker()
result = checker.check_file(Path("test.py"))

if not result.passed:
    print(f"Found {result.error_count} errors")
    for issue in result.issues:
        print(f"  {issue}")

# Use custom configuration
config = QualityConfig(fast_mode=True, validators=["python", "json"])
checker = QualityChecker(config)
results = checker.check_files([Path("file1.py"), Path("file2.json")])

# Generate summary
summary = checker.get_summary(results)
print(f"Checked {summary['total_files']} files")
print(f"Passed: {summary['passed']}, Failed: {summary['failed']}")
```

### PostToolUse Hook Integration

Quality checks run automatically after Write/Edit operations. Results appear in hook logs:

```
Tool used: Write
Quality check failed for test.py: Quality check found 2 errors and 1 warnings
```

## Validators

### Python Validator

Uses Ruff for fast Python linting.

- **Tool**: ruff
- **Extensions**: .py, .pyi
- **Install**: `pip install ruff`

### Shell Validator

Uses ShellCheck for shell script validation.

- **Tool**: shellcheck
- **Extensions**: .sh, .bash
- **Install**: `apt-get install shellcheck` or `brew install shellcheck`

### Markdown Validator

Uses markdownlint for Markdown checking.

- **Tool**: markdownlint-cli
- **Extensions**: .md, .markdown
- **Install**: `npm install -g markdownlint-cli`

### YAML Validator

Uses yamllint for YAML validation.

- **Tool**: yamllint
- **Extensions**: .yaml, .yml
- **Install**: `pip install yamllint`

### JSON Validator

Uses Python's built-in JSON parser (always available).

- **Tool**: Python json module
- **Extensions**: .json
- **Install**: Built-in (no installation needed)

## Performance

- **Fast Mode**: < 5s timeout per file (default)
- **Full Mode**: < 30s timeout per file
- **Batch Processing**: Efficiently validates multiple files
- **Graceful Degradation**: Skips unavailable validators without errors

## Testing

Run tests with pytest:

```bash
# Unit tests
pytest src/amplihack/quality/tests/test_config.py
pytest src/amplihack/quality/tests/test_validators.py
pytest src/amplihack/quality/tests/test_checker.py

# Integration tests
pytest src/amplihack/quality/tests/test_integration.py -m integration

# E2E tests
pytest src/amplihack/quality/tests/test_e2e.py -m e2e

# All tests
pytest src/amplihack/quality/tests/
```

## Architecture

```
quality/
├── __init__.py              # Public API
├── checker.py               # Orchestrator with file-type detection
├── config.py                # Configuration management
├── validators/
│   ├── __init__.py
│   ├── base_validator.py    # Abstract base class
│   ├── python_validator.py  # Ruff integration
│   ├── shell_validator.py   # ShellCheck integration
│   ├── markdown_validator.py # markdownlint integration
│   ├── yaml_validator.py    # yamllint integration
│   └── json_validator.py    # Built-in JSON validation
└── tests/
    ├── test_config.py       # Config tests
    ├── test_validators.py   # Validator tests
    ├── test_checker.py      # Orchestrator tests
    ├── test_integration.py  # Integration tests
    └── test_e2e.py          # End-to-end tests
```

## Extending

To add a new validator:

1. Create validator class inheriting from `BaseValidator`
2. Implement required methods: `name()`, `supported_extensions()`, `is_available()`, `validate()`
3. Add to `VALIDATOR_MAP` in `checker.py`
4. Update configuration defaults in `config.py`

Example:

```python
from .base_validator import BaseValidator, ValidationResult

class CustomValidator(BaseValidator):
    def name(self) -> str:
        return "custom"

    def supported_extensions(self) -> List[str]:
        return [".custom"]

    def is_available(self) -> bool:
        # Check if tool is installed
        return True

    def validate(self, file_path: Path) -> ValidationResult:
        # Run validation logic
        return ValidationResult(...)
```
