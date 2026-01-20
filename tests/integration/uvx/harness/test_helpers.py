"""Test Helpers - Utility functions for UVX integration tests.

Philosophy:
- Single responsibility: Provide common test utilities
- Self-contained and regeneratable
- Standard library only
- Clear, simple implementations

Public API (the "studs"):
    collect_log_files: Collect log files from directory
    create_test_project: Create temporary test project
    wait_for_log_entry: Poll logs for expected entry
    extract_duration_from_output: Parse execution duration
    cleanup_temp_dirs: Clean up temporary test directories
"""

import time
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Callable
import re

__all__ = [
    "collect_log_files",
    "create_test_project",
    "wait_for_log_entry",
    "extract_duration_from_output",
    "cleanup_temp_dirs",
    "create_python_project",
    "create_typescript_project",
    "create_rust_project",
    "create_multi_language_project",
]


def collect_log_files(directory: Path, max_depth: int = 3) -> List[Path]:
    """Collect all log files from directory tree.

    Args:
        directory: Root directory to search
        max_depth: Maximum search depth (default: 3)

    Returns:
        List of log file paths

    Example:
        >>> log_files = collect_log_files(project_dir)
        >>> assert len(log_files) > 0
    """
    log_files = []

    # Common log locations
    log_patterns = [
        ".claude/runtime/logs/**/*.log",
        ".claude/runtime/logs/**/*.md",
        ".claude/runtime/logs/**/*.txt",
        "*.log",
        "logs/**/*.log",
    ]

    for pattern in log_patterns:
        try:
            log_files.extend(directory.glob(pattern))
        except Exception:
            # Ignore glob errors (permissions, etc.)
            pass

    # Remove duplicates and sort by modification time
    unique_logs = list(set(log_files))
    unique_logs.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)

    return unique_logs


def create_test_project(
    files: Dict[str, str],
    project_name: str = "test_project",
) -> Path:
    """Create temporary test project with specified files.

    Args:
        files: Dict of {relative_path: content}
        project_name: Project name (used in temp dir prefix)

    Returns:
        Path to project directory

    Example:
        >>> project_dir = create_test_project({
        ...     "main.py": "print('hello')",
        ...     "test.py": "def test(): pass"
        ... })
        >>> assert (project_dir / "main.py").exists()
    """
    project_dir = Path(tempfile.mkdtemp(prefix=f"{project_name}_"))

    for rel_path, content in files.items():
        file_path = project_dir / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)

    return project_dir


def wait_for_log_entry(
    log_files: List[Path],
    expected_text: str,
    timeout: float = 10.0,
    poll_interval: float = 0.5,
) -> bool:
    """Poll log files until expected text appears or timeout.

    Args:
        log_files: Log files to monitor
        expected_text: Text to wait for
        timeout: Timeout in seconds
        poll_interval: Polling interval in seconds

    Returns:
        True if found, False if timeout

    Example:
        >>> found = wait_for_log_entry(
        ...     log_files,
        ...     "Hook execution complete",
        ...     timeout=5.0
        ... )
        >>> assert found
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        for log_file in log_files:
            if not log_file.exists():
                continue

            try:
                content = log_file.read_text()
                if expected_text in content:
                    return True
            except Exception:
                # Ignore read errors (file being written, etc.)
                pass

        time.sleep(poll_interval)

    return False


def extract_duration_from_output(
    output: str,
    pattern: str = r"Duration: (\d+\.\d+)s",
) -> Optional[float]:
    """Extract execution duration from output.

    Args:
        output: stdout or stderr
        pattern: Regex pattern with duration capture group

    Returns:
        Duration in seconds, or None if not found

    Example:
        >>> duration = extract_duration_from_output(result.stdout)
        >>> assert duration < 60.0
    """
    match = re.search(pattern, output)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, IndexError):
            return None
    return None


def cleanup_temp_dirs(pattern: str = "uvx_test_*") -> int:
    """Clean up temporary test directories.

    Args:
        pattern: Glob pattern for temp dirs (default: "uvx_test_*")

    Returns:
        Number of directories cleaned up

    Example:
        >>> count = cleanup_temp_dirs()
        >>> print(f"Cleaned {count} temp dirs")
    """
    temp_root = Path(tempfile.gettempdir())
    count = 0

    for temp_dir in temp_root.glob(pattern):
        if temp_dir.is_dir():
            try:
                shutil.rmtree(temp_dir)
                count += 1
            except Exception:
                # Ignore cleanup errors
                pass

    return count


# Convenience functions for creating common project types

def create_python_project(
    project_name: str = "python_project",
    include_tests: bool = True,
) -> Path:
    """Create a Python project for testing.

    Args:
        project_name: Project name
        include_tests: Whether to include test files

    Returns:
        Path to project directory

    Example:
        >>> project_dir = create_python_project()
        >>> assert (project_dir / "main.py").exists()
    """
    files = {
        "main.py": """#!/usr/bin/env python3
\"\"\"Main module.\"\"\"

def main():
    print("Hello from Python!")

if __name__ == "__main__":
    main()
""",
        "utils.py": """\"\"\"Utility functions.\"\"\"

def add(a: int, b: int) -> int:
    return a + b
""",
        "requirements.txt": "pytest>=7.0.0\n",
    }

    if include_tests:
        files["tests/test_utils.py"] = """\"\"\"Tests for utils.\"\"\"
import pytest
from utils import add

def test_add():
    assert add(2, 3) == 5
"""

    return create_test_project(files, project_name)


def create_typescript_project(
    project_name: str = "typescript_project",
    include_tests: bool = True,
) -> Path:
    """Create a TypeScript project for testing.

    Args:
        project_name: Project name
        include_tests: Whether to include test files

    Returns:
        Path to project directory

    Example:
        >>> project_dir = create_typescript_project()
        >>> assert (project_dir / "index.ts").exists()
    """
    files = {
        "index.ts": """// Main entry point
export function greet(name: string): string {
    return `Hello, ${name}!`;
}

console.log(greet("World"));
""",
        "utils.ts": """// Utility functions
export function add(a: number, b: number): number {
    return a + b;
}
""",
        "package.json": """{
  "name": "test-project",
  "version": "1.0.0",
  "scripts": {
    "build": "tsc",
    "test": "jest"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "@types/node": "^20.0.0"
  }
}
""",
        "tsconfig.json": """{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "strict": true,
    "esModuleInterop": true,
    "outDir": "dist"
  },
  "include": ["**/*.ts"],
  "exclude": ["node_modules"]
}
""",
    }

    if include_tests:
        files["tests/utils.test.ts"] = """// Tests for utils
import { add } from '../utils';

test('add function', () => {
    expect(add(2, 3)).toBe(5);
});
"""

    return create_test_project(files, project_name)


def create_rust_project(
    project_name: str = "rust_project",
    include_tests: bool = True,
) -> Path:
    """Create a Rust project for testing.

    Args:
        project_name: Project name
        include_tests: Whether to include test files

    Returns:
        Path to project directory

    Example:
        >>> project_dir = create_rust_project()
        >>> assert (project_dir / "main.rs").exists()
    """
    files = {
        "main.rs": """// Main entry point
fn main() {
    println!("Hello from Rust!");
}
""",
        "lib.rs": """// Library module
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}
""",
        "Cargo.toml": """[package]
name = "test-project"
version = "0.1.0"
edition = "2021"

[dependencies]
""",
    }

    if include_tests:
        files["tests/test_lib.rs"] = """// Tests for lib
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add() {
        assert_eq!(add(2, 3), 5);
    }
}
"""

    return create_test_project(files, project_name)


def create_multi_language_project(
    languages: List[str],
    project_name: str = "multi_lang_project",
) -> Path:
    """Create a multi-language project for testing.

    Args:
        languages: Languages to include (python, typescript, rust, javascript, go)
        project_name: Project name

    Returns:
        Path to project directory

    Example:
        >>> project_dir = create_multi_language_project(["python", "typescript"])
        >>> assert (project_dir / "main.py").exists()
        >>> assert (project_dir / "index.ts").exists()
    """
    files = {}

    if "python" in languages:
        files["main.py"] = "print('hello')\n"

    if "typescript" in languages:
        files["index.ts"] = "console.log('hello');\n"

    if "javascript" in languages:
        files["app.js"] = "console.log('hello');\n"

    if "rust" in languages:
        files["main.rs"] = 'fn main() { println!("hello"); }\n'

    if "go" in languages:
        files["main.go"] = "package main\n\nfunc main() {}\n"

    return create_test_project(files, project_name)


# Assertion helpers that combine multiple checks

def assert_all_files_exist(
    directory: Path,
    expected_files: List[str],
    message: str = "",
) -> None:
    """Assert that all expected files exist in directory.

    Args:
        directory: Directory to check
        expected_files: List of relative paths
        message: Custom error message

    Raises:
        AssertionError: If any file is missing

    Example:
        >>> assert_all_files_exist(project_dir, ["main.py", "test.py"])
    """
    missing = []

    for rel_path in expected_files:
        file_path = directory / rel_path
        if not file_path.exists():
            missing.append(rel_path)

    if missing:
        error_msg = f"Missing files: {missing}\n"
        if message:
            error_msg += f"{message}\n"
        error_msg += f"Directory: {directory}"
        raise AssertionError(error_msg)


def retry_with_backoff(
    func: Callable[[], bool],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
) -> bool:
    """Retry a function with exponential backoff.

    Args:
        func: Function to retry (should return bool)
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
        backoff_factor: Backoff multiplier

    Returns:
        True if func eventually returns True, False otherwise

    Example:
        >>> def check_file_exists():
        ...     return Path("output.txt").exists()
        >>> success = retry_with_backoff(check_file_exists)
    """
    delay = initial_delay

    for attempt in range(max_retries):
        if func():
            return True

        if attempt < max_retries - 1:
            time.sleep(delay)
            delay *= backoff_factor

    return False
