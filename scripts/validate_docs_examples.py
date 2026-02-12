#!/usr/bin/env python3
"""Documentation Examples Validator - Validates code blocks in markdown files.

Two-tier validation approach:
1. Syntax Validation (always runs): Validates code blocks are syntactically correct
2. Execution Validation (opt-in): Executes code blocks marked <!-- runnable --> in Docker sandbox

Sandbox environment:
- Docker: Isolated container with read-only filesystem, no network, resource limits

Usage:
    python validate_docs_examples.py docs/README.md
    python validate_docs_examples.py docs/ --skip-execution
    python validate_docs_examples.py docs/ --verbose
"""

import argparse
import ast
import logging
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "DocsExampleValidator",
    "ValidationResult",
    "CodeBlock",
    "extract_code_blocks",
]

# ============================================================================
# Configuration
# ============================================================================

DEFAULT_TIMEOUT = 5  # seconds
DEFAULT_MEMORY_LIMIT = "256m"

# Compiled regex patterns (module-level for performance)
RUNNABLE_MARKER = re.compile(r"<!--\s*runnable\s*-->", re.IGNORECASE)
CODE_FENCE_START = re.compile(r"^(`{3,}|~{3,})(\w+)?")

# Supported languages and their syntax validators
LANGUAGE_VALIDATORS = {
    "python": "python",
    "py": "python",
    "javascript": "javascript",
    "js": "javascript",
    "bash": "bash",
    "sh": "bash",
}

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class CodeBlock:
    """Represents a code block extracted from markdown."""

    language: str
    content: str
    line_number: int
    is_runnable: bool = False


@dataclass
class ValidationResult:
    """Result of validation operation."""

    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
        }


# ============================================================================
# Markdown Parsing
# ============================================================================


def extract_code_blocks(markdown_path: Path) -> list[CodeBlock]:
    """Extract all code blocks from a markdown file.

    Args:
        markdown_path: Path to markdown file

    Returns:
        List of CodeBlock objects
    """
    try:
        content = markdown_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to read {markdown_path}: {e}")
        return []

    blocks = []
    lines = content.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Look for code fence start (```language or ~~~language)
        match = CODE_FENCE_START.match(line)
        if match:
            fence_char = match.group(1)[0]
            fence_length = len(match.group(1))
            language = match.group(2) or ""
            start_line = i + 1

            # Check if previous line has runnable marker
            is_runnable = False
            if i > 0 and RUNNABLE_MARKER.search(lines[i - 1]):
                is_runnable = True

            # Find closing fence
            i += 1
            code_lines = []
            while i < len(lines):
                if re.match(f"^{fence_char}{{{fence_length},}}", lines[i]):
                    break
                code_lines.append(lines[i])
                i += 1

            # Create code block
            code_content = "\n".join(code_lines)
            if language and code_content.strip():
                blocks.append(
                    CodeBlock(
                        language=language.lower(),
                        content=code_content,
                        line_number=start_line,
                        is_runnable=is_runnable,
                    )
                )

        i += 1

    return blocks


# ============================================================================
# Syntax Validation
# ============================================================================


def validate_python_syntax(code: str) -> tuple[bool, str | None]:
    """Validate Python code syntax.

    Args:
        code: Python code as string

    Returns:
        (is_valid, error_message) tuple
    """
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)


def validate_javascript_syntax(code: str) -> tuple[bool, str | None]:
    """Validate JavaScript code syntax using Node.js.

    Args:
        code: JavaScript code as string

    Returns:
        (is_valid, error_message) tuple
    """
    # Check if node is available
    if not shutil.which("node"):
        return True, None  # Skip validation if Node.js not installed (warning only)

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            result = subprocess.run(
                ["node", "--check", temp_path],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                return False, error_msg if error_msg else "Syntax check failed"
            return True, None
        finally:
            Path(temp_path).unlink(missing_ok=True)

    except subprocess.TimeoutExpired:
        return False, "Syntax check timed out"
    except Exception as e:
        return False, str(e)


def validate_bash_syntax(code: str) -> tuple[bool, str | None]:
    """Validate Bash code syntax using bash -n.

    Args:
        code: Bash code as string

    Returns:
        (is_valid, error_message) tuple
    """
    # Check if bash is available
    if not shutil.which("bash"):
        return True, None  # Skip validation if bash not installed

    try:
        result = subprocess.run(
            ["bash", "-n"],
            input=code,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            return False, error_msg if error_msg else "Syntax check failed"
        return True, None

    except subprocess.TimeoutExpired:
        return False, "Syntax check timed out"
    except Exception as e:
        return False, str(e)


# ============================================================================
# Docker Execution
# ============================================================================


def execute_python_docker(
    code: str, timeout: int = DEFAULT_TIMEOUT, memory_limit: str = DEFAULT_MEMORY_LIMIT
) -> tuple[bool, str | None]:
    """Execute Python code in Docker container sandbox.

    Args:
        code: Python code to execute
        timeout: Execution timeout in seconds
        memory_limit: Memory limit (e.g., "256m")

    Returns:
        (success, error_message) tuple
    """
    # Check if docker is available
    if not shutil.which("docker"):
        return False, "Docker not available"

    try:
        # Create temporary script file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            # Run in Docker with security constraints
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--read-only",  # Read-only filesystem
                    "--network=none",  # No network access
                    f"--memory={memory_limit}",  # Memory limit
                    "--cpus=0.5",  # CPU limit
                    "--cap-drop=ALL",  # Drop all capabilities
                    "--security-opt=no-new-privileges",  # Prevent privilege escalation
                    "-v",
                    f"{temp_path}:/script.py:ro",  # Mount script read-only
                    "python:3.11-alpine",  # Minimal Python image
                    "timeout",
                    str(timeout),
                    "python",
                    "/script.py",
                ],
                capture_output=True,
                text=True,
                timeout=timeout + 2,  # Add buffer for Docker overhead
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                if "Traceback" in error_msg:
                    error_msg = error_msg.split("\n")[-1]  # Extract last line
                return False, error_msg if error_msg else "Execution failed"

            return True, None

        finally:
            Path(temp_path).unlink(missing_ok=True)

    except subprocess.TimeoutExpired:
        return False, f"Execution exceeded {timeout}s timeout"
    except Exception as e:
        return False, f"Docker execution error: {e}"


# RestrictedPython removed - Docker-only execution for proper isolation


# ============================================================================
# Main Validator Class
# ============================================================================


class DocsExampleValidator:
    """Validates code examples in documentation."""

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        memory_limit: str = DEFAULT_MEMORY_LIMIT,
    ):
        """Initialize validator.

        Args:
            timeout: Execution timeout in seconds
            memory_limit: Memory limit for Docker (e.g., "256m")
        """
        self.timeout = timeout
        self.memory_limit = memory_limit

        # Cache Docker availability check
        self._docker_available = shutil.which("docker") is not None
        if not self._docker_available:
            logger.warning("Docker not available - execution validation will be skipped")

    def validate_syntax(
        self, markdown_path: Path, blocks: list[CodeBlock] | None = None
    ) -> ValidationResult:
        """Validate syntax of all code blocks in markdown file.

        Args:
            markdown_path: Path to markdown file
            blocks: Pre-extracted code blocks (for performance when calling both validations)

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult(success=True)

        if not markdown_path.exists():
            result.success = False
            result.errors.append(f"File not found: {markdown_path}")
            return result

        if markdown_path.is_dir():
            result.success = False
            result.errors.append(f"Expected file, got directory: {markdown_path}")
            return result

        # Extract code blocks (or use pre-extracted)
        if blocks is None:
            blocks = extract_code_blocks(markdown_path)

        if not blocks:
            result.info.append(f"No code blocks found in {markdown_path}")
            return result

        result.info.append(f"Found {len(blocks)} code block(s)")

        # Validate each block
        for block in blocks:
            validator_lang = LANGUAGE_VALIDATORS.get(block.language)

            if not validator_lang:
                result.warnings.append(
                    f"Line {block.line_number}: Unsupported language '{block.language}' (skipped)"
                )
                continue

            # Validate syntax
            is_valid, error_msg = self._validate_block_syntax(validator_lang, block.content)

            if not is_valid:
                result.success = False
                result.errors.append(f"Line {block.line_number} ({block.language}): {error_msg}")

        return result

    def validate_execution(
        self, markdown_path: Path, blocks: list[CodeBlock] | None = None
    ) -> ValidationResult:
        """Execute code blocks marked as runnable.

        Args:
            markdown_path: Path to markdown file
            blocks: Pre-extracted code blocks (for performance when calling both validations)

        Returns:
            ValidationResult with execution errors and warnings
        """
        result = ValidationResult(success=True)

        if not markdown_path.exists():
            result.success = False
            result.errors.append(f"File not found: {markdown_path}")
            return result

        # Extract code blocks (or use pre-extracted)
        if blocks is None:
            blocks = extract_code_blocks(markdown_path)
        runnable_blocks = [b for b in blocks if b.is_runnable]

        if not runnable_blocks:
            result.info.append("No runnable code blocks found")
            return result

        result.info.append(f"Found {len(runnable_blocks)} runnable block(s)")

        # Execute each runnable block
        for block in runnable_blocks:
            # Only Python is supported for execution currently
            if block.language not in ("python", "py"):
                result.warnings.append(
                    f"Line {block.line_number}: Language '{block.language}' not supported for execution (only Python)"
                )
                continue

            # Execute in sandbox
            success, error_msg = self._execute_block(block.content)

            if not success:
                result.success = False
                result.errors.append(f"Line {block.line_number} (execution): {error_msg}")

        return result

    def _validate_block_syntax(self, language: str, code: str) -> tuple[bool, str | None]:
        """Validate syntax of a code block.

        Args:
            language: Language name (python, javascript, bash)
            code: Code content

        Returns:
            (is_valid, error_message) tuple
        """
        if language == "python":
            return validate_python_syntax(code)
        elif language == "javascript":
            return validate_javascript_syntax(code)
        elif language == "bash":
            return validate_bash_syntax(code)
        else:
            return True, None  # Unsupported language, skip

    def _execute_block(self, code: str) -> tuple[bool, str | None]:
        """Execute a code block in Docker sandbox.

        Args:
            code: Python code to execute

        Returns:
            (success, error_message) tuple
        """
        return execute_python_docker(code, self.timeout, self.memory_limit)


# ============================================================================
# CLI Interface
# ============================================================================


def validate_file(
    file_path: Path,
    validator: DocsExampleValidator,
    skip_execution: bool = False,
) -> tuple[bool, int, int]:
    """Validate a single markdown file.

    Args:
        file_path: Path to markdown file
        validator: DocsExampleValidator instance
        skip_execution: Skip execution validation

    Returns:
        (success, error_count, warning_count) tuple
    """
    print(f"\nValidating: {file_path}")
    print("-" * 60)

    # Extract code blocks once for both validations (performance optimization)
    blocks = extract_code_blocks(file_path)

    # Syntax validation
    syntax_result = validator.validate_syntax(file_path, blocks)

    for info in syntax_result.info:
        logger.info(f"  ℹ {info}")

    for warning in syntax_result.warnings:
        logger.warning(f"  ⚠ {warning}")

    for error in syntax_result.errors:
        logger.error(f"  ✗ {error}")

    # Execution validation
    if not skip_execution:
        exec_result = validator.validate_execution(file_path, blocks)

        for info in exec_result.info:
            logger.info(f"  ℹ {info}")

        for warning in exec_result.warnings:
            logger.warning(f"  ⚠ {warning}")

        for error in exec_result.errors:
            logger.error(f"  ✗ {error}")

        # Combine results
        overall_success = syntax_result.success and exec_result.success
        total_errors = len(syntax_result.errors) + len(exec_result.errors)
        total_warnings = len(syntax_result.warnings) + len(exec_result.warnings)
    else:
        overall_success = syntax_result.success
        total_errors = len(syntax_result.errors)
        total_warnings = len(syntax_result.warnings)

    if overall_success:
        print("  ✓ All validations passed")
    else:
        print(f"  ✗ Validation failed: {total_errors} error(s)")

    return overall_success, total_errors, total_warnings


def validate_directory(
    directory: Path,
    validator: DocsExampleValidator,
    skip_execution: bool = False,
) -> tuple[bool, int, int]:
    """Validate all markdown files in directory.

    Args:
        directory: Path to directory
        validator: DocsExampleValidator instance
        skip_execution: Skip execution validation

    Returns:
        (success, total_errors, total_warnings) tuple
    """
    markdown_files = sorted(directory.rglob("*.md"))

    if not markdown_files:
        print(f"No markdown files found in {directory}")
        return True, 0, 0

    print(f"Found {len(markdown_files)} markdown file(s) in {directory}")

    total_errors = 0
    total_warnings = 0
    failed_files = []

    for md_file in markdown_files:
        success, errors, warnings = validate_file(md_file, validator, skip_execution)
        total_errors += errors
        total_warnings += warnings

        if not success:
            failed_files.append(md_file)

    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Files checked: {len(markdown_files)}")
    print(f"Passed: {len(markdown_files) - len(failed_files)}")
    print(f"Failed: {len(failed_files)}")
    print(f"Total errors: {total_errors}")
    print(f"Total warnings: {total_warnings}")

    if failed_files:
        print("\nFailed files:")
        for f in failed_files:
            print(f"  - {f}")

    return len(failed_files) == 0, total_errors, total_warnings


def parse_args(args=None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate code examples in documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s docs/README.md
  %(prog)s docs/ --skip-execution
  %(prog)s docs/ --verbose
  %(prog)s docs/ --timeout 10 --memory-limit 512m
        """,
    )

    parser.add_argument(
        "path",
        type=Path,
        help="Markdown file or directory to validate",
    )
    parser.add_argument(
        "--skip-execution",
        action="store_true",
        help="Skip execution validation (syntax only)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Execution timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--memory-limit",
        default=DEFAULT_MEMORY_LIMIT,
        help=f"Memory limit for Docker (default: {DEFAULT_MEMORY_LIMIT})",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args(args)


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Configure logging
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
    )

    print("Documentation Examples Validator")
    print("=" * 60)
    print("Sandbox: Docker")
    print(f"Timeout: {args.timeout}s")
    print(f"Memory limit: {args.memory_limit}")
    print()

    # Create validator
    validator = DocsExampleValidator(
        timeout=args.timeout,
        memory_limit=args.memory_limit,
    )

    # Validate file or directory
    if args.path.is_file():
        success, errors, warnings = validate_file(args.path, validator, args.skip_execution)
    elif args.path.is_dir():
        success, errors, warnings = validate_directory(args.path, validator, args.skip_execution)
    else:
        print(f"Error: Path does not exist: {args.path}")
        return 1

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
