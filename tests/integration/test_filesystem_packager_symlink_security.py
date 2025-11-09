"""
Comprehensive tests for path traversal vulnerability fix in FilesystemPackager.

Tests the symlink bypass prevention: resolve() should NOT be called before
checking is_symlink(), otherwise attacker can create /tmp/evil -> /etc bypass.
"""

import tempfile
import pytest
from pathlib import Path

from src.amplihack.bundle_generator.filesystem_packager import FilesystemPackager
from src.amplihack.bundle_generator.exceptions import PackagingError


class TestSymlinkAttackPrevention:
    """Tests for symlink-based path traversal attacks."""

    def test_symlink_to_etc_is_rejected(self):
        """Test that symlink to /etc is rejected before resolve()."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            symlink_path = tmpdir_path / "evil"

            # Create a symlink pointing to /etc
            symlink_path.symlink_to(Path("/etc"))

            # Should raise PackagingError due to symlink detection
            with pytest.raises(PackagingError) as exc_info:
                FilesystemPackager(symlink_path)

            error_msg = str(exc_info.value)
            assert "cannot be a symlink" in error_msg.lower()
            assert "evil" in error_msg

    def test_symlink_to_usr_is_rejected(self):
        """Test that symlink to /usr is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            symlink_path = tmpdir_path / "malicious"

            # Create a symlink pointing to /usr
            symlink_path.symlink_to(Path("/usr"))

            with pytest.raises(PackagingError) as exc_info:
                FilesystemPackager(symlink_path)

            assert "cannot be a symlink" in str(exc_info.value).lower()

    def test_symlink_to_bin_is_rejected(self):
        """Test that symlink to /bin is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            symlink_path = tmpdir_path / "attack"

            # Create a symlink pointing to /bin
            symlink_path.symlink_to(Path("/bin"))

            with pytest.raises(PackagingError) as exc_info:
                FilesystemPackager(symlink_path)

            assert "cannot be a symlink" in str(exc_info.value).lower()

    def test_symlink_to_root_is_rejected(self):
        """Test that symlink to / is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            symlink_path = tmpdir_path / "root_link"

            # Create a symlink pointing to root
            symlink_path.symlink_to(Path("/"))

            with pytest.raises(PackagingError) as exc_info:
                FilesystemPackager(symlink_path)

            assert "cannot be a symlink" in str(exc_info.value).lower()

    def test_symlink_to_sys_is_rejected(self):
        """Test that symlink to /sys is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            symlink_path = tmpdir_path / "sys_link"

            symlink_path.symlink_to(Path("/sys"))

            with pytest.raises(PackagingError) as exc_info:
                FilesystemPackager(symlink_path)

            assert "cannot be a symlink" in str(exc_info.value).lower()

    def test_symlink_to_proc_is_rejected(self):
        """Test that symlink to /proc is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            symlink_path = tmpdir_path / "proc_link"

            symlink_path.symlink_to(Path("/proc"))

            with pytest.raises(PackagingError) as exc_info:
                FilesystemPackager(symlink_path)

            assert "cannot be a symlink" in str(exc_info.value).lower()

    def test_symlink_to_dev_is_rejected(self):
        """Test that symlink to /dev is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            symlink_path = tmpdir_path / "dev_link"

            symlink_path.symlink_to(Path("/dev"))

            with pytest.raises(PackagingError) as exc_info:
                FilesystemPackager(symlink_path)

            assert "cannot be a symlink" in str(exc_info.value).lower()

    def test_symlink_to_var_tmp_is_rejected(self):
        """Test that symlink to /var/tmp is also rejected for consistency."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            symlink_path = tmpdir_path / "var_link"

            symlink_path.symlink_to(Path("/var/tmp"))

            with pytest.raises(PackagingError) as exc_info:
                FilesystemPackager(symlink_path)

            assert "cannot be a symlink" in str(exc_info.value).lower()

    def test_regular_directory_is_accepted(self):
        """Test that regular directories (not symlinks) are accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            regular_dir = tmpdir_path / "regular"
            regular_dir.mkdir()

            # Should not raise - regular directory is fine
            packager = FilesystemPackager(regular_dir)
            assert packager is not None

    def test_nonexistent_path_regular_style_accepted(self):
        """Test that nonexistent regular paths are accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            nonexistent = tmpdir_path / "will_be_created"

            # Should not raise - nonexistent regular path is fine
            packager = FilesystemPackager(nonexistent)
            assert packager is not None

    def test_error_message_includes_symlink_warning(self):
        """Test that error message clearly indicates symlink rejection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            symlink_path = tmpdir_path / "evil"

            symlink_path.symlink_to(Path("/etc"))

            with pytest.raises(PackagingError) as exc_info:
                FilesystemPackager(symlink_path)

            error_msg = str(exc_info.value)
            # Check for clear security warning
            assert "symlink" in error_msg.lower()
            assert "not allowed" in error_msg.lower() or "cannot" in error_msg.lower()

    def test_symlink_check_happens_before_resolve(self):
        """Test that symlink check happens BEFORE calling resolve().

        This is the critical security fix: by checking is_symlink() first,
        we prevent the attacker's symlink from being followed.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            symlink_path = tmpdir_path / "attack"

            # Create symlink to /etc
            symlink_path.symlink_to(Path("/etc"))

            # If symlink check didn't happen first, resolve() would follow the symlink
            # and the path would resolve to /etc. By checking is_symlink() first,
            # we reject it before resolve() can be called.
            with pytest.raises(PackagingError) as exc_info:
                FilesystemPackager(symlink_path)

            # Confirm it's rejected as symlink, not as unsafe path
            assert "symlink" in str(exc_info.value).lower()

    def test_multiple_symlinks_chain_is_rejected(self):
        """Test that even symlink chains are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create a chain: link1 -> link2 -> /etc
            link1 = tmpdir_path / "link1"
            link2 = tmpdir_path / "link2"

            link2.symlink_to(Path("/etc"))
            link1.symlink_to(link2)

            # link1 is a symlink, so it should be rejected
            with pytest.raises(PackagingError) as exc_info:
                FilesystemPackager(link1)

            assert "symlink" in str(exc_info.value).lower()


class TestDirectoryValidation:
    """Tests for proper directory validation logic."""

    def test_temp_directory_allowed(self):
        """Test that regular temp directories are allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            output_dir = tmpdir_path / "output"
            output_dir.mkdir()

            # Should succeed - regular temp directory
            packager = FilesystemPackager(output_dir)
            assert packager is not None

    def test_none_output_dir_raises_error(self):
        """Test that None output_dir raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            FilesystemPackager(None)

        assert "output_dir" in str(exc_info.value).lower()

    def test_empty_string_output_dir_raises_error(self):
        """Test that empty string output_dir raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            FilesystemPackager("")

        assert "output_dir" in str(exc_info.value).lower()


class TestSecurityOrdering:
    """Tests to ensure security checks happen in correct order."""

    def test_symlink_rejection_doesnt_require_resolution(self):
        """Verify that symlink check doesn't depend on resolve()."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            symlink_path = tmpdir_path / "link_to_sys"

            # Create symlink to /sys
            symlink_path.symlink_to(Path("/sys"))

            # is_symlink() should work without resolve()
            assert symlink_path.is_symlink()

            # FilesystemPackager should catch it
            with pytest.raises(PackagingError) as exc_info:
                FilesystemPackager(symlink_path)

            # Should specifically mention symlink, not just unsafe path
            assert "symlink" in str(exc_info.value).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
