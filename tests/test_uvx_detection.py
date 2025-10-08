"""Tests for UVX detection and path resolution logic."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.utils.uvx_detection import (
    detect_uvx_deployment,
    find_framework_root,
    is_uvx_deployment,
    resolve_framework_file,
    resolve_framework_paths,
)
from amplihack.utils.uvx_models import (
    PathResolutionStrategy,
    UVXConfiguration,
    UVXDetectionResult,
    UVXEnvironmentInfo,
)


class TestUVXDetection:
    """Tests for UVX deployment detection logic."""

    def test_detect_uvx_with_uv_python_env(self):
        """Test UVX detection with UV_PYTHON environment variable."""
        with patch.dict(os.environ, {"UV_PYTHON": "/path/to/uv/python"}):
            with patch("pathlib.Path.cwd", return_value=Path("/working")):
                detection = detect_uvx_deployment()

                assert detection.result == UVXDetectionResult.UVX_DEPLOYMENT
                assert detection.is_uvx_deployment is True
                assert detection.is_detection_successful is True
                assert any("UV_PYTHON" in reason for reason in detection.detection_reasons)

    def test_detect_local_with_claude_dir(self):
        """Test local deployment detection with .claude directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            working_dir = Path(temp_dir)
            claude_dir = working_dir / ".claude"
            claude_dir.mkdir()

            with patch.dict(os.environ, {}, clear=True):
                with patch("pathlib.Path.cwd", return_value=working_dir):
                    detection = detect_uvx_deployment()

                    assert detection.result == UVXDetectionResult.LOCAL_DEPLOYMENT
                    assert detection.is_local_deployment is True
                    assert detection.is_detection_successful is True
                    assert any(".claude" in reason for reason in detection.detection_reasons)

    def test_detect_uvx_with_amplihack_root(self):
        """Test UVX detection with AMPLIHACK_ROOT environment variable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            framework_root = Path(temp_dir)
            claude_dir = framework_root / ".claude"
            claude_dir.mkdir()

            with patch.dict(os.environ, {"AMPLIHACK_ROOT": str(framework_root)}):
                with patch("pathlib.Path.cwd", return_value=Path("/different/working")):
                    detection = detect_uvx_deployment()

                    assert detection.result == UVXDetectionResult.UVX_DEPLOYMENT
                    assert detection.is_uvx_deployment is True
                    assert any("AMPLIHACK_ROOT" in reason for reason in detection.detection_reasons)

    def test_detect_uvx_with_sys_path_framework(self):
        """Test UVX detection by finding framework in sys.path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_parent = Path(temp_dir)
            package_dir = package_parent / "amplihack"
            package_dir.mkdir()
            claude_dir = package_dir / ".claude"
            claude_dir.mkdir()

            with patch.dict(os.environ, {}, clear=True):
                with patch("sys.path", [str(package_parent)]):
                    with patch("pathlib.Path.cwd", return_value=Path("/working")):
                        detection = detect_uvx_deployment()

                        assert detection.result == UVXDetectionResult.UVX_DEPLOYMENT
                        assert detection.is_uvx_deployment is True
                        assert any("sys.path" in reason for reason in detection.detection_reasons)

    def test_detect_detection_failed(self):
        """Test detection failure when no indicators found."""
        with patch.dict(os.environ, {}, clear=True), patch("sys.path", ["/normal/path"]):
            with patch("pathlib.Path.cwd", return_value=Path("/no/claude/here")):
                detection = detect_uvx_deployment()

                assert detection.result == UVXDetectionResult.DETECTION_FAILED
                assert detection.is_detection_successful is False
                assert any(
                    "No clear deployment indicators" in reason
                    for reason in detection.detection_reasons
                )

    def test_detect_with_custom_config(self):
        """Test detection with custom configuration."""
        config = UVXConfiguration(
            uv_python_env_var="CUSTOM_UV_PYTHON", amplihack_root_env_var="CUSTOM_AMPLIHACK_ROOT"
        )

        with patch.dict(os.environ, {"CUSTOM_UV_PYTHON": "/custom/path"}, clear=True):
            with patch("pathlib.Path.cwd", return_value=Path("/working")):
                with patch(
                    "src.amplihack.utils.uvx_detection.UVXEnvironmentInfo.from_current_environment"
                ) as mock_env:
                    # Mock environment to use custom env var
                    mock_env.return_value = UVXEnvironmentInfo(
                        uv_python_path="/custom/path",
                        working_directory=Path("/working"),
                        sys_path_entries=[],
                    )
                    detection = detect_uvx_deployment(config)

                    assert detection.result == UVXDetectionResult.UVX_DEPLOYMENT
                    assert detection.is_uvx_deployment is True


class TestPathResolution:
    """Tests for framework path resolution logic."""

    def test_resolve_local_deployment_working_directory(self):
        """Test path resolution for local deployment in working directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            working_dir = Path(temp_dir)
            claude_dir = working_dir / ".claude"
            claude_dir.mkdir()

            env_info = UVXEnvironmentInfo(working_directory=working_dir)
            detection = UVXDetectionResult.LOCAL_DEPLOYMENT
            from src.amplihack.utils.uvx_models import UVXDetectionState

            detection_state = UVXDetectionState(result=detection, environment=env_info)

            resolution = resolve_framework_paths(detection_state)

            assert resolution.is_successful is True
            assert resolution.location.root_path == working_dir
            assert resolution.location.strategy == PathResolutionStrategy.WORKING_DIRECTORY
            assert not resolution.requires_staging

    def test_resolve_environment_variable_path(self):
        """Test path resolution using AMPLIHACK_ROOT environment variable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            framework_root = Path(temp_dir)
            claude_dir = framework_root / ".claude"
            claude_dir.mkdir()

            env_info = UVXEnvironmentInfo(
                amplihack_root=str(framework_root), working_directory=Path("/different/working")
            )
            from src.amplihack.utils.uvx_models import UVXDetectionState

            detection_state = UVXDetectionState(
                result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
            )

            resolution = resolve_framework_paths(detection_state)

            assert resolution.is_successful is True
            assert resolution.location.root_path == framework_root
            assert resolution.location.strategy == PathResolutionStrategy.ENVIRONMENT_VARIABLE

    def test_resolve_sys_path_search(self):
        """Test path resolution via sys.path search."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_parent = Path(temp_dir)
            package_dir = package_parent / "amplihack"
            package_dir.mkdir()
            claude_dir = package_dir / ".claude"
            claude_dir.mkdir()

            env_info = UVXEnvironmentInfo(
                sys_path_entries=[str(package_parent)], working_directory=Path("/working")
            )
            from src.amplihack.utils.uvx_models import UVXDetectionState

            detection_state = UVXDetectionState(
                result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
            )

            resolution = resolve_framework_paths(detection_state)

            assert resolution.is_successful is True
            assert resolution.location.root_path == package_dir
            assert resolution.location.strategy == PathResolutionStrategy.SYSTEM_PATH_SEARCH

    def test_resolve_parent_directory_traversal(self):
        """Test path resolution by traversing parent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            framework_root = Path(temp_dir)
            claude_dir = framework_root / ".claude"
            claude_dir.mkdir()

            # Working in a subdirectory
            subdir = framework_root / "project" / "subdir"
            subdir.mkdir(parents=True)

            env_info = UVXEnvironmentInfo(working_directory=subdir)
            from src.amplihack.utils.uvx_models import UVXDetectionState

            detection_state = UVXDetectionState(
                result=UVXDetectionResult.LOCAL_DEPLOYMENT, environment=env_info
            )

            resolution = resolve_framework_paths(detection_state)

            assert resolution.is_successful is True
            assert resolution.location.root_path == framework_root
            assert resolution.location.strategy == PathResolutionStrategy.WORKING_DIRECTORY

    def test_resolve_staging_required(self):
        """Test path resolution that requires staging."""
        env_info = UVXEnvironmentInfo(working_directory=Path("/working"))
        from src.amplihack.utils.uvx_models import UVXDetectionState

        detection_state = UVXDetectionState(
            result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
        )

        config = UVXConfiguration(allow_staging=True)
        resolution = resolve_framework_paths(detection_state, config)

        assert resolution.requires_staging is True
        assert resolution.location.strategy == PathResolutionStrategy.STAGING_REQUIRED

    def test_resolve_all_strategies_failed(self):
        """Test path resolution when all strategies fail."""
        env_info = UVXEnvironmentInfo(
            sys_path_entries=["/invalid/path"], working_directory=Path("/no/claude")
        )
        from src.amplihack.utils.uvx_models import UVXDetectionState

        detection_state = UVXDetectionState(
            result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
        )

        config = UVXConfiguration(allow_staging=False)
        resolution = resolve_framework_paths(detection_state, config)

        assert resolution.is_successful is False
        assert resolution.location is None
        # Should have recorded at least one failed attempt
        assert len(resolution.attempts) >= 1
        assert resolution.attempts[-1]["success"] is False

    def test_resolve_with_custom_config(self):
        """Test path resolution with custom configuration."""
        config = UVXConfiguration(
            max_parent_traversal=2, validate_framework_structure=True, allow_staging=False
        )

        env_info = UVXEnvironmentInfo(working_directory=Path("/working"))
        from src.amplihack.utils.uvx_models import UVXDetectionState

        detection_state = UVXDetectionState(
            result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
        )

        resolution = resolve_framework_paths(detection_state, config)

        # Since staging disabled and no valid paths, should fail
        assert resolution.is_successful is False


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_is_uvx_deployment_convenience(self):
        """Test is_uvx_deployment convenience function."""
        with patch.dict(os.environ, {"UV_PYTHON": "/path"}):
            assert is_uvx_deployment() is True

        with tempfile.TemporaryDirectory() as temp_dir:
            working_dir = Path(temp_dir)
            claude_dir = working_dir / ".claude"
            claude_dir.mkdir()

            with patch.dict(os.environ, {}, clear=True):
                with patch("pathlib.Path.cwd", return_value=working_dir):
                    assert is_uvx_deployment() is False

    def test_find_framework_root_convenience(self):
        """Test find_framework_root convenience function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            working_dir = Path(temp_dir)
            claude_dir = working_dir / ".claude"
            claude_dir.mkdir()

            with patch.dict(os.environ, {}, clear=True):
                with patch("pathlib.Path.cwd", return_value=working_dir):
                    root = find_framework_root()
                    assert root == working_dir

    def test_resolve_framework_file_convenience(self):
        """Test resolve_framework_file convenience function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            framework_root = Path(temp_dir)
            claude_dir = framework_root / ".claude"
            claude_dir.mkdir()
            context_dir = claude_dir / "context"
            context_dir.mkdir()

            test_file = context_dir / "test.md"
            test_file.write_text("test content")

            with patch.dict(os.environ, {}, clear=True):
                with patch("pathlib.Path.cwd", return_value=framework_root):
                    resolved = resolve_framework_file(".claude/context/test.md")
                    # Use resolve() to handle symlinks consistently on macOS
                    assert resolved.resolve() == test_file.resolve()
                    assert resolved.exists()

    def test_resolve_framework_file_not_found(self):
        """Test resolve_framework_file when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            working_dir = Path(temp_dir)
            claude_dir = working_dir / ".claude"
            claude_dir.mkdir()

            with patch.dict(os.environ, {}, clear=True):
                with patch("pathlib.Path.cwd", return_value=working_dir):
                    resolved = resolve_framework_file(".claude/non_existent.md")
                    assert resolved is None

    def test_resolve_framework_file_no_framework(self):
        """Test resolve_framework_file when no framework found."""
        with patch.dict(os.environ, {}, clear=True), patch("sys.path", ["/normal/path"]):
            with patch("pathlib.Path.cwd", return_value=Path("/no/claude")):
                resolved = resolve_framework_file(".claude/test.md")
                assert resolved is None


class TestPrivateFunctions:
    """Tests for private helper functions."""

    def test_find_framework_in_sys_path_success(self):
        """Test finding framework in sys.path."""
        from src.amplihack.utils.uvx_detection import _find_framework_in_sys_path

        with tempfile.TemporaryDirectory() as temp_dir:
            package_parent = Path(temp_dir)
            package_dir = package_parent / "amplihack"
            package_dir.mkdir()
            claude_dir = package_dir / ".claude"
            claude_dir.mkdir()

            sys_path_entries = [str(package_parent), "/other/path"]
            result = _find_framework_in_sys_path(sys_path_entries)

            assert result == package_dir

    def test_find_framework_in_sys_path_not_found(self):
        """Test framework not found in sys.path."""
        from src.amplihack.utils.uvx_detection import _find_framework_in_sys_path

        sys_path_entries = ["/path1", "/path2"]
        result = _find_framework_in_sys_path(sys_path_entries)

        assert result is None

    def test_find_framework_in_sys_path_invalid_path(self):
        """Test handling invalid paths in sys.path."""
        from src.amplihack.utils.uvx_detection import _find_framework_in_sys_path

        # Include an invalid path that will cause OSError
        sys_path_entries = ["\x00invalid\x00path", "/normal/path"]
        result = _find_framework_in_sys_path(sys_path_entries)

        # Should handle the error gracefully and return None
        assert result is None

    def test_search_parent_directories_success(self):
        """Test successful parent directory search."""
        from src.amplihack.utils.uvx_detection import _search_parent_directories

        with tempfile.TemporaryDirectory() as temp_dir:
            framework_root = Path(temp_dir)
            claude_dir = framework_root / ".claude"
            claude_dir.mkdir()

            subdir = framework_root / "level1" / "level2"
            subdir.mkdir(parents=True)

            result = _search_parent_directories(subdir, max_levels=5)
            assert result == framework_root

    def test_search_parent_directories_max_levels(self):
        """Test parent directory search respects max_levels."""
        from src.amplihack.utils.uvx_detection import _search_parent_directories

        with tempfile.TemporaryDirectory() as temp_dir:
            framework_root = Path(temp_dir)
            claude_dir = framework_root / ".claude"
            claude_dir.mkdir()

            # Create deep nesting
            deep_subdir = framework_root / "l1" / "l2" / "l3" / "l4" / "l5"
            deep_subdir.mkdir(parents=True)

            # Search with limited levels - should not find framework
            result = _search_parent_directories(deep_subdir, max_levels=2)
            assert result is None

            # Search with sufficient levels - should find framework
            result = _search_parent_directories(deep_subdir, max_levels=10)
            assert result == framework_root

    def test_search_parent_directories_not_found(self):
        """Test parent directory search when no framework found."""
        from src.amplihack.utils.uvx_detection import _search_parent_directories

        with tempfile.TemporaryDirectory() as temp_dir:
            subdir = Path(temp_dir) / "no" / "framework" / "here"
            subdir.mkdir(parents=True)

            result = _search_parent_directories(subdir)
            assert result is None
