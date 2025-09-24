"""UVX detection and path resolution using clean data models.

This module provides functions to detect UVX deployment state and resolve
framework paths using the immutable data structures from uvx_models.
"""

from pathlib import Path
from typing import List, Optional

from .uvx_models import (
    FrameworkLocation,
    PathResolutionResult,
    PathResolutionStrategy,
    UVXConfiguration,
    UVXDetectionResult,
    UVXDetectionState,
    UVXEnvironmentInfo,
)


def detect_uvx_deployment(config: Optional[UVXConfiguration] = None) -> UVXDetectionState:
    """Detect UVX deployment state with detailed reasoning.

    Args:
        config: Optional UVX configuration for detection parameters

    Returns:
        UVXDetectionState with detection result and reasoning
    """
    if config is None:
        config = UVXConfiguration()

    env_info = UVXEnvironmentInfo.from_current_environment()
    reasons = []

    # Check for UV_PYTHON environment variable (strongest UVX indicator)
    if env_info.uv_python_path:
        reasons.append(f"UV_PYTHON environment variable present: {env_info.uv_python_path}")
        return UVXDetectionState(
            result=UVXDetectionResult.UVX_DEPLOYMENT,
            environment=env_info,
            detection_reasons=reasons,
        )

    # Check if .claude directory exists in working directory (local deployment indicator)
    claude_dir = env_info.working_directory / ".claude"
    if claude_dir.exists():
        reasons.append(f"Local .claude directory found: {claude_dir}")
        return UVXDetectionState(
            result=UVXDetectionResult.LOCAL_DEPLOYMENT,
            environment=env_info,
            detection_reasons=reasons,
        )

    # If no local .claude but AMPLIHACK_ROOT set, likely UVX
    if env_info.amplihack_root:
        root_path = Path(env_info.amplihack_root)
        if root_path.exists() and (root_path / ".claude").exists():
            reasons.append(f"AMPLIHACK_ROOT points to valid framework: {env_info.amplihack_root}")
            return UVXDetectionState(
                result=UVXDetectionResult.UVX_DEPLOYMENT,
                environment=env_info,
                detection_reasons=reasons,
            )
        else:
            reasons.append(f"AMPLIHACK_ROOT set but invalid: {env_info.amplihack_root}")

    # Check sys.path for framework installation
    framework_in_path = _find_framework_in_sys_path(env_info.sys_path_entries)
    if framework_in_path:
        reasons.append(f"Framework found in sys.path: {framework_in_path}")
        return UVXDetectionState(
            result=UVXDetectionResult.UVX_DEPLOYMENT,
            environment=env_info,
            detection_reasons=reasons,
        )

    # Could not determine deployment type
    reasons.append("No clear deployment indicators found")
    return UVXDetectionState(
        result=UVXDetectionResult.DETECTION_FAILED, environment=env_info, detection_reasons=reasons
    )


def resolve_framework_paths(
    detection_state: UVXDetectionState, config: Optional[UVXConfiguration] = None
) -> PathResolutionResult:
    """Resolve framework paths based on detection state.

    Args:
        detection_state: Result of UVX detection
        config: Optional configuration for path resolution

    Returns:
        PathResolutionResult with resolved location or attempts
    """
    if config is None:
        config = UVXConfiguration()

    result = PathResolutionResult(location=None)

    # Strategy 1: Working directory (for local deployments)
    if detection_state.result == UVXDetectionResult.LOCAL_DEPLOYMENT:
        working_dir = detection_state.environment.working_directory
        result = result.with_attempt(
            PathResolutionStrategy.WORKING_DIRECTORY,
            working_dir,
            success=True,
            notes="Local deployment detected",
        )

        location = FrameworkLocation(
            root_path=working_dir, strategy=PathResolutionStrategy.WORKING_DIRECTORY
        ).validate()

        if location.is_valid:
            return PathResolutionResult(location=location, attempts=result.attempts)

    # Strategy 2: Environment variable (AMPLIHACK_ROOT)
    if detection_state.environment.amplihack_root:
        env_path = Path(detection_state.environment.amplihack_root)
        location = FrameworkLocation(
            root_path=env_path, strategy=PathResolutionStrategy.ENVIRONMENT_VARIABLE
        ).validate()

        result = result.with_attempt(
            PathResolutionStrategy.ENVIRONMENT_VARIABLE,
            env_path,
            success=location.is_valid,
            notes=f"AMPLIHACK_ROOT={detection_state.environment.amplihack_root}",
        )

        if location.is_valid:
            return PathResolutionResult(location=location, attempts=result.attempts)

    # Strategy 3: System path search
    framework_path = _find_framework_in_sys_path(detection_state.environment.sys_path_entries)
    if framework_path:
        location = FrameworkLocation(
            root_path=framework_path, strategy=PathResolutionStrategy.SYSTEM_PATH_SEARCH
        ).validate()

        result = result.with_attempt(
            PathResolutionStrategy.SYSTEM_PATH_SEARCH,
            framework_path,
            success=location.is_valid,
            notes="Found via sys.path search",
        )

        if location.is_valid:
            return PathResolutionResult(location=location, attempts=result.attempts)

    # Strategy 4: Parent directory traversal (for local dev in subdirectories)
    if detection_state.result == UVXDetectionResult.LOCAL_DEPLOYMENT:
        parent_result = _search_parent_directories(
            detection_state.environment.working_directory, max_levels=config.max_parent_traversal
        )

        if parent_result:
            location = FrameworkLocation(
                root_path=parent_result, strategy=PathResolutionStrategy.WORKING_DIRECTORY
            ).validate()

            result = result.with_attempt(
                PathResolutionStrategy.WORKING_DIRECTORY,
                parent_result,
                success=location.is_valid,
                notes="Found in parent directory",
            )

            if location.is_valid:
                return PathResolutionResult(location=location, attempts=result.attempts)

    # Strategy 5: Staging required (for UVX deployments when direct resolution fails)
    if detection_state.result == UVXDetectionResult.UVX_DEPLOYMENT and config.allow_staging:
        # Create a staging location in working directory
        working_dir = detection_state.environment.working_directory
        location = FrameworkLocation(
            root_path=working_dir, strategy=PathResolutionStrategy.STAGING_REQUIRED
        )

        result = result.with_attempt(
            PathResolutionStrategy.STAGING_REQUIRED,
            working_dir,
            success=True,
            notes="Staging required for UVX deployment",
        )

        return PathResolutionResult(location=location, attempts=result.attempts)

    # All strategies failed
    result = result.with_attempt(
        PathResolutionStrategy.RESOLUTION_FAILED,
        detection_state.environment.working_directory,
        success=False,
        notes="All resolution strategies failed",
    )

    return result


def _find_framework_in_sys_path(sys_path_entries: List[str]) -> Optional[Path]:
    """Find framework installation in Python sys.path.

    Args:
        sys_path_entries: List of sys.path entries to search

    Returns:
        Path to framework root if found, None otherwise
    """
    for path_str in sys_path_entries:
        try:
            # Look for amplihack package with .claude directory
            candidate = Path(path_str) / "amplihack"
            if candidate.exists() and (candidate / ".claude").exists():
                return candidate
        except OSError:
            # Invalid path in sys.path, skip
            continue

    return None


def _search_parent_directories(start_path: Path, max_levels: int = 10) -> Optional[Path]:
    """Search parent directories for framework root.

    Args:
        start_path: Directory to start searching from
        max_levels: Maximum number of parent levels to search

    Returns:
        Path to framework root if found, None otherwise
    """
    current = start_path
    levels = 0

    while current != current.parent and levels < max_levels:
        if (current / ".claude").exists():
            return current
        current = current.parent
        levels += 1

    return None


# Convenience functions for backward compatibility
def is_uvx_deployment(config: Optional[UVXConfiguration] = None) -> bool:
    """Check if running in UVX deployment mode."""
    detection = detect_uvx_deployment(config)
    return detection.is_uvx_deployment


def find_framework_root(config: Optional[UVXConfiguration] = None) -> Optional[Path]:
    """Find framework root directory."""
    detection = detect_uvx_deployment(config)
    resolution = resolve_framework_paths(detection, config)

    if resolution.is_successful:
        return resolution.location.root_path
    return None


def resolve_framework_file(
    relative_path: str, config: Optional[UVXConfiguration] = None
) -> Optional[Path]:
    """Resolve a framework file path."""
    detection = detect_uvx_deployment(config)
    resolution = resolve_framework_paths(detection, config)

    if resolution.is_successful:
        return resolution.location.resolve_file(relative_path)
    return None
