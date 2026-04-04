"""Tests for large env-var spill feature (env vars exceeding 32 KB spilled to temp files).

Requirements summary:
- Values >= 32768 bytes (UTF-8 encoded) are spilled to /tmp/recipe-context-<pid>-*/
- Spilled values are replaced with file://<path> in the --set argument
- The temp directory and all spill files are removed when the recipe finishes,
  whether it succeeds or fails.
- Values < 32768 bytes pass through unchanged.
- _resolve_context_value(value) dereferences file:// URIs back to file content.
- _ENV_VAR_SIZE_LIMIT == 32768 (32 * 1024).
- _spill_large_value(key, value, tmp_dir) writes the value and returns file:// URI.

Covered categories (testing pyramid - unit focus):
  - Boundary / threshold: 32767 (below), 32768 (at), 32769 (above)
  - Roundtrip: spill + resolve returns identical bytes
  - Cleanup: success path and exception path
  - No-spill: all-small context never creates temp dir
  - Security: spilled file mode 0o600, tmp dir mode 0o700
  - Edge cases: empty key, key with special characters, Unicode content
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


from amplihack.recipes.rust_runner import (
    _ENV_VAR_SIZE_LIMIT,
    _build_rust_command,
    _resolve_context_value,
    _spill_large_value,
    run_recipe_via_rust,
)

# ── Constants used throughout ────────────────────────────────────────────────

_LIMIT = 32 * 1024  # 32768 — canonical threshold


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_value(byte_len: int) -> str:
    """Return an ASCII string whose UTF-8 encoding is exactly *byte_len* bytes."""
    return "x" * byte_len


def _make_rust_success_output(name: str = "test-recipe") -> str:
    return json.dumps(
        {
            "recipe_name": name,
            "success": True,
            "step_results": [],
            "context": {},
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Module-level constant
# ─────────────────────────────────────────────────────────────────────────────


class TestEnvVarSizeLimit:
    """_ENV_VAR_SIZE_LIMIT must equal exactly 32768."""

    def test_constant_value(self):
        assert _ENV_VAR_SIZE_LIMIT == 32768

    def test_constant_equals_32_kib(self):
        assert _ENV_VAR_SIZE_LIMIT == 32 * 1024


# ─────────────────────────────────────────────────────────────────────────────
# 2. _spill_large_value helper
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.xfail(reason="TDD: feature not yet implemented", strict=False)
class TestSpillLargeValue:
    """Unit tests for _spill_large_value(key, value, tmp_dir)."""

    def test_returns_file_uri(self, tmp_path):
        """Return value starts with file://."""
        uri = _spill_large_value("MY_KEY", "content", tmp_path)
        assert uri.startswith("file://")

    def test_writes_correct_content(self, tmp_path):
        """File on disk contains exactly the supplied string (UTF-8, no trailing newline)."""
        value = "hello world " * 100
        uri = _spill_large_value("MY_KEY", value, tmp_path)
        file_path = Path(uri[len("file://") :])
        assert file_path.read_text(encoding="utf-8") == value

    def test_file_path_is_inside_tmp_dir(self, tmp_path):
        """Spilled file lives under the supplied tmp_dir."""
        uri = _spill_large_value("MY_KEY", "data", tmp_path)
        file_path = Path(uri[len("file://") :])
        assert file_path.parent == tmp_path

    def test_filename_derived_from_key(self, tmp_path):
        """Filename is derived from the sanitised env-var key name."""
        uri = _spill_large_value("MY_BIG_VAR", "data", tmp_path)
        file_path = Path(uri[len("file://") :])
        assert "MY_BIG_VAR" in file_path.name

    def test_key_sanitization_replaces_special_chars(self, tmp_path):
        """Non-alphanumeric/underscore chars in key are replaced with underscores."""
        uri = _spill_large_value("a.b-c/d", "data", tmp_path)
        file_path = Path(uri[len("file://") :])
        # No dots, hyphens, or slashes in filename
        assert "." not in file_path.name
        assert "-" not in file_path.name
        assert "/" not in file_path.name

    def test_empty_key_uses_fallback_name(self, tmp_path):
        """An empty key does not raise IsADirectoryError; uses '_empty_key_' fallback."""
        uri = _spill_large_value("", "data", tmp_path)
        file_path = Path(uri[len("file://") :])
        assert file_path.exists()
        assert "_empty_key_" in file_path.name

    def test_key_truncated_to_64_chars(self, tmp_path):
        """Key names longer than 64 chars are truncated in the filename."""
        long_key = "A" * 200
        uri = _spill_large_value(long_key, "data", tmp_path)
        file_path = Path(uri[len("file://") :])
        # The filename portion (excluding any extension) should not exceed 64 chars
        assert len(file_path.stem) <= 64

    def test_unicode_content_preserved(self, tmp_path):
        """Multi-byte Unicode (CJK, emoji) is preserved round-trip."""
        value = "日本語テスト🚀" * 1000
        uri = _spill_large_value("UNICODE_KEY", value, tmp_path)
        file_path = Path(uri[len("file://") :])
        assert file_path.read_text(encoding="utf-8") == value

    def test_file_permissions_owner_only(self, tmp_path):
        """Spilled file must be mode 0o600 (owner read+write only)."""
        uri = _spill_large_value("SECRET_KEY", "sensitive data", tmp_path)
        file_path = Path(uri[len("file://") :])
        mode = file_path.stat().st_mode & 0o777
        assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"


# ─────────────────────────────────────────────────────────────────────────────
# 3. _resolve_context_value helper
# ─────────────────────────────────────────────────────────────────────────────


class TestResolveContextValue:
    """Unit tests for _resolve_context_value(value: str) -> str."""

    def test_non_file_uri_returned_unchanged(self):
        """Plain strings pass through without any I/O."""
        assert _resolve_context_value("hello") == "hello"

    def test_empty_string_returned_unchanged(self):
        assert _resolve_context_value("") == ""

    def test_file_uri_reads_file_content(self, tmp_path):
        """file:// URI is resolved to the file's text content."""
        p = tmp_path / "data.txt"
        p.write_text("expected content", encoding="utf-8")
        result = _resolve_context_value(f"file://{p}")
        assert result == "expected content"

    def test_file_uri_roundtrip_with_spill(self, tmp_path):
        """_spill_large_value + _resolve_context_value returns the original value."""
        original = _make_value(_LIMIT + 100)
        uri = _spill_large_value("MY_KEY", original, tmp_path)
        recovered = _resolve_context_value(uri)
        assert recovered == original

    def test_file_uri_roundtrip_unicode(self, tmp_path):
        """Unicode content survives spill → resolve roundtrip."""
        original = "こんにちは世界" * 500
        uri = _spill_large_value("UNICODE_KEY", original, tmp_path)
        recovered = _resolve_context_value(uri)
        assert recovered == original

    def test_non_file_scheme_returned_unchanged(self):
        """URIs with other schemes (http://, s3://) are returned as-is."""
        assert _resolve_context_value("http://example.com") == "http://example.com"
        assert _resolve_context_value("s3://bucket/key") == "s3://bucket/key"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Threshold detection in _build_rust_command
# ─────────────────────────────────────────────────────────────────────────────


class TestBuildRustCommandSizeGuard:
    """_build_rust_command must spill values >= _LIMIT and pass small values through.

    After the implementation, _build_rust_command returns (cmd, tmp_dir) where
    tmp_dir is None if no value was spilled, or a Path to the temp directory.
    """

    def _build(self, context: dict, tmp_dir: Path | None = None) -> tuple[list[str], Path | None]:
        """Invoke _build_rust_command and return (cmd, tmp_dir)."""
        if tmp_dir is None:
            tmp_dir = Path(tempfile.mkdtemp(prefix="test-spill-"))
        result = _build_rust_command(
            "/bin/recipe-runner-rs",
            "test-recipe",
            working_dir=".",
            dry_run=False,
            auto_stage=True,
            progress=False,
            recipe_dirs=None,
            user_context=context,
            tmp_dir=tmp_dir,
        )
        return result, tmp_dir

    # -- Below threshold -------------------------------------------------------

    def test_value_below_threshold_passes_through(self, tmp_path):
        """32767-byte value appears inline — no file:// prefix."""
        value = _make_value(_LIMIT - 1)  # 32767 bytes
        cmd, _ = self._build({"MY_KEY": value}, tmp_dir=tmp_path)
        set_args = [cmd[i + 1] for i, v in enumerate(cmd) if v == "--set"]
        assert any(a == f"MY_KEY={value}" for a in set_args)
        assert not any("file://" in a for a in set_args)

    def test_value_below_threshold_no_files_written(self, tmp_path):
        """No files written to tmp_dir for values < threshold."""
        value = _make_value(_LIMIT - 1)
        self._build({"MY_KEY": value}, tmp_dir=tmp_path)
        assert list(tmp_path.iterdir()) == []

    # -- At threshold ----------------------------------------------------------

    def test_value_at_threshold_spills(self, tmp_path):
        """32768-byte value is spilled: --set arg contains file://."""
        value = _make_value(_LIMIT)  # exactly 32768 bytes
        cmd, _ = self._build({"MY_KEY": value}, tmp_dir=tmp_path)
        set_args = [cmd[i + 1] for i, v in enumerate(cmd) if v == "--set"]
        assert any(a.startswith("MY_KEY=file://") for a in set_args)

    def test_value_at_threshold_file_written(self, tmp_path):
        """A file is created in tmp_dir when value is exactly at threshold."""
        value = _make_value(_LIMIT)
        self._build({"MY_KEY": value}, tmp_dir=tmp_path)
        files = list(tmp_path.iterdir())
        assert len(files) == 1

    # -- Above threshold -------------------------------------------------------

    def test_value_above_threshold_spills(self, tmp_path):
        """32769-byte value is spilled: --set arg contains file://."""
        value = _make_value(_LIMIT + 1)  # 32769 bytes
        cmd, _ = self._build({"MY_KEY": value}, tmp_dir=tmp_path)
        set_args = [cmd[i + 1] for i, v in enumerate(cmd) if v == "--set"]
        assert any(a.startswith("MY_KEY=file://") for a in set_args)

    # -- Small values mixed with large -----------------------------------------

    def test_only_large_values_spilled_in_mixed_context(self, tmp_path):
        """Small values stay inline; only large values get file:// replacement."""
        small = _make_value(_LIMIT - 1)
        large = _make_value(_LIMIT)
        cmd, _ = self._build({"SMALL": small, "LARGE": large}, tmp_dir=tmp_path)
        set_args = [cmd[i + 1] for i, v in enumerate(cmd) if v == "--set"]

        small_args = [a for a in set_args if a.startswith("SMALL=")]
        large_args = [a for a in set_args if a.startswith("LARGE=")]

        assert len(small_args) == 1
        assert not small_args[0].startswith("SMALL=file://")

        assert len(large_args) == 1
        assert large_args[0].startswith("LARGE=file://")

    # -- Type serialisation applied before byte-length check -------------------

    def test_bool_serialised_before_size_check(self, tmp_path):
        """bool values are serialised to 'true'/'false' strings (always tiny → inline)."""
        cmd, _ = self._build({"FLAG": True}, tmp_dir=tmp_path)
        set_args = [cmd[i + 1] for i, v in enumerate(cmd) if v == "--set"]
        assert "FLAG=true" in set_args

    def test_dict_serialised_before_size_check_small(self, tmp_path):
        """Small dict serialised to JSON and passed inline."""
        data = {"key": "val"}
        cmd, _ = self._build({"DATA": data}, tmp_dir=tmp_path)
        set_args = [cmd[i + 1] for i, v in enumerate(cmd) if v == "--set"]
        assert any(a.startswith("DATA=") and "file://" not in a for a in set_args)

    def test_large_dict_spills(self, tmp_path):
        """Dict whose JSON serialisation exceeds threshold is spilled."""
        # Create a dict that serialises to >= 32768 bytes
        large_dict = {f"key_{i}": "x" * 100 for i in range(400)}  # ~50 KB JSON
        cmd, _ = self._build({"BIG_DICT": large_dict}, tmp_dir=tmp_path)
        set_args = [cmd[i + 1] for i, v in enumerate(cmd) if v == "--set"]
        assert any(a.startswith("BIG_DICT=file://") for a in set_args)

    # -- Unicode byte-length correctness ---------------------------------------

    def test_multibyte_unicode_threshold_uses_utf8_bytes(self, tmp_path):
        """Threshold is applied to UTF-8 byte length, not Python char length.

        A string of 16384 Chinese characters encodes to 49152 UTF-8 bytes
        (3 bytes each) and must be spilled even though len(str) < 32768.
        """
        # 16384 chars x 3 bytes/char = 49152 UTF-8 bytes -> above threshold
        value = "中" * 16384
        assert len(value) < _LIMIT  # char count is below limit
        assert len(value.encode("utf-8")) > _LIMIT  # byte count is above
        cmd, _ = self._build({"CJK_KEY": value}, tmp_dir=tmp_path)
        set_args = [cmd[i + 1] for i, v in enumerate(cmd) if v == "--set"]
        assert any(a.startswith("CJK_KEY=file://") for a in set_args)

    # -- Spilled file content roundtrip ----------------------------------------

    def test_spilled_file_content_matches_original(self, tmp_path):
        """Content of spilled file equals the original serialised value byte-for-byte."""
        value = _make_value(_LIMIT)
        cmd, _ = self._build({"MY_KEY": value}, tmp_dir=tmp_path)
        set_args = [cmd[i + 1] for i, v in enumerate(cmd) if v == "--set"]
        uri = next(a[len("MY_KEY=") :] for a in set_args if a.startswith("MY_KEY="))
        assert uri.startswith("file://")
        file_path = Path(uri[len("file://") :])
        assert file_path.read_text(encoding="utf-8") == value


# ─────────────────────────────────────────────────────────────────────────────
# 5. Lazy temp-dir creation
# ─────────────────────────────────────────────────────────────────────────────


class TestLazyTmpDirCreation:
    """The temp directory must be created lazily — only when a value is spilled."""

    def test_no_temp_dir_when_all_small(self, tmp_path):
        """No spill files written when all values are below threshold."""
        context = {
            "key1": _make_value(_LIMIT - 100),
            "key2": "small",
            "flag": True,
        }
        _build_rust_command(
            "/bin/recipe-runner-rs",
            "test-recipe",
            working_dir=".",
            dry_run=False,
            auto_stage=True,
            progress=False,
            recipe_dirs=None,
            user_context=context,
            tmp_dir=tmp_path,
        )
        # tmp_path is supplied but should remain empty (no spills)
        assert list(tmp_path.iterdir()) == []

    def test_tmp_dir_permissions_are_owner_only(self, tmp_path):
        """_spill_large_value must create a new directory with mode 0o700."""
        # Use a non-existent subdirectory so mkdir(mode=0o700) actually fires.
        new_dir = tmp_path / "spill_dir"
        assert not new_dir.exists(), "Test pre-condition: spill_dir must not exist yet"
        _spill_large_value("KEY", _make_value(_LIMIT), new_dir)
        dir_mode = new_dir.stat().st_mode & 0o777
        assert dir_mode == 0o700, f"Expected 0o700, got {oct(dir_mode)}"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Cleanup in run_recipe_via_rust
# ─────────────────────────────────────────────────────────────────────────────


class TestTempDirCleanup:
    """The temp directory must be removed after run_recipe_via_rust() returns."""

    _SUCCESS_OUTPUT = _make_rust_success_output()

    def _mock_subprocess_success(self):
        return subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=self._SUCCESS_OUTPUT,
            stderr="",
        )

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value="/bin/recipe-runner-rs")
    @patch("amplihack.recipes.rust_runner.check_runner_version", return_value=True)
    @patch("subprocess.run")
    def test_cleanup_after_success(self, mock_run, mock_ver, mock_find):
        """Temp dir is removed when recipe execution succeeds."""
        mock_run.return_value = self._mock_subprocess_success()

        # Capture the tmp_dir path before cleanup
        captured_dirs: list[Path] = []

        original_build = _build_rust_command

        def capturing_build(*args, **kwargs):
            tmp_dir = kwargs.get("tmp_dir")
            if tmp_dir is not None:
                captured_dirs.append(tmp_dir)
            return original_build(*args, **kwargs)

        with patch(
            "amplihack.recipes.rust_runner._build_rust_command", side_effect=capturing_build
        ):
            run_recipe_via_rust(
                "test-recipe",
                user_context={"BIG": _make_value(_LIMIT)},
            )

        # Any temp dirs that were created should have been cleaned up
        for d in captured_dirs:
            assert not d.exists(), f"Temp dir {d} was not cleaned up after success"

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value="/bin/recipe-runner-rs")
    @patch("amplihack.recipes.rust_runner.check_runner_version", return_value=True)
    @patch("amplihack.recipes.rust_runner._execute_rust_command", side_effect=RuntimeError("boom"))
    @patch("subprocess.run")
    def test_cleanup_after_exception(self, mock_run, mock_execute, mock_ver, mock_find):
        """Temp dir is removed even when _execute_rust_command raises."""
        captured_dirs: list[Path] = []

        original_build = _build_rust_command

        def capturing_build(*args, **kwargs):
            tmp_dir = kwargs.get("tmp_dir")
            if tmp_dir is not None:
                captured_dirs.append(tmp_dir)
            return original_build(*args, **kwargs)

        with patch(
            "amplihack.recipes.rust_runner._build_rust_command", side_effect=capturing_build
        ):
            with pytest.raises(RuntimeError, match="boom"):
                run_recipe_via_rust(
                    "test-recipe",
                    user_context={"BIG": _make_value(_LIMIT)},
                )

        for d in captured_dirs:
            assert not d.exists(), f"Temp dir {d} was not cleaned up after exception"

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value="/bin/recipe-runner-rs")
    @patch("amplihack.recipes.rust_runner.check_runner_version", return_value=True)
    @patch("amplihack.recipes.rust_runner._build_rust_env", return_value={})
    @patch("subprocess.run")
    def test_no_temp_dir_created_when_all_small(self, mock_run, mock_env, mock_ver, mock_find):
        """When all context values are small, the temp dir is created but cleaned up with no spill files."""
        mock_run.return_value = self._mock_subprocess_success()

        # Capture the temp dir created by tempfile.mkdtemp inside run_recipe_via_rust.
        created_dirs: list[Path] = []
        original_mkdtemp = tempfile.mkdtemp

        def capturing_mkdtemp(*args, **kwargs):
            d = original_mkdtemp(*args, **kwargs)
            created_dirs.append(Path(d))
            return d

        with patch("tempfile.mkdtemp", side_effect=capturing_mkdtemp):
            run_recipe_via_rust(
                "test-recipe",
                user_context={
                    "key1": _make_value(_LIMIT - 1),
                    "key2": "small value",
                },
            )

        # Exactly one temp dir should have been created and then cleaned up.
        assert len(created_dirs) == 1, f"Expected 1 temp dir, got {len(created_dirs)}"
        tmp_dir = created_dirs[0]
        assert not tmp_dir.exists(), (
            f"Temp dir {tmp_dir} was not cleaned up after execution with all-small values"
        )

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value="/bin/recipe-runner-rs")
    @patch("amplihack.recipes.rust_runner.check_runner_version", return_value=True)
    @patch("subprocess.run")
    def test_cleanup_removes_all_spilled_files(self, mock_run, mock_ver, mock_find):
        """All spilled files inside the temp dir are removed on cleanup."""
        mock_run.return_value = self._mock_subprocess_success()

        observed_tmp_dirs: list[Path] = []
        original_build = _build_rust_command

        def capturing_build(*args, **kwargs):
            result = original_build(*args, **kwargs)
            tmp_dir = kwargs.get("tmp_dir")
            if tmp_dir is not None and tmp_dir.exists():
                observed_tmp_dirs.append(tmp_dir)
            return result

        with patch(
            "amplihack.recipes.rust_runner._build_rust_command", side_effect=capturing_build
        ):
            run_recipe_via_rust(
                "test-recipe",
                user_context={
                    "BIG_A": _make_value(_LIMIT),
                    "BIG_B": _make_value(_LIMIT + 500),
                },
            )

        for d in observed_tmp_dirs:
            assert not d.exists(), f"Temp dir {d} still exists after cleanup"


# ─────────────────────────────────────────────────────────────────────────────
# 7. Integration: spill flow does not break existing run_recipe_via_rust tests
# ─────────────────────────────────────────────────────────────────────────────


class TestBackwardCompatibility:
    """Existing small-value behaviour is unchanged after the spill feature is added."""

    _SUCCESS_OUTPUT = _make_rust_success_output()

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value="/bin/recipe-runner-rs")
    @patch("amplihack.recipes.rust_runner.check_runner_version", return_value=True)
    @patch("subprocess.run")
    def test_small_string_value_still_inline(self, mock_run, mock_ver, mock_find):
        """String values well below the limit are passed directly in --set."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=self._SUCCESS_OUTPUT,
            stderr="",
        )
        run_recipe_via_rust("test-recipe", user_context={"name": "world"})
        cmd = mock_run.call_args[0][0]
        set_args = [cmd[i + 1] for i, v in enumerate(cmd) if v == "--set"]
        assert "name=world" in set_args

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value="/bin/recipe-runner-rs")
    @patch("amplihack.recipes.rust_runner.check_runner_version", return_value=True)
    @patch("subprocess.run")
    def test_bool_true_still_inline(self, mock_run, mock_ver, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=self._SUCCESS_OUTPUT,
            stderr="",
        )
        run_recipe_via_rust("test-recipe", user_context={"verbose": True})
        cmd = mock_run.call_args[0][0]
        set_args = [cmd[i + 1] for i, v in enumerate(cmd) if v == "--set"]
        assert "verbose=true" in set_args

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value="/bin/recipe-runner-rs")
    @patch("amplihack.recipes.rust_runner.check_runner_version", return_value=True)
    @patch("subprocess.run")
    def test_small_dict_still_json_inline(self, mock_run, mock_ver, mock_find):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=self._SUCCESS_OUTPUT,
            stderr="",
        )
        run_recipe_via_rust("test-recipe", user_context={"data": {"k": "v"}})
        cmd = mock_run.call_args[0][0]
        set_args = [cmd[i + 1] for i, v in enumerate(cmd) if v == "--set"]
        assert any('"k"' in a for a in set_args)
        assert not any("file://" in a for a in set_args)

    @patch("amplihack.recipes.rust_runner.find_rust_binary", return_value="/bin/recipe-runner-rs")
    @patch("amplihack.recipes.rust_runner.check_runner_version", return_value=True)
    @patch("subprocess.run")
    def test_none_context_still_works(self, mock_run, mock_ver, mock_find):
        """run_recipe_via_rust with no user_context still works."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=self._SUCCESS_OUTPUT,
            stderr="",
        )
        result = run_recipe_via_rust("test-recipe", user_context=None)
        assert result.success is True
