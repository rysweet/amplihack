"""
Test suite for runnable examples validator.

This test suite defines the contract for scripts/validate_docs_examples.py
following Test-Driven Development methodology. All tests will fail initially
until the validator is implemented.

Test Coverage:
- Syntax validation for multiple languages (Python, JavaScript, Bash)
- Docker-based sandboxed execution (primary)
- RestrictedPython fallback (when Docker unavailable)
- Security controls (timeout, memory limit, restricted builtins)
- Opt-in execution with <!-- runnable --> marker
- Edge cases and error handling
"""

import subprocess
import tempfile
from pathlib import Path

import pytest

# These imports will fail initially - that's expected for TDD
try:
    from scripts.validate_docs_examples import (
        DocsExampleValidator,
        ValidationResult,
    )
except ImportError:
    # Mark all tests as expected to fail until implementation exists
    pytestmark = pytest.mark.xfail(reason="Implementation does not exist yet")

    # Create placeholder classes for test structure
    class DocsExampleValidator:
        pass

    class ValidationResult:
        pass


class TestSyntaxValidation:
    """Test syntax validation for code blocks in markdown files."""

    def test_valid_python_syntax(self, tmp_path):
        """Should pass for valid Python code."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
# Test Doc

```python
def hello():
    return "world"
```
""")

        validator = DocsExampleValidator()
        result = validator.validate_syntax(markdown)

        assert result.success is True
        assert len(result.errors) == 0

    def test_invalid_python_syntax(self, tmp_path):
        """Should fail for invalid Python syntax."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
```python
def hello(
    return "missing colon and closing paren"
```
""")

        validator = DocsExampleValidator()
        result = validator.validate_syntax(markdown)

        assert result.success is False
        assert len(result.errors) == 1
        assert "SyntaxError" in result.errors[0]

    def test_valid_javascript_syntax(self, tmp_path):
        """Should pass for valid JavaScript code."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
```javascript
function hello() {
    return "world";
}
```
""")

        validator = DocsExampleValidator()
        result = validator.validate_syntax(markdown)

        assert result.success is True

    def test_invalid_javascript_syntax(self, tmp_path):
        """Should fail for invalid JavaScript syntax."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
```javascript
function hello() {
    return "missing closing brace";
```
""")

        validator = DocsExampleValidator()
        result = validator.validate_syntax(markdown)

        assert result.success is False
        assert "SyntaxError" in str(result.errors[0])

    def test_valid_bash_syntax(self, tmp_path):
        """Should pass for valid Bash code."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
```bash
#!/bin/bash
echo "Hello World"
ls -la
```
""")

        validator = DocsExampleValidator()
        result = validator.validate_syntax(markdown)

        assert result.success is True

    def test_multiple_code_blocks(self, tmp_path):
        """Should validate all code blocks in a file."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
# Multiple Examples

```python
def foo():
    pass
```

Some text.

```python
def bar():
    return 42
```

```javascript
const x = 5;
```
""")

        validator = DocsExampleValidator()
        result = validator.validate_syntax(markdown)

        assert result.success is True
        assert len(result.errors) == 0

    def test_ignore_non_code_fenced_blocks(self, tmp_path):
        """Should ignore fenced blocks without language specification."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
```
Plain text block
```

```python
print("Valid Python")
```
""")

        validator = DocsExampleValidator()
        result = validator.validate_syntax(markdown)

        assert result.success is True
        assert len(result.errors) == 0


class TestDockerExecution:
    """Test Docker-based sandboxed execution of runnable examples."""

    def test_successful_python_execution(self, tmp_path):
        """Should execute valid Python code in Docker container."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
<!-- runnable -->
```python
print("Hello from Docker")
result = 2 + 2
assert result == 4
```
""")

        validator = DocsExampleValidator()
        result = validator.validate_execution(markdown)

        assert result.success is True
        assert len(result.errors) == 0

    def test_code_block_without_runnable_marker_skipped(self, tmp_path):
        """Should skip execution for blocks without <!-- runnable --> marker."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
```python
# No runnable marker - should be skipped
import os
os.system("rm -rf /")  # Dangerous but should not execute
```
""")

        validator = DocsExampleValidator()
        result = validator.validate_execution(markdown)

        assert result.success is True
        assert len(result.errors) == 0

    def test_timeout_enforcement(self, tmp_path):
        """Should enforce 5-second timeout in Docker execution."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
<!-- runnable -->
```python
import time
time.sleep(10)  # Should timeout after 5 seconds
```
""")

        validator = DocsExampleValidator(timeout=5)
        result = validator.validate_execution(markdown)

        assert result.success is False
        assert any("timeout" in str(err).lower() for err in result.errors)

    def test_memory_limit_enforcement(self, tmp_path):
        """Should enforce 256MB memory limit in Docker."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
<!-- runnable -->
```python
# Attempt to allocate 512MB
data = bytearray(512 * 1024 * 1024)
```
""")

        validator = DocsExampleValidator(memory_limit="256m")
        result = validator.validate_execution(markdown)

        assert result.success is False
        assert any("memory" in str(err).lower() for err in result.errors)

    def test_read_only_filesystem(self, tmp_path):
        """Should enforce read-only filesystem in Docker container."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
<!-- runnable -->
```python
# Attempt to write to filesystem
with open("/tmp/malicious.txt", "w") as f:
    f.write("Should fail")
```
""")

        validator = DocsExampleValidator()
        result = validator.validate_execution(markdown)

        assert result.success is False
        assert any(
            "read-only" in str(err).lower() or "permission" in str(err).lower()
            for err in result.errors
        )

    def test_network_disabled(self, tmp_path):
        """Should disable network access in Docker container."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
<!-- runnable -->
```python
import urllib.request
# Should fail - no network access
urllib.request.urlopen("http://example.com")
```
""")

        validator = DocsExampleValidator()
        result = validator.validate_execution(markdown)

        assert result.success is False
        assert any(
            "network" in str(err).lower() or "unreachable" in str(err).lower()
            for err in result.errors
        )

    def test_subprocess_blocked(self, tmp_path):
        """Should block subprocess execution in Docker container."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
<!-- runnable -->
```python
import subprocess
# Should fail - subprocess blocked
subprocess.run(["ls", "-la"])
```
""")

        validator = DocsExampleValidator()
        result = validator.validate_execution(markdown)

        assert result.success is False


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_markdown_file(self, tmp_path):
        """Should handle empty markdown files gracefully."""
        markdown = tmp_path / "empty.md"
        markdown.write_text("")

        validator = DocsExampleValidator()
        result = validator.validate_syntax(markdown)

        assert result.success is True
        assert len(result.errors) == 0

    def test_markdown_with_no_code_blocks(self, tmp_path):
        """Should handle markdown with no code blocks."""
        markdown = tmp_path / "text.md"
        markdown.write_text("""
# Just Text

This is a markdown file with no code blocks.
Just plain text and headers.
""")

        validator = DocsExampleValidator()
        result = validator.validate_syntax(markdown)

        assert result.success is True
        assert len(result.errors) == 0

    def test_malformed_fenced_block(self, tmp_path):
        """Should handle malformed fenced code blocks."""
        markdown = tmp_path / "malformed.md"
        markdown.write_text("""
```python
def foo():
    pass
# Missing closing fence
""")

        validator = DocsExampleValidator()
        result = validator.validate_syntax(markdown)

        # Should handle gracefully - either ignore or report error
        assert isinstance(result, ValidationResult)

    def test_unicode_in_code_blocks(self, tmp_path):
        """Should handle Unicode characters in code blocks."""
        markdown = tmp_path / "unicode.md"
        markdown.write_text("""
```python
message = "Hello 世界 🌍"
print(message)
```
""")

        validator = DocsExampleValidator()
        result = validator.validate_syntax(markdown)

        assert result.success is True

    def test_partial_code_example(self, tmp_path):
        """Should recognize partial examples (without runnable marker)."""
        markdown = tmp_path / "partial.md"
        markdown.write_text("""
Example usage:

```python
# This is a partial example showing API usage
client.connect()
# ... rest of code ...
```
""")

        validator = DocsExampleValidator()

        # Syntax validation should still work
        syntax_result = validator.validate_syntax(markdown)
        assert syntax_result.success is False  # Incomplete code

        # But execution should be skipped (no runnable marker)
        exec_result = validator.validate_execution(markdown)
        assert len(exec_result.errors) == 0

    def test_multiple_languages_same_file(self, tmp_path):
        """Should validate multiple languages in same file."""
        markdown = tmp_path / "multi.md"
        markdown.write_text("""
# Multi-Language Examples

Python:
```python
def hello():
    return "world"
```

JavaScript:
```javascript
function hello() {
    return "world";
}
```

Bash:
```bash
echo "Hello World"
```
""")

        validator = DocsExampleValidator()
        result = validator.validate_syntax(markdown)

        assert result.success is True
        assert len(result.errors) == 0

    def test_runnable_marker_case_insensitive(self, tmp_path):
        """Should recognize runnable marker regardless of case."""
        variations = [
            "<!-- runnable -->",
            "<!-- RUNNABLE -->",
            "<!-- Runnable -->",
            "<!--runnable-->",
        ]

        validator = DocsExampleValidator()

        for marker in variations:
            markdown = Path(tempfile.mktemp(suffix=".md"))
            markdown.write_text(f"""
{marker}
```python
print("Test")
```
""")

            result = validator.validate_execution(markdown)
            assert len(result.errors) == 0, f"Should recognize: {marker}"
            markdown.unlink()

    def test_nonexistent_file(self):
        """Should handle error for nonexistent files."""
        validator = DocsExampleValidator()

        result = validator.validate_syntax(Path("/nonexistent/file.md"))
        assert result.success is False
        assert len(result.errors) > 0

    def test_directory_instead_of_file(self, tmp_path):
        """Should handle error when directory provided instead of file."""
        validator = DocsExampleValidator()

        result = validator.validate_syntax(tmp_path)
        assert result.success is False
        assert len(result.errors) > 0


class TestCLIInterface:
    """Test command-line interface for the validator."""

    def test_cli_validates_single_file(self, tmp_path):
        """Should validate single file from CLI."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
```python
print("Valid")
```
""")

        result = subprocess.run(
            ["python", "scripts/validate_docs_examples.py", str(markdown)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "✓" in result.stdout or "PASS" in result.stdout

    def test_cli_validates_directory(self, tmp_path):
        """Should validate all markdown files in directory."""
        (tmp_path / "doc1.md").write_text("```python\nprint(1)\n```")
        (tmp_path / "doc2.md").write_text("```python\nprint(2)\n```")

        result = subprocess.run(
            ["python", "scripts/validate_docs_examples.py", str(tmp_path)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "2" in result.stdout  # Should report 2 files validated

    def test_cli_fails_on_invalid_syntax(self, tmp_path):
        """Should exit with non-zero code on syntax errors."""
        markdown = tmp_path / "invalid.md"
        markdown.write_text("""
```python
def broken(
    invalid syntax here
```
""")

        result = subprocess.run(
            ["python", "scripts/validate_docs_examples.py", str(markdown)],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "SyntaxError" in result.stderr or "FAIL" in result.stdout

    def test_cli_skip_execution_flag(self, tmp_path):
        """Should support --skip-execution flag."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
<!-- runnable -->
```python
import time
time.sleep(100)  # Would timeout if executed
```
""")

        result = subprocess.run(
            ["python", "scripts/validate_docs_examples.py", "--skip-execution", str(markdown)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0  # Should pass syntax check

    def test_cli_docker_mode_flag(self, tmp_path):
        """Should support --use-docker flag."""
        markdown = tmp_path / "test.md"
        markdown.write_text("""
<!-- runnable -->
```python
print("Test")
```
""")

        result = subprocess.run(
            ["python", "scripts/validate_docs_examples.py", "--use-docker", str(markdown)],
            capture_output=True,
            text=True,
        )

        # Should work (or gracefully fallback if Docker unavailable)
        assert "docker" in result.stdout.lower() or "restrictedpython" in result.stdout.lower()

    def test_cli_verbose_output(self, tmp_path):
        """Should support --verbose flag for detailed output."""
        markdown = tmp_path / "test.md"
        markdown.write_text("```python\nprint('test')\n```")

        result = subprocess.run(
            ["python", "scripts/validate_docs_examples.py", "--verbose", str(markdown)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        # Verbose mode should show more details
        assert len(result.stdout) > 50


class TestValidationResult:
    """Test ValidationResult data structure."""

    def test_result_contains_summary(self):
        """Should provide summary of validation results."""
        result = ValidationResult(success=True, errors=[], warnings=[], info=[])

        assert result.success is True
        assert len(result.errors) == 0

    def test_result_contains_errors(self):
        """Should include detailed error information."""
        error = "Line 10: SyntaxError: invalid syntax"

        result = ValidationResult(success=False, errors=[error])

        assert result.success is False
        assert len(result.errors) == 1
        assert "SyntaxError" in result.errors[0]

    def test_result_json_serializable(self):
        """Should be JSON serializable for CI/CD integration."""
        import json

        result = ValidationResult(success=True, errors=[])

        # Should be able to serialize to JSON
        json_str = json.dumps(result.to_dict())
        assert isinstance(json_str, str)

        # Should be able to deserialize
        data = json.loads(json_str)
        assert data["success"] is True
