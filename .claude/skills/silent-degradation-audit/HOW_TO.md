# How to Use the Silent Degradation Audit Skill

Step-by-step guide to detecting silent failures in your codebase.

## Quick Start

```bash
/silent-degradation-audit /path/to/your/project
```

Runs multi-wave audit detecting 6 categories of silent failures.

## What You'll Find

The audit detects bugs where systems silently degrade instead of failing visibly:

- API errors returned as empty data
- Config errors using unsafe defaults
- Background jobs failing without alerts
- Tests that pass on both success AND failure
- Errors invisible to monitoring
- Functions that don't do what their names say

## Step 1: Run Your First Audit

```bash
cd ~/projects/my-api
/silent-degradation-audit .
```

**Output**: `.silent-degradation-report.md` with findings

## Step 2: Review Results

```bash
cat .silent-degradation-report.md
```

Example findings:

```
Wave 1: 27 findings

Critical (3):
- auth.py:45 - Exception returns None, caller treats as authenticated
- processor.py:123 - Background task fails, no alert
- config.py:67 - Missing API_KEY, uses "default"
```

## Step 3: Fix Issues

**Before**:

```python
def authenticate(token):
    try:
        return verify_token(token)
    except TokenExpired:
        return None  # Silent failure!
```

**After**:

```python
def authenticate(token):
    try:
        return verify_token(token)
    except TokenExpired:
        raise AuthenticationError("Token expired")
```

## Using Exclusion Lists

Create `.silent-degradation-exclusions.json`:

```json
[
  {
    "pattern": "tests/**/*.py",
    "reason": "Test fixtures intentionally silent",
    "type": "glob"
  }
]
```

## Multi-Language Projects

Automatically detects Python, JavaScript, TypeScript, Rust, Go, Java, C#, Ruby, PHP.

Each language has specific patterns:

- Python: `except: pass`
- JavaScript: `.catch(err => {})`
- Rust: `.unwrap()`
- Go: `_, _ = ...`

See `patterns.md` for complete list.

## Advanced Configuration

```bash
# Custom thresholds
/silent-degradation-audit . --convergence-absolute 5

# Specific categories only
/silent-degradation-audit . --categories dependency,config

# Debug mode
export AUDIT_DEBUG=1
/silent-degradation-audit .
```

## Integration with CI

```yaml
# .github/workflows/audit.yml
- name: Weekly audit
  run: /silent-degradation-audit .
```

## Troubleshooting

**No findings?** Check language detection in report header.

**Too many false positives?** Add to exclusion list.

**Takes too long?** Audit specific directories or reduce max waves.

## Next Steps

1. Fix Critical/High findings first
2. Re-run to verify convergence
3. Add tests for error paths
4. Add monitoring/alerts for silent failures

See `examples.md` for complete walkthroughs and `reference.md` for full API.
