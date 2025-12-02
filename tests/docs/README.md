# Documentation Structure Tests

Comprehensive test suite for validating documentation reorganization using Test-Driven Development (TDD) methodology.

## Philosophy

These tests embody the TDD principle: **write tests first, then implement changes**.

- Tests **WILL FAIL** before reorganization (expected!)
- Tests **SHOULD PASS** after reorganization (success!)
- Fast execution (< 10 seconds for full suite)
- Clear failure messages
- Reusable for ongoing validation

## Test Structure

### Testing Pyramid (60/30/10)

```
┌─────────────────────────────────────┐
│   E2E Tests (10%)                   │  Complete user journeys
│   - Full documentation health       │  1-2 tests
│   - User journey validation         │
├─────────────────────────────────────┤
│   Integration Tests (30%)           │  Multi-component validation
│   - Link validation across docs    │  4-5 tests
│   - Orphan detection               │
│   - Coverage checking               │
│   - Navigation depth                │
├─────────────────────────────────────┤
│   Unit Tests (60%)                  │  Fast, isolated validation
│   - Link extraction                │  10-15 tests
│   - Path resolution                │
│   - Filter logic                   │
└─────────────────────────────────────┘
```

## Quick Start

### Run All Tests

```bash
# From repo root
pytest tests/docs/test_documentation_structure.py -v

# Or with coverage
pytest tests/docs/test_documentation_structure.py -v --cov=tests/docs
```

### Run Specific Test Categories

```bash
# Unit tests only (fast)
pytest tests/docs/test_documentation_structure.py::TestLinkValidation -v
pytest tests/docs/test_documentation_structure.py::TestOrphanDetection -v

# Integration tests
pytest tests/docs/test_documentation_structure.py::TestDocumentationIntegration -v

# E2E tests (complete validation)
pytest tests/docs/test_documentation_structure.py::TestDocumentationE2E -v
```

### Run Individual Tests

```bash
# Link validation only
pytest tests/docs/test_documentation_structure.py::TestDocumentationIntegration::test_link_validation_on_real_docs -v

# Orphan detection only
pytest tests/docs/test_documentation_structure.py::TestDocumentationIntegration::test_orphan_detection_on_real_docs -v

# Coverage check only
pytest tests/docs/test_documentation_structure.py::TestDocumentationIntegration::test_feature_coverage -v

# Navigation depth only
pytest tests/docs/test_documentation_structure.py::TestDocumentationIntegration::test_navigation_depth -v
```

## Test Components

### 1. Link Validator (`DocLinkValidator`)

**Purpose**: Validates all markdown links in documentation.

**What it checks**:
- ✅ Internal links resolve to existing files
- ✅ Relative paths are correct
- ✅ Absolute paths from repo root work
- ✅ External links are skipped (not validated)
- ✅ Anchor-only links are valid

**Usage**:
```python
from test_documentation_structure import DocLinkValidator

validator = DocLinkValidator(Path("docs"))
broken_links = validator.validate_all_links()
print(validator.get_summary())
```

**Expected failures before reorganization**:
- Broken relative paths
- Files moved without updating links
- Typos in file names
- Links to deleted files

---

### 2. Orphan Detector (`OrphanDetector`)

**Purpose**: Finds documentation files not reachable from index.md.

**What it checks**:
- ✅ All docs are linked from index.md (directly or transitively)
- ✅ No "dead" documentation files
- ✅ Complete link graph from index

**Usage**:
```python
from test_documentation_structure import OrphanDetector

detector = OrphanDetector(Path("docs"))
orphans = detector.find_orphans()
print(detector.get_summary())
```

**Expected failures before reorganization**:
- Old docs not linked from index
- Documentation in subdirectories without parent links
- Archived files not moved to archive/

---

### 3. Coverage Checker (`CoverageChecker`)

**Purpose**: Verifies all major features are documented.

**What it checks**:
- ✅ Goal-seeking agents (user's explicit requirement!)
- ✅ Core workflows (DEFAULT, INVESTIGATION, DDD)
- ✅ Core agents (architect, builder, tester)
- ✅ Commands (/ultrathink, /analyze, etc.)
- ✅ Memory systems (Neo4j)

**Usage**:
```python
from test_documentation_structure import CoverageChecker

checker = CoverageChecker(Path("docs"))
coverage = checker.check_coverage()
print(checker.get_summary())
```

**Expected failures before reorganization**:
- Goal-seeking agents not prominently featured
- Some features buried in subsections
- Missing keywords in index

---

### 4. Navigation Depth Checker (`NavigationDepthChecker`)

**Purpose**: Ensures all docs are accessible within 3 clicks from index.

**What it checks**:
- ✅ All documents reachable from index.md
- ✅ Navigation depth ≤ 3 clicks
- ✅ No deeply buried documentation

**Usage**:
```python
from test_documentation_structure import NavigationDepthChecker

checker = NavigationDepthChecker(Path("docs"))
deep_docs = checker.find_deep_docs(threshold=3)
print(checker.get_summary())
```

**Expected failures before reorganization**:
- Some docs 4-5 clicks deep
- Nested subdirectories without shortcuts
- Missing direct links from index

---

## Pass/Fail Criteria

### Pre-Reorganization (Expected: FAIL)

These tests SHOULD fail initially - that proves we're solving a real problem!

**Expected failures**:
- ❌ 10-20 broken links
- ❌ 15-30 orphaned documents
- ❌ 1-2 missing major features
- ❌ 10-20 documents beyond 3-click depth

### Post-Reorganization (Expected: PASS)

After reorganization, ALL tests should pass:

- ✅ Zero broken links
- ✅ Zero orphaned documents
- ✅ All major features documented
- ✅ All documents within 3 clicks

## Manual Testing

Automated tests catch structural issues, but human testing catches UX issues.

**See**: `MANUAL_TEST_PLAN.md` for complete manual testing procedures.

**Key manual tests**:
1. New user experience (can they get started quickly?)
2. Goal-seeking agent discoverability (user's explicit requirement)
3. Link integrity (random clicking doesn't hit 404s)
4. Information architecture (logical grouping)

## CI/CD Integration

Add to GitHub Actions or other CI:

```yaml
- name: Validate Documentation Structure
  run: |
    pytest tests/docs/test_documentation_structure.py -v --tb=short
```

**When to run**:
- On every PR that touches `docs/`
- Before each release
- Nightly builds (catch link rot)

## Troubleshooting

### Tests Pass But Should Fail

If tests pass before reorganization, check:
1. Are you running from correct directory?
2. Is `docs/` path correct?
3. Are test thresholds too lenient?

### Tests Fail After Reorganization

Common issues and fixes:

**Broken Links**:
```bash
# Run link validator to see specific failures
pytest tests/docs/test_documentation_structure.py::TestDocumentationIntegration::test_link_validation_on_real_docs -v

# Fix broken links, then re-run
```

**Orphans**:
```bash
# Run orphan detector
pytest tests/docs/test_documentation_structure.py::TestDocumentationIntegration::test_orphan_detection_on_real_docs -v

# For each orphan: add link from parent doc or move to archive/
```

**Coverage Gaps**:
```bash
# Run coverage checker
pytest tests/docs/test_documentation_structure.py::TestDocumentationIntegration::test_feature_coverage -v

# Add missing features to index.md with links
```

**Deep Navigation**:
```bash
# Run depth checker
pytest tests/docs/test_documentation_structure.py::TestDocumentationIntegration::test_navigation_depth -v

# Add direct links from index.md for deeply nested docs
```

## Extending the Tests

### Adding New Feature Coverage

Edit `CoverageChecker.required_features` in `test_documentation_structure.py`:

```python
self.required_features = {
    # ... existing features ...
    'new-feature': [
        'keyword1',
        'keyword2',
        'alternative-name'
    ],
}
```

### Adjusting Navigation Depth

Change threshold in tests:

```python
# More strict (2 clicks max)
deep_docs = checker.find_deep_docs(threshold=2)

# More lenient (4 clicks max)
deep_docs = checker.find_deep_docs(threshold=4)
```

### Adding Custom Validators

Follow the pattern:

```python
class CustomValidator:
    """Validates custom aspect of documentation."""

    def __init__(self, docs_dir: Path):
        self.docs_dir = docs_dir

    def validate(self) -> Dict[str, Any]:
        """Run validation."""
        # ... validation logic ...
        return results

    def get_summary(self) -> str:
        """Human-readable summary."""
        return summary_string
```

## Maintenance

### Weekly

- Run full test suite
- Review any new failures
- Update MANUAL_TEST_PLAN.md if needed

### Monthly

- Review test coverage
- Check for new features needing coverage
- Update `required_features` in `CoverageChecker`

### Before Each Release

- Full automated test suite
- Complete manual test plan
- Document any known issues in DISCOVERIES.md

## Philosophy Alignment

These tests follow amplihack's core principles:

✅ **Ruthless Simplicity**
- No complex frameworks
- Standard library + pytest
- < 500 lines of test code

✅ **Zero-BS Implementation**
- No stubs or placeholders
- Every function works or doesn't exist
- Real validation, real results

✅ **Modular Design**
- Each validator is self-contained
- Clear public API
- Easily testable components

✅ **TDD Approach**
- Tests written BEFORE implementation
- Tests define success criteria
- Red → Green → Refactor

## Success Metrics

**Before reorganization**:
- Test suite execution time: < 10 seconds
- Test coverage: 100% of validators
- Expected failures: 4 major categories

**After reorganization**:
- All tests passing
- Zero broken links
- Zero orphans
- Full feature coverage
- Navigation depth ≤ 3 clicks

## Questions?

See:
- `MANUAL_TEST_PLAN.md` - Manual testing procedures
- `test_documentation_structure.py` - Automated test implementation
- `/home/azureuser/src/amplihack/docs/DISCOVERIES.md` - Known issues and solutions

---

**Remember**: These tests are your safety net. They tell you if the reorganization is successful BEFORE users discover problems!
