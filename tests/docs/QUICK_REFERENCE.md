# Documentation Tests - Quick Reference

Quick commands for running documentation structure tests.

## Prerequisites

```bash
# Install dependencies (if needed)
uv pip install pytest pytest-cov
```

## Quick Commands

### Run All Tests

```bash
# Full test suite
/home/azureuser/src/amplihack/.venv/bin/python -m pytest tests/docs/test_documentation_structure.py -v

# With detailed output
/home/azureuser/src/amplihack/.venv/bin/python -m pytest tests/docs/test_documentation_structure.py -vv
```

### Run Specific Checks

```bash
# Check for broken links only
/home/azureuser/src/amplihack/.venv/bin/python -m pytest tests/docs/test_documentation_structure.py::TestDocumentationIntegration::test_link_validation_on_real_docs -v

# Check for orphaned documents only
/home/azureuser/src/amplihack/.venv/bin/python -m pytest tests/docs/test_documentation_structure.py::TestDocumentationIntegration::test_orphan_detection_on_real_docs -v

# Check feature coverage only
/home/azureuser/src/amplihack/.venv/bin/python -m pytest tests/docs/test_documentation_structure.py::TestDocumentationIntegration::test_feature_coverage -v

# Check navigation depth only
/home/azureuser/src/amplihack/.venv/bin/python -m pytest tests/docs/test_documentation_structure.py::TestDocumentationIntegration::test_navigation_depth -v
```

### Run Complete Health Check

```bash
# E2E test with full report
/home/azureuser/src/amplihack/.venv/bin/python -m pytest tests/docs/test_documentation_structure.py::TestDocumentationE2E::test_complete_documentation_health -v
```

### Run Test Categories

```bash
# Unit tests only (fast)
/home/azureuser/src/amplihack/.venv/bin/python -m pytest tests/docs/test_documentation_structure.py::TestLinkValidation -v
/home/azureuser/src/amplihack/.venv/bin/python -m pytest tests/docs/test_documentation_structure.py::TestOrphanDetection -v

# Integration tests
/home/azureuser/src/amplihack/.venv/bin/python -m pytest tests/docs/test_documentation_structure.py::TestDocumentationIntegration -v

# E2E tests
/home/azureuser/src/amplihack/.venv/bin/python -m pytest tests/docs/test_documentation_structure.py::TestDocumentationE2E -v
```

## Expected Results

### Pre-Reorganization (CURRENT)

All tests SHOULD fail:

- ❌ 87 broken links
- ❌ 26 orphaned documents
- ❌ 8 documents beyond 3-click depth

### Post-Reorganization (TARGET)

All tests SHOULD pass:

- ✅ Zero broken links
- ✅ Zero orphaned documents
- ✅ All docs within 3 clicks

## Interpreting Output

### Success Example

```
tests/docs/test_documentation_structure.py::TestDocumentationIntegration::test_link_validation_on_real_docs PASSED [100%]

✓ All links valid across 135 documents
```

### Failure Example

```
tests/docs/test_documentation_structure.py::TestDocumentationIntegration::test_link_validation_on_real_docs FAILED [100%]

✗ Found 87 broken links:

  skills/SKILL_CATALOG.md
    Link: ../../.claude/runtime/logs/20251108_skills_research/RESEARCH.md
    Issue: Target not found: /home/azureuser/src/amplihack/...
```

## Troubleshooting

### "No module named pytest"

```bash
# Install pytest
uv pip install pytest pytest-cov

# Or use project venv
/home/azureuser/src/amplihack/.venv/bin/python -m pytest tests/docs/
```

### Tests Pass But Should Fail

Check you're in the correct directory:

```bash
pwd
# Should be: /home/azureuser/src/amplihack/worktrees/feat-issue-1824-gh-pages-docs-improvements
```

### Want More Details

```bash
# Increase verbosity
/home/azureuser/src/amplihack/.venv/bin/python -m pytest tests/docs/ -vv

# Show print statements
/home/azureuser/src/amplihack/.venv/bin/python -m pytest tests/docs/ -v -s

# Show full tracebacks
/home/azureuser/src/amplihack/.venv/bin/python -m pytest tests/docs/ -v --tb=long
```

## Manual Testing

After running automated tests, complete the manual test plan:

```bash
# Open manual test checklist
cat tests/docs/MANUAL_TEST_PLAN.md
```

## Files in This Directory

```
tests/docs/
├── test_documentation_structure.py  # Main automated tests
├── MANUAL_TEST_PLAN.md             # Human verification tests
├── README.md                        # Complete documentation
├── TEST_RESULTS_BASELINE.md        # Pre-reorganization results
└── QUICK_REFERENCE.md              # This file
```

## Common Workflows

### Daily Development

```bash
# Quick check before commit
/home/azureuser/src/amplihack/.venv/bin/python -m pytest tests/docs/test_documentation_structure.py::TestDocumentationIntegration::test_link_validation_on_real_docs -v
```

### Before PR

```bash
# Full test suite
/home/azureuser/src/amplihack/.venv/bin/python -m pytest tests/docs/ -v

# Complete manual checklist
open tests/docs/MANUAL_TEST_PLAN.md
```

### After Reorganization

```bash
# Full validation
/home/azureuser/src/amplihack/.venv/bin/python -m pytest tests/docs/ -v

# Should see all green ✅
```

## CI/CD Integration

Add to `.github/workflows/test.yml`:

```yaml
- name: Documentation Structure Tests
  run: |
    /home/azureuser/src/amplihack/.venv/bin/python -m pytest tests/docs/ -v --tb=short
```

## Questions?

See:

- **Complete docs**: `tests/docs/README.md`
- **Manual tests**: `tests/docs/MANUAL_TEST_PLAN.md`
- **Baseline results**: `tests/docs/TEST_RESULTS_BASELINE.md`
- **Test implementation**: `tests/docs/test_documentation_structure.py`
