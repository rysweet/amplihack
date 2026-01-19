# Test Coverage Summary for check-broken-links

## Overview

Comprehensive test suite written following TDD approach for issue #1886. All tests are designed to **FAIL INITIALLY** to guide implementation.

## Testing Pyramid Distribution

Following amplihack testing philosophy:

- **60% Unit Tests** (fast, heavily mocked) - 18 tests
- **30% Integration Tests** (multiple components) - 8 tests
- **10% E2E Tests** (complete workflows) - 3 tests

**Total: 29 tests covering all major functionality**

## Test Files

### 1. `test_link_checker.py` - Main test suite

Comprehensive tests for the check-broken-links module with strategic mocking.

#### Unit Tests (18 tests - 60%)

**Prerequisite Checking (3 tests)**

- ✓ `test_check_linkinator_installed_when_available` - Detects linkinator in PATH
- ✓ `test_check_linkinator_missing_when_not_installed` - Detects missing linkinator
- ✓ `test_prerequisite_check_includes_installation_instructions` - Platform-specific install guidance

**Subprocess Wrapper (4 tests)**

- ✓ `test_safe_subprocess_call_returns_success` - Returns (0, stdout, stderr) on success
- ✓ `test_safe_subprocess_call_handles_command_not_found` - Returns 127 with helpful message
- ✓ `test_safe_subprocess_call_handles_timeout` - Returns 124 with timeout info
- ✓ `test_safe_subprocess_call_provides_context_in_errors` - Includes context in all errors

**Report Parsing (5 tests)**

- ✓ `test_parse_linkinator_report_with_no_broken_links` - Parses successful JSON
- ✓ `test_parse_linkinator_report_with_broken_links` - Detects broken links in JSON
- ✓ `test_parse_linkinator_report_handles_invalid_json` - Graceful JSON error handling
- ✓ `test_parse_linkinator_report_handles_empty_output` - Handles empty output

**Report Formatting (3 tests)**

- ✓ `test_format_report_with_no_broken_links` - Pretty text for success
- ✓ `test_format_report_with_broken_links` - Pretty text with broken link details
- ✓ `test_format_report_includes_summary_statistics` - Includes total/broken/success rate

**Data Structures (2 tests)**

- ✓ `test_link_check_report_structure` - Verifies LinkCheckReport fields
- ✓ `test_broken_link_structure` - Verifies BrokenLink fields

**Exit Codes (3 tests)**

- ✓ `test_exit_code_zero_when_all_links_pass` - Returns 0 for success
- ✓ `test_exit_code_one_when_broken_links_found` - Returns 1 for broken links
- ✓ `test_exit_code_two_when_error_occurs` - Returns 2 for errors

#### Integration Tests (8 tests - 30%)

**check_site() Integration (4 tests)**

- ✓ `test_check_site_calls_linkinator_with_correct_args` - Correct subprocess invocation
- ✓ `test_check_site_returns_error_report_when_linkinator_fails` - Error handling
- ✓ `test_check_site_respects_timeout_parameter` - Timeout passed to subprocess
- ✓ `test_check_site_with_broken_links_returns_failed_report` - End-to-end broken link flow

**check_local() Integration (3 tests)**

- ✓ `test_check_local_calls_linkinator_with_file_path` - Local path handling
- ✓ `test_check_local_validates_path_exists` - Path validation
- ✓ `test_check_local_handles_relative_paths` - Relative to absolute conversion

**End-to-End Report Flow (1 test)**

- ✓ `test_full_flow_from_check_to_formatted_output` - Complete check → format flow

#### E2E Tests (3 tests - 10%)

**Real linkinator tests (all marked skip for MVP)**

- ⊗ `test_e2e_check_valid_site` - Skipped (requires network + linkinator)
- ⊗ `test_e2e_check_site_with_broken_links` - Skipped (requires network + linkinator)
- ⊗ `test_e2e_check_local_documentation` - Skipped (requires file system setup)

#### Error Boundary Tests (3 tests)

- ✓ `test_handles_malformed_url` - URL validation
- ✓ `test_handles_network_timeout` - Network timeout error handling
- ✓ `test_handles_permission_denied` - Permission error handling

### 2. `test_docs_step_count_references.py` - Documentation validation

Tests to prevent regression of issue #1886 (hardcoded step counts in docs).

#### Documentation Tests (6 tests)

**Core Tests (3 tests)**

- ✓ `test_no_hardcoded_step_counts_in_workflow_docs` - No "13-step" or "22-step" patterns
- ✓ `test_workflow_documentation_uses_flexible_language` - Uses "multi-step", "systematic"
- ✓ `test_readme_uses_flexible_step_references` - READMEs use flexible language

**Design Tests (2 tests)**

- ✓ `test_workflow_can_change_step_count_without_doc_updates` - Design verification
- ⊗ `test_no_step_count_references_in_recent_commits` - Skipped (requires git history)

**Helper Tests (2 tests)**

- ✓ `test_find_hardcoded_step_references_detects_violations` - Test the test helper
- ✓ `test_find_hardcoded_step_references_allows_generic_references` - Verify false positives

## Test Execution Strategy

### Phase 1: MVP Implementation

1. Run `test_link_checker.py` - all unit/integration tests should FAIL
2. Implement each function to make tests pass
3. Strategic mocking keeps tests fast (< 5 seconds total)

### Phase 2: E2E Validation

1. Install pytest: `uv add --dev pytest`
2. Run full suite: `pytest .claude/scenarios/check-broken-links/tests/`
3. Verify all non-skipped tests pass

### Phase 3: Real Integration

1. Install linkinator: `npm install -g linkinator`
2. Unskip E2E tests
3. Run against real URLs and local files

## Key Testing Patterns Used

### From PATTERNS.md

1. **Safe Subprocess Wrapper** - Comprehensive error handling (lines 206-245)
2. **Fail-Fast Prerequisite Checking** - Check all deps at startup (lines 254-300)
3. **TDD Testing Pyramid** - 60/30/10 distribution (lines 337-382)

### Strategic Mocking

All external dependencies are mocked:

- `subprocess.run` - Mock linkinator calls
- `shutil.which` - Mock prerequisite detection
- `pathlib.Path.exists` - Mock file system checks

### Error Coverage

Tests cover all failure modes:

- Command not found (exit 127)
- Timeout (exit 124)
- Permission denied
- Invalid JSON
- Malformed URLs
- Network failures

## Running Tests

```bash
# Install pytest if needed
uv add --dev pytest

# Run all tests
pytest .claude/scenarios/check-broken-links/tests/ -v

# Run only unit tests (fast)
pytest .claude/scenarios/check-broken-links/tests/ -v -k "not e2e"

# Run with coverage
pytest .claude/scenarios/check-broken-links/tests/ --cov=.claude/scenarios/check-broken-links

# Run documentation tests
pytest tests/test_docs_step_count_references.py -v
```

## Expected Test Results (TDD)

### Initial Run (Before Implementation)

- **29 failures** - All tests fail because functions not implemented
- **3 skipped** - E2E tests marked skip for MVP

### After Implementation

- **26 passed** - All unit/integration tests pass
- **3 skipped** - E2E tests remain skipped until real linkinator integration

### Final (With Real Integration)

- **29 passed** - All tests pass including E2E

## Test Implementation Notes

### Data Structures Needed

```python
@dataclass
class BrokenLink:
    url: str
    status_code: int
    parent_url: str
    error_message: str

@dataclass
class LinkCheckReport:
    passed: bool
    checked_count: int
    broken_count: int
    broken_links: List[BrokenLink]
    error: bool
    error_message: Optional[str]
```

### Functions to Implement

1. `check_prerequisites()` - Detect linkinator availability
2. `safe_subprocess_call()` - Wrapper for subprocess with error handling
3. `parse_linkinator_output()` - Parse linkinator JSON
4. `format_report()` - Pretty text formatting
5. `check_site()` - Check remote URL
6. `check_local()` - Check local path
7. `get_exit_code()` - Determine exit code from report
8. `get_install_instructions()` - Platform-specific install guidance

### Mocking Strategy

```python
# Mock linkinator subprocess call
mock_result = Mock(
    returncode=0,
    stdout=json.dumps({"passed": True, "links": [...]}),
    stderr=""
)
with patch("subprocess.run", return_value=mock_result):
    # Test code here
```

## Philosophy Compliance

- ✓ **Zero-BS Implementation** - No stubs, all tests fail initially
- ✓ **Ruthless Simplicity** - ONE output format (pretty text)
- ✓ **Strategic Testing** - 60/30/10 pyramid, fast execution
- ✓ **Safe Subprocess Wrapper** - Comprehensive error handling pattern
- ✓ **Fail-Fast Prerequisites** - Check deps before operations

## Next Steps for Builder

1. Read this summary to understand test expectations
2. Implement data structures (LinkCheckReport, BrokenLink)
3. Implement functions one by one, making tests pass
4. Run tests frequently to verify progress
5. All tests should pass after implementation complete

---

**Legend:**

- ✓ = Test implemented, should fail initially (TDD)
- ⊗ = Test skipped for MVP
- 🔧 = Helper/utility test
