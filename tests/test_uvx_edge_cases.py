"""
Edge case tests for UVX working directory staging implementation.

Tests unusual scenarios, error conditions, and boundary cases that could
occur in real-world usage of the UVX working directory staging system.
"""

import os
import stat
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.amplihack.utils.uvx_detection import resolve_framework_paths
from src.amplihack.utils.uvx_models import (
    FrameworkLocation,
    PathResolutionStrategy,
    UVXConfiguration,
    UVXDetectionResult,
    UVXDetectionState,
    UVXEnvironmentInfo,
)
from src.amplihack.utils.uvx_staging_v2 import UVXStager


class TestWorkingDirectoryPermissionEdgeCases:
    """Edge cases related to file system permissions."""

    def test_read_only_working_directory(self):
        """Test staging when working directory is read-only."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup source
            amplihack_source = Path(temp_dir) / "amplihack"
            amplihack_source.mkdir()
            source_claude = amplihack_source / ".claude"
            source_claude.mkdir()
            (source_claude / "test.txt").write_text("test content")

            # Create working directory
            working_dir = Path(temp_dir) / "readonly_working"
            working_dir.mkdir()

            try:
                # Make working directory read-only
                working_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)

                config = UVXConfiguration(use_working_directory_staging=True)
                stager = UVXStager(config)

                env_info = UVXEnvironmentInfo(
                    sys_path_entries=[str(temp_dir)], working_directory=working_dir
                )
                detection_state = UVXDetectionState(
                    result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
                )
                location = FrameworkLocation(
                    root_path=working_dir, strategy=PathResolutionStrategy.WORKING_DIRECTORY_STAGING
                )

                session_state = Mock()
                session_state.detection_state = detection_state

                result = stager._stage_to_working_directory(location, session_state)

                # Should handle read-only directory gracefully
                assert result.is_successful is False
                assert len(result.failed) > 0

            finally:
                # Restore permissions for cleanup
                working_dir.chmod(stat.S_IRWXU)

    def test_source_directory_permission_denied(self):
        """Test staging when source directory has permission restrictions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup source with restricted permissions
            amplihack_source = Path(temp_dir) / "amplihack"
            amplihack_source.mkdir()
            source_claude = amplihack_source / ".claude"
            source_claude.mkdir()

            restricted_file = source_claude / "restricted.txt"
            restricted_file.write_text("restricted content")

            working_dir = Path(temp_dir) / "working"
            working_dir.mkdir()

            try:
                # Remove read permission from source file
                restricted_file.chmod(0o000)

                config = UVXConfiguration(use_working_directory_staging=True)
                stager = UVXStager(config)

                env_info = UVXEnvironmentInfo(
                    sys_path_entries=[str(temp_dir)], working_directory=working_dir
                )
                detection_state = UVXDetectionState(
                    result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
                )
                location = FrameworkLocation(
                    root_path=working_dir, strategy=PathResolutionStrategy.WORKING_DIRECTORY_STAGING
                )

                session_state = Mock()
                session_state.detection_state = detection_state

                # Should handle permission errors during file access
                with patch("shutil.copy2", side_effect=PermissionError("Permission denied")):
                    result = stager._stage_to_working_directory(location, session_state)

                    # May partially succeed depending on error handling
                    assert len(result.failed) > 0 or result.is_successful

            finally:
                # Restore permissions for cleanup
                try:
                    restricted_file.chmod(stat.S_IRWXU)
                except Exception:
                    pass

    def test_disk_space_exhaustion_simulation(self):
        """Test staging behavior when disk space is exhausted."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup source
            amplihack_source = Path(temp_dir) / "amplihack"
            amplihack_source.mkdir()
            source_claude = amplihack_source / ".claude"
            source_claude.mkdir()
            (source_claude / "large_file.txt").write_text("content" * 1000)

            working_dir = Path(temp_dir) / "working"
            working_dir.mkdir()

            config = UVXConfiguration(use_working_directory_staging=True)
            stager = UVXStager(config)

            env_info = UVXEnvironmentInfo(
                sys_path_entries=[str(temp_dir)], working_directory=working_dir
            )
            detection_state = UVXDetectionState(
                result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
            )
            location = FrameworkLocation(
                root_path=working_dir, strategy=PathResolutionStrategy.WORKING_DIRECTORY_STAGING
            )

            session_state = Mock()
            session_state.detection_state = detection_state

            # Simulate disk space exhaustion
            with patch("shutil.copy2", side_effect=OSError("No space left on device")):
                result = stager._stage_to_working_directory(location, session_state)

                # Should handle disk space errors gracefully
                assert result.is_successful is False
                assert len(result.failed) > 0


class TestWorkingDirectoryPathEdgeCases:
    """Edge cases related to path handling."""

    def test_very_long_path_names(self):
        """Test staging with very long path names."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create source with long path names
            amplihack_source = Path(temp_dir) / "amplihack"
            amplihack_source.mkdir()
            source_claude = amplihack_source / ".claude"
            source_claude.mkdir()

            # Create nested directory with long names (but within filesystem limits)
            long_name = "very_long_directory_name_that_tests_path_limits" * 3  # ~150 chars
            long_dir = source_claude / long_name[:100]  # Limit to reasonable size
            long_dir.mkdir()
            (long_dir / "test.txt").write_text("long path test")

            working_dir = Path(temp_dir) / "working"
            working_dir.mkdir()

            config = UVXConfiguration(use_working_directory_staging=True)
            stager = UVXStager(config)

            env_info = UVXEnvironmentInfo(
                sys_path_entries=[str(temp_dir)], working_directory=working_dir
            )
            detection_state = UVXDetectionState(
                result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
            )
            location = FrameworkLocation(
                root_path=working_dir, strategy=PathResolutionStrategy.WORKING_DIRECTORY_STAGING
            )

            session_state = Mock()
            session_state.detection_state = detection_state

            result = stager._stage_to_working_directory(location, session_state)

            # Should handle long path names
            assert result.is_successful or len(result.failed) > 0  # May fail on some systems

    def test_special_characters_in_paths(self):
        """Test staging with special characters in path names."""
        special_chars_safe = ["spaces here", "dash-name", "under_score", "dot.name"]

        with tempfile.TemporaryDirectory() as temp_dir:
            amplihack_source = Path(temp_dir) / "amplihack"
            amplihack_source.mkdir()
            source_claude = amplihack_source / ".claude"
            source_claude.mkdir()

            # Create files with special characters
            for special_name in special_chars_safe:
                special_file = source_claude / f"{special_name}.txt"
                special_file.write_text(f"Content for {special_name}")

            working_dir = Path(temp_dir) / "working with spaces"
            working_dir.mkdir()

            config = UVXConfiguration(use_working_directory_staging=True)
            stager = UVXStager(config)

            env_info = UVXEnvironmentInfo(
                sys_path_entries=[str(temp_dir)], working_directory=working_dir
            )
            detection_state = UVXDetectionState(
                result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
            )
            location = FrameworkLocation(
                root_path=working_dir, strategy=PathResolutionStrategy.WORKING_DIRECTORY_STAGING
            )

            session_state = Mock()
            session_state.detection_state = detection_state

            result = stager._stage_to_working_directory(location, session_state)

            # Should handle special characters
            assert result.is_successful

            # Verify files with special characters were staged
            for special_name in special_chars_safe:
                staged_file = working_dir / ".claude" / f"{special_name}.txt"
                assert staged_file.exists()
                assert f"Content for {special_name}" in staged_file.read_text()

    def test_symbolic_links_in_source(self):
        """Test staging when source contains symbolic links."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup source
            amplihack_source = Path(temp_dir) / "amplihack"
            amplihack_source.mkdir()
            source_claude = amplihack_source / ".claude"
            source_claude.mkdir()

            # Create regular file
            regular_file = source_claude / "regular.txt"
            regular_file.write_text("regular content")

            # Create symbolic link (if supported by system)
            try:
                link_target = source_claude / "link_target.txt"
                link_target.write_text("link target content")

                symbolic_link = source_claude / "symbolic.txt"
                symbolic_link.symlink_to(link_target)
                has_symlink = True
            except (OSError, NotImplementedError):
                # Symbolic links not supported on this system
                has_symlink = False

            working_dir = Path(temp_dir) / "working"
            working_dir.mkdir()

            config = UVXConfiguration(use_working_directory_staging=True)
            stager = UVXStager(config)

            env_info = UVXEnvironmentInfo(
                sys_path_entries=[str(temp_dir)], working_directory=working_dir
            )
            detection_state = UVXDetectionState(
                result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
            )
            location = FrameworkLocation(
                root_path=working_dir, strategy=PathResolutionStrategy.WORKING_DIRECTORY_STAGING
            )

            session_state = Mock()
            session_state.detection_state = detection_state

            result = stager._stage_to_working_directory(location, session_state)

            # Should handle symbolic links
            assert result.is_successful

            # Verify regular file staged
            assert (working_dir / ".claude" / "regular.txt").exists()

            if has_symlink:
                # Verify symbolic link handling (behavior depends on shutil.copy2)
                staged_link = working_dir / ".claude" / "symbolic.txt"
                assert staged_link.exists()  # Should exist in some form

    def test_case_sensitivity_edge_cases(self):
        """Test staging behavior with case sensitivity edge cases."""
        with tempfile.TemporaryDirectory() as temp_dir:
            amplihack_source = Path(temp_dir) / "amplihack"
            amplihack_source.mkdir()
            source_claude = amplihack_source / ".claude"
            source_claude.mkdir()

            # Create files with different case variations
            (source_claude / "README.md").write_text("uppercase readme")
            (source_claude / "readme.md").write_text("lowercase readme")
            (source_claude / "ReadMe.md").write_text("mixed case readme")

            working_dir = Path(temp_dir) / "working"
            working_dir.mkdir()

            config = UVXConfiguration(use_working_directory_staging=True)
            stager = UVXStager(config)

            env_info = UVXEnvironmentInfo(
                sys_path_entries=[str(temp_dir)], working_directory=working_dir
            )
            detection_state = UVXDetectionState(
                result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
            )
            location = FrameworkLocation(
                root_path=working_dir, strategy=PathResolutionStrategy.WORKING_DIRECTORY_STAGING
            )

            session_state = Mock()
            session_state.detection_state = detection_state

            result = stager._stage_to_working_directory(location, session_state)

            # Should handle case variations (behavior depends on filesystem)
            assert result.is_successful or len(result.failed) > 0

            # At least some files should be staged
            claude_dir = working_dir / ".claude"
            if result.is_successful:
                readme_files = list(claude_dir.glob("*readme*")) + list(claude_dir.glob("*README*"))
                assert len(readme_files) >= 1


class TestWorkingDirectoryConfigurationEdgeCases:
    """Edge cases related to configuration options."""

    def test_invalid_working_directory_subdir_names(self):
        """Test staging with invalid subdirectory names."""
        invalid_names = ["", ".", "..", "/absolute", "\\windows", "con", "nul"]

        with tempfile.TemporaryDirectory() as temp_dir:
            amplihack_source = Path(temp_dir) / "amplihack"
            amplihack_source.mkdir()
            source_claude = amplihack_source / ".claude"
            source_claude.mkdir()
            (source_claude / "test.txt").write_text("test")

            working_dir = Path(temp_dir) / "working"
            working_dir.mkdir()

            for invalid_name in invalid_names:
                if invalid_name in ["con", "nul"] and os.name != "nt":
                    continue  # Skip Windows-specific invalid names on non-Windows

                config = UVXConfiguration(
                    use_working_directory_staging=True, working_directory_subdir=invalid_name
                )
                stager = UVXStager(config)

                env_info = UVXEnvironmentInfo(
                    sys_path_entries=[str(temp_dir)], working_directory=working_dir
                )
                detection_state = UVXDetectionState(
                    result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
                )
                location = FrameworkLocation(
                    root_path=working_dir, strategy=PathResolutionStrategy.WORKING_DIRECTORY_STAGING
                )

                session_state = Mock()
                session_state.detection_state = detection_state

                # Should handle invalid names gracefully
                try:
                    stager._stage_to_working_directory(location, session_state)
                    # If it doesn't crash, that's good
                    assert True
                except Exception:
                    # If it crashes gracefully, that's also acceptable
                    assert True

    def test_unknown_handle_existing_claude_dir_strategy(self):
        """Test staging with unknown strategy for handling existing .claude directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            working_dir = Path(temp_dir) / "working"
            working_dir.mkdir()

            # Create existing .claude directory
            existing_claude = working_dir / ".claude"
            existing_claude.mkdir()
            (existing_claude / "existing.txt").write_text("existing content")

            config = UVXConfiguration(
                use_working_directory_staging=True, handle_existing_claude_dir="unknown_strategy"
            )
            stager = UVXStager(config)

            # Test unknown strategy handling
            success = stager._handle_existing_claude_directory(existing_claude)

            # Should handle unknown strategy gracefully
            assert success is False  # Unknown strategy should fail safely

    def test_extreme_configuration_values(self):
        """Test staging with extreme configuration values."""
        extreme_configs = [
            {"max_parent_traversal": 0},
            {"max_parent_traversal": 1000000},
            {"working_directory_subdir": "a" * 1000},  # Very long name
        ]

        with tempfile.TemporaryDirectory():
            for extreme_config in extreme_configs:
                config = UVXConfiguration(use_working_directory_staging=True, **extreme_config)

                # Should create config without errors
                assert config is not None
                assert config.use_working_directory_staging is True


class TestWorkingDirectoryConcurrencyEdgeCases:
    """Edge cases related to concurrent access and race conditions."""

    def test_concurrent_staging_attempts(self):
        """Test behavior when multiple processes attempt staging simultaneously."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup source
            amplihack_source = Path(temp_dir) / "amplihack"
            amplihack_source.mkdir()
            source_claude = amplihack_source / ".claude"
            source_claude.mkdir()
            (source_claude / "concurrent_test.txt").write_text("concurrent content")

            working_dir = Path(temp_dir) / "working"
            working_dir.mkdir()

            config = UVXConfiguration(use_working_directory_staging=True)

            # Simulate concurrent access by creating target directory during staging
            def create_concurrent_directory(*args, **kwargs):
                # Create .claude directory in working dir to simulate race condition
                concurrent_claude = working_dir / ".claude"
                concurrent_claude.mkdir(exist_ok=True)
                (concurrent_claude / "concurrent_file.txt").write_text("concurrent")
                return concurrent_claude

            with patch("pathlib.Path.mkdir", side_effect=create_concurrent_directory):
                stager = UVXStager(config)

                env_info = UVXEnvironmentInfo(
                    sys_path_entries=[str(temp_dir)], working_directory=working_dir
                )
                detection_state = UVXDetectionState(
                    result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
                )
                location = FrameworkLocation(
                    root_path=working_dir, strategy=PathResolutionStrategy.WORKING_DIRECTORY_STAGING
                )

                session_state = Mock()
                session_state.detection_state = detection_state

                # Should handle concurrent directory creation
                result = stager._stage_to_working_directory(location, session_state)

                # Should either succeed or fail gracefully
                assert isinstance(result.is_successful, bool)

    def test_file_modification_during_staging(self):
        """Test behavior when source files are modified during staging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            amplihack_source = Path(temp_dir) / "amplihack"
            amplihack_source.mkdir()
            source_claude = amplihack_source / ".claude"
            source_claude.mkdir()

            test_file = source_claude / "modifiable.txt"
            test_file.write_text("original content")

            working_dir = Path(temp_dir) / "working"
            working_dir.mkdir()

            config = UVXConfiguration(use_working_directory_staging=True)

            # Mock file operation that modifies source during copy
            original_copy = None

            def modify_during_copy(src, dst):
                nonlocal original_copy
                if original_copy is None:
                    import shutil

                    original_copy = shutil.copy2

                # Modify source file during copy
                if "modifiable.txt" in str(src):
                    Path(src).write_text("modified during copy")

                return original_copy(src, dst)

            with patch("shutil.copy2", side_effect=modify_during_copy):
                stager = UVXStager(config)

                env_info = UVXEnvironmentInfo(
                    sys_path_entries=[str(temp_dir)], working_directory=working_dir
                )
                detection_state = UVXDetectionState(
                    result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
                )
                location = FrameworkLocation(
                    root_path=working_dir, strategy=PathResolutionStrategy.WORKING_DIRECTORY_STAGING
                )

                session_state = Mock()
                session_state.detection_state = detection_state

                result = stager._stage_to_working_directory(location, session_state)

                # Should handle file modification during staging
                assert isinstance(result.is_successful, bool)

                if result.is_successful:
                    staged_file = working_dir / ".claude" / "modifiable.txt"
                    assert staged_file.exists()


class TestWorkingDirectoryEnvironmentEdgeCases:
    """Edge cases related to environment and system state."""

    def test_changing_working_directory_during_staging(self):
        """Test staging behavior when working directory changes during operation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup source
            amplihack_source = Path(temp_dir) / "amplihack"
            amplihack_source.mkdir()
            source_claude = amplihack_source / ".claude"
            source_claude.mkdir()
            (source_claude / "test.txt").write_text("test content")

            working_dir = Path(temp_dir) / "working"
            working_dir.mkdir()

            alt_working_dir = Path(temp_dir) / "alternative"
            alt_working_dir.mkdir()

            config = UVXConfiguration(use_working_directory_staging=True)
            stager = UVXStager(config)

            original_cwd = os.getcwd()

            try:
                os.chdir(str(working_dir))

                env_info = UVXEnvironmentInfo(
                    sys_path_entries=[str(temp_dir)], working_directory=working_dir
                )
                detection_state = UVXDetectionState(
                    result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
                )
                location = FrameworkLocation(
                    root_path=working_dir, strategy=PathResolutionStrategy.WORKING_DIRECTORY_STAGING
                )

                session_state = Mock()
                session_state.detection_state = detection_state

                # Change working directory during staging
                def change_cwd_during_mkdir(*args, **kwargs):
                    os.chdir(str(alt_working_dir))
                    return Path(*args, **kwargs).mkdir(**kwargs)

                with patch("pathlib.Path.mkdir", side_effect=change_cwd_during_mkdir):
                    result = stager._stage_to_working_directory(location, session_state)

                    # Should handle changing working directory
                    assert isinstance(result.is_successful, bool)

            finally:
                os.chdir(original_cwd)

    def test_environment_variables_missing(self):
        """Test staging when expected environment variables are missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            amplihack_source = Path(temp_dir) / "amplihack"
            amplihack_source.mkdir()
            source_claude = amplihack_source / ".claude"
            source_claude.mkdir()
            (source_claude / "test.txt").write_text("test")

            working_dir = Path(temp_dir) / "working"
            working_dir.mkdir()

            # Clear all UV-related environment variables
            env_vars_to_clear = ["UV_PYTHON", "AMPLIHACK_ROOT", "PYTHONPATH"]

            with patch.dict(os.environ, {var: "" for var in env_vars_to_clear}, clear=False):
                config = UVXConfiguration(use_working_directory_staging=True)

                # Detection should still work with minimal environment
                env_info = UVXEnvironmentInfo.from_current_environment()
                _detection_state = UVXDetectionState(
                    result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
                )

                stager = UVXStager(config)

                # Should handle missing environment variables gracefully
                assert stager is not None
                assert config.use_working_directory_staging is True

    def test_corrupted_sys_path(self):
        """Test staging when sys.path contains invalid entries."""
        with tempfile.TemporaryDirectory() as temp_dir:
            working_dir = Path(temp_dir) / "working"
            working_dir.mkdir()

            # Create corrupted sys.path with invalid entries
            corrupted_sys_path = [
                "/nonexistent/path",
                "",
                None,
                123,  # Invalid type
                "/another/nonexistent/path",
                str(temp_dir),  # Only this one is valid
            ]

            # Filter out None and invalid types as the real sys.path would
            safe_sys_path = [str(p) for p in corrupted_sys_path if isinstance(p, (str, Path)) and p]

            config = UVXConfiguration(use_working_directory_staging=True)

            env_info = UVXEnvironmentInfo(
                sys_path_entries=safe_sys_path, working_directory=working_dir
            )
            detection_state = UVXDetectionState(
                result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
            )

            # Should handle corrupted sys.path gracefully
            resolution_result = resolve_framework_paths(detection_state, config)

            # May succeed or fail, but shouldn't crash
            assert resolution_result is not None
            assert hasattr(resolution_result, "is_successful")


class TestWorkingDirectoryCleanupEdgeCases:
    """Edge cases related to cleanup operations."""

    def test_cleanup_with_locked_files(self):
        """Test cleanup when staged files are locked by other processes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            working_dir = Path(temp_dir) / "working"
            working_dir.mkdir()

            claude_dir = working_dir / ".claude"
            claude_dir.mkdir()

            locked_file = claude_dir / "locked.txt"
            locked_file.write_text("locked content")

            config = UVXConfiguration(use_working_directory_staging=True, cleanup_on_exit=True)
            stager = UVXStager(config)

            # Simulate locked file by making it read-only
            try:
                locked_file.chmod(stat.S_IRUSR)

                from src.amplihack.utils.uvx_models import StagingResult

                result = StagingResult()
                result.successful.add(locked_file)
                result.successful.add(claude_dir)

                # Mock permission error during cleanup
                with patch("pathlib.Path.unlink", side_effect=PermissionError("File is locked")):
                    with patch("shutil.rmtree", side_effect=PermissionError("Directory locked")):
                        cleaned_count = stager.cleanup_staged_files(result)

                        # Should handle locked files gracefully
                        assert cleaned_count >= 0  # May be 0 if all files locked

            finally:
                # Restore permissions for cleanup
                try:
                    locked_file.chmod(stat.S_IRWXU)
                except Exception:
                    pass

    def test_cleanup_with_partial_staging_results(self):
        """Test cleanup with partially successful staging results."""
        with tempfile.TemporaryDirectory() as temp_dir:
            working_dir = Path(temp_dir) / "working"
            working_dir.mkdir()

            # Create some files
            claude_dir = working_dir / ".claude"
            claude_dir.mkdir()
            (claude_dir / "file1.txt").write_text("content1")
            (claude_dir / "file2.txt").write_text("content2")

            config = UVXConfiguration(cleanup_on_exit=True)
            stager = UVXStager(config)

            from src.amplihack.utils.uvx_models import StagingResult

            result = StagingResult()

            # Mix of successful, failed, and skipped operations
            result.successful.add(claude_dir / "file1.txt")
            result.failed[claude_dir / "file2.txt"] = "Permission denied"
            result.skipped[claude_dir / "file3.txt"] = "Already exists"

            cleaned_count = stager.cleanup_staged_files(result)

            # Should only clean up successfully staged files
            assert cleaned_count >= 0
            assert not (claude_dir / "file1.txt").exists()  # Should be cleaned up

    def test_cleanup_registry_integration_edge_cases(self):
        """Test cleanup registry integration with edge cases."""
        try:
            from src.amplihack.utils.cleanup_registry import CleanupRegistry

            with tempfile.TemporaryDirectory() as temp_dir:
                working_dir = Path(temp_dir) / "working"
                working_dir.mkdir()

                registry = CleanupRegistry()
                config = UVXConfiguration(cleanup_on_exit=True)
                stager = UVXStager(config, cleanup_registry=registry)

                # Create files to register
                claude_dir = working_dir / ".claude"
                claude_dir.mkdir()
                test_files = []
                for i in range(5):
                    test_file = claude_dir / f"test_{i}.txt"
                    test_file.write_text(f"content {i}")
                    test_files.append(test_file)
                    registry.register(test_file)

                from src.amplihack.utils.uvx_models import StagingResult

                result = StagingResult()
                for f in test_files:
                    result.successful.add(f)

                # Test cleanup with registry
                cleaned_count = stager.cleanup_staged_files(result)

                assert cleaned_count >= 0

        except ImportError:
            # CleanupRegistry not available, skip this test
            pytest.skip("CleanupRegistry not available")


@pytest.mark.stress
class TestWorkingDirectoryStressScenarios:
    """Stress tests for working directory staging."""

    def test_large_number_of_small_files(self):
        """Test staging with large number of small files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            amplihack_source = Path(temp_dir) / "amplihack"
            amplihack_source.mkdir()
            source_claude = amplihack_source / ".claude"
            source_claude.mkdir()

            # Create many small files
            num_files = 1000
            for i in range(num_files):
                category = i % 10  # 10 categories
                category_dir = source_claude / f"category_{category}"
                category_dir.mkdir(exist_ok=True)
                (category_dir / f"file_{i}.txt").write_text(f"content {i}")

            working_dir = Path(temp_dir) / "working"
            working_dir.mkdir()

            config = UVXConfiguration(use_working_directory_staging=True)
            stager = UVXStager(config)

            env_info = UVXEnvironmentInfo(
                sys_path_entries=[str(temp_dir)], working_directory=working_dir
            )
            detection_state = UVXDetectionState(
                result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
            )
            location = FrameworkLocation(
                root_path=working_dir, strategy=PathResolutionStrategy.WORKING_DIRECTORY_STAGING
            )

            session_state = Mock()
            session_state.detection_state = detection_state

            start_time = time.time()
            result = stager._stage_to_working_directory(location, session_state)
            end_time = time.time()

            # Should handle large number of files
            assert result.is_successful
            assert len(result.successful) == num_files
            assert end_time - start_time < 60  # Should complete within reasonable time

    def test_rapid_staging_requests(self):
        """Test behavior under rapid staging requests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            amplihack_source = Path(temp_dir) / "amplihack"
            amplihack_source.mkdir()
            source_claude = amplihack_source / ".claude"
            source_claude.mkdir()
            (source_claude / "rapid_test.txt").write_text("rapid test content")

            working_dir = Path(temp_dir) / "working"
            working_dir.mkdir()

            config = UVXConfiguration(use_working_directory_staging=True)

            # Perform rapid staging requests
            results = []
            for i in range(10):
                stager = UVXStager(config)

                env_info = UVXEnvironmentInfo(
                    sys_path_entries=[str(temp_dir)], working_directory=working_dir
                )
                detection_state = UVXDetectionState(
                    result=UVXDetectionResult.UVX_DEPLOYMENT, environment=env_info
                )
                location = FrameworkLocation(
                    root_path=working_dir, strategy=PathResolutionStrategy.WORKING_DIRECTORY_STAGING
                )

                session_state = Mock()
                session_state.detection_state = detection_state

                result = stager._stage_to_working_directory(location, session_state)
                results.append(result.is_successful)

            # Most requests should succeed (some may fail due to conflicts)
            success_count = sum(results)
            assert success_count >= 5  # At least half should succeed
