"""Tests for UVX staging operations using clean data models."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.amplihack.utils.uvx_models import (
    FrameworkLocation,
    PathResolutionStrategy,
    UVXConfiguration,
    UVXDetectionResult,
    UVXDetectionState,
    UVXEnvironmentInfo,
    UVXSessionState,
)
from src.amplihack.utils.uvx_staging_v2 import (
    UVXStager,
    create_uvx_session,
    stage_uvx_framework,
)


class TestUVXStager:
    """Tests for UVXStager class with clean data models."""

    def test_stager_initialization(self):
        """Test UVXStager initialization with configuration."""
        config = UVXConfiguration(debug_enabled=True)
        stager = UVXStager(config)

        assert stager.config == config
        assert stager._debug_enabled is True

    def test_stager_initialization_default(self):
        """Test UVXStager initialization with default configuration."""
        stager = UVXStager()

        assert isinstance(stager.config, UVXConfiguration)
        assert stager._debug_enabled == stager.config.is_debug_enabled

    def test_debug_logging_enabled(self):
        """Test debug logging when enabled."""
        config = UVXConfiguration(debug_enabled=True)
        stager = UVXStager(config)

        with patch("sys.stderr") as mock_stderr:
            stager._debug_log("Test message")
            # Should have written to stderr
            assert mock_stderr.write.called

    def test_debug_logging_disabled(self):
        """Test debug logging when disabled."""
        config = UVXConfiguration(debug_enabled=False)
        stager = UVXStager(config)

        with patch("sys.stderr") as mock_stderr:
            stager._debug_log("Test message")
            # Should not have written to stderr
            assert not mock_stderr.write.called

    def test_stage_framework_files_not_uvx_deployment(self):
        """Test staging when not in UVX deployment mode."""
        stager = UVXStager()
        session_state = UVXSessionState()

        # Mock detection to return local deployment
        env_info = UVXEnvironmentInfo()
        detection_state = UVXDetectionState(
            result=UVXDetectionResult.LOCAL_DEPLOYMENT, environment=env_info
        )
        session_state.initialize_detection(detection_state)

        result = stager.stage_framework_files(session_state)

        assert result.is_successful is False
        assert result.total_operations == 0

    def test_stage_framework_files_path_resolution_failed(self):
        """Test staging when path resolution fails."""
        stager = UVXStager()

        # Create session with UVX deployment but invalid paths
        with patch("src.amplihack.utils.uvx_staging_v2.detect_uvx_deployment") as mock_detect:
            with patch(
                "src.amplihack.utils.uvx_staging_v2.resolve_framework_paths"
            ) as mock_resolve:
                env_info = UVXEnvironmentInfo()
                detection_state = UVXDetectionState(
                    result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
                )
                mock_detect.return_value = detection_state

                # Mock failed path resolution
                from src.amplihack.utils.uvx_models import PathResolutionResult

                failed_resolution = PathResolutionResult(location=None)
                mock_resolve.return_value = failed_resolution

                result = stager.stage_framework_files()

                assert result.is_successful is False

    def test_stage_framework_files_staging_required_success(self):
        """Test successful staging when staging is required."""
        config = UVXConfiguration(debug_enabled=True)
        stager = UVXStager(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create source framework structure
            source_root = Path(temp_dir) / "source"
            source_root.mkdir()
            claude_dir = source_root / ".claude"
            claude_dir.mkdir()
            context_dir = claude_dir / "context"
            context_dir.mkdir()
            (context_dir / "test.md").write_text("test content")
            (source_root / "CLAUDE.md").write_text("# CLAUDE.md")

            # Create target directory
            target_root = Path(temp_dir) / "target"
            target_root.mkdir()

            # Create session state
            env_info = UVXEnvironmentInfo(
                sys_path_entries=[str(temp_dir)],  # Will find amplihack under temp_dir
                working_directory=target_root,
            )
            detection_state = UVXDetectionState(
                result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
            )

            # Create staging-required location
            location = FrameworkLocation(
                root_path=target_root, strategy=PathResolutionStrategy.STAGING_REQUIRED
            )
            from src.amplihack.utils.uvx_models import PathResolutionResult

            resolution = PathResolutionResult(location=location)

            session_state = UVXSessionState(configuration=config)
            session_state.initialize_detection(detection_state)
            session_state.set_path_resolution(resolution)

            # Mock sys.path search to find our source
            # Rename source to amplihack for sys.path search
            amplihack_source = Path(temp_dir) / "amplihack"
            source_root.rename(amplihack_source)

            result = stager.stage_framework_files(session_state)

            assert result.is_successful is True
            assert len(result.successful) > 0
            assert (target_root / ".claude").exists()
            assert (target_root / "CLAUDE.md").exists()

    def test_stage_framework_files_existing_files_no_overwrite(self):
        """Test staging behavior with existing files and overwrite disabled."""
        config = UVXConfiguration(overwrite_existing=False)
        stager = UVXStager(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create source
            amplihack_source = Path(temp_dir) / "amplihack"
            amplihack_source.mkdir()
            claude_dir = amplihack_source / ".claude"
            claude_dir.mkdir()
            (amplihack_source / "CLAUDE.md").write_text("source content")

            # Create target with existing files
            target_root = Path(temp_dir) / "target"
            target_root.mkdir()
            (target_root / "CLAUDE.md").write_text("existing content")

            # Setup session
            env_info = UVXEnvironmentInfo(
                sys_path_entries=[str(temp_dir)], working_directory=target_root
            )
            detection_state = UVXDetectionState(
                result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
            )
            location = FrameworkLocation(
                root_path=target_root, strategy=PathResolutionStrategy.STAGING_REQUIRED
            )
            from src.amplihack.utils.uvx_models import PathResolutionResult

            resolution = PathResolutionResult(location=location)

            session_state = UVXSessionState(configuration=config)
            session_state.initialize_detection(detection_state)
            session_state.set_path_resolution(resolution)

            result = stager.stage_framework_files(session_state)

            # Should have skipped existing file
            assert (target_root / "CLAUDE.md").read_text() == "existing content"
            assert len(result.skipped) > 0

    def test_stage_framework_files_with_backup(self):
        """Test staging with backup creation enabled."""
        config = UVXConfiguration(overwrite_existing=True, create_backup=True)
        stager = UVXStager(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create source
            amplihack_source = Path(temp_dir) / "amplihack"
            amplihack_source.mkdir()
            claude_dir = amplihack_source / ".claude"
            claude_dir.mkdir()
            (amplihack_source / "CLAUDE.md").write_text("new content")

            # Create target with existing file
            target_root = Path(temp_dir) / "target"
            target_root.mkdir()
            existing_file = target_root / "CLAUDE.md"
            existing_file.write_text("original content")

            # Setup session
            env_info = UVXEnvironmentInfo(
                sys_path_entries=[str(temp_dir)], working_directory=target_root
            )
            detection_state = UVXDetectionState(
                result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
            )
            location = FrameworkLocation(
                root_path=target_root, strategy=PathResolutionStrategy.STAGING_REQUIRED
            )
            from src.amplihack.utils.uvx_models import PathResolutionResult

            resolution = PathResolutionResult(location=location)

            session_state = UVXSessionState(configuration=config)
            session_state.initialize_detection(detection_state)
            session_state.set_path_resolution(resolution)

            stager.stage_framework_files(session_state)

            # Should have created backup
            backup_file = target_root / "CLAUDE.md.backup"
            assert backup_file.exists()
            assert backup_file.read_text() == "original content"
            # And updated original
            assert existing_file.read_text() == "new content"

    def test_stage_framework_files_permission_error(self):
        """Test staging handles permission errors gracefully."""
        stager = UVXStager()

        with tempfile.TemporaryDirectory() as temp_dir:
            amplihack_source = Path(temp_dir) / "amplihack"
            amplihack_source.mkdir()
            claude_dir = amplihack_source / ".claude"
            claude_dir.mkdir()
            (amplihack_source / "test.txt").write_text("test")

            target_root = Path(temp_dir) / "target"
            target_root.mkdir()

            # Mock permission error during copy
            with patch("shutil.copy2", side_effect=PermissionError("Access denied")):
                env_info = UVXEnvironmentInfo(
                    sys_path_entries=[str(temp_dir)], working_directory=target_root
                )
                detection_state = UVXDetectionState(
                    result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
                )
                location = FrameworkLocation(
                    root_path=target_root, strategy=PathResolutionStrategy.STAGING_REQUIRED
                )
                from src.amplihack.utils.uvx_models import PathResolutionResult

                resolution = PathResolutionResult(location=location)

                session_state = UVXSessionState()
                session_state.initialize_detection(detection_state)
                session_state.set_path_resolution(resolution)

                result = stager.stage_framework_files(session_state)

                assert result.is_successful is False
                assert len(result.failed) > 0
                assert "Permission denied" in str(result.failed)

    def test_cleanup_staged_files_success(self):
        """Test successful cleanup of staged files."""
        config = UVXConfiguration(cleanup_on_exit=True)
        stager = UVXStager(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some test files
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("test")
            test_dir = Path(temp_dir) / "test_dir"
            test_dir.mkdir()

            # Create staging result with successful operations
            from src.amplihack.utils.uvx_models import StagingResult

            result = StagingResult()
            result.successful.add(test_file)
            result.successful.add(test_dir)

            cleaned_count = stager.cleanup_staged_files(result)

            assert cleaned_count == 2
            assert not test_file.exists()
            assert not test_dir.exists()

    def test_cleanup_staged_files_disabled(self):
        """Test cleanup when disabled in configuration."""
        config = UVXConfiguration(cleanup_on_exit=False)
        stager = UVXStager(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("test")

            from src.amplihack.utils.uvx_models import StagingResult

            result = StagingResult()
            result.successful.add(test_file)

            cleaned_count = stager.cleanup_staged_files(result)

            assert cleaned_count == 0
            assert test_file.exists()  # Should not be cleaned up

    def test_cleanup_staged_files_handles_missing_files(self):
        """Test cleanup handles missing files gracefully."""
        config = UVXConfiguration(cleanup_on_exit=True)
        stager = UVXStager(config)

        # Create staging result with non-existent files
        from src.amplihack.utils.uvx_models import StagingResult

        result = StagingResult()
        result.successful.add(Path("/non/existent/file"))
        result.successful.add(Path("/non/existent/dir"))

        # Should not raise exception
        cleaned_count = stager.cleanup_staged_files(result)
        assert cleaned_count == 0


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_stage_uvx_framework_default_stager(self):
        """Test stage_uvx_framework with default stager."""
        with patch("src.amplihack.utils.uvx_staging_v2._default_stager") as mock_stager:
            mock_result = Mock()
            mock_result.is_successful = True
            mock_stager.stage_framework_files.return_value = mock_result

            result = stage_uvx_framework()

            assert result is True
            mock_stager.stage_framework_files.assert_called_once()

    def test_stage_uvx_framework_custom_config(self):
        """Test stage_uvx_framework with custom configuration."""
        config = UVXConfiguration(debug_enabled=True)

        with patch("src.amplihack.utils.uvx_staging_v2.UVXStager") as mock_stager_class:
            mock_stager = Mock()
            mock_result = Mock()
            mock_result.is_successful = False
            mock_stager.stage_framework_files.return_value = mock_result
            mock_stager_class.return_value = mock_stager

            result = stage_uvx_framework(config)

            assert result is False
            mock_stager_class.assert_called_once_with(config)
            mock_stager.stage_framework_files.assert_called_once()

    def test_create_uvx_session_success(self):
        """Test successful creation of UVX session."""
        with tempfile.TemporaryDirectory() as temp_dir:
            working_dir = Path(temp_dir)
            claude_dir = working_dir / ".claude"
            claude_dir.mkdir()

            with patch("src.amplihack.utils.uvx_staging_v2.detect_uvx_deployment") as mock_detect:
                with patch(
                    "src.amplihack.utils.uvx_staging_v2.resolve_framework_paths"
                ) as mock_resolve:
                    # Mock detection
                    env_info = UVXEnvironmentInfo(working_directory=working_dir)
                    detection_state = UVXDetectionState(
                        result=UVXDetectionResult.LOCAL_DEPLOYMENT, environment=env_info
                    )
                    mock_detect.return_value = detection_state

                    # Mock resolution
                    location = FrameworkLocation(
                        root_path=working_dir, strategy=PathResolutionStrategy.WORKING_DIRECTORY
                    ).validate()
                    from src.amplihack.utils.uvx_models import PathResolutionResult

                    resolution = PathResolutionResult(location=location)
                    mock_resolve.return_value = resolution

                    session = create_uvx_session()

                    assert session.is_ready is True
                    assert session.initialized is True
                    assert session.session_id is not None
                    assert session.framework_root == working_dir

    def test_create_uvx_session_with_staging(self):
        """Test creating UVX session that requires staging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            working_dir = Path(temp_dir)

            # Create amplihack source for staging
            amplihack_source = Path(temp_dir) / "amplihack"
            amplihack_source.mkdir()
            claude_dir = amplihack_source / ".claude"
            claude_dir.mkdir()

            with patch("src.amplihack.utils.uvx_staging_v2.detect_uvx_deployment") as mock_detect:
                with patch(
                    "src.amplihack.utils.uvx_staging_v2.resolve_framework_paths"
                ) as mock_resolve:
                    # Mock UVX deployment detection
                    env_info = UVXEnvironmentInfo(
                        sys_path_entries=[str(temp_dir)], working_directory=working_dir
                    )
                    detection_state = UVXDetectionState(
                        result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
                    )
                    mock_detect.return_value = detection_state

                    # Mock resolution requiring staging
                    location = FrameworkLocation(
                        root_path=working_dir, strategy=PathResolutionStrategy.STAGING_REQUIRED
                    )
                    from src.amplihack.utils.uvx_models import PathResolutionResult

                    resolution = PathResolutionResult(location=location)
                    mock_resolve.return_value = resolution

                    session = create_uvx_session()

                    assert session.detection_state.is_uvx_deployment is True
                    assert session.path_resolution.requires_staging is True
                    assert session.staging_result is not None
                    assert session.initialized is True

    def test_create_uvx_session_detection_failed(self):
        """Test creating UVX session when detection fails."""
        with patch("src.amplihack.utils.uvx_staging_v2.detect_uvx_deployment") as mock_detect:
            # Mock failed detection
            env_info = UVXEnvironmentInfo()
            detection_state = UVXDetectionState(
                result=UVXDetectionResult.DETECTION_FAILED, environment=env_info
            )
            mock_detect.return_value = detection_state

            session = create_uvx_session()

            assert session.is_ready is False  # Detection failed
            assert session.initialized is True  # Still marked as initialized
            assert session.detection_state.is_detection_successful is False
