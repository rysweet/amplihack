# PR Triage Automation

Automated PR validation, compliance checking, and triage reporting for GitHub pull requests.

## Overview

This package provides automated PR triage that validates workflow compliance, detects priority/complexity, identifies unrelated changes, and posts comprehensive triage reports as PR comments.

## Architecture

### MVP Implementation (Default)

By default, the system uses **heuristic-based analysis** for fast, deterministic validation without requiring Claude CLI:

```
pr_triage/
├── __init__.py              # Public interface
├── validator.py             # Main orchestrator
├── analyzers_mvp.py         # Heuristic-based analyzers (DEFAULT)
├── analyzers.py             # Claude-based analyzers (optional)
├── security.py              # Security validation
├── github_client.py         # GitHub API operations
├── report_generator.py      # Report formatting
├── formatters.py            # Data formatting utilities
├── claude_runner.py         # Claude CLI runner (optional)
└── tests/                   # Test suite
```

### Switching to Claude-Based Analysis

To use Claude AI for more sophisticated analysis:

```bash
export USE_CLAUDE_ANALYZERS=1
```

## Security Controls

Implements comprehensive security controls per requirements:

- **M1.2**: Input validation for PR numbers, data structures
- **M2.1**: Sanitization of markdown content to prevent injection
- **M3.1**: Read-only GitHub operations
- **M3.2**: Label operations limited to allowed prefixes
- **M3.4**: Clear validation rules with audit logging

See `security.py` for full implementation.

## Usage

### Command Line

```bash
# Set PR number
export PR_NUMBER=123

# Run triage
python3 .github/scripts/pr_triage_main.py
```

### GitHub Actions

```yaml
- name: PR Triage
  env:
    PR_NUMBER: ${{ github.event.pull_request.number }}
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: python3 .github/scripts/pr_triage_main.py
```

### Programmatic

```python
from pr_triage import PRTriageValidator

validator = PRTriageValidator(pr_number=123)

# Fetch PR data
pr_data = validator.get_pr_data()

# Run validations
compliance = validator.validate_workflow_compliance(pr_data)
labels = validator.detect_priority_complexity(pr_data)
unrelated = validator.detect_unrelated_changes(pr_data)

# Generate and post report
report = validator.generate_triage_report(pr_data, compliance, labels, unrelated)
validator.post_report(report)

# Apply labels
validator.apply_labels(labels)

# Handle non-compliance
if not compliance["overall_compliant"]:
    validator.return_to_draft()
```

## MVP Heuristics

### Workflow Compliance

**Step 11 (Review)** - Requires review score >= 5 from:

- Approved reviews (+5 each)
- Review keywords: "code review", "security review", "lgtm", etc. (+1 each)

**Step 12 (Feedback)** - Requires response score >= 3 from:

- Response keywords: "addressed", "fixed", "updated", "implemented", etc.
- Or 5+ total comments

### Priority Detection

- **CRITICAL**: Contains "security", "critical", "urgent", "vulnerability"
- **HIGH**: Contains "bug", "fix", "error", "crash"
- **LOW**: Contains "docs", "documentation", "typo", "cleanup"
- **MEDIUM**: Default

### Complexity Detection

- **SIMPLE**: 1 file, < 50 lines
- **MODERATE**: <= 3 files, < 200 lines
- **COMPLEX**: <= 10 files, < 500 lines
- **VERY_COMPLEX**: > 10 files or > 500 lines or architectural changes

### Unrelated Changes

Detected when PR has 3+ file categories:

- Documentation
- Tests
- Configuration
- Core code
- Workflows

## Testing

```bash
cd .github/scripts
export PYTHONPATH=.

# Run all tests
python3 -m pytest pr_triage/tests/ -v

# Run specific test module
python3 -m pytest pr_triage/tests/test_security.py -v
python3 -m pytest pr_triage/tests/test_analyzers_mvp.py -v
```

## Output

### Triage Report

Posted as PR comment with:

- ✅/❌ Workflow compliance status
- 🏷️ Priority and complexity labels
- 🔍 Unrelated changes detection
- 💡 Recommendations
- 📊 Statistics

### Audit Log

Security audit trail in `~/.amplihack/.claude/runtime/logs/pr-triage-{number}/audit.log`:

```
[2025-11-23 23:45:12] PR-123 | get_pr_data | success | {'num_files': 5}
[2025-11-23 23:45:15] PR-123 | apply_labels | success | {'labels': ['priority:high', 'complexity:moderate']}
[2025-11-23 23:45:16] PR-123 | post_report | success
```

### Log File

Detailed execution log in `~/.amplihack/.claude/runtime/logs/pr-triage-{number}/triage.log`:

```
[23:45:12] [INFO] [PR-123] Fetching PR data...
[23:45:13] [INFO] [PR-123] Validating workflow compliance...
[23:45:14] [INFO] [PR-123] Detecting priority and complexity...
[23:45:15] [INFO] [PR-123] Applying labels...
[23:45:16] [INFO] [PR-123] Posted triage report to PR #123
[23:45:16] [INFO] [PR-123] PR triage completed successfully
```

## Error Handling

- **Validation errors**: Logged with details, execution continues where safe
- **GitHub API errors**: Logged as warnings, non-critical operations continue
- **Security violations**: Immediately raise ValueError with audit trail
- **All operations**: Wrapped in try-except with logging

## Module Boundaries

### Public Interface (`__init__.py`)

```python
from .validator import PRTriageValidator
__all__ = ["PRTriageValidator"]
```

### Module Responsibilities

- **validator.py**: Orchestration and workflow
- **analyzers_mvp.py**: Heuristic analysis logic
- **security.py**: All security validations
- **github_client.py**: GitHub API operations via gh CLI
- **report_generator.py**: Report formatting
- **formatters.py**: Data formatting utilities

## Dependencies

- Python 3.11+
- `gh` CLI (GitHub CLI) - must be authenticated
- `pytest` (for tests)

No external Python dependencies required for MVP mode.

## Future Enhancements

1. **Claude Integration**: More sophisticated analysis when enabled
2. **Auto-fix**: Spawn Claude agent to fix compliance issues
3. **Machine Learning**: Train model on historical PRs
4. **Custom Rules**: User-defined validation rules
5. **Metrics Dashboard**: Track PR health over time

## Philosophy Alignment

- **Zero-BS**: No stubs, all functions work or don't exist
- **Modular**: Clear module boundaries and responsibilities
- **Security First**: Comprehensive input validation and sanitization
- **Fail-Safe**: Graceful degradation, never block PRs incorrectly
- **Testable**: 27 tests covering security and analysis logic
