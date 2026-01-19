"""
LSP Auto-Configuration Test Suite
==================================

Comprehensive TDD test suite following the Testing Pyramid principle.

## Test Structure

```
tests/
├── conftest.py                 # Pytest fixtures and test utilities
├── test_language_detector.py  # Unit tests (60%)
├── test_lsp_configurator.py   # Unit tests (60%)
├── test_plugin_manager.py     # Unit tests (60%)
├── test_status_tracker.py     # Unit tests (60%)
├── test_integration.py         # Integration tests (30%)
└── test_e2e.py                 # End-to-end tests (10%)
```

## Testing Pyramid

### 60% Unit Tests (Fast, Heavily Mocked)
- **test_language_detector.py**: 33 tests
  - Language detection for all 16 languages
  - File extension mapping
  - Directory exclusion (.gitignore, node_modules)
  - Confidence scoring

- **test_lsp_configurator.py**: 22 tests
  - .env file creation and modification
  - LSP enable/disable functionality
  - Environment variable management
  - Error handling (permissions, I/O)
  - Comment/whitespace preservation

- **test_plugin_manager.py**: 25 tests
  - Plugin installation via `npx cclsp`
  - Plugin listing and status checks
  - Retry logic and timeout handling
  - npx availability detection
  - Installation command generation

- **test_status_tracker.py**: 26 tests
  - Three-layer status checking
  - User guidance generation
  - Platform-specific requirements
  - Troubleshooting tips
  - Progress tracking

**Total Unit Tests**: 106 tests

### 30% Integration Tests (Multiple Components)
- **test_integration.py**: 15 tests
  - Language detection + status checking
  - Plugin installation workflows
  - Multi-language setup
  - Error handling across modules
  - Status reporting

### 10% E2E Tests (Complete Workflows)
- **test_e2e.py**: 18 tests
  - First-time user auto-setup
  - Manual setup with guidance
  - Multi-language projects
  - Troubleshooting workflows
  - Platform-specific scenarios
  - Edge cases (empty project, large project)

**Total Tests**: 139 comprehensive tests

## Running Tests

### Run All Tests
```bash
pytest .claude/skills/lsp-setup/tests/
```

### Run by Category
```bash
# Unit tests only (fast)
pytest .claude/skills/lsp-setup/tests/test_language_detector.py
pytest .claude/skills/lsp-setup/tests/test_lsp_configurator.py
pytest .claude/skills/lsp-setup/tests/test_plugin_manager.py
pytest .claude/skills/lsp-setup/tests/test_status_tracker.py

# Integration tests
pytest .claude/skills/lsp-setup/tests/test_integration.py

# E2E tests
pytest .claude/skills/lsp-setup/tests/test_e2e.py
```

### Run with Coverage
```bash
pytest --cov=lsp_setup --cov-report=html .claude/skills/lsp-setup/tests/
```

### Run Specific Test
```bash
pytest .claude/skills/lsp-setup/tests/test_language_detector.py::TestLanguageDetector::test_detect_single_python_project
```

## Test Fixtures (conftest.py)

### Directory Fixtures
- `mock_project_root`: Temporary project directory
- `mock_env_file`: Mock .env file path

### File Fixtures
- `sample_python_files`: Python project structure
- `sample_typescript_files`: TypeScript project structure
- `sample_mixed_language_files`: Multi-language project

### Mock Fixtures
- `mock_subprocess_run`: Mock subprocess calls
- `mock_shutil_which`: Mock binary detection
- `mock_npx_cclsp_success`: Mock successful plugin installation
- `mock_npx_cclsp_failure`: Mock failed plugin installation

### Data Fixtures
- `installed_lsp_binaries`: Simulated installed LSP servers
- `missing_lsp_binaries`: Simulated missing LSP servers
- `language_to_lsp_mapping`: Language to LSP server mapping

## Test Coverage Goals

### Module Coverage Targets
- `language_detector.py`: 95%+ coverage
- `lsp_configurator.py`: 90%+ coverage
- `plugin_manager.py`: 90%+ coverage
- `status_tracker.py`: 95%+ coverage

### Critical Paths (Must be 100%)
- Language detection for all 16 languages
- Three-layer status checking
- .env file manipulation
- Plugin installation via npx cclsp

## TDD Red-Green-Refactor Cycle

### Current State: RED ❌
All tests currently FAIL because implementation doesn't exist yet.

### Next Steps (GREEN ✅)
1. Implement `language_detector.py` to pass unit tests
2. Implement `lsp_configurator.py` to pass unit tests
3. Implement `plugin_manager.py` to pass unit tests
4. Implement `status_tracker.py` to pass unit tests
5. Verify integration tests pass
6. Verify E2E tests pass

### Refactor Phase
Once all tests pass:
1. Identify code duplication
2. Extract common patterns
3. Optimize performance
4. Improve error messages
5. Re-run all tests to ensure refactoring didn't break anything

## Test Ratio Analysis

### Current Test-to-Code Ratio
- **139 comprehensive tests** written
- **~350 lines per test file** (average)
- **Total test code**: ~2,100 lines
- **Expected implementation**: ~500-700 lines
- **Ratio**: 3:1 to 4:1 (within target 3:1 to 5:1)

This ratio ensures:
- Comprehensive coverage without over-testing
- Fast test execution (unit tests run in seconds)
- Clear test intent (each test tests ONE thing)
- Maintainable test suite (not excessive)

## Key Testing Patterns Used

### 1. Arrange-Act-Assert
Every test follows AAA pattern:
```python
def test_example(self, mock_project_root):
    # Arrange
    (mock_project_root / "test.py").write_text("# Python")

    # Act
    detector = LanguageDetector(mock_project_root)
    languages = detector.detect_languages()

    # Assert
    assert "python" in languages
```

### 2. Strategic Mocking
Mock external dependencies (filesystem, subprocess, network):
```python
with patch("subprocess.run", mock_subprocess_run):
    manager = PluginManager()
    result = manager.install_plugin("python")
```

### 3. Parametrized Tests (Not Used Here)
Could be added for testing all 16 languages:
```python
@pytest.mark.parametrize("language,extension", [
    ("python", ".py"),
    ("typescript", ".ts"),
    ("rust", ".rs"),
])
def test_language_detection(language, extension):
    ...
```

## Dependencies

```bash
pip install pytest pytest-cov pytest-mock
```

## CI Integration

### GitHub Actions Example
```yaml
- name: Run Tests
  run: |
    pytest .claude/skills/lsp-setup/tests/ \
      --cov=lsp_setup \
      --cov-report=xml \
      --cov-fail-under=90
```

## Troubleshooting

### Import Errors
If tests fail with import errors:
```bash
# Ensure lsp_setup package is in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:.claude/skills"
pytest .claude/skills/lsp-setup/tests/
```

### Fixture Not Found
Ensure `conftest.py` is in the same directory as test files.

### Mock Not Working
Check that patches are applied in correct order (innermost first):
```python
with patch("shutil.which", mock_which):
    with patch("subprocess.run", mock_run):
        # Test code
```

## Philosophy Compliance

This test suite follows amplihack philosophy:

✅ **Ruthless Simplicity**: Clear, focused tests
✅ **Proportionality**: 3:1 to 5:1 ratio (not excessive)
✅ **Zero-BS**: No stub tests, all tests verify real behavior
✅ **Fast Execution**: Unit tests run in seconds
✅ **Clear Intent**: Each test has ONE purpose

## Next Steps

1. **Run tests**: `pytest .claude/skills/lsp-setup/tests/` (expect ALL to FAIL)
2. **Implement modules**: Write code to make tests pass
3. **Iterate**: Red -> Green -> Refactor
4. **Verify coverage**: `pytest --cov`
5. **Document learnings**: Update DISCOVERIES.md

---

**Remember**: These tests define the contract. Implementation must satisfy these tests.
