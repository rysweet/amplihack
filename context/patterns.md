# Amplihack Proven Patterns

14 battle-tested patterns for robust, maintainable AI-assisted development.

## 1. Bricks & Studs Module Design

**Problem**: Modules become entangled, making changes risky and regeneration impossible.

**Pattern**: Design every module as a self-contained brick with clear studs (interfaces).

```
module_name/
├── __init__.py       # Public interface ONLY (the studs)
├── README.md         # Contract specification
├── core.py           # Main implementation (internal)
├── models.py         # Data structures
└── tests/            # Self-contained tests
```

**Rules**:
- `__init__.py` exports ONLY public interface via `__all__`
- Internal helpers use `_prefix` naming
- No reaching into other modules' internals
- Tests run without external setup

**Anti-pattern**: Importing `from other_module.core._internal import helper`

---

## 2. Zero-BS Implementation

**Problem**: Codebases accumulate stubs, TODOs, and placeholder code that never gets finished.

**Pattern**: Every function must work completely or not exist at all.

**Checklist**:
- [ ] No `pass` statements in production code (except abstract methods)
- [ ] No `# TODO` or `# FIXME` comments
- [ ] No `raise NotImplementedError()` except in abstract base classes
- [ ] No mock implementations outside test files
- [ ] No swallowed exceptions (`except: pass`)
- [ ] No commented-out code

**Instead of**:
```python
def process_data(data):
    # TODO: implement this later
    pass
```

**Do**:
```python
# Don't create the function until you implement it
# Or implement a minimal working version:
def process_data(data):
    if not data:
        return []
    return [item.strip() for item in data]
```

---

## 3. API Validation Before Implementation

**Problem**: Building against an API that doesn't work as expected wastes significant time.

**Pattern**: Always validate external APIs before writing integration code.

```python
# Step 1: Manual validation
async def validate_api():
    """Run this first to confirm API behavior"""
    response = await client.get("/endpoint")
    print(f"Status: {response.status}")
    print(f"Headers: {response.headers}")
    print(f"Body: {response.json()}")
    # Verify: Does this match documentation?

# Step 2: Only after validation, write integration
async def integration_code():
    """Now safe to implement"""
    ...
```

**Checklist**:
1. Read API documentation
2. Make manual test request
3. Verify response format matches docs
4. Check error responses
5. Then implement integration

---

## 4. Safe Subprocess Wrapper

**Problem**: Raw subprocess calls are error-prone, insecure, and inconsistent.

**Pattern**: Always wrap subprocess execution with safety and consistency.

```python
import subprocess
import shlex
from pathlib import Path

def run_command(
    cmd: str | list[str],
    cwd: Path | None = None,
    timeout: int = 30,
    check: bool = True,
    capture: bool = True
) -> subprocess.CompletedProcess:
    """Safe subprocess wrapper with consistent behavior.
    
    Args:
        cmd: Command string or list of arguments
        cwd: Working directory
        timeout: Max execution time in seconds
        check: Raise on non-zero exit
        capture: Capture stdout/stderr
    
    Returns:
        CompletedProcess with stdout/stderr
    
    Raises:
        subprocess.TimeoutExpired: Command exceeded timeout
        subprocess.CalledProcessError: Non-zero exit (if check=True)
    """
    if isinstance(cmd, str):
        args = shlex.split(cmd)
    else:
        args = cmd
    
    return subprocess.run(
        args,
        cwd=cwd,
        timeout=timeout,
        check=check,
        capture_output=capture,
        text=True
    )
```

**Never do**:
```python
os.system(f"rm -rf {user_input}")  # Command injection!
subprocess.run(cmd, shell=True)    # Shell injection risk
```

---

## 5. Fail-Fast Prerequisite Checking

**Problem**: Operations fail deep in execution with unclear errors.

**Pattern**: Check all prerequisites upfront before any work begins.

```python
def deploy_application(config: DeployConfig) -> DeployResult:
    """Deploy with fail-fast validation."""
    
    # Phase 1: Validate ALL prerequisites first
    errors = []
    
    if not config.target_host:
        errors.append("target_host is required")
    
    if not Path(config.artifact_path).exists():
        errors.append(f"Artifact not found: {config.artifact_path}")
    
    if not check_ssh_access(config.target_host):
        errors.append(f"Cannot SSH to {config.target_host}")
    
    if not check_disk_space(config.target_host, min_gb=5):
        errors.append(f"Insufficient disk space on {config.target_host}")
    
    if errors:
        raise DeploymentError(
            "Prerequisites not met:\n" + "\n".join(f"  - {e}" for e in errors)
        )
    
    # Phase 2: Only now do actual work
    return _do_deployment(config)
```

**Benefits**:
- Users see all problems at once
- No partial state from mid-operation failures
- Clear error messages

---

## 6. Resilient Batch Processing

**Problem**: One failure in a batch kills the entire operation.

**Pattern**: Process items independently, collect results and errors separately.

```python
from dataclasses import dataclass
from typing import TypeVar, Generic

T = TypeVar('T')
R = TypeVar('R')

@dataclass
class BatchResult(Generic[T, R]):
    succeeded: list[tuple[T, R]]
    failed: list[tuple[T, Exception]]
    
    @property
    def success_count(self) -> int:
        return len(self.succeeded)
    
    @property
    def failure_count(self) -> int:
        return len(self.failed)
    
    @property
    def all_succeeded(self) -> bool:
        return self.failure_count == 0

def process_batch(
    items: list[T],
    processor: Callable[[T], R],
    continue_on_error: bool = True
) -> BatchResult[T, R]:
    """Process items with resilience."""
    result = BatchResult(succeeded=[], failed=[])
    
    for item in items:
        try:
            output = processor(item)
            result.succeeded.append((item, output))
        except Exception as e:
            result.failed.append((item, e))
            if not continue_on_error:
                break
    
    return result
```

---

## 7. TDD Testing Pyramid (60/30/10)

**Problem**: Test suites are slow, brittle, or don't catch real bugs.

**Pattern**: Follow the testing pyramid with specific ratios.

```
        /\
       /  \     10% E2E Tests (critical paths only)
      /----\
     /      \   30% Integration Tests (module boundaries)
    /--------\
   /          \ 60% Unit Tests (pure functions, logic)
  --------------
```

**Unit Tests (60%)**:
```python
def test_calculate_discount():
    """Pure logic, no I/O, fast"""
    assert calculate_discount(100, 0.1) == 90
    assert calculate_discount(100, 0) == 100
```

**Integration Tests (30%)**:
```python
async def test_user_service_creates_user(db_session):
    """Tests module boundary with real dependencies"""
    service = UserService(db_session)
    user = await service.create_user("test@example.com")
    assert user.id is not None
```

**E2E Tests (10%)**:
```python
async def test_signup_flow(browser):
    """Critical user journey only"""
    await browser.goto("/signup")
    await browser.fill("#email", "test@example.com")
    await browser.click("#submit")
    assert await browser.is_visible(".welcome-message")
```

---

## 8. Graceful Environment Adaptation

**Problem**: Code fails when environment differs from development setup.

**Pattern**: Detect and adapt to environment gracefully.

```python
import os
import sys
from pathlib import Path

class Environment:
    """Graceful environment detection and adaptation."""
    
    @staticmethod
    def get_config_dir() -> Path:
        """Get config directory, creating if needed."""
        if xdg := os.environ.get("XDG_CONFIG_HOME"):
            base = Path(xdg)
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        elif sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", Path.home()))
        else:
            base = Path.home() / ".config"
        
        config_dir = base / "myapp"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
    
    @staticmethod
    def get_optional_dependency(name: str):
        """Import optional dependency gracefully."""
        try:
            return __import__(name)
        except ImportError:
            return None
```

---

## 9. Intelligent Caching

**Problem**: Caching is either missing (slow) or stale (incorrect).

**Pattern**: Cache with explicit invalidation strategies.

```python
from functools import lru_cache
from datetime import datetime, timedelta
from typing import TypeVar, Callable

T = TypeVar('T')

class TTLCache:
    """Simple time-based cache."""
    
    def __init__(self, ttl_seconds: int = 300):
        self._cache: dict[str, tuple[datetime, any]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)
    
    def get(self, key: str) -> any | None:
        if key in self._cache:
            timestamp, value = self._cache[key]
            if datetime.now() - timestamp < self._ttl:
                return value
            del self._cache[key]
        return None
    
    def set(self, key: str, value: any) -> None:
        self._cache[key] = (datetime.now(), value)
    
    def invalidate(self, key: str) -> None:
        self._cache.pop(key, None)
    
    def clear(self) -> None:
        self._cache.clear()

# Usage
config_cache = TTLCache(ttl_seconds=60)

def get_config(key: str) -> str:
    if cached := config_cache.get(key):
        return cached
    value = load_config_from_disk(key)
    config_cache.set(key, value)
    return value
```

---

## 10. File I/O with Cloud Sync Resilience

**Problem**: File operations fail mysteriously when cloud sync (iCloud, Dropbox) interferes.

**Pattern**: Handle cloud sync edge cases explicitly.

```python
import time
from pathlib import Path

def write_file_safely(path: Path, content: str, max_retries: int = 3) -> None:
    """Write file with cloud sync resilience.
    
    Handles common issues:
    - File locked by sync process
    - Directory not yet created by sync
    - Temporary sync conflicts
    """
    path = Path(path)
    
    for attempt in range(max_retries):
        try:
            # Ensure directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temp file first
            temp_path = path.with_suffix(f".tmp.{os.getpid()}")
            temp_path.write_text(content, encoding="utf-8")
            
            # Atomic rename
            temp_path.rename(path)
            return
            
        except OSError as e:
            if attempt < max_retries - 1:
                time.sleep(0.5 * (attempt + 1))  # Exponential backoff
            else:
                raise IOError(f"Failed to write {path} after {max_retries} attempts: {e}")

def read_file_safely(path: Path, max_retries: int = 3) -> str:
    """Read file with cloud sync resilience."""
    path = Path(path)
    
    for attempt in range(max_retries):
        try:
            return path.read_text(encoding="utf-8")
        except OSError as e:
            if attempt < max_retries - 1:
                time.sleep(0.5 * (attempt + 1))
            else:
                raise IOError(f"Failed to read {path} after {max_retries} attempts: {e}")
```

---

## 11. System Metadata vs User Content Classification

**Problem**: System metadata and user content get mixed, causing confusion and bugs.

**Pattern**: Explicitly classify and separate metadata from content.

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass
class Document:
    """Clear separation of system and user data."""
    
    # User content - what the user created/controls
    title: str
    body: str
    tags: list[str] = field(default_factory=list)
    
    # System metadata - managed by system
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version: int = 1
    
    def to_user_dict(self) -> dict[str, Any]:
        """Export only user-editable fields."""
        return {
            "title": self.title,
            "body": self.body,
            "tags": self.tags,
        }
    
    def to_full_dict(self) -> dict[str, Any]:
        """Export everything including system metadata."""
        return {
            **self.to_user_dict(),
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
        }
```

---

## 12. Explicit Error Context

**Problem**: Errors are caught but context is lost.

**Pattern**: Always add context when re-raising or logging errors.

```python
class ContextualError(Exception):
    """Error with explicit context."""
    
    def __init__(self, message: str, context: dict | None = None, cause: Exception | None = None):
        super().__init__(message)
        self.context = context or {}
        self.cause = cause
    
    def __str__(self):
        parts = [super().__str__()]
        if self.context:
            parts.append(f"Context: {self.context}")
        if self.cause:
            parts.append(f"Caused by: {self.cause}")
        return " | ".join(parts)

# Usage
def process_user(user_id: str) -> User:
    try:
        data = fetch_user_data(user_id)
        return parse_user(data)
    except ValidationError as e:
        raise ContextualError(
            "Failed to process user",
            context={"user_id": user_id, "stage": "parsing"},
            cause=e
        )
```

---

## 13. Configuration Layering

**Problem**: Configuration comes from multiple sources with unclear precedence.

**Pattern**: Explicit configuration layers with clear override order.

```python
from dataclasses import dataclass, field
from pathlib import Path
import os
import yaml

@dataclass
class Config:
    """Layered configuration with explicit precedence."""
    
    # Defaults (lowest precedence)
    timeout: int = 30
    max_retries: int = 3
    log_level: str = "INFO"
    
    @classmethod
    def load(cls, config_file: Path | None = None) -> "Config":
        """Load config with precedence: env > file > defaults"""
        config = cls()
        
        # Layer 1: File config (if exists)
        if config_file and config_file.exists():
            file_config = yaml.safe_load(config_file.read_text())
            for key, value in file_config.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        # Layer 2: Environment variables (highest precedence)
        env_map = {
            "APP_TIMEOUT": "timeout",
            "APP_MAX_RETRIES": "max_retries",
            "APP_LOG_LEVEL": "log_level",
        }
        for env_var, attr in env_map.items():
            if value := os.environ.get(env_var):
                # Type coercion based on default type
                default = getattr(config, attr)
                if isinstance(default, int):
                    value = int(value)
                setattr(config, attr, value)
        
        return config
```

---

## 14. Idempotent Operations

**Problem**: Operations fail midway and can't be safely retried.

**Pattern**: Design all operations to be safely re-runnable.

```python
def ensure_user_exists(user_id: str, email: str) -> User:
    """Idempotent user creation - safe to call multiple times.
    
    Returns existing user if already exists, creates if not.
    """
    # Check if already exists
    if existing := db.users.get(user_id):
        return existing
    
    # Create new user
    user = User(id=user_id, email=email)
    
    # Use upsert to handle race conditions
    db.users.upsert(user)
    
    return user

def migrate_data(batch_id: str) -> MigrationResult:
    """Idempotent migration - tracks progress and resumes."""
    
    # Check what's already done
    progress = db.migrations.get(batch_id) or MigrationProgress(batch_id)
    
    # Skip already-processed items
    remaining = [
        item for item in get_items(batch_id)
        if item.id not in progress.completed_ids
    ]
    
    for item in remaining:
        process_item(item)
        progress.completed_ids.add(item.id)
        db.migrations.save(progress)  # Checkpoint after each item
    
    return MigrationResult(
        batch_id=batch_id,
        total=len(get_items(batch_id)),
        processed=len(progress.completed_ids)
    )
```

---

## Pattern Selection Guide

| Situation | Patterns to Apply |
|-----------|------------------|
| Starting new module | #1 Bricks & Studs, #2 Zero-BS |
| External integration | #3 API Validation, #4 Safe Subprocess |
| Complex operation | #5 Fail-Fast, #14 Idempotent |
| Processing lists | #6 Resilient Batch |
| Writing tests | #7 Testing Pyramid |
| Cross-platform | #8 Environment Adaptation |
| Performance issues | #9 Intelligent Caching |
| File operations | #10 Cloud Sync Resilience |
| Data modeling | #11 Metadata Classification |
| Error handling | #12 Explicit Context |
| App settings | #13 Configuration Layering |
