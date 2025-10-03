"""Data models for UVX system state management.

This module provides immutable, type-safe data structures for managing UVX
path resolution, installation detection, and configuration state.

Design Philosophy:
- Make invalid states unrepresentable
- Immutable where possible for thread safety
- Clear validation and error handling
- Easy serialization for debugging
- Type hints for all public interfaces
"""

import os
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Union


class UVXDetectionResult(Enum):
    """Result of UVX environment detection."""

    LOCAL_DEPLOYMENT = auto()  # Running in local development mode
    UVX_DEPLOYMENT = auto()  # Running via UVX package
    DETECTION_FAILED = auto()  # Could not determine deployment type
    AMBIGUOUS_STATE = auto()  # Multiple deployment indicators present


class PathResolutionStrategy(Enum):
    """Strategy used for path resolution."""

    WORKING_DIRECTORY = auto()  # Found framework files in working directory
    ENVIRONMENT_VARIABLE = auto()  # Using AMPLIHACK_ROOT environment variable
    SYSTEM_PATH_SEARCH = auto()  # Found via sys.path search
    WORKING_DIRECTORY_STAGING = auto()  # Stage files to working directory/.claude
    STAGING_REQUIRED = auto()  # Need to stage files from UVX installation
    RESOLUTION_FAILED = auto()  # Could not resolve framework location


@dataclass(frozen=True)
class UVXEnvironmentInfo:
    """Information about the UVX environment."""

    uv_python_path: Optional[str] = None
    amplihack_root: Optional[str] = None
    sys_path_entries: List[str] = field(default_factory=list)
    working_directory: Path = field(default_factory=Path.cwd)
    python_executable: str = field(default_factory=str)

    @classmethod
    def from_current_environment(cls) -> "UVXEnvironmentInfo":
        """Create UVXEnvironmentInfo from current environment."""
        import sys

        return cls(
            uv_python_path=os.environ.get("UV_PYTHON"),
            amplihack_root=os.environ.get("AMPLIHACK_ROOT"),
            sys_path_entries=sys.path.copy(),
            working_directory=Path.cwd(),
            python_executable=sys.executable,
        )

    @property
    def is_uv_cache_execution(self) -> bool:
        """Check if Python is running from UV cache.

        This is a key indicator of UVX execution, as uvx runs packages
        from the UV cache directory (e.g., ~/.cache/uv/).

        Returns:
            True if running from UV cache, False otherwise
        """
        return ".cache/uv/" in self.python_executable or "\\cache\\uv\\" in self.python_executable


@dataclass(frozen=True)
class UVXDetectionState:
    """Immutable state representing UVX detection results."""

    result: UVXDetectionResult
    environment: UVXEnvironmentInfo
    detection_reasons: List[str] = field(default_factory=list)

    @property
    def is_uvx_deployment(self) -> bool:
        """True if running in UVX deployment mode."""
        return self.result == UVXDetectionResult.UVX_DEPLOYMENT

    @property
    def is_local_deployment(self) -> bool:
        """True if running in local development mode."""
        return self.result == UVXDetectionResult.LOCAL_DEPLOYMENT

    @property
    def is_detection_successful(self) -> bool:
        """True if detection succeeded (not failed or ambiguous)."""
        return self.result in (
            UVXDetectionResult.LOCAL_DEPLOYMENT,
            UVXDetectionResult.UVX_DEPLOYMENT,
        )

    def with_additional_reason(self, reason: str) -> "UVXDetectionState":
        """Return new state with additional detection reason."""
        new_reasons = self.detection_reasons + [reason]
        return UVXDetectionState(
            result=self.result, environment=self.environment, detection_reasons=new_reasons
        )


@dataclass(frozen=True)
class FrameworkLocation:
    """Represents a located framework installation."""

    root_path: Path
    strategy: PathResolutionStrategy
    validation_errors: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True if the framework location is valid."""
        return len(self.validation_errors) == 0 and self.root_path.exists()

    @property
    def claude_dir(self) -> Path:
        """Path to the .claude directory."""
        return self.root_path / ".claude"

    @property
    def has_claude_dir(self) -> bool:
        """True if .claude directory exists."""
        return self.claude_dir.exists() and self.claude_dir.is_dir()

    def validate(self) -> "FrameworkLocation":
        """Return new FrameworkLocation with validation results."""
        errors = []

        if not self.root_path.exists():
            errors.append(f"Framework root does not exist: {self.root_path}")
        elif not self.root_path.is_dir():
            errors.append(f"Framework root is not a directory: {self.root_path}")

        if not self.has_claude_dir:
            errors.append(f"Missing .claude directory in: {self.root_path}")

        return FrameworkLocation(
            root_path=self.root_path, strategy=self.strategy, validation_errors=errors
        )

    def resolve_file(self, relative_path: str) -> Optional[Path]:
        """Resolve a file path relative to framework root.

        Args:
            relative_path: Relative path to resolve

        Returns:
            Absolute path if file exists and is within framework root, None otherwise
        """
        if not self.is_valid:
            return None

        # Basic validation for path traversal attacks
        if ".." in relative_path or "\x00" in relative_path or relative_path.startswith("/"):
            return None

        try:
            # Resolve to absolute path, following symlinks
            file_path = (self.root_path / relative_path).resolve()
            root_resolved = self.root_path.resolve()

            # Verify the resolved path is within the framework root
            file_path.relative_to(root_resolved)

            # Only return if file actually exists
            return file_path if file_path.exists() else None

        except (ValueError, OSError):
            # Path is outside framework root or resolution failed
            return None


@dataclass(frozen=True)
class PathResolutionResult:
    """Result of framework path resolution."""

    location: Optional[FrameworkLocation]
    attempts: List[Dict[str, Union[str, Path, bool]]] = field(default_factory=list)

    @property
    def is_successful(self) -> bool:
        """True if path resolution succeeded."""
        return self.location is not None and self.location.is_valid

    @property
    def requires_staging(self) -> bool:
        """True if successful resolution requires staging files."""
        return self.location is not None and self.location.strategy in (
            PathResolutionStrategy.STAGING_REQUIRED,
            PathResolutionStrategy.WORKING_DIRECTORY_STAGING,
        )

    def with_attempt(
        self, strategy: PathResolutionStrategy, path: Path, success: bool, notes: str = ""
    ) -> "PathResolutionResult":
        """Return new result with additional resolution attempt."""
        new_attempt = {"strategy": strategy.name, "path": path, "success": success, "notes": notes}
        new_attempts = self.attempts + [new_attempt]

        return PathResolutionResult(location=self.location, attempts=new_attempts)


@dataclass(frozen=True)
class UVXConfiguration:
    """Configuration for UVX operations."""

    # Environment variables to check
    uv_python_env_var: str = "UV_PYTHON"
    amplihack_root_env_var: str = "AMPLIHACK_ROOT"
    debug_env_var: str = "AMPLIHACK_DEBUG"

    # Path resolution settings
    max_parent_traversal: int = 10
    validate_framework_structure: bool = True
    allow_staging: bool = True

    # Staging behavior
    overwrite_existing: bool = False
    create_backup: bool = False
    cleanup_on_exit: bool = True  # Default to cleanup for UVX deployments
    use_working_directory_staging: bool = True  # Use working directory instead of temp dirs
    working_directory_subdir: str = ".claude"  # Subdirectory name for staging
    handle_existing_claude_dir: str = "backup"  # "backup", "merge", "overwrite"

    # Debug settings
    debug_enabled: Optional[bool] = None

    @property
    def is_debug_enabled(self) -> bool:
        """True if debug mode is enabled."""
        if self.debug_enabled is not None:
            return self.debug_enabled

        debug_value = os.environ.get(self.debug_env_var, "").lower()
        return debug_value in ("true", "1", "yes")

    def with_debug(self, enabled: bool) -> "UVXConfiguration":
        """Return new configuration with debug setting."""
        return UVXConfiguration(
            uv_python_env_var=self.uv_python_env_var,
            amplihack_root_env_var=self.amplihack_root_env_var,
            debug_env_var=self.debug_env_var,
            max_parent_traversal=self.max_parent_traversal,
            validate_framework_structure=self.validate_framework_structure,
            allow_staging=self.allow_staging,
            overwrite_existing=self.overwrite_existing,
            create_backup=self.create_backup,
            cleanup_on_exit=self.cleanup_on_exit,
            use_working_directory_staging=self.use_working_directory_staging,
            working_directory_subdir=self.working_directory_subdir,
            handle_existing_claude_dir=self.handle_existing_claude_dir,
            debug_enabled=enabled,
        )


@dataclass(frozen=True)
class StagingOperation:
    """Represents a file staging operation."""

    source_path: Path
    target_path: Path
    operation_type: str  # "file", "directory", "symlink"

    @property
    def is_valid(self) -> bool:
        """True if the staging operation is valid."""
        return self.source_path.exists() and self.target_path.parent.exists()


@dataclass
class StagingResult:
    """Result of file staging operations."""

    operations: List[StagingOperation] = field(default_factory=list)
    successful: Set[Path] = field(default_factory=set)
    failed: Dict[Path, str] = field(default_factory=dict)
    skipped: Dict[Path, str] = field(default_factory=dict)

    @property
    def is_successful(self) -> bool:
        """True if all operations succeeded."""
        return len(self.failed) == 0 and len(self.successful) > 0

    @property
    def total_operations(self) -> int:
        """Total number of staging operations attempted."""
        return len(self.successful) + len(self.failed) + len(self.skipped)

    def add_success(self, path: Path, operation: StagingOperation) -> None:
        """Record a successful staging operation."""
        self.operations.append(operation)
        self.successful.add(path)

    def add_failure(self, path: Path, error: str) -> None:
        """Record a failed staging operation."""
        self.failed[path] = error

    def add_skipped(self, path: Path, reason: str) -> None:
        """Record a skipped staging operation."""
        self.skipped[path] = reason


@dataclass
class UVXSessionState:
    """Mutable session state for UVX operations."""

    detection_state: Optional[UVXDetectionState] = None
    path_resolution: Optional[PathResolutionResult] = None
    configuration: UVXConfiguration = field(default_factory=UVXConfiguration)
    staging_result: Optional[StagingResult] = None
    session_id: Optional[str] = None
    initialized: bool = False

    @property
    def is_ready(self) -> bool:
        """True if session is fully initialized and ready."""
        return (
            self.initialized
            and self.detection_state is not None
            and self.detection_state.is_detection_successful
            and self.path_resolution is not None
            and self.path_resolution.is_successful
        )

    @property
    def framework_root(self) -> Optional[Path]:
        """Current framework root path if available."""
        if (
            self.path_resolution
            and self.path_resolution.location
            and self.path_resolution.location.is_valid
        ):
            return self.path_resolution.location.root_path
        return None

    def initialize_detection(self, detection_state: UVXDetectionState) -> None:
        """Initialize with UVX detection results."""
        self.detection_state = detection_state

    def set_path_resolution(self, resolution_result: PathResolutionResult) -> None:
        """Set path resolution results."""
        self.path_resolution = resolution_result

    def set_staging_result(self, staging_result: StagingResult) -> None:
        """Set staging operation results."""
        self.staging_result = staging_result

    def mark_initialized(self, session_id: str) -> None:
        """Mark session as fully initialized."""
        self.session_id = session_id
        self.initialized = True

    def to_debug_dict(self) -> Dict[str, Union[str, bool, int, None]]:
        """Convert session state to dictionary for debugging."""
        return {
            "session_id": self.session_id,
            "initialized": self.initialized,
            "is_ready": self.is_ready,
            "detection_result": self.detection_state.result.name if self.detection_state else None,
            "is_uvx_deployment": self.detection_state.is_uvx_deployment
            if self.detection_state
            else None,
            "framework_root": str(self.framework_root) if self.framework_root else None,
            "path_strategy": self.path_resolution.location.strategy.name
            if self.path_resolution and self.path_resolution.location
            else None,
            "staging_successful": self.staging_result.is_successful
            if self.staging_result
            else None,
            "staging_operations": self.staging_result.total_operations
            if self.staging_result
            else 0,
            "debug_enabled": self.configuration.is_debug_enabled,
        }


# Type aliases for common use cases

UVXDetector = Callable[[], UVXDetectionState]
PathResolver = Callable[[UVXDetectionState], PathResolutionResult]
FileStager = Callable[[FrameworkLocation], StagingResult]
