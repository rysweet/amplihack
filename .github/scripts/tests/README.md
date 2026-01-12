# GitHub Scripts Tests

Test suite fer GitHub workflow scripts, followin' Test-Driven Development (TDD)
approach.

## Test Structure

Tests follow the **Testing Pyramid** distribution:

- **60% Unit Tests**: `test_date_parser.py` - Fast, isolated tests fer date
  parsing logic
- **30% Integration Tests**: `test_docs_cleanup.py` - Multi-component tests fer
  cleanup workflow
- **10% E2E Tests**: `test_docs_cleanup.py` - Complete workflow tests

## Test Files

### test_date_parser.py (Unit Tests - 60%)

Tests fer the `date_parser.py` module:

**DateParseResult Tests**:

- Data structure validation
- Valid/invalid state representation

**parse_discovery_date() Tests**:

- Valid ISO 8601 date parsing (with/without time)
- Missing date handling (conservative approach)
- Malformed date handling (conservative approach)
- Future date detection
- Various header format handling
- Empty header edge cases

**is_old_enough() Tests**:

- Exactly at cutoff boundary (6 months)
- Just under cutoff (5.9 months)
- Well past cutoff (7 months, 12 months)
- Timezone-aware date handling

**Total Unit Tests**: 15 scenarios

### test_docs_cleanup.py (Integration + E2E Tests - 40%)

Tests fer the `docs_cleanup.py` module:

**filter_entries_by_age() Tests** (Integration - 30%):

- Mixed age entries filtering
- All recent entries (nothing to remove)
- All old entries (everything removed)
- Conservative handling of missing dates
- Empty entries list edge case

**run_cleanup() Tests** (Integration - 30%):

- Dry-run mode (no file modifications)
- Actual cleanup mode (file modifications)
- Nonexistent file error handling
- File structure preservation

**End-to-End Tests** (10%):

- Complete workflow with realistic DISCOVERIES.md format
- Structure preservation across full workflow
- Claude API integration placeholder

**parse_discoveries_file() Helper Tests**:

- File structure parsing

**Data Structure Tests**:

- FilterResult structure validation
- CleanupResult structure validation

**Total Integration + E2E Tests**: 14 scenarios

## Running Tests

```bash
# Run all tests
python -m pytest .github/scripts/tests/ -v

# Run unit tests only
python -m pytest .github/scripts/tests/test_date_parser.py -v

# Run integration tests only
python -m pytest .github/scripts/tests/test_docs_cleanup.py -v

# Run with coverage
python -m pytest .github/scripts/tests/ --cov=.github/scripts --cov-report=html
```

## TDD Status

These tests were written BEFORE implementation and currently FAIL as expected:

- `test_date_parser.py`: ❌ ModuleNotFoundError: No module named 'date_parser'
- `test_docs_cleanup.py`: ❌ ModuleNotFoundError: No module named 'date_parser'

**Next Step**: Implement the modules to make these tests pass.

## Test Philosophy

Following amplihack's testing philosophy:

- **Conservative approach**: When in doubt, keep entries (don't delete)
- **Clear test purpose**: Each test has a single, clear responsibility
- **Fast execution**: All unit tests run in milliseconds
- **Strategic mocking**: Mock external dependencies, not business logic
- **Boundary testing**: Test edge cases and boundary conditions thoroughly

## Module Architecture

Tests validate these module contracts:

### date_parser.py

```python
@dataclass
class DateParseResult:
    valid: bool
    date: Optional[datetime]
    error: Optional[str]

def parse_discovery_date(header_line: str) -> DateParseResult:
    """Parse date from discovery header line."""

def is_old_enough(date, cutoff_months, reference_date) -> bool:
    """Check if date is older than cutoff."""
```

### docs_cleanup.py

```python
@dataclass
class FilterResult:
    old_entries: List[Dict]
    kept_entries: List[Dict]
    total_processed: int

@dataclass
class CleanupResult:
    entries_removed: int
    entries_kept: int
    dry_run: bool
    summary: str

def filter_entries_by_age(entries, cutoff_months, reference_date) -> FilterResult:
    """Filter entries by age."""

def run_cleanup(path, cutoff_months, dry_run, reference_date=None) -> CleanupResult:
    """Run cleanup workflow."""

def parse_discoveries_file(path) -> List[Dict]:
    """Parse DISCOVERIES.md into entry structures."""
```

## Coverage Goals

- **Line Coverage**: > 80%
- **Branch Coverage**: > 75%
- **Critical Paths**: 100% coverage (date parsing, age filtering)
