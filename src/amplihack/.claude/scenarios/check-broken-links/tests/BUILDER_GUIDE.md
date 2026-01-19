# Builder Guide: Implementing check-broken-links

**Ahoy builder! This guide be helpin' ye navigate the test-driven implementation.**

## Quick Start

1. Read `TEST_COVERAGE_SUMMARY.md` to understand what tests expect
2. Run tests frequently to see progress: `pytest tests/ -v`
3. Implement functions to make tests pass one by one
4. All tests should FAIL initially (TDD approach)

## Implementation Order (Recommended)

### Phase 1: Data Structures (10 minutes)

Create `link_checker.py` with core data structures:

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class BrokenLink:
    """Represents a broken link found during checking."""
    url: str
    status_code: int
    parent_url: str
    error_message: str

@dataclass
class LinkCheckReport:
    """Report of link checking results."""
    passed: bool
    checked_count: int
    broken_count: int
    broken_links: List[BrokenLink]
    error: bool
    error_message: Optional[str]
```

**Tests to pass:** `TestDataStructures` (2 tests)

### Phase 2: Subprocess Wrapper (20 minutes)

Implement safe subprocess wrapper following PATTERNS.md (lines 206-245):

```python
def safe_subprocess_call(
    cmd: List[str],
    context: str,
    timeout: Optional[int] = 30,
) -> Tuple[int, str, str]:
    """Safely execute subprocess with comprehensive error handling."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        # Return 127, include context in error message
        pass
    except subprocess.TimeoutExpired:
        # Return 124, include timeout info
        pass
    except Exception as e:
        # Return 1, generic error handling
        pass
```

**Tests to pass:** `TestSubprocessWrapper` (4 tests)

### Phase 3: Prerequisites (15 minutes)

Implement prerequisite checking following PATTERNS.md (lines 254-300):

```python
def check_prerequisites() -> PrerequisiteCheckResult:
    """Check if linkinator is installed."""
    linkinator_path = shutil.which("linkinator")
    if linkinator_path:
        # Get version, return success
        pass
    else:
        # Return error with install instructions
        pass

def get_install_instructions(tool: str) -> str:
    """Get platform-specific installation instructions."""
    return "npm install -g linkinator"
```

**Tests to pass:** `TestPrerequisiteChecking` (3 tests)

### Phase 4: Report Parsing (25 minutes)

Parse linkinator JSON output:

```python
def parse_linkinator_output(json_output: str) -> LinkCheckReport:
    """Parse linkinator JSON output into LinkCheckReport."""
    try:
        data = json.loads(json_output)
        passed = data.get("passed", False)
        links = data.get("links", [])

        broken_links = []
        for link in links:
            if link.get("state") == "BROKEN":
                broken_links.append(BrokenLink(
                    url=link["url"],
                    status_code=link.get("status", 0),
                    parent_url=link.get("parent", ""),
                    error_message=link.get("error", ""),
                ))

        return LinkCheckReport(
            passed=passed,
            checked_count=len(links),
            broken_count=len(broken_links),
            broken_links=broken_links,
            error=False,
            error_message=None,
        )
    except json.JSONDecodeError:
        # Return error report
        pass
    except Exception as e:
        # Return error report
        pass
```

**Tests to pass:** `TestReportParsing` (5 tests)

### Phase 5: Report Formatting (20 minutes)

Pretty text formatting:

```python
def format_report(report: LinkCheckReport) -> str:
    """Format LinkCheckReport into pretty text."""
    if report.error:
        return f"ERROR: {report.error_message}"

    output = []
    output.append(f"Checked {report.checked_count} links")

    if report.passed:
        output.append("✓ All links valid!")
    else:
        output.append(f"✗ Found {report.broken_count} broken links:")
        for broken_link in report.broken_links:
            output.append(f"  [{broken_link.status_code}] {broken_link.url}")
            output.append(f"      From: {broken_link.parent_url}")

    return "\n".join(output)
```

**Tests to pass:** `TestReportFormatting` (3 tests)

### Phase 6: check_site() Integration (30 minutes)

Main function for checking remote URLs:

```python
def check_site(url: str, timeout: int = 60) -> LinkCheckReport:
    """Check links on a remote site."""
    # 1. Check prerequisites
    prereqs = check_prerequisites()
    if not prereqs.linkinator_available:
        return LinkCheckReport(
            passed=False,
            checked_count=0,
            broken_count=0,
            broken_links=[],
            error=True,
            error_message=prereqs.error_message,
        )

    # 2. Call linkinator via subprocess
    returncode, stdout, stderr = safe_subprocess_call(
        ["linkinator", url, "--format", "json"],
        context=f"checking {url}",
        timeout=timeout,
    )

    # 3. Handle errors
    if returncode != 0:
        return LinkCheckReport(
            passed=False,
            checked_count=0,
            broken_count=0,
            broken_links=[],
            error=True,
            error_message=stderr,
        )

    # 4. Parse output
    return parse_linkinator_output(stdout)
```

**Tests to pass:** `TestCheckSiteIntegration` (4 tests)

### Phase 7: check_local() Integration (20 minutes)

Function for checking local files:

```python
def check_local(path: Path) -> LinkCheckReport:
    """Check links in local files."""
    # 1. Validate path exists
    if not path.exists():
        return LinkCheckReport(
            passed=False,
            checked_count=0,
            broken_count=0,
            broken_links=[],
            error=True,
            error_message=f"Path does not exist: {path}",
        )

    # 2. Convert to absolute path
    abs_path = path.resolve()

    # 3. Call check_site with file:// URL
    file_url = f"file://{abs_path}"
    return check_site(file_url)
```

**Tests to pass:** `TestCheckLocalIntegration` (3 tests)

### Phase 8: Exit Codes (10 minutes)

Exit code logic:

```python
def get_exit_code(report: LinkCheckReport) -> int:
    """Determine exit code from report."""
    if report.error:
        return 2  # Error occurred
    elif not report.passed:
        return 1  # Broken links found
    else:
        return 0  # All links valid
```

**Tests to pass:** `TestExitCodes` (3 tests)

### Phase 9: Error Boundaries (15 minutes)

Additional error handling:

```python
# Add URL validation to check_site()
def check_site(url: str, timeout: int = 60) -> LinkCheckReport:
    # Validate URL format
    if not url.startswith(("http://", "https://", "file://")):
        return LinkCheckReport(
            passed=False,
            checked_count=0,
            broken_count=0,
            broken_links=[],
            error=True,
            error_message=f"Invalid URL format: {url}",
        )
    # ... rest of implementation
```

**Tests to pass:** `TestErrorBoundaries` (3 tests)

## Running Tests During Implementation

```bash
# Run all tests (will see failures decrease as you implement)
pytest .claude/scenarios/check-broken-links/tests/ -v

# Run specific test class
pytest .claude/scenarios/check-broken-links/tests/test_link_checker.py::TestDataStructures -v

# Run with output (see print statements)
pytest .claude/scenarios/check-broken-links/tests/ -v -s

# Stop on first failure
pytest .claude/scenarios/check-broken-links/tests/ -v -x
```

## Test Progress Tracking

Use this checklist to track implementation progress:

### Unit Tests (18 tests)

- [ ] TestPrerequisiteChecking (3 tests)
- [ ] TestSubprocessWrapper (4 tests)
- [ ] TestReportParsing (5 tests)
- [ ] TestReportFormatting (3 tests)
- [ ] TestDataStructures (2 tests)
- [ ] TestExitCodes (3 tests)

### Integration Tests (8 tests)

- [ ] TestCheckSiteIntegration (4 tests)
- [ ] TestCheckLocalIntegration (3 tests)
- [ ] TestEndToEndReportFlow (1 test)

### Error Tests (3 tests)

- [ ] TestErrorBoundaries (3 tests)

### Documentation Tests

- [ ] test_docs_step_count_references.py (should pass if issue #1886 fixed)

## Common Pitfalls to Avoid

1. **Don't skip error handling** - Tests expect comprehensive error messages
2. **Include context in errors** - Use the `context` parameter in subprocess calls
3. **Mock external dependencies** - Tests mock subprocess.run, don't call real linkinator
4. **Return proper exit codes** - 0=success, 1=broken links, 2=error
5. **Handle edge cases** - Empty output, invalid JSON, malformed URLs

## Key Patterns from PATTERNS.md

- **Safe Subprocess Wrapper** (lines 206-245) - Error handling template
- **Fail-Fast Prerequisites** (lines 254-300) - Check deps at startup
- **TDD Testing Pyramid** (lines 337-382) - 60/30/10 distribution

## Expected Timeline

- **Total implementation time:** ~3 hours
- **Phase 1-3:** ~45 minutes (foundations)
- **Phase 4-5:** ~45 minutes (parsing and formatting)
- **Phase 6-7:** ~50 minutes (main functionality)
- **Phase 8-9:** ~25 minutes (exit codes and error handling)
- **Testing and polish:** ~15 minutes

## Success Criteria

✓ All 26 unit/integration tests pass
✓ 3 E2E tests remain skipped (will implement with real linkinator later)
✓ Tests run in < 5 seconds
✓ No real external calls during tests (all mocked)
✓ Clear error messages for all failure modes

## Questions?

Refer to:

- `TEST_COVERAGE_SUMMARY.md` - Complete test breakdown
- `.claude/context/PATTERNS.md` - Implementation patterns
- Architect specs - Module design and API

Good luck, and may yer code be bug-free! 🏴‍☠️
