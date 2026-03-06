# UVX Data Models Design

Clean, type-safe data structures for UVX system state management.

## Overview

The UVX data models provide immutable, type-safe structures for managing UVX path resolution, installation detection, and configuration state. These models make invalid states unrepresentable and provide clear validation and error handling.

## Key Design Principles

### 1. Make Invalid States Unrepresentable

```python
# UVX detection can only be one of four explicit states
class UVXDetectionResult(Enum):
    LOCAL_DEPLOYMENT = auto()      # Clear: running locally
    UVX_DEPLOYMENT = auto()        # Clear: running via UVX
    DETECTION_FAILED = auto()      # Clear: could not determine
    AMBIGUOUS_STATE = auto()       # Clear: conflicting indicators
```

### 2. Immutable Where Possible

```python
@dataclass(frozen=True)
class UVXDetectionState:
    """Immutable state representing UVX detection results."""
    result: UVXDetectionResult
    environment: UVXEnvironmentInfo
    detection_reasons: List[str] = field(default_factory=list)

    # All mutations return new instances
    def with_additional_reason(self, reason: str) -> 'UVXDetectionState':
        return UVXDetectionState(...)
```

### 3. Clear Validation and Error States

```python
@dataclass(frozen=True)
class FrameworkLocation:
    validation_errors: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.validation_errors) == 0 and self.root_path.exists()

    def validate(self) -> 'FrameworkLocation':
        """Return new FrameworkLocation with validation results."""
        errors = []
        if not self.root_path.exists():
            errors.append(f"Framework root does not exist: {self.root_path}")
        # ... more validation
        return FrameworkLocation(..., validation_errors=errors)
```

### 4. Security-Focused Path Resolution

```python
def resolve_file(self, relative_path: str) -> Optional[Path]:
    # Basic validation for path traversal attacks
    if ".." in relative_path or "\x00" in relative_path:
        return None

    try:
        file_path = (self.root_path / relative_path).resolve()
        # Verify resolved path is within framework root
        file_path.relative_to(self.root_path.resolve())
        return file_path if file_path.exists() else None
    except (ValueError, OSError):
        return None
```

## Core Data Structures

### 1. UVX Detection State

```python
# Environment information
@dataclass(frozen=True)
class UVXEnvironmentInfo:
    uv_python_path: Optional[str] = None
    amplihack_root: Optional[str] = None
    sys_path_entries: List[str] = field(default_factory=list)
    working_directory: Path = field(default_factory=Path.cwd)

# Detection results with reasoning
@dataclass(frozen=True)
class UVXDetectionState:
    result: UVXDetectionResult
    environment: UVXEnvironmentInfo
    detection_reasons: List[str] = field(default_factory=list)

    @property
    def is_uvx_deployment(self) -> bool:
        return self.result == UVXDetectionResult.UVX_DEPLOYMENT
```

### 2. Path Resolution Data

```python
# Resolved framework location
@dataclass(frozen=True)
class FrameworkLocation:
    root_path: Path
    strategy: PathResolutionStrategy
    validation_errors: List[str] = field(default_factory=list)

# Resolution result with attempt history
@dataclass(frozen=True)
class PathResolutionResult:
    location: Optional[FrameworkLocation]
    attempts: List[Dict[str, Union[str, Path, bool]]] = field(default_factory=list)

    @property
    def requires_staging(self) -> bool:
        return (self.location is not None and
                self.location.strategy == PathResolutionStrategy.STAGING_REQUIRED)
```

### 3. Configuration State

```python
@dataclass(frozen=True)
class UVXConfiguration:
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
    cleanup_on_exit: bool = False

    @property
    def is_debug_enabled(self) -> bool:
        if self.debug_enabled is not None:
            return self.debug_enabled
        debug_value = os.environ.get(self.debug_env_var, "").lower()
        return debug_value in ("true", "1", "yes")
```

### 4. Session State Management

```python
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
        return (self.initialized and
                self.detection_state is not None and
                self.detection_state.is_detection_successful and
                self.path_resolution is not None and
                self.path_resolution.is_successful)
```

## Usage Examples

### Basic Detection and Resolution

```python
from amplihack.utils.uvx_detection import detect_uvx_deployment, resolve_framework_paths
from amplihack.utils.uvx_models import UVXConfiguration

# Configure detection
config = UVXConfiguration(debug_enabled=True, allow_staging=True)

# Detect UVX deployment state
detection = detect_uvx_deployment(config)
print(f"UVX deployment: {detection.is_uvx_deployment}")

# Resolve framework paths
resolution = resolve_framework_paths(detection, config)
if resolution.is_successful:
    print(f"Framework root: {resolution.location.root_path}")
```

### Complete Session Management

```python
from amplihack.utils.uvx_staging_v2 import create_uvx_session

# Create complete initialized session
session = create_uvx_session()
if session.is_ready:
    print(f"Session {session.session_id} ready")
    print(f"Framework at: {session.framework_root}")
```

### File Staging with Error Handling

```python
from amplihack.utils.uvx_staging_v2 import UVXStager
from amplihack.utils.uvx_models import UVXConfiguration

config = UVXConfiguration(
    overwrite_existing=False,
    create_backup=True,
    cleanup_on_exit=True
)

stager = UVXStager(config)
result = stager.stage_framework_files()

if result.is_successful:
    print(f"Staged {len(result.successful)} files")
else:
    print(f"Staging failed: {result.failed}")
```

## Benefits

### 1. Type Safety

- All operations are type-safe with proper IDE support
- Compile-time error detection for invalid operations
- Clear API contracts with type hints

### 2. Thread Safety

- Immutable data structures prevent race conditions
- Safe to share between threads without locking
- No hidden mutable state

### 3. Error Handling

- Invalid states are unrepresentable by design
- Clear validation and error reporting
- Detailed failure reasons for debugging

### 4. Security

- Path traversal attacks are automatically blocked
- All file operations stay within framework boundaries
- Null byte injection prevention

### 5. Debuggability

- Easy serialization for debugging
- Complete audit trail of operations
- Session state can be dumped for analysis

### 6. Testability

- Immutable structures are easy to test
- No side effects between tests
- Deterministic behavior

## Migration from Old Code

### Before (Mutable State)

```python
class UVXStager:
    def __init__(self):
        self._staged_files: Set[Path] = set()
        self._debug_enabled = os.environ.get("AMPLIHACK_DEBUG")

    def detect_uvx_deployment(self) -> bool:
        # Returns just True/False, no context
```

### After (Immutable State)

```python
# Clear data structures
detection = detect_uvx_deployment()
print(f"Result: {detection.result.name}")
print(f"Reasons: {detection.detection_reasons}")

# Session management
session = UVXSessionState()
session.initialize_detection(detection)
print(f"Ready: {session.is_ready}")
```

## Files

- **`uvx_models.py`** - Core data structures and type definitions
- **`uvx_detection.py`** - Detection and path resolution logic
- **`uvx_staging_v2.py`** - File staging operations using clean models
- **`test_uvx_models.py`** - Comprehensive tests for data models
- **`test_uvx_detection.py`** - Tests for detection logic
- **`test_uvx_staging_v2.py`** - Tests for staging operations
- **`uvx_models_example.py`** - Complete usage demonstration

## Testing

```bash
# Run all UVX model tests
python -m pytest tests/test_uvx_models.py tests/test_uvx_detection.py tests/test_uvx_staging_v2.py -v

# Run example
python examples/uvx_models_example.py
```

The new UVX data models provide a solid foundation for reliable, maintainable, and secure UVX operations.
