# UVX Integration Tests

**Outside-in integration testing fer amplihack plugin architecture using real UVX launches.**

## Overview

This test suite validates amplihack functionality from the user's perspective by:

- Launching amplihack via `uvx --from git+...`
- Using non-interactive prompts (`-p` flag)
- Validating output through stdout, stderr, and log files
- Testing real plugin installation and configuration flows

## Philosophy

- **Outside-in testing**: Tests from user perspective, not internal implementation
- **Real UVX execution**: No mocking - tests actual UVX installation flow
- **CI-ready**: All tests use non-interactive mode
- **Fast execution**: < 5 minutes for complete suite
- **Self-contained**: Each test creates its own temp environment

## Test Structure

```
tests/integration/uvx/
├── harness/                     # Test harness (the "brick")
│   ├── __init__.py              # Public API exports
│   ├── uvx_launcher.py          # UVX launch wrapper
│   ├── output_validator.py      # Assertion helpers
│   └── test_helpers.py          # Utility functions
├── test_hooks.py                # Hook validation tests
├── test_skills.py               # Skill auto-discovery tests
├── test_commands.py             # Slash command tests
├── test_agents.py               # Agent invocation tests
├── test_lsp_detection.py        # LSP language detection tests
├── test_settings_generation.py  # Settings.json generation tests
└── README.md                    # This file
```

## Running Tests

### Quick Start

```bash
# Run all UVX integration tests
pytest tests/integration/uvx/ -v

# Run specific test file
pytest tests/integration/uvx/test_hooks.py -v

# Run with markers
pytest -m "uvx and hooks" -v

# Run with output visible
pytest tests/integration/uvx/ -v -s
```

### Test Markers

- `integration` - All integration tests
- `uvx` - UVX-based tests
- `hooks` - Hook validation tests
- `skills` - Skill system tests
- `commands` - Slash command tests
- `agents` - Agent invocation tests
- `lsp` - LSP detection tests
- `settings` - Settings generation tests

### Performance Testing

```bash
# Run with timing
pytest tests/integration/uvx/ -v --durations=10

# Run with timeout
pytest tests/integration/uvx/ -v --timeout=300
```

## Test Harness API

### UVX Launcher

```python
from tests.integration.uvx.harness import (
    uvx_launch,
    uvx_launch_with_test_project,
    UVXLaunchResult,
)

# Simple launch
result = uvx_launch(
    git_ref="feat/issue-1948-plugin-architecture",
    prompt="List available skills",
    timeout=60,
)

# Launch with test project
result = uvx_launch_with_test_project(
    project_files={"main.py": "print('hello')"},
    prompt="Analyze this project",
    timeout=60,
)

# Assertions
result.assert_success()
result.assert_in_output("expected text")
result.assert_in_logs("log entry")
```

### Output Validation

```python
from tests.integration.uvx.harness import (
    assert_output_contains,
    assert_log_contains,
    assert_hook_executed,
    assert_skill_loaded,
    assert_command_executed,
    assert_agent_invoked,
    assert_lsp_detected,
    assert_settings_generated,
)

# Validate output
assert_output_contains(result.stdout, "SessionStart")
assert_log_contains(result.log_files, "Hook executed")

# Validate specific components
assert_hook_executed(result.stdout, result.log_files, "SessionStart")
assert_skill_loaded(result.stdout, result.log_files, "pdf")
assert_command_executed(result.stdout, result.log_files, "/ultrathink")
assert_agent_invoked(result.stdout, result.log_files, "architect")
assert_lsp_detected(result.stdout, result.log_files, "Python")
assert_settings_generated(project_dir)
```

### Test Helpers

```python
from tests.integration.uvx.harness import (
    collect_log_files,
    create_test_project,
    create_python_project,
    create_typescript_project,
    create_rust_project,
    create_multi_language_project,
)

# Create test projects
project_dir = create_python_project()
project_dir = create_typescript_project()
project_dir = create_multi_language_project(["python", "typescript"])

# Collect logs
log_files = collect_log_files(project_dir)
```

## Test Coverage

### Hook Tests (test_hooks.py)

- SessionStart hook execution
- Stop hook execution
- PostToolUse hook execution
- PreCompact hook awareness
- Hook integration and ordering
- Hook error handling

### Skill Tests (test_skills.py)

- Skill auto-discovery
- Skill listing with descriptions
- Explicit skill invocation
- Common skills (pdf, mcp-manager, agent-sdk)
- Context-based triggers
- Multiple skills in session
- Skill error handling

### Command Tests (test_commands.py)

- /ultrathink command
- /fix command with patterns
- /analyze command
- /improve command
- Multiple commands in session
- Command help system
- Command error handling
- Plugin-provided commands

### Agent Tests (test_agents.py)

- Architect agent for design
- Builder agent for implementation
- Tester agent for test generation
- Reviewer agent for code review
- Specialized agents
- Multi-agent workflows
- Agent delegation via Task tool
- Agent parallel execution

### LSP Detection Tests (test_lsp_detection.py)

- Python language detection
- TypeScript language detection
- Rust language detection
- Multi-language project detection
- Hidden file/directory exclusion (node_modules, .git, venv)
- LSP configuration generation
- Detection performance
- Error handling

### Settings Generation Tests (test_settings_generation.py)

- settings.json creation
- JSON structure validation
- Plugin metadata inclusion
- LSP configuration merging
- MCP server configuration
- Settings formatting
- Update and merge behavior
- Conflict resolution

## Configuration

### Git Reference

Tests default to `feat/issue-1948-plugin-architecture` branch. Override with:

```python
result = uvx_launch(
    git_ref="main",  # or any branch/tag/commit
    prompt="...",
)
```

### Timeout

Default timeout is 60 seconds. Adjust fer longer operations:

```python
result = uvx_launch(
    prompt="Complex task",
    timeout=120,  # 2 minutes
)
```

### Environment Variables

Tests set these automatically:

- `AMPLIHACK_CI_MODE=1` - Non-interactive mode
- `AMPLIHACK_LOG_LEVEL=DEBUG` - Verbose logging

Override with:

```python
result = uvx_launch(
    prompt="...",
    env={"CUSTOM_VAR": "value"},
)
```

## CI Integration

### GitHub Actions

```yaml
- name: Run UVX Integration Tests
  run: |
    pytest tests/integration/uvx/ -v --timeout=300
```

### Azure DevOps

```yaml
- script: |
    pytest tests/integration/uvx/ -v --timeout=300
  displayName: "UVX Integration Tests"
```

## Performance Targets

- Individual test: < 60 seconds
- Complete suite: < 5 minutes
- UVX launch: < 30 seconds (typical)
- Hook execution: < 5 seconds
- LSP detection: < 10 seconds
- Settings generation: < 5 seconds

## Troubleshooting

### Tests Timing Out

```bash
# Increase timeout
pytest tests/integration/uvx/ -v --timeout=600

# Run specific slow tests
pytest tests/integration/uvx/test_commands.py::TestUltrathinkCommand -v
```

### UVX Installation Failures

```bash
# Check UVX is available
which uvx

# Test UVX manually
uvx --from git+https://github.com/rysweet/amplihack@main amplihack --version
```

### Log File Issues

```python
# Debug log collection
from tests.integration.uvx.harness import collect_log_files

log_files = collect_log_files(project_dir)
print(f"Found {len(log_files)} log files")
for log_file in log_files:
    print(f"  - {log_file}")
```

### Temp Directory Cleanup

```python
# Manual cleanup
from tests.integration.uvx.harness import cleanup_temp_dirs

count = cleanup_temp_dirs()
print(f"Cleaned {count} temp directories")
```

## Development

### Adding New Tests

1. Create test file in `tests/integration/uvx/`
2. Import harness: `from .harness import ...`
3. Use `uvx_launch` or `uvx_launch_with_test_project`
4. Add assertions using validation helpers
5. Mark with appropriate pytest markers

### Adding New Assertions

1. Add function to `harness/output_validator.py`
2. Export in `harness/__init__.py`
3. Document in this README
4. Add test fer the assertion helper

### Extending Harness

1. Add utility to appropriate harness module
2. Export via `__all__`
3. Update `harness/__init__.py`
4. Document in this README

## Philosophy Compliance

✅ **Ruthless Simplicity**

- Direct, focused tests
- No complex test frameworks
- Simple assertion helpers

✅ **Zero-BS Implementation**

- All tests verify real behavior
- No mocking of UVX or amplihack
- Real subprocess execution

✅ **Modular Design (Bricks & Studs)**

- Self-contained harness module
- Clear public API via `__all__`
- Tests are independent

✅ **Outside-In Testing**

- Tests from user perspective
- Validates actual UVX workflow
- Verifies end-to-end functionality

## Contributing

When adding tests:

1. Follow existing test structure
2. Use harness helpers consistently
3. Keep tests under 60 seconds
4. Add clear assertions with messages
5. Document new features in README

## References

- [Plugin Architecture Test Plan](../TEST_PLAN_PLUGIN_ARCHITECTURE.md)
- [E2E Test Harness](../../harness/README.md)
- [Subprocess Test Harness](../../harness/subprocess_test_harness.py)
- [UVX Documentation](https://github.com/astral-sh/uv)

---

**Status**: ✅ Complete - UVX integration test harness and full test suite implemented

**Philosophy**: Outside-in, real UVX execution, CI-ready, fast, self-contained
