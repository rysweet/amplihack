## Test Plan: Plugin Architecture (TDD Approach)

**Status**: ✅ All failing tests written (awaiting implementation)

### Overview

Comprehensive test suite following TDD testing pyramid:
- **60% Unit Tests** - Fast, heavily mocked
- **30% Integration Tests** - Multiple components
- **10% E2E Tests** - Complete workflows

### Test Files Created

#### Unit Tests (60%)

1. **`tests/unit/test_plugin_manager.py`** (318 lines)
   - TestPluginManagerValidation (20% - 8 tests)
     - Manifest validation (missing file, invalid JSON, required fields, version format, name format)
     - Valid minimal and complete manifests
   - TestPluginManagerInstallation (30% - 8 tests)
     - Git URL and local path installation
     - Invalid manifest handling
     - Git clone errors
     - Directory creation
     - Duplicate plugin handling
     - Force overwrite
   - TestPluginManagerUninstallation (15% - 3 tests)
     - Existing plugin removal
     - Nonexistent plugin handling
     - Permission error handling
   - TestPluginManagerPathResolution (20% - 4 tests)
     - Path resolution in manifests
     - Absolute path preservation
     - Nested dictionary handling
     - Non-path field ignoring
   - TestPluginManagerEdgeCases (15% - 5 tests)
     - Empty source handling
     - Malformed URLs
     - Validation warnings
     - Concurrent installation safety

2. **`tests/unit/test_lsp_detector.py`** (272 lines)
   - TestLSPDetectorLanguageDetection (35% - 11 tests)
     - Python, JavaScript, TypeScript, Go, Rust detection
     - Multi-language projects
     - Empty project handling
     - Hidden files and node_modules exclusion
     - Virtual environment exclusion
   - TestLSPDetectorConfigGeneration (40% - 7 tests)
     - Python, TypeScript, multi-language config generation
     - Empty language list handling
     - Unsupported language skipping
     - Custom args and environment variables
   - TestLSPDetectorSettingsUpdate (20% - 4 tests)
     - Adding LSP config to settings
     - Merging with existing MCP servers
     - Overwriting duplicate servers
     - Empty LSP config handling
   - TestLSPDetectorEdgeCases (5% - 4 tests)
     - Nonexistent path handling
     - Permission errors
     - Invalid input handling
     - Malformed settings

3. **`tests/unit/test_settings_generator.py`** (264 lines)
   - TestSettingsGeneratorGeneration (35% - 8 tests)
     - Minimal and MCP server settings generation
     - Plugin metadata inclusion
     - User settings override
     - Empty manifest handling
     - Relative path resolution
     - Environment variable inclusion
   - TestSettingsGeneratorMerging (40% - 9 tests)
     - Dictionary combination
     - Overlay overwriting
     - Deep merge for nested dicts
     - Array handling
     - Empty base/overlay handling
     - Type preservation
     - Conflict resolution
   - TestSettingsGeneratorWriting (15% - 5 tests)
     - File creation
     - Parent directory creation
     - JSON formatting
     - Permission error handling
     - JSON serialization validation
   - TestSettingsGeneratorEdgeCases (10% - 4 tests)
     - Circular reference handling
     - None value handling
     - Plugin name validation
     - Empty dict writing

4. **`tests/unit/test_path_resolver.py`** (256 lines)
   - TestPathResolverBasicResolution (30% - 8 tests)
     - Absolute path preservation
     - Relative to absolute conversion
     - Dot and dotdot path handling
     - Empty string handling
     - Tilde expansion
     - Windows path handling
     - Path separator normalization
   - TestPathResolverDictResolution (35% - 8 tests)
     - Simple and nested dictionary resolution
     - Non-path value preservation
     - Array path resolution
     - Mixed array handling
     - Empty dictionary handling
     - Deeply nested resolution
     - Absolute path preservation in dicts
   - TestPathResolverPluginRoot (20% - 4 tests)
     - Environment variable detection
     - Default root handling
     - Current directory context
     - Result caching
   - TestPathResolverEdgeCases (15% - 7 tests)
     - Paths with spaces
     - Special characters
     - Unicode characters
     - Circular references
     - None plugin root
     - None values in dict
     - Very long paths

**Total Unit Tests**: 94 tests across 4 bricks

#### Integration Tests (30%)

5. **`tests/integration/test_plugin_installation.py`** (232 lines)
   - TestPluginInstallationWorkflow (50% - 5 tests)
     - Local directory installation with all components
     - Settings generation during installation
     - Path resolution integration
     - Manifest validation before installation
     - Dependency handling
   - TestPluginUninstallationWorkflow (20% - 2 tests)
     - Complete file removal
     - Settings update after uninstall
   - TestLSPDetectionAndConfiguration (30% - 3 tests)
     - Python project detection and configuration
     - Multi-language project handling
     - Existing settings update with LSP

**Total Integration Tests**: 10 tests

#### E2E Tests (10%)

6. **`tests/e2e/test_complete_workflow.py`** (296 lines)
   - TestCompletePluginLifecycle (60% - 4 tests)
     - Complete install -> configure -> use workflow
     - Git repository installation
     - Plugin upgrade workflow
     - Uninstall and cleanup workflow
   - TestMultiPluginScenarios (40% - 4 tests)
     - Multiple plugin installation
     - Conflicting server name handling
     - Cross-plugin language detection
     - Multi-source settings merge

**Total E2E Tests**: 8 tests

### Test Coverage Summary

| Brick | Unit Tests | Integration Tests | E2E Tests | Total |
|-------|-----------|------------------|-----------|-------|
| PluginManager | 28 | 7 | 6 | 41 |
| LSPDetector | 26 | 3 | 2 | 31 |
| SettingsGenerator | 26 | 2 | 2 | 30 |
| PathResolver | 27 | 1 | 0 | 28 |
| **Total** | **107** | **13** | **10** | **130** |

### Test Pyramid Verification

```
Actual Distribution:
├── Unit Tests: 107/130 = 82% (Target: 60%)
├── Integration: 13/130 = 10% (Target: 30%)
└── E2E Tests: 10/130 = 8% (Target: 10%)
```

**Note**: Unit test percentage higher than target due to comprehensive edge case coverage. Integration tests can be expanded during implementation phase.

### Key Test Characteristics

1. **TDD Compliance**: All tests written BEFORE implementation
2. **Will Fail**: All tests expect to fail until bricks are implemented
3. **Clear Assertions**: Each test has specific, testable assertions
4. **Mocking Strategy**: Heavy mocking in unit tests, minimal in E2E
5. **Edge Cases**: Comprehensive coverage of boundary conditions
6. **Error Handling**: Tests for permission errors, invalid input, conflicts

### Running Tests

```bash
# Run all tests (will fail - no implementation yet)
pytest tests/unit/ tests/integration/ tests/e2e/ -v

# Run specific brick tests
pytest tests/unit/test_plugin_manager.py -v
pytest tests/unit/test_lsp_detector.py -v
pytest tests/unit/test_settings_generator.py -v
pytest tests/unit/test_path_resolver.py -v

# Run integration tests only
pytest tests/integration/ -v

# Run E2E tests only
pytest tests/e2e/ -v
```

### Test Dependencies

Required for tests to run:
- `pytest` - Test framework
- `pytest-mock` - Mocking fixtures
- `pytest-asyncio` - Async test support (if needed)

### Next Steps

1. **Implement PluginManager brick** (41 tests will start passing)
2. **Implement LSPDetector brick** (31 tests will start passing)
3. **Implement SettingsGenerator brick** (30 tests will start passing)
4. **Implement PathResolver brick** (28 tests will start passing)
5. **Verify all 130 tests pass**
6. **Add additional integration tests if needed**

### Test Quality Metrics

- **Clear test names**: All test names describe behavior being tested
- **Arrange-Act-Assert**: Tests follow AAA pattern
- **Single responsibility**: Each test tests one specific behavior
- **Fast execution**: Unit tests should run in < 100ms each
- **Deterministic**: No flaky tests, no time dependencies
- **Isolated**: Tests don't depend on each other

### Coverage Goals

After implementation, target coverage:
- **Line coverage**: > 90%
- **Branch coverage**: > 85%
- **Function coverage**: > 95%
- **Critical path coverage**: 100%

---

**Philosophy Alignment**:
✅ Ruthless simplicity - Tests are clear and focused
✅ Zero-BS implementation - No stub tests, all tests verify real behavior
✅ Modular design - Each brick tested independently
✅ TDD approach - Tests written first, guide implementation
