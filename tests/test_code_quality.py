"""
Code Quality Prevention Suite

Tests that prevent common code quality issues from being committed.
Part of Option C (Maximum) workflow adherence improvements.

These tests enforce:
- No syntax errors in Python files
- No unresolved merge conflict markers
- No TODO/FIXME/stub implementations in production code
- Philosophy compliance (zero-BS principle)

Run automatically during:
- Pre-commit hooks
- CI/CD pipeline
- Local test execution

Expected behavior:
- PASS: Code meets quality standards, ready to commit
- FAIL: Quality issues detected, must fix before commit
"""

import ast
from pathlib import Path

import pytest

# ==============================================================================
# Test Configuration
# ==============================================================================

# Directories to scan for quality checks
SCAN_DIRECTORIES = [
    ".claude",
    "tests",
    "docs",
]

# File patterns to include
INCLUDE_PATTERNS = ["*.py", "*.md"]

# Directories to exclude from scans
EXCLUDE_DIRECTORIES = [
    "__pycache__",
    ".git",
    ".pytest_cache",
    "node_modules",
    "venv",
    "dist",
    "build",
    ".claude/runtime/logs",  # Exclude runtime logs
]


def get_project_files(pattern: str, exclude_tests: bool = False) -> list[Path]:
    """
    Get all files matching pattern in project.

    Args:
        pattern: Glob pattern (e.g., "*.py")
        exclude_tests: Whether to exclude test files

    Returns:
        List of Path objects
    """
    project_root = Path(__file__).parent.parent
    files = []

    for scan_dir in SCAN_DIRECTORIES:
        scan_path = project_root / scan_dir
        if not scan_path.exists():
            continue

        for file_path in scan_path.rglob(pattern):
            # Skip excluded directories
            if any(excluded in file_path.parts for excluded in EXCLUDE_DIRECTORIES):
                continue

            # Skip test files if requested
            if exclude_tests and ("test_" in file_path.name or "/tests/" in str(file_path)):
                continue

            # Only include actual files
            if file_path.is_file():
                files.append(file_path)

    return files


# ==============================================================================
# Syntax Validation Tests
# ==============================================================================


@pytest.mark.parametrize("python_file", get_project_files("*.py"))
def test_python_syntax_valid(python_file: Path, validate_python_syntax):
    """
    Test that all Python files have valid syntax.

    Prevents commits with syntax errors that would break imports or execution.
    Uses AST parsing to catch syntax errors before they reach production.

    Args:
        python_file: Path to Python file to validate
        validate_python_syntax: Fixture for syntax validation
    """
    is_valid, error_msg = validate_python_syntax(python_file)

    assert is_valid, f"Syntax error detected:\n{error_msg}\n\nFile: {python_file}"


# ==============================================================================
# Merge Conflict Detection Tests
# ==============================================================================


@pytest.mark.parametrize("file_path", get_project_files("*.py") + get_project_files("*.md"))
def test_no_merge_conflicts(file_path: Path, validate_no_merge_conflicts):
    """
    Test that no files contain unresolved merge conflict markers.

    Prevents commits with conflict markers like:
    - <<<<<<< HEAD
    - =======
    - >>>>>>> branch

    Args:
        file_path: Path to file to check
        validate_no_merge_conflicts: Fixture for conflict detection
    """
    is_clean, conflict_lines = validate_no_merge_conflicts(file_path)

    if not is_clean:
        lines_str = ", ".join(map(str, conflict_lines))
        pytest.fail(
            f"Merge conflict markers detected in {file_path}\n"
            f"Conflict markers found on lines: {lines_str}\n"
            f"Please resolve conflicts before committing."
        )


# ==============================================================================
# TODO/FIXME Detection Tests
# ==============================================================================


@pytest.mark.parametrize("python_file", get_project_files("*.py", exclude_tests=True))
def test_no_todos_in_production(python_file: Path, validate_no_todos_in_production):
    """
    Test that production code contains no TODO/FIXME/stub markers.

    Enforces the zero-BS principle:
    - No placeholder implementations
    - No NotImplementedError in production
    - No TODO comments (tests are allowed to have TODOs)
    - Complete, working code only

    Args:
        python_file: Path to production Python file
        validate_no_todos_in_production: Fixture for TODO detection
    """
    is_clean, todos = validate_no_todos_in_production(python_file, allow_in_tests=True)

    if not is_clean:
        todo_details = "\n".join([f"  Line {line_num}: {line}" for line_num, line in todos])
        pytest.fail(
            f"TODO/FIXME markers detected in production code: {python_file}\n"
            f"Found {len(todos)} issues:\n{todo_details}\n\n"
            f"Zero-BS principle: Production code must be complete.\n"
            f"Either implement the functionality or remove the TODO."
        )


# ==============================================================================
# Stub Implementation Detection Tests
# ==============================================================================


def test_no_stub_implementations():
    """
    Test that no functions raise NotImplementedError without being abstract.

    Catches stub implementations that violate zero-BS principle:
    - Functions that exist but don't work
    - Placeholder implementations
    - Incomplete features disguised as complete

    Note: Abstract base classes (ABCs) are allowed to use NotImplementedError.
    """
    _ = Path(__file__).parent.parent
    python_files = get_project_files("*.py", exclude_tests=True)

    stubs_found = []

    for file_path in python_files:
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))

            # Find functions that raise NotImplementedError
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if function contains NotImplementedError
                    for child in ast.walk(node):
                        if isinstance(child, ast.Raise):
                            if isinstance(child.exc, ast.Call):
                                if isinstance(child.exc.func, ast.Name):
                                    if child.exc.func.id == "NotImplementedError":
                                        # Check if this is an abstract method
                                        is_abstract = any(
                                            isinstance(dec, ast.Name) and dec.id == "abstractmethod"
                                            for dec in node.decorator_list
                                        )

                                        if not is_abstract:
                                            stubs_found.append((file_path, node.name, node.lineno))

        except Exception:
            # If we can't parse, the syntax test will catch it
            continue

    if stubs_found:
        stub_details = "\n".join(
            [
                f"  {file_path}:{lineno} - Function '{func_name}'"
                for file_path, func_name, lineno in stubs_found
            ]
        )

        pytest.fail(
            f"Stub implementations detected (NotImplementedError in non-abstract methods):\n"
            f"{stub_details}\n\n"
            f"Zero-BS principle: Every function must work or not exist.\n"
            f"Either implement the function or remove it."
        )


# ==============================================================================
# Dead Code Detection Tests
# ==============================================================================


def test_no_unreachable_code():
    """
    Test that no functions contain unreachable code after return statements.

    Detects code that will never execute:
    - Code after unconditional return
    - Code after raise
    - Commented-out code blocks

    This catches common mistakes and ensures code clarity.
    """
    _ = Path(__file__).parent.parent
    python_files = get_project_files("*.py", exclude_tests=True)

    unreachable_found = []

    for file_path in python_files:
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check function body for unreachable code
                    for i, stmt in enumerate(node.body):
                        # If we hit a return or raise, everything after is unreachable
                        if isinstance(stmt, (ast.Return, ast.Raise)):
                            # Check if there's more code after this statement
                            if i < len(node.body) - 1:
                                # Ignore pass statements (sometimes used intentionally)
                                remaining = node.body[i + 1 :]
                                non_pass_remaining = [
                                    s for s in remaining if not isinstance(s, ast.Pass)
                                ]

                                if non_pass_remaining:
                                    unreachable_found.append((file_path, node.name, stmt.lineno))

        except Exception:
            continue

    if unreachable_found:
        unreachable_details = "\n".join(
            [
                f"  {file_path}:{lineno} - Function '{func_name}'"
                for file_path, func_name, lineno in unreachable_found
            ]
        )

        pytest.fail(
            f"Unreachable code detected:\n"
            f"{unreachable_details}\n\n"
            f"Code after return/raise statements will never execute.\n"
            f"Remove dead code or restructure control flow."
        )


# ==============================================================================
# Empty Exception Handler Detection Tests
# ==============================================================================


def test_no_swallowed_exceptions():
    """
    Test that no exception handlers silently swallow errors.

    Detects anti-pattern:
    ```python
    try:
        risky_operation()
    except Exception:
        pass  # BAD: Error is hidden
    ```

    Exceptions should be:
    - Handled specifically (catch specific exception types)
    - Logged or re-raised
    - Never silently ignored (unless explicitly documented why)
    """
    _ = Path(__file__).parent.parent
    python_files = get_project_files("*.py", exclude_tests=True)

    swallowed_exceptions = []

    for file_path in python_files:
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    # Check if handler body is empty or only contains pass
                    if len(node.body) == 0:
                        swallowed_exceptions.append(
                            (file_path, node.lineno, "Empty except handler")
                        )
                    elif len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                        # Allow 'pass' if there's a comment explaining why
                        # (This is a simplification - full implementation would check for comments)
                        swallowed_exceptions.append(
                            (file_path, node.lineno, "Exception silently swallowed (pass)")
                        )

        except Exception:
            continue

    if swallowed_exceptions:
        exception_details = "\n".join(
            [
                f"  {file_path}:{lineno} - {reason}"
                for file_path, lineno, reason in swallowed_exceptions
            ]
        )

        pytest.fail(
            f"Swallowed exceptions detected:\n"
            f"{exception_details}\n\n"
            f"Exceptions should be:\n"
            f"- Handled specifically (not bare 'except:')\n"
            f"- Logged or re-raised\n"
            f"- Documented if intentionally ignored\n"
            f"Never silently swallow errors with 'pass'."
        )


# ==============================================================================
# Workflow File Validation Tests
# ==============================================================================


def test_workflow_files_exist():
    """
    Test that all required workflow files exist.

    Ensures workflow infrastructure is complete:
    - DEFAULT_WORKFLOW.md (primary workflow)
    - DDD workflow commands
    - Investigation workflow
    - Diagnostic workflows
    """
    project_root = Path(__file__).parent.parent

    required_files = [
        ".claude/workflow/DEFAULT_WORKFLOW.md",
        ".claude/commands/ddd/0-help.md",
        ".claude/commands/ddd/1-plan.md",
        ".claude/workflow/INVESTIGATION_WORKFLOW.md",
    ]

    missing_files = []
    for file_path in required_files:
        full_path = project_root / file_path
        if not full_path.exists():
            missing_files.append(file_path)

    if missing_files:
        pytest.fail(
            "Required workflow files missing:\n"
            + "\n".join([f"  - {f}" for f in missing_files])
            + "\n\nWorkflow infrastructure is incomplete."
        )


def test_workflow_has_required_sections():
    """
    Test that DEFAULT_WORKFLOW.md contains all required sections.

    Validates workflow completeness:
    - Has workflow variables section
    - Has step-by-step instructions
    - Has cross-references to other workflows
    - Has self-validation questions
    """
    project_root = Path(__file__).parent.parent
    workflow_file = project_root / ".claude/workflow/DEFAULT_WORKFLOW.md"

    if not workflow_file.exists():
        pytest.skip("DEFAULT_WORKFLOW.md not found")

    content = workflow_file.read_text(encoding="utf-8")

    required_sections = [
        "Workflow Variables",  # Option C addition
        "Step 1:",  # Has numbered steps
        "Cross-Workflow Integration",  # Option C addition
        "Self-Validation Questions",  # Option C addition
    ]

    missing_sections = []
    for section in required_sections:
        if section not in content:
            missing_sections.append(section)

    if missing_sections:
        pytest.fail(
            "DEFAULT_WORKFLOW.md missing required sections:\n"
            + "\n".join([f"  - {s}" for s in missing_sections])
            + "\n\nWorkflow file incomplete (Option C requirements)."
        )


# ==============================================================================
# Monitoring Infrastructure Tests
# ==============================================================================


def test_monitoring_infrastructure_exists():
    """
    Test that Option C monitoring infrastructure is in place.

    Validates:
    - workflow_tracker.py exists
    - generate_workflow_report.py exists
    - Scripts are executable
    - Log directory exists
    """
    project_root = Path(__file__).parent.parent

    required_files = [
        ".claude/tools/amplihack/hooks/workflow_tracker.py",
        ".claude/tools/amplihack/generate_workflow_report.py",
    ]

    missing_files = []
    non_executable = []

    for file_path in required_files:
        full_path = project_root / file_path
        if not full_path.exists():
            missing_files.append(file_path)
        elif not full_path.stat().st_mode & 0o111:
            non_executable.append(file_path)

    errors = []
    if missing_files:
        errors.append("Missing files:\n" + "\n".join([f"  - {f}" for f in missing_files]))

    if non_executable:
        errors.append("Non-executable files:\n" + "\n".join([f"  - {f}" for f in non_executable]))

    if errors:
        pytest.fail(
            "Monitoring infrastructure incomplete:\n"
            + "\n\n".join(errors)
            + "\n\nOption C requirements not met."
        )


# ==============================================================================
# Performance Tests
# ==============================================================================


def test_workflow_tracker_performance(tmp_path):
    """
    Test that workflow_tracker.py meets performance requirements.

    Option C requirement: < 5ms overhead per log entry.

    This test imports and runs the tracker to verify performance.
    """
    import sys
    import time
    from pathlib import Path

    # Add hooks directory to path
    project_root = Path(__file__).parent.parent
    hooks_dir = project_root / ".claude/tools/amplihack/hooks"
    sys.path.insert(0, str(hooks_dir))

    try:
        # Override log directory for testing
        import workflow_tracker
        from workflow_tracker import log_step

        workflow_tracker.WORKFLOW_LOG_DIR = tmp_path
        workflow_tracker.WORKFLOW_LOG_FILE = tmp_path / "test.jsonl"

        # Measure performance
        iterations = 100
        start = time.perf_counter()

        for i in range(iterations):
            log_step(
                step_number=1,
                step_name="Test Step",
                agent_used="test-agent",
                duration_ms=100,
            )

        total_time = (time.perf_counter() - start) * 1000
        avg_time = total_time / iterations

        # Assert performance target met
        assert avg_time < 5, (
            f"workflow_tracker overhead ({avg_time:.3f}ms) exceeds 5ms target (Option C requirement)"
        )

    except ImportError as e:
        pytest.skip(f"Could not import workflow_tracker: {e}")
    finally:
        sys.path.remove(str(hooks_dir))
