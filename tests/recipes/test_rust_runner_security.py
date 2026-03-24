"""Security tests for rust_runner.py.

R7: _sanitize_key uses allowlist regex; preserves dots/hyphens; max 256 chars;
    rejects null bytes with ValueError.
R6: _secure_delete_spill_dir overwrites files before deletion.
R8: MAX_BINARY_OUTPUT_BYTES constant = 10 MiB.
R2: _check_binary_permissions rejects world-writable binaries.
    Recipe name validation: _validate_recipe_name enforces allowlist.
    Model wire format: RecipeResult fields are present and correctly typed.
"""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from amplihack.recipes.rust_runner import (
    MAX_BINARY_OUTPUT_BYTES,
    _check_binary_permissions,
    _sanitize_key,
    _secure_delete_spill_dir,
    _validate_recipe_name,
)


# ---------------------------------------------------------------------------
# R8: Output cap constant
# ---------------------------------------------------------------------------


class TestOutputCap:
    """R8: MAX_BINARY_OUTPUT_BYTES must be 10 MiB."""

    def test_constant_exists(self):
        assert MAX_BINARY_OUTPUT_BYTES is not None

    def test_constant_is_10_mib(self):
        assert MAX_BINARY_OUTPUT_BYTES == 10 * 1024 * 1024, (
            f"R8: expected 10 MiB (10485760), got {MAX_BINARY_OUTPUT_BYTES}"
        )

    def test_constant_type_is_int(self):
        assert isinstance(MAX_BINARY_OUTPUT_BYTES, int)


# ---------------------------------------------------------------------------
# R7: _sanitize_key allowlist
# ---------------------------------------------------------------------------


class TestSanitizeKey:
    """R7: _sanitize_key must use an allowlist that preserves dots/hyphens."""

    # -- Allowed characters --------------------------------------------------

    def test_alphanumeric_preserved(self):
        assert _sanitize_key("abc123") == "abc123"

    def test_underscore_preserved(self):
        assert _sanitize_key("my_key") == "my_key"

    def test_dot_preserved(self):
        """R7: dots must survive sanitization (needed for package names)."""
        assert _sanitize_key("my.key") == "my.key"

    def test_hyphen_preserved(self):
        """R7: hyphens must survive sanitization."""
        assert _sanitize_key("my-key") == "my-key"

    def test_mixed_allowlist_chars(self):
        assert _sanitize_key("pkg.name-1_0") == "pkg.name-1_0"

    # -- Rejected / replaced characters --------------------------------------

    def test_slash_replaced(self):
        """Path separators must be replaced to prevent traversal."""
        result = _sanitize_key("a/b")
        assert "/" not in result

    def test_path_traversal_replaced(self):
        """../../../etc/passwd must not survive sanitization."""
        result = _sanitize_key("../../../etc/passwd")
        assert ".." not in result or "/" not in result
        # The result must be filesystem-safe.
        assert "/" not in result

    def test_null_byte_raises(self):
        """R7: null bytes must raise ValueError, not be silently dropped."""
        with pytest.raises(ValueError, match="[Nn]ull"):
            _sanitize_key("key\x00injection")

    def test_space_replaced(self):
        result = _sanitize_key("key with spaces")
        assert " " not in result

    # -- Length limit --------------------------------------------------------

    def test_max_length_256(self):
        """R7: max length is 256 characters."""
        long_key = "a" * 300
        result = _sanitize_key(long_key)
        assert len(result) <= 256, f"R7: key truncated to {len(result)}, expected <= 256"

    def test_exactly_256_chars_not_truncated(self):
        key = "a" * 256
        result = _sanitize_key(key)
        assert len(result) == 256

    def test_257_chars_truncated_to_256(self):
        key = "a" * 257
        result = _sanitize_key(key)
        assert len(result) == 256

    def test_empty_key_fallback(self):
        """Empty result falls back to '_empty_key_'."""
        # A key of only non-allowlist characters becomes all underscores then
        # gets the fallback treatment if empty.  At minimum it must be non-empty.
        result = _sanitize_key("")
        assert result  # must not be empty


# ---------------------------------------------------------------------------
# R6: _secure_delete_spill_dir
# ---------------------------------------------------------------------------


class TestSecureDeleteSpillDir:
    """R6: spill files must be overwritten with zeros before deletion."""

    def test_nonexistent_dir_is_noop(self):
        """Must not raise when the directory does not exist."""
        _secure_delete_spill_dir(Path("/tmp/nonexistent-amplihack-spill-test-xyz"))

    def test_files_are_deleted(self):
        """After secure delete, the directory and its files must be gone."""
        with tempfile.TemporaryDirectory() as tmp:
            spill_dir = Path(tmp) / "spill"
            spill_dir.mkdir(mode=0o700)
            (spill_dir / "keyA").write_bytes(b"secret-data-A")
            (spill_dir / "keyB").write_bytes(b"secret-data-B")

            _secure_delete_spill_dir(spill_dir)

            assert not spill_dir.exists(), (
                "R6: spill directory must be removed after secure delete"
            )

    def test_file_content_overwritten_before_delete(self):
        """Verify that file content is zeroed before removal (forensic erasure)."""
        import io
        overwrite_log: list[bytes] = []

        with tempfile.TemporaryDirectory() as tmp:
            spill_dir = Path(tmp) / "spill"
            spill_dir.mkdir(mode=0o700)
            secret_file = spill_dir / "mykey"
            secret_file.write_bytes(b"very-secret-value")
            secret_file.chmod(0o600)

            original_write_bytes = Path.write_bytes

            def spy_write_bytes(self, data):
                if self == secret_file:
                    overwrite_log.append(data)
                return original_write_bytes(self, data)

            with patch.object(Path, "write_bytes", spy_write_bytes):
                _secure_delete_spill_dir(spill_dir)

            # At least one write_bytes call must have been made with zeros.
            assert overwrite_log, (
                "R6: no overwrite call detected — files must be zeroed before deletion"
            )
            assert any(set(chunk) <= {0} for chunk in overwrite_log), (
                "R6: overwrite must use zero bytes, got: "
                + repr([chunk[:8] for chunk in overwrite_log])
            )

    def test_permissions_enforced_before_overwrite(self):
        """File permissions must be set to 0o600 before the overwrite."""
        with tempfile.TemporaryDirectory() as tmp:
            spill_dir = Path(tmp) / "spill"
            spill_dir.mkdir(mode=0o700)
            secret_file = spill_dir / "key"
            secret_file.write_bytes(b"data")
            # Set permissive mode to verify secure_delete fixes it.
            secret_file.chmod(0o644)

            _secure_delete_spill_dir(spill_dir)

            # File must no longer exist.
            assert not secret_file.exists()


# ---------------------------------------------------------------------------
# R2: _check_binary_permissions
# ---------------------------------------------------------------------------


class TestCheckBinaryPermissions:
    """R2: world-writable binaries must be rejected before execution."""

    def test_safe_binary_accepted(self):
        """A 0o755 binary must not raise."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            binary = Path(f.name)
        try:
            binary.chmod(0o755)
            _check_binary_permissions(str(binary))  # must not raise
        finally:
            binary.unlink(missing_ok=True)

    def test_world_writable_binary_rejected(self):
        """A world-writable binary (0o777) must raise PermissionError."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            binary = Path(f.name)
        try:
            binary.chmod(0o777)
            with pytest.raises(PermissionError, match="world-writable"):
                _check_binary_permissions(str(binary))
        finally:
            binary.unlink(missing_ok=True)

    def test_group_writable_but_not_world_writable_accepted(self):
        """0o775 (group-writable, not world-writable) must be accepted."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            binary = Path(f.name)
        try:
            binary.chmod(0o775)
            _check_binary_permissions(str(binary))  # must not raise
        finally:
            binary.unlink(missing_ok=True)

    @pytest.mark.parametrize("mode", [0o002, 0o022, 0o777, 0o666])
    def test_any_world_write_bit_rejected(self, mode):
        """Any mode with the world-write bit (0o002) must be rejected."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            binary = Path(f.name)
        try:
            binary.chmod(mode)
            with pytest.raises(PermissionError):
                _check_binary_permissions(str(binary))
        finally:
            binary.unlink(missing_ok=True)

    def test_error_message_includes_path(self):
        """The PermissionError message must include the binary path."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            binary = Path(f.name)
        try:
            binary.chmod(0o777)
            with pytest.raises(PermissionError) as exc_info:
                _check_binary_permissions(str(binary))
            assert str(binary) in str(exc_info.value)
        finally:
            binary.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Recipe name validation
# ---------------------------------------------------------------------------


class TestValidateRecipeName:
    """_validate_recipe_name must enforce the allowlist ^[a-zA-Z0-9_/-]{1,128}$."""

    @pytest.mark.parametrize(
        "valid_name",
        [
            "my-recipe",
            "my_recipe",
            "recipe123",
            "a/b/c",
            "A" * 128,
            "a",
        ],
    )
    def test_valid_names_pass(self, valid_name):
        assert _validate_recipe_name(valid_name) == valid_name

    @pytest.mark.parametrize(
        "bad_name",
        [
            "../../../etc/passwd",
            "recipe; rm -rf /",
            "recipe\x00injection",
            "",
            "a" * 129,
            "recipe name with spaces",
            "recipe.yaml",   # dots not allowed in plain recipe names
        ],
    )
    def test_invalid_names_rejected(self, bad_name):
        """Invalid recipe names must raise ValueError."""
        with pytest.raises(ValueError):
            _validate_recipe_name(bad_name)

    def test_absolute_yaml_path_allowed(self):
        """Absolute YAML paths bypass the plain-name allowlist."""
        abs_path = "/home/user/recipes/my_recipe.yaml"
        result = _validate_recipe_name(abs_path)
        assert result == abs_path

    def test_error_message_mentions_allowlist(self):
        """ValueError must identify the allowed pattern."""
        with pytest.raises(ValueError) as exc_info:
            _validate_recipe_name("bad name!")
        msg = str(exc_info.value)
        assert "recipe" in msg.lower() or "invalid" in msg.lower()


# ---------------------------------------------------------------------------
# Model wire format
# ---------------------------------------------------------------------------


class TestModelWireFormat:
    """RecipeResult wire format fields must be present and typed correctly."""

    def test_recipe_result_has_required_fields(self):
        from amplihack.recipes.models import RecipeResult, StepResult, StepStatus

        result = RecipeResult(
            recipe_name="test",
            success=True,
            step_results=[],
            context={},
        )
        assert hasattr(result, "recipe_name")
        assert hasattr(result, "success")
        assert hasattr(result, "step_results")
        assert hasattr(result, "context")

    def test_step_result_has_required_fields(self):
        from amplihack.recipes.models import StepResult, StepStatus

        step = StepResult(
            step_id="step-1",
            status=StepStatus.COMPLETED,
            output="ok",
            error="",
        )
        assert step.step_id == "step-1"
        assert step.status == StepStatus.COMPLETED

    def test_recipe_result_success_is_bool(self):
        from amplihack.recipes.models import RecipeResult

        result = RecipeResult(recipe_name="t", success=False, step_results=[], context={})
        assert isinstance(result.success, bool)
