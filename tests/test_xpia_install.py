"""Tests for xpia_install module — auto-download of xpia-defend binary."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.security.xpia_install import (
    BINARY_NAME,
    XPIAInstallError,
    _get_installed_version,
    _get_latest_release_tag,
    _get_target_triple,
    _safe_zip_extract,
    _verify_checksum,
    ensure_xpia_binary,
    get_install_dir,
)


class TestGetTargetTriple:
    """Test platform detection."""

    @patch("platform.system", return_value="Linux")
    @patch("platform.machine", return_value="x86_64")
    def test_linux_x86_64(self, _m, _s):
        assert _get_target_triple() == "x86_64-unknown-linux-gnu"

    @patch("platform.system", return_value="Linux")
    @patch("platform.machine", return_value="aarch64")
    def test_linux_arm64(self, _m, _s):
        assert _get_target_triple() == "aarch64-unknown-linux-gnu"

    @patch("platform.system", return_value="Darwin")
    @patch("platform.machine", return_value="x86_64")
    def test_macos_x86_64(self, _m, _s):
        assert _get_target_triple() == "x86_64-apple-darwin"

    @patch("platform.system", return_value="Darwin")
    @patch("platform.machine", return_value="arm64")
    def test_macos_arm64(self, _m, _s):
        assert _get_target_triple() == "aarch64-apple-darwin"

    @patch("platform.system", return_value="Windows")
    @patch("platform.machine", return_value="AMD64")
    def test_windows_x86_64(self, _m, _s):
        assert _get_target_triple() == "x86_64-pc-windows-msvc"

    @patch("platform.system", return_value="Windows")
    @patch("platform.machine", return_value="aarch64")
    def test_windows_arm_unsupported(self, _m, _s):
        with pytest.raises(XPIAInstallError, match="only supports x86_64"):
            _get_target_triple()

    @patch("platform.system", return_value="Linux")
    @patch("platform.machine", return_value="mips")
    def test_unsupported_arch(self, _m, _s):
        with pytest.raises(XPIAInstallError, match="Unsupported architecture"):
            _get_target_triple()

    @patch("platform.system", return_value="FreeBSD")
    @patch("platform.machine", return_value="x86_64")
    def test_unsupported_os(self, _m, _s):
        with pytest.raises(XPIAInstallError, match="Unsupported OS"):
            _get_target_triple()


class TestGetInstalledVersion:
    """Test version marker file reading."""

    def test_no_version_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "amplihack.security.xpia_install.VERSION_FILE", tmp_path / "nonexistent"
        )
        assert _get_installed_version() is None

    def test_reads_version(self, tmp_path, monkeypatch):
        vfile = tmp_path / ".xpia-defend-version"
        vfile.write_text("v0.1.0\n")
        monkeypatch.setattr("amplihack.security.xpia_install.VERSION_FILE", vfile)
        assert _get_installed_version() == "v0.1.0"


class TestGetLatestReleaseTag:
    """Test GitHub release tag fetching."""

    @patch("subprocess.run")
    def test_gh_cli_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="v0.2.0\n")
        assert _get_latest_release_tag() == "v0.2.0"
        # Verify gh CLI was called
        args = mock_run.call_args_list[0]
        assert "gh" in args[0][0][0]

    @patch("subprocess.run")
    def test_gh_cli_fails_curl_succeeds(self, mock_run):
        # gh fails, curl succeeds
        import json

        mock_run.side_effect = [
            MagicMock(returncode=1, stdout="", stderr="not found"),
            MagicMock(returncode=0, stdout=json.dumps({"tag_name": "v0.3.0"})),
        ]
        assert _get_latest_release_tag() == "v0.3.0"

    @patch("subprocess.run")
    def test_both_fail_raises(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout="", stderr="error"),
            MagicMock(returncode=1, stdout="", stderr="error"),
        ]
        with pytest.raises(XPIAInstallError, match="Cannot determine"):
            _get_latest_release_tag()


class TestEnsureXpiaBinary:
    """Test the main ensure_xpia_binary function."""

    def test_already_installed_and_healthy(self, tmp_path, monkeypatch):
        """If binary exists, version matches, and health check passes, skip download."""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        binary = bin_dir / BINARY_NAME
        binary.write_text("#!/bin/sh\necho ok")
        binary.chmod(0o755)
        vfile = tmp_path / ".version"
        vfile.write_text("v0.1.0\n")

        monkeypatch.setattr("amplihack.security.xpia_install.INSTALL_DIR", bin_dir)
        monkeypatch.setattr("amplihack.security.xpia_install.VERSION_FILE", vfile)

        # Mock the health check subprocess
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='{"status":"ok"}')
            result = ensure_xpia_binary()
            assert result == binary

    def test_not_installed_triggers_download(self, tmp_path, monkeypatch):
        """If binary not present, download is triggered."""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        vfile = tmp_path / ".version"

        monkeypatch.setattr("amplihack.security.xpia_install.INSTALL_DIR", bin_dir)
        monkeypatch.setattr("amplihack.security.xpia_install.VERSION_FILE", vfile)

        with (
            patch("amplihack.security.xpia_install._get_latest_release_tag", return_value="v0.1.0"),
            patch("amplihack.security.xpia_install._download_and_install") as mock_dl,
        ):
            mock_dl.return_value = bin_dir / BINARY_NAME
            result = ensure_xpia_binary()
            mock_dl.assert_called_once_with("v0.1.0")

    def test_force_redownload(self, tmp_path, monkeypatch):
        """force=True always triggers download."""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        binary = bin_dir / BINARY_NAME
        binary.write_text("old binary")
        binary.chmod(0o755)
        vfile = tmp_path / ".version"
        vfile.write_text("v0.1.0\n")

        monkeypatch.setattr("amplihack.security.xpia_install.INSTALL_DIR", bin_dir)
        monkeypatch.setattr("amplihack.security.xpia_install.VERSION_FILE", vfile)

        with (
            patch("amplihack.security.xpia_install._get_latest_release_tag", return_value="v0.2.0"),
            patch("amplihack.security.xpia_install._download_and_install") as mock_dl,
        ):
            mock_dl.return_value = bin_dir / BINARY_NAME
            ensure_xpia_binary(force=True)
            mock_dl.assert_called_once_with("v0.2.0")


class TestGetInstallDir:
    def test_returns_amplihack_bin(self):
        assert get_install_dir() == Path.home() / ".amplihack" / "bin"


class TestFindBinaryAutoInstall:
    """Test that find_binary triggers auto-install."""

    @patch("shutil.which", return_value=None)
    @patch("amplihack.security.xpia_install.ensure_xpia_binary")
    def test_auto_install_on_missing(self, mock_ensure, mock_which, tmp_path):
        from amplihack.security.rust_xpia import find_binary

        mock_ensure.return_value = tmp_path / "xpia-defend"
        # auto_install=True required since default is now False
        with patch.object(Path, "is_file", return_value=False):
            result = find_binary(auto_install=True)
            mock_ensure.assert_called_once()
            assert "xpia-defend" in result

    @patch("shutil.which", return_value=None)
    def test_no_auto_install_by_default(self, mock_which):
        """find_binary() with default auto_install=False raises when binary not found."""
        from amplihack.security.rust_xpia import RustXPIAError, find_binary

        with patch.object(Path, "is_file", return_value=False):
            with pytest.raises(RustXPIAError, match="not found"):
                find_binary()

    @patch("shutil.which", return_value="/usr/bin/xpia-defend")
    def test_path_found_no_install(self, mock_which):
        from amplihack.security.rust_xpia import find_binary

        result = find_binary()
        assert result == "/usr/bin/xpia-defend"


class TestVerifyChecksum:
    """Test SHA256 checksum verification."""

    def test_valid_checksum_passes(self, tmp_path):
        asset = tmp_path / "test-asset.tar.gz"
        asset.write_bytes(b"test binary content")
        expected_hash = hashlib.sha256(b"test binary content").hexdigest()

        checksums = tmp_path / "SHA256SUMS.txt"
        checksums.write_text(f"{expected_hash}  test-asset.tar.gz\n")

        # Should not raise
        _verify_checksum(asset, checksums, "test-asset.tar.gz")

    def test_invalid_checksum_raises(self, tmp_path):
        asset = tmp_path / "test-asset.tar.gz"
        asset.write_bytes(b"test binary content")

        checksums = tmp_path / "SHA256SUMS.txt"
        checksums.write_text(
            "0000000000000000000000000000000000000000000000000000000000000000  test-asset.tar.gz\n"
        )

        with pytest.raises(XPIAInstallError, match="Checksum mismatch"):
            _verify_checksum(asset, checksums, "test-asset.tar.gz")

    def test_missing_checksums_file_raises(self, tmp_path):
        asset = tmp_path / "test-asset.tar.gz"
        asset.write_bytes(b"data")
        missing = tmp_path / "SHA256SUMS.txt"

        with pytest.raises(XPIAInstallError, match="SHA256SUMS.txt not found"):
            _verify_checksum(asset, missing, "test-asset.tar.gz")

    def test_asset_not_in_checksums_raises(self, tmp_path):
        asset = tmp_path / "test-asset.tar.gz"
        asset.write_bytes(b"data")
        checksums = tmp_path / "SHA256SUMS.txt"
        checksums.write_text("abcdef  other-asset.tar.gz\n")

        with pytest.raises(XPIAInstallError, match="No checksum found"):
            _verify_checksum(asset, checksums, "test-asset.tar.gz")


class TestSafeZipExtract:
    """Test path traversal protection in zip extraction."""

    def test_normal_extraction_works(self, tmp_path):
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("xpia-defend.exe", b"binary data")

        _safe_zip_extract(zip_path, "xpia-defend.exe", tmp_path)
        assert (tmp_path / "xpia-defend.exe").exists()

    def test_path_traversal_blocked(self, tmp_path):
        zip_path = tmp_path / "malicious.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("../../../etc/passwd", b"malicious")

        with pytest.raises(XPIAInstallError, match="Unsafe path"):
            _safe_zip_extract(zip_path, "../../../etc/passwd", tmp_path)

    def test_absolute_path_blocked(self, tmp_path):
        zip_path = tmp_path / "malicious.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("/etc/passwd", b"malicious")

        with pytest.raises(XPIAInstallError, match="Unsafe path"):
            _safe_zip_extract(zip_path, "/etc/passwd", tmp_path)
