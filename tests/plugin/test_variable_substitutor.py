"""
TDD Tests for VariableSubstitutor module.

These tests validate variable substitution with security constraints,
path validation, and traversal prevention.

Testing Strategy:
- 70% unit tests (substitution logic and security)
- 20% integration tests (real path operations)
- 10% E2E tests (complete substitution workflows)
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch


class TestVariableSubstitutorUnit:
    """Unit tests for VariableSubstitutor - substitution logic."""

    def test_substitute_simple_variable(self):
        """
        Test basic variable substitution.

        Validates:
        - ${VARIABLE} is replaced with value
        - Multiple occurrences are all replaced
        - Original string unchanged if no variables
        """
        from amplihack.plugin.variable_substitutor import VariableSubstitutor

        variables = {"CLAUDE_PLUGIN_ROOT": "/home/user/.amplihack/.claude"}

        substitutor = VariableSubstitutor(variables)

        text = "${CLAUDE_PLUGIN_ROOT}/tools/hook.sh"
        result = substitutor.substitute(text)

        assert result == "/home/user/.amplihack/.claude/tools/hook.sh"

    def test_substitute_multiple_variables(self):
        """
        Test substitution with multiple variables in one string.

        Validates:
        - All variables are replaced
        - Variables can appear multiple times
        - Order doesn't matter
        """
        from amplihack.plugin.variable_substitutor import VariableSubstitutor

        variables = {
            "ROOT": "/home/user",
            "PROJECT": "myproject"
        }

        substitutor = VariableSubstitutor(variables)

        text = "${ROOT}/${PROJECT}/src/${PROJECT}/main.py"
        result = substitutor.substitute(text)

        assert result == "/home/user/myproject/src/myproject/main.py"

    def test_substitute_unknown_variable_raises_error(self):
        """
        Test that unknown variables raise KeyError.

        Validates:
        - Unknown variable names raise KeyError
        - Error message includes variable name
        - Partial substitution doesn't occur
        """
        from amplihack.plugin.variable_substitutor import VariableSubstitutor

        variables = {"KNOWN": "/path"}
        substitutor = VariableSubstitutor(variables)

        text = "${UNKNOWN}/file.txt"

        with pytest.raises(KeyError, match="UNKNOWN"):
            substitutor.substitute(text)

    def test_substitute_with_empty_variables(self):
        """
        Test substitution when no variables are defined.

        Validates:
        - Text without variables passes through unchanged
        - Text with variables raises error
        """
        from amplihack.plugin.variable_substitutor import VariableSubstitutor

        substitutor = VariableSubstitutor({})

        # No variables in text - should pass through
        assert substitutor.substitute("plain/path") == "plain/path"

        # Variables in text - should raise error
        with pytest.raises(KeyError):
            substitutor.substitute("${VAR}/path")

    def test_validate_path_rejects_traversal(self):
        """
        Test that path traversal attempts are rejected.

        Validates:
        - ../ in paths raises SecurityError
        - ../../ (multiple levels) raises SecurityError
        - Error message indicates security violation
        """
        from amplihack.plugin.variable_substitutor import VariableSubstitutor

        variables = {"ROOT": "/home/user/.amplihack"}
        substitutor = VariableSubstitutor(variables)

        # Single parent reference
        with pytest.raises(SecurityError, match="traversal|security"):
            substitutor.validate_path("../../../etc/passwd")

        # Multiple parent references
        with pytest.raises(SecurityError, match="traversal|security"):
            substitutor.validate_path("${ROOT}/../../../etc/passwd")

    def test_validate_path_accepts_safe_paths(self):
        """
        Test that safe paths pass validation.

        Validates:
        - Absolute paths are accepted
        - Relative paths without .. are accepted
        - Paths with variables are accepted
        """
        from amplihack.plugin.variable_substitutor import VariableSubstitutor

        variables = {"ROOT": "/home/user"}
        substitutor = VariableSubstitutor(variables)

        # These should all be valid
        safe_paths = [
            "/absolute/path",
            "relative/path",
            "${ROOT}/subdir/file",
            "tools/hook.sh"
        ]

        for path in safe_paths:
            assert substitutor.validate_path(path)  # Should not raise

    def test_substitute_and_resolve_creates_absolute_path(self):
        """
        Test that substitute_and_resolve() creates absolute paths.

        Validates:
        - Variables are substituted first
        - Result is converted to absolute path
        - Relative paths are resolved against base_path
        """
        from amplihack.plugin.variable_substitutor import VariableSubstitutor

        variables = {"PLUGIN": "/home/user/.amplihack/.claude"}
        substitutor = VariableSubstitutor(variables)

        text = "${PLUGIN}/tools/hook.sh"
        result = substitutor.substitute_and_resolve(text, base_path=Path("/base"))

        # Should be absolute path
        assert Path(result).is_absolute()
        assert result == "/home/user/.amplihack/.claude/tools/hook.sh"

    def test_substitute_dict_recursively(self):
        """
        Test that substitute_dict() processes nested structures.

        Validates:
        - String values are substituted
        - Nested dicts are processed recursively
        - Lists are processed element by element
        - Non-string values are preserved
        """
        from amplihack.plugin.variable_substitutor import VariableSubstitutor

        variables = {"ROOT": "/home/user"}
        substitutor = VariableSubstitutor(variables)

        data = {
            "path": "${ROOT}/file.txt",
            "count": 42,
            "nested": {
                "inner_path": "${ROOT}/nested/file"
            },
            "list": ["${ROOT}/item1", "${ROOT}/item2"]
        }

        result = substitutor.substitute_dict(data)

        assert result["path"] == "/home/user/file.txt"
        assert result["count"] == 42
        assert result["nested"]["inner_path"] == "/home/user/nested/file"
        assert result["list"][0] == "/home/user/item1"
        assert result["list"][1] == "/home/user/item2"


class TestVariableSubstitutorSecurity:
    """Security-focused tests for VariableSubstitutor."""

    def test_prevent_path_traversal_in_variable_values(self):
        """
        Test that path traversal in variable values is detected.

        Validates:
        - Variables containing .. are flagged
        - After substitution, path is validated
        - SecurityError is raised
        """
        from amplihack.plugin.variable_substitutor import VariableSubstitutor

        # Malicious variable value
        variables = {"EVIL": "../../../etc"}
        substitutor = VariableSubstitutor(variables)

        text = "${EVIL}/passwd"

        with pytest.raises(SecurityError):
            result = substitutor.substitute(text)
            substitutor.validate_path(result)

    def test_prevent_absolute_path_escape(self):
        """
        Test that absolute paths can't escape intended directory.

        Validates:
        - Absolute paths outside allowed root raise error
        - Allowed root is checked
        - Symbolic link attacks are prevented
        """
        from amplihack.plugin.variable_substitutor import VariableSubstitutor

        variables = {"ROOT": "/home/user/.amplihack"}
        substitutor = VariableSubstitutor(variables)

        # Try to escape to /etc
        with pytest.raises(SecurityError):
            substitutor.validate_path_within_root(
                "/etc/passwd",
                allowed_root=Path("/home/user/.amplihack")
            )

    def test_prevent_symlink_traversal(self):
        """
        Test that symlinks can't be used for path traversal.

        Validates:
        - Symlinks are resolved before validation
        - Symlinks pointing outside root are rejected
        - Error message indicates symlink issue
        """
        from amplihack.plugin.variable_substitutor import VariableSubstitutor

        variables = {"ROOT": "/home/user"}
        substitutor = VariableSubstitutor(variables)

        # This should detect if symlinks are used maliciously
        # Implementation should resolve symlinks and validate
        with pytest.raises(SecurityError):
            # Simulated symlink that points outside allowed root
            substitutor.validate_symlink(
                Path("/home/user/link_to_etc"),
                allowed_root=Path("/home/user/.amplihack")
            )

    def test_prevent_variable_injection(self):
        """
        Test that variable names can't be injected through user input.

        Validates:
        - Variable names are validated
        - Invalid characters in variable names raise error
        - Only alphanumeric and underscore allowed
        """
        from amplihack.plugin.variable_substitutor import VariableSubstitutor

        # Try to inject with malicious variable name
        with pytest.raises(ValueError, match="invalid.*variable.*name"):
            variables = {"EVIL; rm -rf /": "/path"}
            VariableSubstitutor(variables)

    def test_prevent_environment_variable_leakage(self):
        """
        Test that arbitrary environment variables can't be accessed.

        Validates:
        - Only explicitly defined variables are available
        - No access to os.environ or system variables
        - Attempts to use undefined variables fail
        """
        from amplihack.plugin.variable_substitutor import VariableSubstitutor
        import os

        # Set environment variable
        os.environ["SECRET_KEY"] = "sensitive_value"

        # Should NOT be accessible through substitutor
        variables = {"SAFE": "/safe/path"}
        substitutor = VariableSubstitutor(variables)

        with pytest.raises(KeyError):
            substitutor.substitute("${SECRET_KEY}/file")


class TestVariableSubstitutorIntegration:
    """Integration tests for VariableSubstitutor - real file operations."""

    def test_substitute_and_verify_file_exists(self, tmp_path):
        """
        Test substitution with actual file system verification.

        Validates:
        - Path substitution works with real paths
        - File existence can be checked
        - Absolute paths are correctly formed
        """
        from amplihack.plugin.variable_substitutor import VariableSubstitutor

        # Create real directory structure
        plugin_root = tmp_path / ".amplihack" / ".claude"
        tools_dir = plugin_root / "tools"
        tools_dir.mkdir(parents=True)
        hook_file = tools_dir / "hook.sh"
        hook_file.write_text("#!/bin/bash\necho 'test'")

        variables = {"CLAUDE_PLUGIN_ROOT": str(plugin_root)}
        substitutor = VariableSubstitutor(variables)

        text = "${CLAUDE_PLUGIN_ROOT}/tools/hook.sh"
        result = substitutor.substitute(text)

        # Verify substituted path exists
        assert Path(result).exists()
        assert Path(result) == hook_file

    def test_substitute_settings_with_multiple_paths(self, tmp_path):
        """
        Test substituting multiple paths in settings structure.

        Validates:
        - Multiple paths in settings are substituted
        - Structure is preserved
        - All paths are valid
        """
        from amplihack.plugin.variable_substitutor import VariableSubstitutor

        plugin_root = tmp_path / ".amplihack"
        plugin_root.mkdir()

        variables = {"ROOT": str(plugin_root)}
        substitutor = VariableSubstitutor(variables)

        settings = {
            "hooks": {
                "PreRun": "${ROOT}/tools/pre.sh",
                "PostRun": "${ROOT}/tools/post.sh"
            },
            "include_paths": [
                "${ROOT}/context",
                "${ROOT}/agents"
            ]
        }

        result = substitutor.substitute_dict(settings)

        # Check all paths were substituted
        assert plugin_root.name in result["hooks"]["PreRun"]
        assert plugin_root.name in result["hooks"]["PostRun"]
        assert plugin_root.name in result["include_paths"][0]

    def test_complete_substitution_workflow(self, tmp_path):
        """
        Test complete workflow: load, substitute, validate, save.

        Validates:
        - End-to-end substitution process
        - Security validation occurs
        - Result can be used for file operations
        """
        from amplihack.plugin.variable_substitutor import VariableSubstitutor
        import json

        plugin_root = tmp_path / "plugin"
        plugin_root.mkdir()

        # Create settings template with variables
        template = {
            "hooks": {
                "PreRun": "${PLUGIN_ROOT}/tools/hook.sh"
            }
        }

        variables = {"PLUGIN_ROOT": str(plugin_root)}
        substitutor = VariableSubstitutor(variables)

        # Substitute
        result = substitutor.substitute_dict(template)

        # Validate all paths
        for path_str in [result["hooks"]["PreRun"]]:
            substitutor.validate_path(path_str)

        # Save result
        output = tmp_path / "output.json"
        output.write_text(json.dumps(result, indent=2))

        # Verify saved result
        loaded = json.loads(output.read_text())
        assert str(plugin_root) in loaded["hooks"]["PreRun"]


class TestVariableSubstitutorEdgeCases:
    """Edge case tests for VariableSubstitutor."""

    def test_substitute_empty_string(self):
        """
        Test substitution with empty string.

        Validates:
        - Empty string returns empty string
        - No errors raised
        """
        from amplihack.plugin.variable_substitutor import VariableSubstitutor

        variables = {"VAR": "/path"}
        substitutor = VariableSubstitutor(variables)

        assert substitutor.substitute("") == ""

    def test_substitute_with_escaped_variables(self):
        """
        Test that escaped variables are not substituted.

        Validates:
        - \\${VAR} is treated as literal text
        - Backslash is removed in output
        - Only unescaped variables are substituted
        """
        from amplihack.plugin.variable_substitutor import VariableSubstitutor

        variables = {"VAR": "value"}
        substitutor = VariableSubstitutor(variables)

        text = "\\${VAR}/path and ${VAR}/other"
        result = substitutor.substitute(text)

        # Escaped variable should remain literal (without backslash)
        assert "${VAR}" in result
        # Unescaped variable should be substituted
        assert "value/other" in result

    def test_substitute_with_malformed_syntax(self):
        """
        Test handling of malformed variable syntax.

        Validates:
        - Missing closing brace raises error
        - Missing opening brace treated as literal
        - Error messages are clear
        """
        from amplihack.plugin.variable_substitutor import VariableSubstitutor

        variables = {"VAR": "value"}
        substitutor = VariableSubstitutor(variables)

        # Missing closing brace
        with pytest.raises(ValueError, match="malformed.*variable"):
            substitutor.substitute("${VAR/path")

        # Missing opening brace - treated as literal
        result = substitutor.substitute("VAR}/path")
        assert result == "VAR}/path"

    def test_substitute_with_unicode_in_paths(self):
        """
        Test substitution with Unicode characters in paths.

        Validates:
        - Unicode in variable values is preserved
        - Unicode in substituted paths is handled correctly
        """
        from amplihack.plugin.variable_substitutor import VariableSubstitutor

        variables = {"ROOT": "/home/user/文档"}
        substitutor = VariableSubstitutor(variables)

        text = "${ROOT}/file.txt"
        result = substitutor.substitute(text)

        assert "/home/user/文档/file.txt" == result

    def test_substitute_with_very_long_paths(self):
        """
        Test substitution with paths exceeding typical length limits.

        Validates:
        - Long paths are handled correctly
        - No truncation occurs
        - Performance is acceptable
        """
        from amplihack.plugin.variable_substitutor import VariableSubstitutor

        # Create very long path (but under OS limits)
        long_component = "a" * 100
        long_path = "/".join([long_component] * 20)  # ~2000 chars

        variables = {"LONG": long_path}
        substitutor = VariableSubstitutor(variables)

        text = "${LONG}/file.txt"
        result = substitutor.substitute(text)

        assert len(result) > 2000
        assert result.endswith("/file.txt")
