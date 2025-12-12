# Pre-commit Workflow Tool

A Python tool for managing pre-commit hook failures efficiently.

## Features

- **Analyze failures**: Identify which hooks are failing and categorize them
- **Auto-fix**: Automatically fix formatting issues with supported tools
- **Environment verification**: Check pre-commit setup and dependencies
- **Success verification**: Run all pre-commit checks and report status

## Usage

### Command Line Interface

```bash
# Analyze current pre-commit failures
python .claude/tools/precommit_workflow.py analyze

# Auto-fix formatting issues (tries common tools)
python .claude/tools/precommit_workflow.py auto-fix

# Auto-fix with specific tools
python .claude/tools/precommit_workflow.py auto-fix --tools prettier,ruff

# Verify pre-commit environment setup
python .claude/tools/precommit_workflow.py verify-env

# Verify all pre-commit checks pass
python .claude/tools/precommit_workflow.py verify-success
```

### Python API

```python
from claude.tools.precommit_workflow import PreCommitWorkflow

workflow = PreCommitWorkflow()

# Analyze failures
analysis = workflow.analyze_failures()
print(f"Failed hooks: {analysis['failed_hooks']}")
print(f"Auto-fixable: {analysis['fixable']}")

# Auto-fix issues
success = workflow.auto_fix(tools=["ruff", "prettier"])

# Verify environment
checks = workflow.verify_environment()

# Verify all checks pass
all_pass = workflow.verify_success()
```

## Supported Auto-fix Tools

- **Python**: ruff, black, isort, autopep8
- **JavaScript/TypeScript**: prettier, eslint
- **Rust**: rustfmt

## Example Workflow

1. When pre-commit fails, run `analyze` to understand issues
2. Run `auto-fix` to fix formatting issues automatically
3. Run `verify-success` to confirm all checks pass
4. If issues persist, check `verify-env` to ensure tools are installed
