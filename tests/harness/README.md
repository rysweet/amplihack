## Subprocess Test Harness fer Plugin Architecture

### Overview

This harness provides subprocess-based outside-in testin' fer the plugin architecture. Tests execute real commands and verify behavior from a user's perspective.

### Philosophy

- **Outside-in testin'**: Test from the user's perspective, not implementation details
- **Real subprocess execution**: No mockin' - execute actual commands
- **Fast execution**: Complete test suite runs in < 5 minutes
- **Clear failure messages**: Helpful error output when tests fail
- **Non-interactive**: No user input required

### Test Harnesses

#### PluginTestHarness

Tests plugin lifecycle management:

```python
from tests.harness import PluginTestHarness

# Create harness
harness = PluginTestHarness()

# Install plugin
result = harness.install_plugin("path/to/plugin")
result.assert_success()

# Verify installation
assert harness.verify_plugin_installed("my-plugin")

# Uninstall plugin
harness.uninstall_plugin("my-plugin")

# Cleanup
harness.cleanup()
```

**Key Methods:**

- `install_plugin(source, force=False)` - Install plugin from source
- `uninstall_plugin(plugin_name, purge=False)` - Uninstall plugin
- `list_plugins()` - List installed plugins
- `verify_plugin_installed(plugin_name)` - Check if plugin is installed
- `verify_settings_json_exists()` - Check if settings.json was created
- `read_settings_json()` - Read and parse settings.json

#### HookTestHarness

Tests hook protocol and execution:

```python
from tests.harness import HookTestHarness

# Create harness
harness = HookTestHarness()

# Create hook
hook_script = """
import sys
print("Hook executed")
sys.exit(0)
"""
harness.create_hook("pre_commit", hook_script, language="python")

# Trigger hook
result = harness.trigger_hook("pre_commit")
result.assert_success()
result.assert_in_stdout("Hook executed")

# Cleanup
harness.cleanup()
```

**Key Methods:**

- `create_hook(hook_name, script_content, language)` - Create test hook
- `trigger_hook(hook_name, extra_args=None)` - Execute hook
- `list_hooks()` - List available hooks
- `verify_hook_exists(hook_name)` - Check if hook exists

#### LSPTestHarness

Tests LSP detection and configuration:

```python
from tests.harness import LSPTestHarness

# Create harness
harness = LSPTestHarness()

# Create test project
harness.create_python_project()
harness.create_typescript_project()

# Detect languages
result = harness.detect_languages()
result.assert_success()
result.assert_in_stdout("python")
result.assert_in_stdout("typescript")

# Configure LSP
config_result = harness.configure_lsp()
config_result.assert_success()

# Verify configs created
assert harness.verify_lsp_config_exists("python")
assert harness.verify_lsp_config_exists("typescript")

# Cleanup
harness.cleanup()
```

**Key Methods:**

- `create_python_project()` - Create Python test project
- `create_typescript_project()` - Create TypeScript test project
- `create_rust_project()` - Create Rust test project
- `create_multi_language_project()` - Create multi-language project
- `detect_languages()` - Run language detection
- `configure_lsp(languages=None)` - Configure LSP
- `verify_lsp_config_exists(language)` - Check if LSP config exists

### SubprocessResult

All harness methods return `SubprocessResult` with helper assertions:

```python
result = harness.install_plugin("path/to/plugin")

# Assert success
result.assert_success("Custom error message")

# Assert failure
result.assert_failure("Should have failed")

# Assert text in output
result.assert_in_stdout("expected text")
result.assert_in_stderr("error text")

# Access result data
print(f"Exit code: {result.returncode}")
print(f"Duration: {result.duration} seconds")
print(f"Command: {' '.join(result.command)}")
```

### Test Structure

Tests are organized by workflow:

```
tests/
├── harness/
│   ├── __init__.py
│   ├── subprocess_test_harness.py
│   └── README.md (this file)
├── e2e/
│   ├── test_plugin_manager_e2e.py    # Plugin lifecycle tests
│   ├── test_hook_protocol_e2e.py     # Hook execution tests
│   └── test_lsp_detection_e2e.py     # LSP detection tests
└── conftest.py                        # Shared fixtures
```

### Fixtures

Additional fixtures in `conftest.py`:

```python
def test_with_sample_plugin(sample_plugin):
    """Use pre-built sample plugin."""
    # sample_plugin is Path to valid plugin directory

def test_with_invalid_plugin(invalid_plugin):
    """Use invalid plugin fer error testin'."""
    # invalid_plugin is Path to plugin without manifest

def test_with_multi_language_project(multi_language_project):
    """Use project with Python, TypeScript, and Rust."""
    # multi_language_project is Path to multi-lang project

def test_with_assertion_helper():
    """Use assertion helper."""
    result = harness.some_operation()
    assert_subprocess_success(result)
```

### Runnin' Tests

```bash
# Run all E2E tests
pytest tests/e2e/ -v

# Run specific test file
pytest tests/e2e/test_plugin_manager_e2e.py -v

# Run specific test
pytest tests/e2e/test_plugin_manager_e2e.py::TestPluginLifecycle::test_install_local_plugin -v

# Run with output
pytest tests/e2e/ -v -s

# Run with coverage
pytest tests/e2e/ --cov=src/amplihack --cov-report=html
```

### Test Pyramid Distribution

Follows 60/30/10 testing pyramid:

- **60% Unit Tests** - Fast, heavily mocked (in `tests/unit/`)
- **30% Integration Tests** - Multiple components (in `tests/integration/`)
- **10% E2E Tests** - Complete workflows (in `tests/e2e/`)

### Performance Guidelines

- Individual E2E test should complete in < 30 seconds
- Complete E2E suite should run in < 5 minutes
- Use appropriate timeouts (default: 30-60 seconds)
- Cleanup after each test (use fixtures with yield)

### Troubleshootin'

**Tests timeout:**

- Increase timeout in harness initialization
- Check if commands are hangin' on user input
- Verify commands are available in PATH

**Tests fail with "command not found":**

- Ensure amplihack is installed: `pip install -e .`
- Check PATH includes installation directory
- Verify running in correct virtual environment

**Cleanup failures:**

- Tests should use fixtures with `yield` fer automatic cleanup
- Check permissions on temp directories
- Verify no processes holdin' file locks

### Best Practices

1. **Always use fixtures** - Let pytest handle setup/teardown
2. **Clear assertions** - Use helper methods like `assert_success()`
3. **Meaningful messages** - Provide context in assertion messages
4. **Clean up properly** - Use harness.cleanup() or fixture teardown
5. **Test isolation** - Each test should be independent
6. **Fast tests** - Keep E2E tests focused and quick

### Examples

See the E2E test files fer complete examples:

- `test_plugin_manager_e2e.py` - Plugin installation workflows
- `test_hook_protocol_e2e.py` - Hook execution workflows
- `test_lsp_detection_e2e.py` - LSP detection workflows

---

**Philosophy Alignment:**

- ✅ Outside-in testin' (user perspective)
- ✅ Real subprocess execution (no mockin')
- ✅ Fast execution (< 5 minutes)
- ✅ Clear failure messages
- ✅ Zero-BS implementation (workin' code only)
