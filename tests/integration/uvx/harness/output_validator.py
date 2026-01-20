"""Output Validator - Assertion helpers for UVX integration tests.

Philosophy:
- Single responsibility: Validate output from UVX launches
- Self-contained and regeneratable
- Clear, informative error messages
- Standard library only

Public API (the "studs"):
    assert_output_contains: Check stdout contains text
    assert_log_contains: Check log files contain text
    assert_stderr_contains: Check stderr contains text
    assert_hook_executed: Verify hook execution in logs
    assert_skill_loaded: Verify skill was loaded
    assert_command_executed: Verify command was executed
    assert_agent_invoked: Verify agent was invoked via Task tool
    assert_lsp_detected: Verify language was detected
    assert_settings_generated: Verify settings.json was created
"""

import re
from pathlib import Path
from typing import List, Optional, Pattern

__all__ = [
    "assert_output_contains",
    "assert_log_contains",
    "assert_stderr_contains",
    "assert_hook_executed",
    "assert_skill_loaded",
    "assert_command_executed",
    "assert_agent_invoked",
    "assert_lsp_detected",
    "assert_settings_generated",
]


def assert_output_contains(
    stdout: str,
    expected: str,
    message: str = "",
    case_sensitive: bool = True,
) -> None:
    """Assert that stdout contains expected text.

    Args:
        stdout: Standard output to check
        expected: Text that should be present
        message: Custom error message
        case_sensitive: Whether to match case

    Raises:
        AssertionError: If text not found

    Example:
        >>> assert_output_contains(output, "SessionStart hook executed")
    """
    search_text = stdout if case_sensitive else stdout.lower()
    target = expected if case_sensitive else expected.lower()

    if target not in search_text:
        error_msg = f"Expected text not found in stdout: '{expected}'\n"
        if message:
            error_msg += f"{message}\n"
        error_msg += f"Stdout:\n{stdout[:500]}"
        if len(stdout) > 500:
            error_msg += f"\n... ({len(stdout) - 500} more characters)"
        raise AssertionError(error_msg)


def assert_log_contains(
    log_files: List[Path],
    expected: str,
    message: str = "",
    case_sensitive: bool = True,
) -> None:
    """Assert that any log file contains expected text.

    Args:
        log_files: List of log file paths
        expected: Text that should be present
        message: Custom error message
        case_sensitive: Whether to match case

    Raises:
        AssertionError: If text not found in any log

    Example:
        >>> assert_log_contains(result.log_files, "Hook execution complete")
    """
    target = expected if case_sensitive else expected.lower()

    for log_file in log_files:
        if not log_file.exists():
            continue

        content = log_file.read_text()
        search_text = content if case_sensitive else content.lower()

        if target in search_text:
            return  # Found it!

    # Not found in any log
    error_msg = f"Expected text not found in logs: '{expected}'\n"
    if message:
        error_msg += f"{message}\n"
    error_msg += f"Searched {len(log_files)} log files:\n"
    for log_file in log_files:
        error_msg += f"  - {log_file}\n"
    raise AssertionError(error_msg)


def assert_stderr_contains(
    stderr: str,
    expected: str,
    message: str = "",
    case_sensitive: bool = True,
) -> None:
    """Assert that stderr contains expected text.

    Args:
        stderr: Standard error to check
        expected: Text that should be present
        message: Custom error message
        case_sensitive: Whether to match case

    Raises:
        AssertionError: If text not found

    Example:
        >>> assert_stderr_contains(result.stderr, "Warning: hook timeout")
    """
    search_text = stderr if case_sensitive else stderr.lower()
    target = expected if case_sensitive else expected.lower()

    if target not in search_text:
        error_msg = f"Expected text not found in stderr: '{expected}'\n"
        if message:
            error_msg += f"{message}\n"
        error_msg += f"Stderr:\n{stderr[:500]}"
        if len(stderr) > 500:
            error_msg += f"\n... ({len(stderr) - 500} more characters)"
        raise AssertionError(error_msg)


def assert_hook_executed(
    stdout: str,
    log_files: List[Path],
    hook_name: str,
    message: str = "",
) -> None:
    """Assert that a hook was executed.

    Checks both stdout and logs for hook execution evidence.

    Args:
        stdout: Standard output
        log_files: Log file paths
        hook_name: Hook name (SessionStart, Stop, etc.)
        message: Custom error message

    Raises:
        AssertionError: If hook execution not found

    Example:
        >>> assert_hook_executed(
        ...     result.stdout,
        ...     result.log_files,
        ...     "SessionStart"
        ... )
    """
    # Common hook execution patterns
    patterns = [
        f"Executing hook: {hook_name}",
        f"Hook {hook_name} executed",
        f"{hook_name} hook triggered",
        f"Running {hook_name}",
    ]

    # Check stdout
    for pattern in patterns:
        if pattern.lower() in stdout.lower():
            return

    # Check logs
    for log_file in log_files:
        if not log_file.exists():
            continue

        content = log_file.read_text().lower()
        for pattern in patterns:
            if pattern.lower() in content:
                return

    # Not found
    error_msg = f"Hook '{hook_name}' execution not found\n"
    if message:
        error_msg += f"{message}\n"
    error_msg += f"Checked patterns: {patterns}\n"
    error_msg += f"Stdout preview: {stdout[:200]}"
    raise AssertionError(error_msg)


def assert_skill_loaded(
    stdout: str,
    log_files: List[Path],
    skill_name: str,
    message: str = "",
) -> None:
    """Assert that a skill was loaded.

    Args:
        stdout: Standard output
        log_files: Log file paths
        skill_name: Skill name
        message: Custom error message

    Raises:
        AssertionError: If skill loading not found

    Example:
        >>> assert_skill_loaded(result.stdout, result.log_files, "pdf")
    """
    patterns = [
        f"Loading skill: {skill_name}",
        f"Skill {skill_name} loaded",
        f"Skill '{skill_name}'",
        f"skill: {skill_name}",
    ]

    # Check stdout
    for pattern in patterns:
        if pattern.lower() in stdout.lower():
            return

    # Check logs
    for log_file in log_files:
        if not log_file.exists():
            continue

        content = log_file.read_text().lower()
        for pattern in patterns:
            if pattern.lower() in content:
                return

    # Not found
    error_msg = f"Skill '{skill_name}' loading not found\n"
    if message:
        error_msg += f"{message}\n"
    error_msg += f"Checked patterns: {patterns}"
    raise AssertionError(error_msg)


def assert_command_executed(
    stdout: str,
    log_files: List[Path],
    command: str,
    message: str = "",
) -> None:
    """Assert that a slash command was executed.

    Args:
        stdout: Standard output
        log_files: Log file paths
        command: Command name (with or without leading slash)
        message: Custom error message

    Raises:
        AssertionError: If command execution not found

    Example:
        >>> assert_command_executed(
        ...     result.stdout,
        ...     result.log_files,
        ...     "/ultrathink"
        ... )
    """
    # Normalize command (remove leading slash)
    cmd = command.lstrip("/")

    patterns = [
        f"Executing command: /{cmd}",
        f"Command /{cmd} executed",
        f"Running /{cmd}",
        f"SlashCommand: {cmd}",
    ]

    # Check stdout
    for pattern in patterns:
        if pattern.lower() in stdout.lower():
            return

    # Check logs
    for log_file in log_files:
        if not log_file.exists():
            continue

        content = log_file.read_text().lower()
        for pattern in patterns:
            if pattern.lower() in content:
                return

    # Not found
    error_msg = f"Command '/{cmd}' execution not found\n"
    if message:
        error_msg += f"{message}\n"
    error_msg += f"Checked patterns: {patterns}"
    raise AssertionError(error_msg)


def assert_agent_invoked(
    stdout: str,
    log_files: List[Path],
    agent_name: str,
    message: str = "",
) -> None:
    """Assert that an agent was invoked via Task tool.

    Args:
        stdout: Standard output
        log_files: Log file paths
        agent_name: Agent name (architect, builder, etc.)
        message: Custom error message

    Raises:
        AssertionError: If agent invocation not found

    Example:
        >>> assert_agent_invoked(
        ...     result.stdout,
        ...     result.log_files,
        ...     "architect"
        ... )
    """
    patterns = [
        f"Invoking agent: {agent_name}",
        f"Agent {agent_name} invoked",
        f"Task tool: {agent_name}",
        f"subagent_type: {agent_name}",
        f"Delegating to {agent_name}",
    ]

    # Check stdout
    for pattern in patterns:
        if pattern.lower() in stdout.lower():
            return

    # Check logs
    for log_file in log_files:
        if not log_file.exists():
            continue

        content = log_file.read_text().lower()
        for pattern in patterns:
            if pattern.lower() in content:
                return

    # Not found
    error_msg = f"Agent '{agent_name}' invocation not found\n"
    if message:
        error_msg += f"{message}\n"
    error_msg += f"Checked patterns: {patterns}"
    raise AssertionError(error_msg)


def assert_lsp_detected(
    stdout: str,
    log_files: List[Path],
    language: str,
    message: str = "",
) -> None:
    """Assert that LSP detection found a language.

    Args:
        stdout: Standard output
        log_files: Log file paths
        language: Language name (Python, TypeScript, etc.)
        message: Custom error message

    Raises:
        AssertionError: If language detection not found

    Example:
        >>> assert_lsp_detected(result.stdout, result.log_files, "Python")
    """
    patterns = [
        f"Detected language: {language}",
        f"Language {language} detected",
        f"Found {language} files",
        f"LSP for {language}",
    ]

    # Check stdout
    for pattern in patterns:
        if pattern.lower() in stdout.lower():
            return

    # Check logs
    for log_file in log_files:
        if not log_file.exists():
            continue

        content = log_file.read_text().lower()
        for pattern in patterns:
            if pattern.lower() in content:
                return

    # Not found
    error_msg = f"Language '{language}' detection not found\n"
    if message:
        error_msg += f"{message}\n"
    error_msg += f"Checked patterns: {patterns}"
    raise AssertionError(error_msg)


def assert_settings_generated(
    cwd: Path,
    message: str = "",
) -> None:
    """Assert that settings.json was generated.

    Args:
        cwd: Working directory where settings should exist
        message: Custom error message

    Raises:
        AssertionError: If settings.json not found

    Example:
        >>> assert_settings_generated(project_dir)
    """
    settings_path = cwd / ".claude" / "settings.json"

    if not settings_path.exists():
        error_msg = f"settings.json not found at: {settings_path}\n"
        if message:
            error_msg += f"{message}\n"

        # Check if .claude directory exists
        claude_dir = cwd / ".claude"
        if not claude_dir.exists():
            error_msg += ".claude directory does not exist\n"
        else:
            error_msg += f".claude directory contents: {list(claude_dir.iterdir())}"

        raise AssertionError(error_msg)


# Pattern-based assertions for advanced validation

def assert_pattern_in_output(
    stdout: str,
    pattern: Pattern[str],
    message: str = "",
) -> Optional[re.Match]:
    """Assert that stdout matches a regex pattern.

    Args:
        stdout: Standard output
        pattern: Compiled regex pattern
        message: Custom error message

    Returns:
        Match object if found

    Raises:
        AssertionError: If pattern not found

    Example:
        >>> import re
        >>> pattern = re.compile(r"Duration: \d+\.\d+s")
        >>> assert_pattern_in_output(result.stdout, pattern)
    """
    match = pattern.search(stdout)

    if not match:
        error_msg = f"Pattern not found in stdout: {pattern.pattern}\n"
        if message:
            error_msg += f"{message}\n"
        error_msg += f"Stdout preview: {stdout[:300]}"
        raise AssertionError(error_msg)

    return match


def assert_pattern_in_logs(
    log_files: List[Path],
    pattern: Pattern[str],
    message: str = "",
) -> Optional[re.Match]:
    """Assert that log files match a regex pattern.

    Args:
        log_files: Log file paths
        pattern: Compiled regex pattern
        message: Custom error message

    Returns:
        Match object if found

    Raises:
        AssertionError: If pattern not found

    Example:
        >>> import re
        >>> pattern = re.compile(r"Hook execution time: \d+ms")
        >>> assert_pattern_in_logs(result.log_files, pattern)
    """
    for log_file in log_files:
        if not log_file.exists():
            continue

        content = log_file.read_text()
        match = pattern.search(content)

        if match:
            return match

    # Not found
    error_msg = f"Pattern not found in logs: {pattern.pattern}\n"
    if message:
        error_msg += f"{message}\n"
    error_msg += f"Searched {len(log_files)} log files"
    raise AssertionError(error_msg)
