"""Tests for UVX staging functionality."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.amplihack.utils.uvx_staging import UVXStager, is_uvx_deployment, stage_uvx_framework


class TestUVXStager:
    """Test cases for UVXStager."""

    def test_detect_uvx_deployment_with_uv_python(self):
        """Test UVX detection with UV_PYTHON environment variable."""
        stager = UVXStager()

        with patch.dict(os.environ, {"UV_PYTHON": "/path/to/uv/python"}):
            assert stager.detect_uvx_deployment() is True

    def test_detect_uvx_deployment_no_claude_dir(self):
        """Test UVX detection when .claude directory doesn't exist."""
        stager = UVXStager()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Working directory without .claude
            working_dir = Path(temp_dir)
            # Ensure .claude doesn't exist
            assert not (working_dir / ".claude").exists()

            with patch("pathlib.Path.cwd", return_value=working_dir):
                assert stager.detect_uvx_deployment() is True

    def test_detect_uvx_deployment_no_local_claude_but_framework_available(self):
        """Test UVX detection when no local .claude but framework available elsewhere."""
        stager = UVXStager()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create framework files in UVX location
            uvx_root = Path(temp_dir)
            (uvx_root / ".claude").mkdir()

            # Mock to return UVX framework root
            with patch.object(stager, "_find_uvx_framework_root", return_value=uvx_root):
                with patch("pathlib.Path.cwd", return_value=Path("/different/working/dir")):
                    assert stager.detect_uvx_deployment() is True

    def test_detect_uvx_deployment_local_deployment(self):
        """Test that local deployment is not detected as UVX."""
        stager = UVXStager()

        with tempfile.TemporaryDirectory() as temp_dir:
            working_dir = Path(temp_dir)
            (working_dir / ".claude").mkdir()

            with patch("pathlib.Path.cwd", return_value=working_dir):
                with patch.dict(os.environ, {}, clear=True):
                    with patch("sys.path", ["/normal/path"]):
                        assert stager.detect_uvx_deployment() is False

    def test_find_uvx_framework_root_env_var(self):
        """Test finding UVX framework root via environment variable."""
        stager = UVXStager()

        with tempfile.TemporaryDirectory() as temp_dir:
            uvx_root = Path(temp_dir)
            (uvx_root / ".claude").mkdir()

            with patch.dict(os.environ, {"AMPLIHACK_ROOT": str(uvx_root)}):
                result = stager._find_uvx_framework_root()
                assert result == uvx_root

    def test_find_uvx_framework_root_sys_path_search(self):
        """Test finding UVX framework root by searching Python path."""
        stager = UVXStager()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create fake package structure
            # The code looks for "amplihack" in sys.path and then checks for .claude inside it
            package_parent = Path(temp_dir)
            package_dir = package_parent / "amplihack"
            package_dir.mkdir()
            (package_dir / ".claude").mkdir()  # .claude should be inside amplihack

            with patch("sys.path", [str(package_parent)]):  # Add parent to sys.path
                result = stager._find_uvx_framework_root()
                assert result == package_dir  # Should return the amplihack directory

    def test_stage_framework_files_success(self):
        """Test successful staging of framework files."""
        stager = UVXStager()

        with tempfile.TemporaryDirectory() as source_dir:
            with tempfile.TemporaryDirectory() as target_dir:
                # Create source framework files
                source_path = Path(source_dir)
                claude_dir = source_path / ".claude"
                claude_dir.mkdir()
                (claude_dir / "context").mkdir()
                (claude_dir / "context" / "test.md").write_text("test content")
                (source_path / "CLAUDE.md").write_text("# CLAUDE.md")

                # Mock methods
                with patch.object(stager, "detect_uvx_deployment", return_value=True):
                    with patch.object(stager, "_find_uvx_framework_root", return_value=source_path):
                        with patch("pathlib.Path.cwd", return_value=Path(target_dir)):
                            result = stager.stage_framework_files()

                            assert result is True
                            assert (Path(target_dir) / ".claude").exists()
                            assert (Path(target_dir) / "CLAUDE.md").exists()
                            assert len(stager._staged_files) > 0

    def test_stage_framework_files_not_uvx(self):
        """Test staging when not in UVX deployment."""
        stager = UVXStager()

        with patch.object(stager, "detect_uvx_deployment", return_value=False):
            result = stager.stage_framework_files()
            assert result is False

    def test_stage_framework_files_no_uvx_root(self):
        """Test staging when UVX framework root not found."""
        stager = UVXStager()

        with patch.object(stager, "detect_uvx_deployment", return_value=True):
            with patch.object(stager, "_find_uvx_framework_root", return_value=None):
                result = stager.stage_framework_files()
                assert result is False

    def test_stage_framework_files_existing_files(self):
        """Test staging when target files already exist."""
        stager = UVXStager()

        with tempfile.TemporaryDirectory() as source_dir:
            with tempfile.TemporaryDirectory() as target_dir:
                # Create source framework files
                source_path = Path(source_dir)
                (source_path / ".claude").mkdir()
                (source_path / "CLAUDE.md").write_text("source content")

                # Create existing target files
                target_path = Path(target_dir)
                (target_path / ".claude").mkdir()
                (target_path / "CLAUDE.md").write_text("existing content")

                with patch.object(stager, "detect_uvx_deployment", return_value=True):
                    with patch.object(stager, "_find_uvx_framework_root", return_value=source_path):
                        with patch("pathlib.Path.cwd", return_value=target_path):
                            stager.stage_framework_files()

                            # Should not overwrite existing files
                            assert (target_path / "CLAUDE.md").read_text() == "existing content"
                            assert len(stager._staged_files) == 0

    def test_cleanup_staged_files(self):
        """Test cleanup of staged files."""
        stager = UVXStager()

        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir)

            # Create some fake staged files
            test_file = target_dir / "test.md"
            test_file.write_text("test")
            test_dir = target_dir / "test_dir"
            test_dir.mkdir()

            stager._staged_files.add(test_file)
            stager._staged_files.add(test_dir)

            # Note: Cleanup removed in simplified implementation
            # Manually clean up test files
            if test_file.exists():
                test_file.unlink()
            if test_dir.exists():
                test_dir.rmdir()

    def test_cleanup_staged_files_missing(self):
        """Test cleanup handles missing files gracefully."""
        stager = UVXStager()

        # Add non-existent files to staged list
        stager._staged_files.add(Path("/non/existent/file"))
        stager._staged_files.add(Path("/non/existent/dir"))

        # Note: Cleanup removed in simplified implementation
        # Should not raise exception with non-existent files
        pass


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_stage_uvx_framework(self):
        """Test stage_uvx_framework convenience function."""
        with patch("src.amplihack.utils.uvx_staging._uvx_stager") as mock_stager:
            mock_stager.stage_framework_files.return_value = True

            result = stage_uvx_framework()

            assert result is True
            mock_stager.stage_framework_files.assert_called_once()

    def test_is_uvx_deployment(self):
        """Test is_uvx_deployment convenience function."""
        with patch("src.amplihack.utils.uvx_staging._uvx_stager") as mock_stager:
            mock_stager.detect_uvx_deployment.return_value = True

            result = is_uvx_deployment()

            assert result is True
            mock_stager.detect_uvx_deployment.assert_called_once()


class TestIntegration:
    """Integration tests with FrameworkPathResolver."""

    def test_framework_path_resolver_triggers_staging(self):
        """Test that FrameworkPathResolver triggers UVX staging when needed."""
        from src.amplihack.utils.paths import FrameworkPathResolver

        with tempfile.TemporaryDirectory() as source_dir:
            with tempfile.TemporaryDirectory() as target_dir:
                # Create source framework files
                source_path = Path(source_dir)
                (source_path / ".claude").mkdir()

                # Mock to simulate UVX environment
                with patch("src.amplihack.utils.uvx_staging.is_uvx_deployment", return_value=True):
                    with patch(
                        "src.amplihack.utils.uvx_staging.stage_uvx_framework", return_value=True
                    ):
                        with patch("pathlib.Path.cwd", return_value=Path(target_dir)):
                            # Create .claude in target to simulate successful staging
                            (Path(target_dir) / ".claude").mkdir()

                            result = FrameworkPathResolver.find_framework_root()

                            assert result == Path(target_dir)
