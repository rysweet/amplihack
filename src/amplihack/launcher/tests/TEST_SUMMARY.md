# Smart Memory Management Test Suite Summary

**Issue**: #1953
**Module**: `amplihack.launcher.memory_config`
**Approach**: Test-Driven Development (TDD)
**Status**: Tests written FIRST - Implementation pending

## Test Strategy

Following the testing pyramid:

- **60% Unit Tests**: Fast, heavily mocked, test individual functions
- **30% Integration Tests**: Test multiple components working together
- **10% E2E Tests**: Complete workflow validation

## Formula Under Test

```python
N = max(8192, total_ram_mb // 4)  # Capped at 32GB (32768 MB)
```

Where:

- `N` = Recommended Node.js memory limit in MB
- `total_ram_mb` = Total system RAM in MB
- Minimum limit: 8192 MB (8 GB)
- Maximum limit: 32768 MB (32 GB)

## Test Coverage Overview

### Unit Tests (60%) - 7 Test Classes

1. **TestDetectSystemRAM** (5 tests)
   - Linux RAM detection via `/proc/meminfo`
   - macOS RAM detection via `sysctl`
   - Windows RAM detection via `wmic`
   - Insufficient memory systems (< 4GB)
   - Command failure handling

2. **TestCalculateRecommendedLimit** (6 tests)
   - Small systems use 8GB minimum
   - Medium systems use 1/4 RAM
   - Large systems capped at 32GB
   - Exact boundary conditions (32GB, 128GB)
   - Edge cases (4GB, 8GB, 32GB, 48GB, 96GB, 192GB)

3. **TestParseNodeOptions** (5 tests)
   - Empty NODE_OPTIONS
   - Single memory flag parsing
   - Multiple flags parsing
   - Mixed format flags
   - Invalid format handling

4. **TestMergeNodeOptions** (5 tests)
   - Merge into empty options
   - Replace existing limit
   - Preserve other flags
   - Output format validation

5. **TestShouldWarnAboutLimit** (4 tests)
   - Warning below 8GB minimum
   - No warning at/above minimum
   - Zero/negative value warnings

6. **TestPromptUserConsent** (5 tests)
   - Display current and recommended limits
   - Accept yes variants (y, Y, yes, YES, Yes)
   - Reject no variants (n, N, no, NO, No)
   - Handle empty input (default no)

7. **TestFormulaCorrectness** (4 tests)
   - Minimum enforcement (4GB→8GB, 16GB→8GB)
   - Quarter calculation (64GB→16GB, 96GB→24GB)
   - Maximum cap (256GB→32GB, 1TB→32GB)
   - Exact boundaries (32GB→8GB, 128GB→32GB)

### Integration Tests (30%) - 1 Test Class

**TestMemoryConfigIntegration** (4 tests)

- Full detection → calculation workflow
- Parse → merge workflow
- Detection → calculation → warning workflow
- Environment variable update workflow

### E2E Tests (10%) - 1 Test Class

**TestGetMemoryConfigE2E** (5 tests)

- Normal system (16+ GB) complete flow
- With existing NODE_OPTIONS
- User declines update
- Insufficient memory warning
- Detection failure handling

### Additional Test Coverage

**TestEdgeCases** (5 tests)

- Maximum possible RAM (1TB+)
- Very small RAM (< 4GB)
- Fractional GB values
- NODE_OPTIONS with quotes
- Concurrent modifications

**TestErrorHandling** (4 tests)

- Invalid RAM GB input
- Malformed NODE_OPTIONS
- Permission denied reading meminfo
- Subprocess timeout

**TestPlatformSpecifics** (3 tests)

- Linux meminfo parsing variants
- macOS sysctl bytes parsing
- Windows wmic output parsing

## Total Test Count

- **Unit Tests**: ~35 tests (60%)
- **Integration Tests**: ~4 tests (30%)
- **E2E Tests**: ~5 tests (10%)
- **Edge Cases**: ~5 tests
- **Error Handling**: ~4 tests
- **Platform-Specific**: ~3 tests

**Total**: ~56 comprehensive tests

## Key Functions Being Tested

1. `detect_system_ram_gb()` → Detect total system RAM
2. `calculate_recommended_limit(ram_gb)` → Calculate limit with formula
3. `parse_node_options(node_options)` → Parse existing NODE_OPTIONS
4. `merge_node_options(existing, new_limit_mb)` → Merge new limit
5. `should_warn_about_limit(limit_mb)` → Check warning needed
6. `prompt_user_consent(config)` → Prompt user for consent
7. `get_memory_config()` → Main entry point (E2E)

## Expected Test Results (Before Implementation)

All tests should **FAIL** with:

```
ModuleNotFoundError: No module named 'amplihack.launcher.memory_config'
```

This confirms TDD approach - tests written FIRST.

## Implementation Checklist

When implementing `memory_config.py`, ensure:

- [ ] All unit tests pass (60% coverage)
- [ ] All integration tests pass (30% coverage)
- [ ] All E2E tests pass (10% coverage)
- [ ] Edge cases handled properly
- [ ] Error handling robust
- [ ] Platform-specific code works on Linux, macOS, Windows
- [ ] Formula correctness verified: `max(8192, total_ram_mb // 4)` capped at 32GB
- [ ] User consent flow implemented
- [ ] Environment variable updates work correctly

## Running the Tests

```bash
# Run all tests
pytest src/amplihack/launcher/tests/test_memory_config.py -v

# Run specific test class
pytest src/amplihack/launcher/tests/test_memory_config.py::TestDetectSystemRAM -v

# Run with coverage
pytest src/amplihack/launcher/tests/test_memory_config.py --cov=amplihack.launcher.memory_config --cov-report=html

# Run only unit tests
pytest src/amplihack/launcher/tests/test_memory_config.py -k "not Integration and not E2E" -v
```

## Test Philosophy Alignment

These tests follow amplihack philosophy:

- ✅ **Ruthless Simplicity**: Tests are clear and focused
- ✅ **Zero-BS Implementation**: No stub tests, all tests verify real behavior
- ✅ **Testing Pyramid**: 60% unit, 30% integration, 10% E2E
- ✅ **TDD Approach**: Tests written FIRST, implementation follows
- ✅ **Proportional Testing**: Test coverage matches complexity
- ✅ **Clear Boundaries**: Each test class tests one component

## Notes for Implementation

1. **Formula is EXPLICIT**: User specifically requested `max(8192, total_ram_mb // 4)` - NOT the tiered approach
2. **User Consent Required**: Always prompt before modifying NODE_OPTIONS
3. **Platform Support**: Must work on Linux, macOS, Windows
4. **Graceful Degradation**: Handle detection failures elegantly
5. **Preserve Existing Flags**: When merging NODE_OPTIONS, preserve non-memory flags
6. **Warning Threshold**: Warn when recommended limit < 8GB

## Success Criteria

Implementation is complete when:

1. All 56 tests pass
2. Tests run in < 5 seconds (unit tests are fast)
3. No test mocking is excessive (60% unit test guideline)
4. Formula produces correct values across all test cases
5. Platform-specific code works on all supported OS

---

**Generated**: 2026-01-17
**Test File**: `src/amplihack/launcher/tests/test_memory_config.py`
**TDD Status**: ✅ Tests written, ⏳ Implementation pending
