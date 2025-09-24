"""Tests for UVX manager module."""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.utils.uvx_models import (
    FrameworkLocation,
    PathResolutionResult,
    PathResolutionStrategy,
    UVXDetectionResult,
    UVXDetectionState,
    UVXEnvironmentInfo,
)
from amplihack.uvx.manager import UVXManager


class TestUVXManagerDetection(unittest.TestCase):
    """Test UVX environment detection."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = UVXManager()

    @patch("amplihack.uvx.manager.detect_uvx_deployment")
    def test_detect_uvx_environment(self, mock_detect):
        """Test UVX detection returns true for UVX deployment."""
        mock_detect.return_value = UVXDetectionState(
            result=UVXDetectionResult.UVX_DEPLOYMENT,
            environment=UVXEnvironmentInfo(),
            detection_reasons=["UV_PYTHON set"],
        )

        self.assertTrue(self.manager.is_uvx_environment())

    @patch("amplihack.uvx.manager.detect_uvx_deployment")
    def test_detect_local_environment(self, mock_detect):
        """Test UVX detection returns false for local deployment."""
        mock_detect.return_value = UVXDetectionState(
            result=UVXDetectionResult.LOCAL_DEPLOYMENT,
            environment=UVXEnvironmentInfo(working_directory=Path("/project")),
            detection_reasons=["Local .claude found"],
        )

        self.assertFalse(self.manager.is_uvx_environment())

    @patch("amplihack.uvx.manager.detect_uvx_deployment")
    def test_detect_failed(self, mock_detect):
        """Test detection when it fails."""
        mock_detect.return_value = UVXDetectionState(
            result=UVXDetectionResult.DETECTION_FAILED,
            environment=UVXEnvironmentInfo(),
            detection_reasons=["No indicators found"],
        )

        self.assertFalse(self.manager.is_uvx_environment())


class TestUVXManagerPathResolution(unittest.TestCase):
    """Test framework path resolution."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = UVXManager()

    @patch("amplihack.uvx.manager.detect_uvx_deployment")
    @patch("amplihack.uvx.manager.resolve_framework_paths")
    def test_get_framework_path_success(self, mock_resolve, mock_detect):
        """Test successful framework path resolution."""
        # Set up mocks
        mock_detect.return_value = UVXDetectionState(
            result=UVXDetectionResult.UVX_DEPLOYMENT,
            environment=UVXEnvironmentInfo(),
            detection_reasons=["UV_PYTHON set"],
        )

        mock_location = Mock(spec=FrameworkLocation)
        mock_location.root_path = Path("/uvx/amplihack")
        mock_location.strategy = PathResolutionStrategy.SYSTEM_PATH_SEARCH

        mock_resolution = Mock(spec=PathResolutionResult)
        mock_resolution.is_successful = True
        mock_resolution.location = mock_location
        mock_resolution.attempts = []

        mock_resolve.return_value = mock_resolution

        # Test
        framework_path = self.manager.get_framework_path()
        self.assertEqual(framework_path, Path("/uvx/amplihack"))

    @patch("amplihack.uvx.manager.detect_uvx_deployment")
    @patch("amplihack.uvx.manager.resolve_framework_paths")
    def test_get_framework_path_local_dev(self, mock_resolve, mock_detect):
        """Test framework path in local development."""
        # Set up mocks for local deployment
        mock_detect.return_value = UVXDetectionState(
            result=UVXDetectionResult.LOCAL_DEPLOYMENT,
            environment=UVXEnvironmentInfo(working_directory=Path("/project")),
            detection_reasons=["Local .claude found"],
        )

        mock_location = Mock(spec=FrameworkLocation)
        mock_location.root_path = Path("/project")
        mock_location.strategy = PathResolutionStrategy.WORKING_DIRECTORY

        mock_resolution = Mock(spec=PathResolutionResult)
        mock_resolution.is_successful = True
        mock_resolution.location = mock_location
        mock_resolution.attempts = []

        mock_resolve.return_value = mock_resolution

        # Test
        framework_path = self.manager.get_framework_path()
        self.assertEqual(framework_path, Path("/project"))

    @patch("amplihack.uvx.manager.detect_uvx_deployment")
    @patch("amplihack.uvx.manager.resolve_framework_paths")
    def test_get_framework_path_failed(self, mock_resolve, mock_detect):
        """Test framework path when resolution fails."""
        mock_detect.return_value = UVXDetectionState(
            result=UVXDetectionResult.DETECTION_FAILED,
            environment=UVXEnvironmentInfo(),
            detection_reasons=["No indicators found"],
        )

        mock_resolution = Mock(spec=PathResolutionResult)
        mock_resolution.is_successful = False
        mock_resolution.location = None
        mock_resolution.attempts = []

        mock_resolve.return_value = mock_resolution

        # Test
        framework_path = self.manager.get_framework_path()
        self.assertIsNone(framework_path)


class TestUVXManagerAddDir(unittest.TestCase):
    """Test --add-dir argument generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = UVXManager()

    @patch.object(UVXManager, "is_uvx_environment")
    @patch.object(UVXManager, "get_framework_path")
    @patch.object(UVXManager, "validate_path_security")
    def test_should_use_add_dir_in_uvx(self, mock_validate, mock_get_path, mock_is_uvx):
        """Test that --add-dir is used in UVX environment."""
        mock_is_uvx.return_value = True
        mock_get_path.return_value = Path("/uvx/amplihack")
        mock_validate.return_value = True

        self.assertTrue(self.manager.should_use_add_dir())

    @patch.object(UVXManager, "is_uvx_environment")
    def test_should_not_use_add_dir_in_local(self, mock_is_uvx):
        """Test that --add-dir is not used in local development."""
        mock_is_uvx.return_value = False
        self.assertFalse(self.manager.should_use_add_dir())

    def test_force_staging_prevents_add_dir(self):
        """Test that force_staging prevents --add-dir usage."""
        manager = UVXManager(force_staging=True)
        self.assertFalse(manager.should_use_add_dir())

    @patch.object(UVXManager, "should_use_add_dir")
    @patch.object(UVXManager, "get_framework_path")
    def test_get_add_dir_args(self, mock_get_path, mock_should_use):
        """Test generation of --add-dir arguments."""
        mock_should_use.return_value = True
        mock_get_path.return_value = Path("/uvx/amplihack")

        args = self.manager.get_add_dir_args()
        self.assertEqual(args, ["--add-dir", "/uvx/amplihack"])

    @patch.object(UVXManager, "should_use_add_dir")
    def test_get_add_dir_args_when_disabled(self, mock_should_use):
        """Test that empty list is returned when --add-dir shouldn't be used."""
        mock_should_use.return_value = False
        args = self.manager.get_add_dir_args()
        self.assertEqual(args, [])

    @patch.object(UVXManager, "should_use_add_dir")
    @patch.object(UVXManager, "get_framework_path")
    def test_get_add_dir_args_no_framework_path(self, mock_get_path, mock_should_use):
        """Test that empty list is returned when framework path can't be resolved."""
        mock_should_use.return_value = True
        mock_get_path.return_value = None

        args = self.manager.get_add_dir_args()
        self.assertEqual(args, [])


class TestUVXManagerSecurity(unittest.TestCase):
    """Test security validations in UVX manager."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = UVXManager()

    def test_validate_path_security_valid(self):
        """Test validation of safe paths."""
        valid_paths = [
            Path("/home/user/project"),
            Path("/uvx/installations/amplihack"),
            Path("/tmp/staging"),
        ]

        for path in valid_paths:
            with self.subTest(path=path):
                self.assertTrue(self.manager.validate_path_security(path))

    def test_validate_path_security_traversal(self):
        """Test rejection of path traversal attempts."""
        unsafe_paths = [
            Path("../../../etc/passwd"),
            Path("/home/user/../../../etc"),
            Path("/tmp/../../../sensitive"),
        ]

        for path in unsafe_paths:
            with self.subTest(path=path):
                # Paths with traversal patterns should be rejected
                self.assertFalse(self.manager.validate_path_security(path))

    def test_validate_path_security_system_dirs(self):
        """Test rejection of system directories."""
        system_paths = [
            Path("/etc/passwd"),
            Path("/root/.ssh"),
            Path("/System/Library"),
        ]

        for path in system_paths:
            with self.subTest(path=path):
                self.assertFalse(self.manager.validate_path_security(path))

    def test_validate_path_security_null(self):
        """Test rejection of None path."""
        self.assertFalse(self.manager.validate_path_security(None))


class TestUVXManagerIntegration(unittest.TestCase):
    """Test UVX manager integration with launcher."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = UVXManager()

    @patch.object(UVXManager, "get_add_dir_args")
    def test_enhance_claude_command_with_add_dir(self, mock_get_args):
        """Test enhancing Claude command with --add-dir."""
        mock_get_args.return_value = ["--add-dir", "/uvx/amplihack"]

        base_cmd = ["claude", "--dangerously-skip-permissions"]
        enhanced_cmd = self.manager.enhance_claude_command(base_cmd)

        expected = ["claude", "--dangerously-skip-permissions", "--add-dir", "/uvx/amplihack"]
        self.assertEqual(enhanced_cmd, expected)

    @patch.object(UVXManager, "get_add_dir_args")
    def test_enhance_claude_command_no_add_dir(self, mock_get_args):
        """Test command is unchanged when no --add-dir needed."""
        mock_get_args.return_value = []

        base_cmd = ["claude", "--dangerously-skip-permissions"]
        enhanced_cmd = self.manager.enhance_claude_command(base_cmd)

        self.assertEqual(enhanced_cmd, base_cmd)

    @patch.object(UVXManager, "get_framework_path")
    def test_get_environment_variables(self, mock_get_path):
        """Test environment variable generation for session hook."""
        mock_get_path.return_value = Path("/uvx/amplihack")

        env_vars = self.manager.get_environment_variables()
        self.assertEqual(env_vars.get("AMPLIHACK_PROJECT_ROOT"), "/uvx/amplihack")

    @patch.object(UVXManager, "get_framework_path")
    def test_get_environment_variables_no_path(self, mock_get_path):
        """Test environment variables when no framework path."""
        mock_get_path.return_value = None

        env_vars = self.manager.get_environment_variables()
        self.assertEqual(env_vars, {})


class TestUVXManagerStaging(unittest.TestCase):
    """Test fallback to staging approach."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = UVXManager()

    @patch("amplihack.uvx.manager.detect_uvx_deployment")
    @patch("amplihack.uvx.manager.resolve_framework_paths")
    def test_should_use_staging_when_required(self, mock_resolve, mock_detect):
        """Test detection of when staging is required."""
        mock_detection = Mock(spec=UVXDetectionState)
        mock_detection.result = UVXDetectionResult.UVX_DEPLOYMENT
        mock_detection.detection_reasons = ["Test reason"]
        mock_detection.is_uvx_deployment = True
        mock_detect.return_value = mock_detection

        mock_location = Mock(spec=FrameworkLocation)
        mock_location.root_path = Path("/tmp/staging")
        mock_location.strategy = PathResolutionStrategy.STAGING_REQUIRED

        mock_resolution = Mock(spec=PathResolutionResult)
        mock_resolution.requires_staging = True
        mock_resolution.is_successful = False
        mock_resolution.location = mock_location
        mock_resolution.attempts = []

        mock_resolve.return_value = mock_resolution

        # Force path resolution to occur
        self.manager._ensure_path_resolution()
        self.assertTrue(self.manager.should_use_staging())

    @patch("amplihack.uvx.manager.detect_uvx_deployment")
    @patch("amplihack.uvx.manager.resolve_framework_paths")
    def test_should_not_use_staging_for_direct_resolution(self, mock_resolve, mock_detect):
        """Test that staging is not used when direct resolution works."""
        mock_detection = Mock(spec=UVXDetectionState)
        mock_detection.result = UVXDetectionResult.UVX_DEPLOYMENT
        mock_detection.detection_reasons = ["Test reason"]
        mock_detection.is_uvx_deployment = True
        mock_detect.return_value = mock_detection

        mock_location = Mock(spec=FrameworkLocation)
        mock_location.root_path = Path("/uvx/amplihack")
        mock_location.strategy = PathResolutionStrategy.SYSTEM_PATH_SEARCH

        mock_resolution = Mock(spec=PathResolutionResult)
        mock_resolution.requires_staging = False
        mock_resolution.is_successful = True
        mock_resolution.location = mock_location
        mock_resolution.attempts = []

        mock_resolve.return_value = mock_resolution

        # Force path resolution to occur
        self.manager._ensure_path_resolution()
        self.assertFalse(self.manager.should_use_staging())


if __name__ == "__main__":
    unittest.main()
