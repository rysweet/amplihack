# E2E Tests fer Plugin Architecture

## Overview

End-to-end tests that verify plugin architecture from outside-in perspective usin' real subprocess execution.

## Test Files

### `test_plugin_manager_e2e.py`
Tests complete plugin lifecycle:
- Installation (local and Git)
- Uninstallation
- Plugin listin'
- Settings.json generation
- Settings mergin'

**Tests**: 11

### `test_hook_protocol_e2e.py`
Tests hook execution and lifecycle:
- Python and Bash hooks
- Hook arguments
- Error handlin'
- Timeouts
- Environment variables

**Tests**: 12

### `test_lsp_detection_e2e.py`
Tests LSP detection and configuration:
- Language detection (Python, TypeScript, Rust)
- Multi-language projects
- LSP configuration generation
- Performance testin'

**Tests**: 16

**Total**: 39 E2E tests

## Prerequisites

```bash
# Install pytest and dependencies
pip install pytest pytest-asyncio

# Install amplihack in development mode
pip install -e .
```

## Runnin' Tests

```bash
# Run all E2E tests
pytest tests/e2e/ -v

# Run specific test file
pytest tests/e2e/test_plugin_manager_e2e.py -v

# Run specific test class
pytest tests/e2e/test_plugin_manager_e2e.py::TestPluginLifecycle -v

# Run specific test
pytest tests/e2e/test_plugin_manager_e2e.py::TestPluginLifecycle::test_install_local_plugin -v

# Run with output visible
pytest tests/e2e/ -v -s

# Run with coverage
pytest tests/e2e/ --cov=src/amplihack --cov-report=html
```

## Expected Behavior

### Before Implementation

Tests will fail because plugin commands don't exist yet:

```
FAILED - FileNotFoundError: Command 'amplihack plugin install' not found
```

This be expected! Tests are written BEFORE implementation (TDD).

### After Implementation

Tests should pass when plugin bricks are implemented:

```
PASSED test_plugin_manager_e2e.py::TestPluginLifecycle::test_install_local_plugin
PASSED test_hook_protocol_e2e.py::TestHookExecution::test_execute_python_hook
PASSED test_lsp_detection_e2e.py::TestLanguageDetection::test_detect_python_project
...
39 passed in X.XXs
```

## Test Harness Usage

Tests use subprocess-based harnesses from `tests/harness/`:

```python
from tests.harness import PluginTestHarness, HookTestHarness, LSPTestHarness

# Plugin testin'
harness = PluginTestHarness()
result = harness.install_plugin("path/to/plugin")
result.assert_success()

# Hook testin'
harness = HookTestHarness()
harness.create_hook("pre_commit", script_content)
result = harness.trigger_hook("pre_commit")
result.assert_success()

# LSP testin'
harness = LSPTestHarness()
harness.create_python_project()
result = harness.detect_languages()
result.assert_in_stdout("python")
```

See `tests/harness/README.md` fer complete harness documentation.

## Fixtures

Use fixtures from `tests/conftest.py`:

```python
def test_with_sample_plugin(sample_plugin):
    """Use pre-built valid plugin."""
    # sample_plugin is Path to valid plugin directory

def test_with_invalid_plugin(invalid_plugin):
    """Use invalid plugin fer error testin'."""
    # invalid_plugin is Path to plugin without manifest

def test_with_multi_language_project(multi_language_project):
    """Use project with Python, TypeScript, and Rust."""
    # multi_language_project is Path to multi-lang project
```

## Performance

- Individual test: < 30 seconds
- Complete suite: < 5 minutes
- Cleanup: Automatic via fixtures

## Troubleshootin'

**Tests timeout:**
- Check timeout settings in harness initialization
- Verify commands aren't waitin' fer user input

**Command not found:**
- Install amplihack: `pip install -e .`
- Verify PATH includes installation directory
- Check virtual environment is activated

**Import errors:**
- Install test dependencies: `pip install pytest`
- Verify harness module: `python -c "from tests.harness import PluginTestHarness"`

## Philosophy

- **Outside-in**: Test from user's perspective
- **Real execution**: No mockin' of subprocess calls
- **Fast**: Complete in < 5 minutes
- **Clear**: Helpful error messages
- **Isolated**: Each test independent

---

**Status**: ✅ Tests written, ready fer implementation

Fer more details, see:
- `tests/harness/README.md` - Harness documentation
- `tests/PLUGIN_TEST_HARNESS_SUMMARY.md` - Complete summary
- `tests/TEST_PLAN_PLUGIN_ARCHITECTURE.md` - Full test plan
