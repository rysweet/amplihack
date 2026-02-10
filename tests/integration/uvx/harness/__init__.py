"""UVX Integration Test Harness.

Philosophy:
- Self-contained test harness for UVX-based integration tests
- Tests amplihack from the outside using real UVX installation
- Clear public API ("studs") for test consumption

Public API (the "studs"):
    From uvx_launcher:
        - uvx_launch: Launch amplihack via UVX
        - uvx_launch_with_test_project: Launch with temp project
        - UVXLaunchResult: Result dataclass

    From output_validator:
        - assert_output_contains: Check stdout
        - assert_log_contains: Check logs
        - assert_stderr_contains: Check stderr
        - assert_hook_executed: Verify hook
        - assert_skill_loaded: Verify skill
        - assert_command_executed: Verify command
        - assert_agent_invoked: Verify agent
        - assert_lsp_detected: Verify LSP detection
        - assert_settings_generated: Verify settings.json

    From test_helpers:
        - collect_log_files: Collect logs
        - create_test_project: Create temp project
        - wait_for_log_entry: Poll logs
        - extract_duration_from_output: Parse duration
        - cleanup_temp_dirs: Cleanup
        - create_python_project: Python project
        - create_typescript_project: TypeScript project
        - create_rust_project: Rust project
        - create_multi_language_project: Multi-language project
"""

# Import all public APIs
from .output_validator import (
    assert_agent_invoked,
    assert_command_executed,
    assert_hook_executed,
    assert_log_contains,
    assert_lsp_detected,
    assert_output_contains,
    assert_pattern_in_logs,
    assert_pattern_in_output,
    assert_settings_generated,
    assert_skill_loaded,
    assert_stderr_contains,
)
from .test_helpers import (
    assert_all_files_exist,
    cleanup_temp_dirs,
    collect_log_files,
    create_multi_language_project,
    create_python_project,
    create_rust_project,
    create_test_project,
    create_typescript_project,
    extract_duration_from_output,
    retry_with_backoff,
    wait_for_log_entry,
)
from .uvx_launcher import (
    UVXLaunchResult,
    launch_and_test_command,
    launch_and_test_hook,
    launch_and_test_skill,
    launch_with_lsp_detection,
    uvx_launch,
    uvx_launch_with_test_project,
)

__all__ = [
    # Launcher
    "uvx_launch",
    "uvx_launch_with_test_project",
    "UVXLaunchResult",
    "launch_and_test_hook",
    "launch_and_test_skill",
    "launch_and_test_command",
    "launch_with_lsp_detection",
    # Validators
    "assert_output_contains",
    "assert_log_contains",
    "assert_stderr_contains",
    "assert_hook_executed",
    "assert_skill_loaded",
    "assert_command_executed",
    "assert_agent_invoked",
    "assert_lsp_detected",
    "assert_settings_generated",
    "assert_pattern_in_output",
    "assert_pattern_in_logs",
    # Helpers
    "collect_log_files",
    "create_test_project",
    "wait_for_log_entry",
    "extract_duration_from_output",
    "cleanup_temp_dirs",
    "create_python_project",
    "create_typescript_project",
    "create_rust_project",
    "create_multi_language_project",
    "assert_all_files_exist",
    "retry_with_backoff",
]
