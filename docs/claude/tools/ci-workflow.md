# CI Workflow Tool

A comprehensive CI workflow management tool that provides higher-level CI/CD functionality.

## Features

- **Parallel CI Diagnostics**: Run multiple checks simultaneously
- **Iterative Fix Application**: Automatically apply and test fixes
- **Status Polling**: Monitor CI status with exponential backoff
- **Local and Remote Checks**: Combines local validation with GitHub CI status

## Installation

The tool is located at `.claude/tools/ci_workflow.py` and can be used both as a Python module and a command-line tool.

## Command-Line Usage

### Diagnose CI Issues

Run comprehensive diagnostics to identify CI problems:

```bash
# Diagnose current branch
python .claude/tools/ci_workflow.py diagnose

# Diagnose specific PR
python .claude/tools/ci_workflow.py diagnose --pr 123

# Diagnose specific branch
python .claude/tools/ci_workflow.py diagnose --branch feature/new-feature

# Get JSON output
python .claude/tools/ci_workflow.py diagnose --json
```

### Iterate CI Fixes

Automatically attempt to fix CI issues with configurable retry logic:

```bash
# Default 5 attempts
python .claude/tools/ci_workflow.py iterate-fixes --pr 123

# Custom attempt limit
python .claude/tools/ci_workflow.py iterate-fixes --max-attempts 3 --pr 123

# JSON output for scripting
python .claude/tools/ci_workflow.py iterate-fixes --pr 123 --json
```

### Poll CI Status

Monitor CI status with intelligent polling and backoff:

```bash
# Poll current branch (5 minute default timeout)
python .claude/tools/ci_workflow.py poll-status

# Poll specific PR with custom timeout
python .claude/tools/ci_workflow.py poll-status 123 --timeout 600

# Disable exponential backoff
python .claude/tools/ci_workflow.py poll-status --no-backoff --interval 10

# JSON output for automation
python .claude/tools/ci_workflow.py poll-status --json
```

## Python API Usage

```python
from claude.tools.ci_workflow import diagnose_ci, iterate_fixes, poll_status

# Run diagnostics
result = diagnose_ci(pr_number=123)
print(f"Overall status: {result['overall_status']}")

# Iterate fixes
fixes_result = iterate_fixes(max_attempts=3, pr_number=123)
if fixes_result['success']:
    print("CI issues resolved!")

# Poll status
poll_result = poll_status(
    reference="123",  # PR number or branch
    timeout=300,       # 5 minutes
    exponential_backoff=True
)
print(f"Final status: {poll_result['final_status']}")
```

## Diagnostic Components

The `diagnose` command checks:

1. **CI Status**: GitHub Actions/CI status from PR or branch
2. **Lint Check**: Runs available linters (pre-commit, flake8, etc.)
3. **Test Check**: Executes test suites (pytest, unittest, etc.)
4. **Build Check**: Verifies build process (make, npm, cargo, etc.)

## Fix Iteration Strategy

The `iterate-fixes` command:

1. Runs diagnostics to identify issues
2. Applies automatic fixes based on issue type:
   - **Lint issues**: Runs auto-formatters (black, isort, pre-commit)
   - **Dependency issues**: Updates dependencies (npm install, pip install)
   - **Test failures**: Logs for manual intervention
3. Commits and pushes fixes
4. Re-runs diagnostics
5. Repeats until success or max attempts reached

## Polling Behavior

The `poll-status` command:

- Starts with specified interval (default 10s)
- Optionally applies exponential backoff (1.5x multiplier)
- Caps maximum interval at 60 seconds
- Exits when CI completes or timeout reached
- Returns appropriate exit codes for scripting

## Exit Codes

- `0`: Success (CI passing or command succeeded)
- `1`: Failure (CI failing or command failed)

## Integration with CI/CD Agents

This tool is designed to work with the CI/CD specialist agent (`.claude/agents/amplihack/cicd.md`) to provide automated CI management capabilities.

## Dependencies

- Python 3.7+
- GitHub CLI (`gh`) installed and authenticated
- Git configured with appropriate permissions
- Project-specific tools (linters, test runners, build tools)
