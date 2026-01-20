# Plugin Architecture Tests

**TDD Test Suite** - Written before implementation (Red Phase)

These tests define the expected behavior of the amplihack plugin architecture before any code is written. They follow Test-Driven Development principles: write failing tests first, then implement code to make them pass.

## Test Structure

```
tests/plugin/
├── test_installer.py          # PluginInstaller tests
├── test_settings_merger.py    # SettingsMerger tests
├── test_variable_substitutor.py # VariableSubstitutor tests
├── test_lsp_detector.py       # LSPDetector tests
├── test_migration_helper.py   # MigrationHelper tests
├── test_integration.py        # Integration & E2E tests
├── conftest.py                # Shared fixtures
├── pytest.ini                 # Pytest configuration
└── README.md                  # This file
```

## Test Coverage Goals

**Target Test Ratio**: 0.62:1 (test lines to implementation lines)

- **Implementation**: ~2600 lines
- **Tests**: ~1600 lines

**Testing Pyramid**:
- 60% Unit tests (fast, isolated)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)

## Running Tests

### All Tests

```bash
pytest tests/plugin/
```

### Specific Test File

```bash
pytest tests/plugin/test_installer.py
pytest tests/plugin/test_settings_merger.py
pytest tests/plugin/test_variable_substitutor.py
pytest tests/plugin/test_lsp_detector.py
pytest tests/plugin/test_migration_helper.py
pytest tests/plugin/test_integration.py
```

### By Test Category

```bash
# Unit tests only
pytest tests/plugin/ -m unit

# Integration tests only
pytest tests/plugin/ -m integration

# E2E tests only
pytest tests/plugin/ -m e2e

# Fast tests (exclude slow)
pytest tests/plugin/ -m "not slow"
```

### With Coverage

```bash
pytest tests/plugin/ --cov=amplihack.plugin --cov-report=html
```

### Verbose Output

```bash
pytest tests/plugin/ -vv
```

## Test Organization

### test_installer.py (PluginInstaller)

**Unit Tests** (60%):
- Install validation
- Target directory creation
- Runtime directory exclusion
- Executable permissions
- Backup creation
- Installation verification
- Uninstall cleanup

**Integration Tests** (30%):
- Full installation workflow
- Upgrade with backup
- Real file operations

**Edge Cases** (10%):
- Symlink handling
- Permission errors
- Nonexistent installations
- Timestamp preservation

### test_settings_merger.py (SettingsMerger)

**Unit Tests** (60%):
- Empty override handling
- Non-conflicting key merging
- Conflicting value resolution
- Deep nested dict merging
- Array value appending
- LSP server combination
- Settings validation
- Hook path resolution

**Integration Tests** (30%):
- File-based merging
- Save/load workflows
- Complete merge workflow

**Edge Cases** (10%):
- Null value handling
- Deeply nested structures
- Circular reference detection
- Type preservation
- Windows path handling

### test_variable_substitutor.py (VariableSubstitutor)

**Unit Tests** (70%):
- Simple variable substitution
- Multiple variables
- Unknown variable errors
- Empty variable handling
- Path traversal rejection
- Safe path validation
- Absolute path creation
- Recursive dict substitution

**Security Tests** (20%):
- Path traversal prevention
- Absolute path escape prevention
- Symlink traversal prevention
- Variable injection prevention
- Environment variable leakage prevention

**Integration Tests** (10%):
- Real file system verification
- Multiple path substitution
- Complete workflow

### test_lsp_detector.py (LSPDetector)

**Unit Tests** (60%):
- Python detection (requirements.txt, pyproject.toml, .py files)
- TypeScript detection (package.json with typescript)
- JavaScript detection (package.json without typescript)
- Rust detection (Cargo.toml)
- Go detection (go.mod)
- Multi-language detection
- LSP config generation (single & multiple languages)
- Empty project handling

**Integration Tests** (30%):
- Nested directory detection
- Monorepo detection
- Fullstack project detection
- Config file saving

**Edge Cases** (10%):
- Symlink handling
- Hidden file/directory handling
- Invalid manifest files
- Unsupported languages
- Shebang detection
- Large project performance

### test_migration_helper.py (MigrationHelper)

**Unit Tests** (50%):
- Old installation detection
- Customization identification
- Migration plan creation
- Precondition validation
- Size calculation

**Integration Tests** (40%):
- User preferences preservation
- Custom agent preservation
- Runtime data migration
- Backup creation
- Rollback functionality

**E2E Tests** (10%):
- Complete migration workflow
- Conflict resolution
- Partial migration handling

### test_integration.py (Complete System)

**Integration Tests** (30%):
- Plugin installation + project settings
- LSP auto-detection integration
- Multi-project shared plugin

**E2E Tests** (70%):
- Migration workflow preservation
- Migration rollback
- Hook execution with variables
- CLI commands (install, migrate, verify)
- Concurrent project setup
- Plugin upgrade

## Current Status

🔴 **RED PHASE** - All tests FAIL (expected)

These tests are written BEFORE implementation. They define the expected behavior and API contracts. They will fail until the implementation is complete.

## Next Steps

1. ✅ Write failing tests (COMPLETE)
2. 🔄 Implement modules to make tests pass (IN PROGRESS)
3. ⏳ Refactor for simplicity and quality
4. ⏳ Verify all tests pass
5. ⏳ Measure test coverage

## Test Writing Standards

All tests follow these standards:

### AAA Pattern
```python
def test_example():
    # Arrange - Setup test conditions
    data = create_test_data()

    # Act - Execute the operation
    result = function_under_test(data)

    # Assert - Verify expectations
    assert result == expected_value
```

### Clear Docstrings
```python
def test_example():
    """
    Test that function handles edge case correctly.

    Validates:
    - Specific behavior 1
    - Specific behavior 2
    - Error handling
    """
```

### Descriptive Names
```python
# Good
def test_merge_conflicting_values_prefers_override():
    pass

# Bad
def test_merge():
    pass
```

### Fixture Usage
```python
def test_with_fixture(tmp_path, plugin_source):
    # Use fixtures for common test data
    pass
```

### Isolation
- No test dependencies
- Clean state for each test
- tmp_path for file operations
- Mocks for external dependencies

## Philosophy Alignment

These tests embody amplihack philosophy:

- **Ruthless Simplicity**: Tests are clear and focused
- **Zero-BS**: No stub tests, all tests validate real behavior
- **Proportionality**: Test effort matches criticality
- **TDD Approach**: Tests define requirements before implementation

## Contributing

When adding new tests:

1. Follow testing pyramid (60/30/10)
2. Use AAA pattern
3. Write clear docstrings
4. Use fixtures for common setup
5. Keep tests isolated and fast
6. Mark appropriately (unit/integration/e2e)
