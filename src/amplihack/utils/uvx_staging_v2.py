"""UVX file staging operations using clean data models.

This module provides file staging functionality for UVX deployments
using the immutable data structures and proper error handling.
"""

import shutil
from pathlib import Path
from typing import List, Optional

from .uvx_detection import detect_uvx_deployment, resolve_framework_paths
from .uvx_models import (
    FrameworkLocation,
    PathResolutionStrategy,
    StagingOperation,
    StagingResult,
    UVXConfiguration,
    UVXSessionState,
)


class UVXStager:
    """Handles UVX file staging operations with clean state management."""

    def __init__(self, config: Optional[UVXConfiguration] = None):
        """Initialize UVX stager with configuration.

        Args:
            config: Optional UVX configuration
        """
        self.config = config or UVXConfiguration()
        self._debug_enabled = self.config.is_debug_enabled

    def _debug_log(self, message: str) -> None:
        """Log debug message if debugging is enabled."""
        if self._debug_enabled:
            import sys

            print(f"[UVX STAGING DEBUG] {message}", file=sys.stderr)

    def stage_framework_files(
        self, session_state: Optional[UVXSessionState] = None
    ) -> StagingResult:
        """Stage framework files from UVX installation to working directory.

        Args:
            session_state: Optional existing session state to update

        Returns:
            StagingResult with details of staging operations
        """
        result = StagingResult()

        # Initialize session state if not provided
        if session_state is None:
            session_state = UVXSessionState(configuration=self.config)

        # Detect UVX deployment if not already done
        if session_state.detection_state is None:
            detection = detect_uvx_deployment(self.config)
            session_state.initialize_detection(detection)
            self._debug_log(f"UVX detection: {detection.result.name}")

        # Skip staging if not UVX deployment
        if (
            session_state.detection_state is None
            or not session_state.detection_state.is_uvx_deployment
        ):
            self._debug_log("Not in UVX deployment mode, skipping staging")
            return result

        # Resolve framework paths if not already done
        if session_state.path_resolution is None:
            if session_state.detection_state is None:
                self._debug_log("Detection state is None, cannot resolve paths")
                return result
            resolution = resolve_framework_paths(session_state.detection_state, self.config)
            session_state.set_path_resolution(resolution)

        if session_state.path_resolution is None or not session_state.path_resolution.is_successful:
            self._debug_log("Framework path resolution failed")
            return result

        framework_location = session_state.path_resolution.location
        if framework_location is None:
            self._debug_log("Framework location is None after successful resolution")
            return result

        # Perform staging based on resolution strategy
        if framework_location.strategy == PathResolutionStrategy.STAGING_REQUIRED:
            result = self._stage_from_uvx_installation(framework_location, session_state)
        elif framework_location.strategy in (
            PathResolutionStrategy.ENVIRONMENT_VARIABLE,
            PathResolutionStrategy.SYSTEM_PATH_SEARCH,
        ):
            result = self._stage_from_resolved_location(framework_location, session_state)
        else:
            self._debug_log(f"No staging needed for strategy: {framework_location.strategy.name}")

        # Update session state with staging results
        session_state.set_staging_result(result)
        self._debug_log(
            f"Staging complete: {result.total_operations} operations, "
            f"{len(result.successful)} successful"
        )

        return result

    def _stage_from_uvx_installation(
        self, target_location: FrameworkLocation, session_state: UVXSessionState
    ) -> StagingResult:
        """Stage files from UVX installation discovered via sys.path.

        Args:
            target_location: Where to stage files
            session_state: Current session state

        Returns:
            StagingResult with staging operation details
        """
        result = StagingResult()

        # Find source location in sys.path
        source_root = None
        if session_state.detection_state is None:
            result.add_failure(target_location.root_path, "Detection state is None")
            return result

        for path_str in session_state.detection_state.environment.sys_path_entries:
            candidate = Path(path_str) / "amplihack"
            if candidate.exists() and (candidate / ".claude").exists():
                source_root = candidate
                break

        if not source_root:
            result.add_failure(target_location.root_path, "Could not find UVX framework source")
            return result

        self._debug_log(f"Staging from UVX source: {source_root}")
        return self._perform_staging_operations(source_root, target_location.root_path, result)

    def _stage_from_resolved_location(
        self, source_location: FrameworkLocation, session_state: UVXSessionState
    ) -> StagingResult:
        """Stage files from already resolved framework location.

        Args:
            source_location: Source framework location
            session_state: Current session state

        Returns:
            StagingResult with staging operation details
        """
        result = StagingResult()
        if session_state.detection_state is None:
            result.add_failure(source_location.root_path, "Detection state is None")
            return result

        target_dir = session_state.detection_state.environment.working_directory

        self._debug_log(f"Staging from resolved location: {source_location.root_path}")
        return self._perform_staging_operations(source_location.root_path, target_dir, result)

    def _perform_staging_operations(
        self, source_root: Path, target_root: Path, result: StagingResult
    ) -> StagingResult:
        """Perform actual file staging operations.

        Args:
            source_root: Source directory containing framework files
            target_root: Target directory for staging
            result: StagingResult to update

        Returns:
            Updated StagingResult
        """
        # Find all items to stage
        items_to_stage = self._find_stageable_items(source_root)
        self._debug_log(f"Found {len(items_to_stage)} items to stage")

        for item_name in items_to_stage:
            source_path = source_root / item_name
            target_path = target_root / item_name

            # Check if target already exists
            if target_path.exists() and not self.config.overwrite_existing:
                result.add_skipped(target_path, "Target already exists")
                self._debug_log(f"Skipping existing: {target_path}")
                continue

            # Create staging operation
            operation_type = "directory" if source_path.is_dir() else "file"
            operation = StagingOperation(
                source_path=source_path, target_path=target_path, operation_type=operation_type
            )

            if not operation.is_valid:
                result.add_failure(target_path, "Invalid staging operation")
                continue

            # Perform the staging
            try:
                if self.config.create_backup and target_path.exists():
                    self._create_backup(target_path)

                if source_path.is_dir():
                    shutil.copytree(
                        source_path, target_path, dirs_exist_ok=self.config.overwrite_existing
                    )
                    self._debug_log(f"Staged directory: {source_path} -> {target_path}")
                else:
                    shutil.copy2(source_path, target_path)
                    self._debug_log(f"Staged file: {source_path} -> {target_path}")

                result.add_success(target_path, operation)

            except PermissionError as e:
                result.add_failure(target_path, f"Permission denied: {e}")
                self._debug_log(f"Permission error staging {item_name}: {e}")
            except OSError as e:
                result.add_failure(target_path, f"OS error: {e}")
                self._debug_log(f"OS error staging {item_name}: {e}")
            except Exception as e:
                result.add_failure(target_path, f"Unexpected error: {type(e).__name__}: {e}")
                self._debug_log(f"Unexpected error staging {item_name}: {e}")

        return result

    def _find_stageable_items(self, source_root: Path) -> List[str]:
        """Find all items in source root that should be staged.

        Args:
            source_root: Source directory to examine

        Returns:
            List of item names to stage
        """
        try:
            # Stage all items in framework root
            return [item.name for item in source_root.iterdir()]
        except OSError:
            self._debug_log(f"Cannot read source directory: {source_root}")
            return []

    def _create_backup(self, target_path: Path) -> None:
        """Create backup of existing target file/directory.

        Args:
            target_path: Path to create backup for
        """
        backup_path = target_path.with_suffix(target_path.suffix + ".backup")
        try:
            if target_path.is_dir():
                shutil.copytree(target_path, backup_path)
            else:
                shutil.copy2(target_path, backup_path)
            self._debug_log(f"Created backup: {backup_path}")
        except Exception as e:
            self._debug_log(f"Failed to create backup for {target_path}: {e}")

    def cleanup_staged_files(self, staging_result: StagingResult) -> int:
        """Clean up staged files.

        Args:
            staging_result: Result of previous staging operations

        Returns:
            Number of files successfully cleaned up
        """
        if not self.config.cleanup_on_exit:
            self._debug_log("Cleanup disabled in configuration")
            return 0

        cleaned_count = 0
        for staged_path in staging_result.successful:
            try:
                if staged_path.is_dir():
                    shutil.rmtree(staged_path)
                else:
                    staged_path.unlink()
                cleaned_count += 1
                self._debug_log(f"Cleaned up: {staged_path}")
            except Exception as e:
                self._debug_log(f"Failed to clean up {staged_path}: {e}")

        return cleaned_count


# Global stager instance for compatibility
_default_stager = UVXStager()


def stage_uvx_framework(config: Optional[UVXConfiguration] = None) -> bool:
    """Stage UVX framework files using default stager.

    Args:
        config: Optional UVX configuration

    Returns:
        True if staging succeeded, False otherwise
    """
    stager = UVXStager(config) if config else _default_stager
    result = stager.stage_framework_files()
    return result.is_successful


def create_uvx_session() -> UVXSessionState:
    """Create and initialize a new UVX session state.

    Returns:
        Initialized UVXSessionState
    """
    session_state = UVXSessionState()

    # Perform detection and path resolution
    detection = detect_uvx_deployment(session_state.configuration)
    session_state.initialize_detection(detection)

    resolution = resolve_framework_paths(detection, session_state.configuration)
    session_state.set_path_resolution(resolution)

    # Perform staging if needed
    if detection.is_uvx_deployment and resolution.requires_staging:
        stager = UVXStager(session_state.configuration)
        staging_result = stager.stage_framework_files(session_state)
        session_state.set_staging_result(staging_result)

    # Mark as initialized
    import uuid

    session_state.mark_initialized(str(uuid.uuid4()))

    return session_state
