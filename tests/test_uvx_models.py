"""Tests for UVX data models and immutable state management."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.amplihack.utils.uvx_models import (
    FrameworkLocation,
    PathResolutionResult,
    PathResolutionStrategy,
    StagingOperation,
    StagingResult,
    UVXConfiguration,
    UVXDetectionResult,
    UVXDetectionState,
    UVXEnvironmentInfo,
    UVXSessionState,
)


class TestUVXEnvironmentInfo:
    """Tests for UVXEnvironmentInfo immutable data structure."""

    def test_from_current_environment(self):
        """Test creating UVXEnvironmentInfo from current environment."""
        with patch.dict(
            os.environ, {"UV_PYTHON": "/path/to/uv/python", "AMPLIHACK_ROOT": "/path/to/framework"}
        ), patch("sys.path", ["/path1", "/path2"]):
            with patch("pathlib.Path.cwd", return_value=Path("/working")):
                env_info = UVXEnvironmentInfo.from_current_environment()

                assert env_info.uv_python_path == "/path/to/uv/python"
                assert env_info.amplihack_root == "/path/to/framework"
                assert env_info.sys_path_entries == ["/path1", "/path2"]
                assert env_info.working_directory == Path("/working")

    def test_from_current_environment_minimal(self):
        """Test creating UVXEnvironmentInfo with minimal environment."""
        with patch.dict(os.environ, {}, clear=True), patch("sys.path", []):
            env_info = UVXEnvironmentInfo.from_current_environment()

            assert env_info.uv_python_path is None
            assert env_info.amplihack_root is None
            assert env_info.sys_path_entries == []


class TestUVXDetectionState:
    """Tests for UVXDetectionState immutable data structure."""

    def test_immutable_creation(self):
        """Test creating immutable UVXDetectionState."""
        env_info = UVXEnvironmentInfo(uv_python_path="/test")
        state = UVXDetectionState(
            result=UVXDetectionResult.UVX_DEPLOYMENT,
            environment=env_info,
            detection_reasons=["UV_PYTHON found"],
        )

        assert state.result == UVXDetectionResult.UVX_DEPLOYMENT
        assert state.environment.uv_python_path == "/test"
        assert state.detection_reasons == ["UV_PYTHON found"]

    def test_is_uvx_deployment_property(self):
        """Test is_uvx_deployment property."""
        env_info = UVXEnvironmentInfo()

        uvx_state = UVXDetectionState(
            result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
        )
        local_state = UVXDetectionState(
            result=UVXDetectionResult.LOCAL_DEPLOYMENT, environment=env_info
        )

        assert uvx_state.is_uvx_deployment is True
        assert uvx_state.is_local_deployment is False
        assert local_state.is_uvx_deployment is False
        assert local_state.is_local_deployment is True

    def test_is_detection_successful_property(self):
        """Test is_detection_successful property."""
        env_info = UVXEnvironmentInfo()

        successful_states = [
            UVXDetectionState(result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info),
            UVXDetectionState(result=UVXDetectionResult.LOCAL_DEPLOYMENT, environment=env_info),
        ]

        failed_states = [
            UVXDetectionState(result=UVXDetectionResult.DETECTION_FAILED, environment=env_info),
            UVXDetectionState(result=UVXDetectionResult.AMBIGUOUS_STATE, environment=env_info),
        ]

        for state in successful_states:
            assert state.is_detection_successful is True

        for state in failed_states:
            assert state.is_detection_successful is False

    def test_with_additional_reason(self):
        """Test immutable addition of detection reason."""
        env_info = UVXEnvironmentInfo()
        original_state = UVXDetectionState(
            result=UVXDetectionResult.UVX_DEPLOYMENT,
            environment=env_info,
            detection_reasons=["Original reason"],
        )

        new_state = original_state.with_additional_reason("Additional reason")

        # Original state unchanged
        assert original_state.detection_reasons == ["Original reason"]
        # New state has both reasons
        assert new_state.detection_reasons == ["Original reason", "Additional reason"]
        # Other properties preserved
        assert new_state.result == UVXDetectionResult.UVX_DEPLOYMENT
        assert new_state.environment == env_info


class TestFrameworkLocation:
    """Tests for FrameworkLocation immutable data structure."""

    def test_valid_framework_location(self):
        """Test valid framework location with real directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            framework_root = Path(temp_dir)
            claude_dir = framework_root / ".claude"
            claude_dir.mkdir()

            location = FrameworkLocation(
                root_path=framework_root, strategy=PathResolutionStrategy.WORKING_DIRECTORY
            )

            assert location.is_valid is True
            assert location.claude_dir == claude_dir
            assert location.has_claude_dir is True
            assert len(location.validation_errors) == 0

    def test_invalid_framework_location(self):
        """Test invalid framework location."""
        non_existent = Path("/non/existent/path")
        location = FrameworkLocation(
            root_path=non_existent, strategy=PathResolutionStrategy.WORKING_DIRECTORY
        )

        assert location.is_valid is False
        assert location.has_claude_dir is False

    def test_validate_method(self):
        """Test validation method returns new instance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            framework_root = Path(temp_dir)
            # Don't create .claude directory

            original_location = FrameworkLocation(
                root_path=framework_root, strategy=PathResolutionStrategy.WORKING_DIRECTORY
            )

            validated_location = original_location.validate()

            # Original unchanged
            assert len(original_location.validation_errors) == 0
            # Validated has errors
            assert len(validated_location.validation_errors) > 0
            assert "Missing .claude directory" in str(validated_location.validation_errors)

    def test_resolve_file_valid(self):
        """Test resolving valid file within framework."""
        with tempfile.TemporaryDirectory() as temp_dir:
            framework_root = Path(temp_dir)
            claude_dir = framework_root / ".claude"
            claude_dir.mkdir()

            test_file = claude_dir / "test.md"
            test_file.write_text("test content")

            location = FrameworkLocation(
                root_path=framework_root, strategy=PathResolutionStrategy.WORKING_DIRECTORY
            ).validate()

            resolved = location.resolve_file(".claude/test.md")
            # Use resolve() to handle symlinks consistently on macOS
            assert resolved.resolve() == test_file.resolve()
            assert resolved.exists()

    def test_resolve_file_path_traversal_attack(self):
        """Test that path traversal attacks are blocked."""
        with tempfile.TemporaryDirectory() as temp_dir:
            framework_root = Path(temp_dir)
            claude_dir = framework_root / ".claude"
            claude_dir.mkdir()

            location = FrameworkLocation(
                root_path=framework_root, strategy=PathResolutionStrategy.WORKING_DIRECTORY
            ).validate()

            # Test various path traversal attempts
            attack_paths = [
                "../../../etc/passwd",
                "..\\..\\..\\windows\\system32\\config",
                "/etc/passwd",
                "\\windows\\system32",
                ".claude/../../../etc/passwd",
                ".claude\0/test.md",  # Null byte injection
            ]

            for attack_path in attack_paths:
                resolved = location.resolve_file(attack_path)
                assert resolved is None, f"Path traversal attack should fail: {attack_path}"

    def test_resolve_file_non_existent(self):
        """Test resolving non-existent file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            framework_root = Path(temp_dir)
            claude_dir = framework_root / ".claude"
            claude_dir.mkdir()

            location = FrameworkLocation(
                root_path=framework_root, strategy=PathResolutionStrategy.WORKING_DIRECTORY
            ).validate()

            resolved = location.resolve_file(".claude/non_existent.md")
            assert resolved is None


class TestPathResolutionResult:
    """Tests for PathResolutionResult data structure."""

    def test_successful_resolution(self):
        """Test successful path resolution result."""
        with tempfile.TemporaryDirectory() as temp_dir:
            framework_root = Path(temp_dir)
            claude_dir = framework_root / ".claude"
            claude_dir.mkdir()

            location = FrameworkLocation(
                root_path=framework_root, strategy=PathResolutionStrategy.WORKING_DIRECTORY
            ).validate()

            result = PathResolutionResult(location=location)

            assert result.is_successful is True
            assert result.requires_staging is False

    def test_staging_required_resolution(self):
        """Test resolution that requires staging."""
        location = FrameworkLocation(
            root_path=Path("/working"), strategy=PathResolutionStrategy.STAGING_REQUIRED
        )

        result = PathResolutionResult(location=location)

        assert result.requires_staging is True

    def test_with_attempt_immutable(self):
        """Test immutable addition of resolution attempts."""
        original_result = PathResolutionResult(location=None)

        new_result = original_result.with_attempt(
            PathResolutionStrategy.WORKING_DIRECTORY,
            Path("/test"),
            success=False,
            notes="Test attempt",
        )

        # Original unchanged
        assert len(original_result.attempts) == 0
        # New result has attempt
        assert len(new_result.attempts) == 1
        assert new_result.attempts[0]["strategy"] == "WORKING_DIRECTORY"
        assert new_result.attempts[0]["path"] == Path("/test")
        assert new_result.attempts[0]["success"] is False
        assert new_result.attempts[0]["notes"] == "Test attempt"


class TestUVXConfiguration:
    """Tests for UVXConfiguration data structure."""

    def test_default_configuration(self):
        """Test default configuration values."""
        config = UVXConfiguration()

        assert config.uv_python_env_var == "UV_PYTHON"
        assert config.amplihack_root_env_var == "AMPLIHACK_ROOT"
        assert config.debug_env_var == "AMPLIHACK_DEBUG"
        assert config.max_parent_traversal == 10
        assert config.validate_framework_structure is True
        assert config.allow_staging is True
        assert config.overwrite_existing is False

    def test_debug_enabled_from_env(self):
        """Test debug enabled detection from environment."""
        config = UVXConfiguration()

        debug_values = ["true", "1", "yes", "TRUE", "YES"]
        non_debug_values = ["false", "0", "no", "", "maybe"]

        for debug_value in debug_values:
            with patch.dict(os.environ, {"AMPLIHACK_DEBUG": debug_value}):
                assert config.is_debug_enabled is True

        for non_debug_value in non_debug_values:
            with patch.dict(os.environ, {"AMPLIHACK_DEBUG": non_debug_value}):
                assert config.is_debug_enabled is False

    def test_with_debug_immutable(self):
        """Test immutable debug setting change."""
        original_config = UVXConfiguration()
        new_config = original_config.with_debug(True)

        # Original unchanged
        assert original_config.debug_enabled is None
        # New config has explicit debug setting
        assert new_config.debug_enabled is True
        assert new_config.is_debug_enabled is True


class TestStagingOperation:
    """Tests for StagingOperation data structure."""

    def test_valid_staging_operation(self):
        """Test valid staging operation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source.txt"
            source_path.write_text("test")

            target_dir = Path(temp_dir) / "target_dir"
            target_dir.mkdir()
            target_path = target_dir / "target.txt"

            operation = StagingOperation(
                source_path=source_path, target_path=target_path, operation_type="file"
            )

            assert operation.is_valid is True

    def test_invalid_staging_operation(self):
        """Test invalid staging operation."""
        operation = StagingOperation(
            source_path=Path("/non/existent/source"),
            target_path=Path("/non/existent/target"),
            operation_type="file",
        )

        assert operation.is_valid is False


class TestStagingResult:
    """Tests for StagingResult mutable data structure."""

    def test_empty_staging_result(self):
        """Test empty staging result."""
        result = StagingResult()

        assert result.is_successful is False
        assert result.total_operations == 0
        assert len(result.successful) == 0
        assert len(result.failed) == 0
        assert len(result.skipped) == 0

    def test_successful_staging_operations(self):
        """Test recording successful staging operations."""
        result = StagingResult()

        operation = StagingOperation(
            source_path=Path("/source"), target_path=Path("/target"), operation_type="file"
        )

        result.add_success(Path("/target"), operation)

        assert result.is_successful is True
        assert result.total_operations == 1
        assert Path("/target") in result.successful
        assert len(result.operations) == 1

    def test_failed_staging_operations(self):
        """Test recording failed staging operations."""
        result = StagingResult()

        result.add_failure(Path("/target"), "Permission denied")

        assert result.is_successful is False
        assert result.total_operations == 1
        assert Path("/target") in result.failed
        assert result.failed[Path("/target")] == "Permission denied"

    def test_mixed_staging_operations(self):
        """Test mixed success/failure/skip operations."""
        result = StagingResult()

        operation = StagingOperation(
            source_path=Path("/source"), target_path=Path("/target1"), operation_type="file"
        )

        result.add_success(Path("/target1"), operation)
        result.add_failure(Path("/target2"), "Error")
        result.add_skipped(Path("/target3"), "Already exists")

        assert result.is_successful is False  # Has failures
        assert result.total_operations == 3
        assert len(result.successful) == 1
        assert len(result.failed) == 1
        assert len(result.skipped) == 1


class TestUVXSessionState:
    """Tests for UVXSessionState mutable session management."""

    def test_empty_session_state(self):
        """Test empty session state."""
        session = UVXSessionState()

        assert session.is_ready is False
        assert session.framework_root is None
        assert session.initialized is False
        assert session.session_id is None

    def test_session_initialization_flow(self):
        """Test complete session initialization flow."""
        session = UVXSessionState()

        # Initialize detection
        env_info = UVXEnvironmentInfo()
        detection_state = UVXDetectionState(
            result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
        )
        session.initialize_detection(detection_state)

        assert session.detection_state == detection_state
        assert session.is_ready is False  # Still need path resolution

        # Set path resolution
        with tempfile.TemporaryDirectory() as temp_dir:
            framework_root = Path(temp_dir)
            claude_dir = framework_root / ".claude"
            claude_dir.mkdir()

            location = FrameworkLocation(
                root_path=framework_root, strategy=PathResolutionStrategy.WORKING_DIRECTORY
            ).validate()

            resolution = PathResolutionResult(location=location)
            session.set_path_resolution(resolution)

            assert session.path_resolution == resolution
            assert session.framework_root == framework_root
            assert session.is_ready is False  # Still need initialization

            # Mark as initialized
            session.mark_initialized("test-session-123")

            assert session.is_ready is True
            assert session.initialized is True
            assert session.session_id == "test-session-123"

    def test_to_debug_dict(self):
        """Test debug dictionary generation."""
        session = UVXSessionState()

        debug_dict = session.to_debug_dict()

        expected_keys = [
            "session_id",
            "initialized",
            "is_ready",
            "detection_result",
            "is_uvx_deployment",
            "framework_root",
            "path_strategy",
            "staging_successful",
            "staging_operations",
            "debug_enabled",
        ]

        for key in expected_keys:
            assert key in debug_dict

        assert debug_dict["initialized"] is False
        assert debug_dict["is_ready"] is False
