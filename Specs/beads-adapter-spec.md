# Module: BeadsAdapter

## Purpose

Safe, type-safe abstraction over the `bd` CLI tool, providing all beads operations with comprehensive error handling and no external dependencies beyond Python stdlib.

## Contract

### Inputs

- **project_root**: Optional Path to project directory (defaults to current directory)
- **timeout**: Configurable per-operation timeout in seconds
- **CLI arguments**: Type-checked parameters for each beads operation

### Outputs

- **Result types**: All operations return `Result[T, BeadsError]` for explicit error handling
- **JSON parsing**: All CLI outputs parsed into type-safe dataclasses
- **Structured errors**: Specific error types for each failure mode

### Side Effects

- **Subprocess calls**: All operations execute `bd` CLI via subprocess
- **JSONL writes**: Create/update operations trigger beads' auto-sync (5s debounce)
- **SQLite updates**: Beads updates local cache in `.beads/*.db`

## Public API

```python
from pathlib import Path
from typing import List, Optional, Dict
from .models import BeadsIssue, Result, BeadsError

class BeadsAdapter:
    """Safe subprocess wrapper for beads CLI operations.

    Philosophy:
    - Standard library only (subprocess, json, pathlib)
    - All operations return explicit Result types
    - No exceptions for operational failures
    - JSON output mode for all commands
    - Comprehensive timeout handling
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        default_timeout: int = 30,
    ):
        """Initialize adapter.

        Args:
            project_root: Project directory (defaults to cwd)
            default_timeout: Default timeout for CLI operations in seconds
        """
        pass

    def is_installed(self) -> bool:
        """Check if bd CLI is available in PATH.

        Returns:
            True if bd command found, False otherwise
        """
        pass

    def get_version(self) -> Optional[str]:
        """Get installed beads version.

        Returns:
            Version string (e.g., "v0.9.5") or None if not installed
        """
        pass

    def init(self, prefix: str = "bd") -> Result[bool, BeadsError]:
        """Initialize beads in project directory.

        Creates .beads/ directory structure and initial database.

        Args:
            prefix: Issue ID prefix (e.g., "amplihack" → "amplihack-1")

        Returns:
            Result with True on success, BeadsError on failure
        """
        pass

    def is_initialized(self) -> bool:
        """Check if beads is initialized in project.

        Returns:
            True if .beads/ directory exists and valid
        """
        pass

    def create_issue(
        self,
        title: str,
        description: Optional[str] = None,
        issue_type: str = "task",
        priority: int = 2,
        assignee: Optional[str] = None,
        labels: Optional[List[str]] = None,
        explicit_id: Optional[str] = None,
    ) -> Result[BeadsIssue, BeadsError]:
        """Create new issue with full options.

        CLI: bd create "title" -d "desc" -t type -p priority -a assignee -l label1,label2 --id ID --json

        Args:
            title: Issue title (required)
            description: Long-form description
            issue_type: bug|feature|task|epic|chore (default: task)
            priority: 0-4 (0=highest, 2=default, 4=lowest)
            assignee: Username to assign
            labels: List of label strings
            explicit_id: Force specific ID (for parallel agent coordination)

        Returns:
            Result with BeadsIssue on success, BeadsError on failure
        """
        pass

    def get_issue(self, issue_id: str) -> Result[BeadsIssue, BeadsError]:
        """Retrieve issue by ID.

        CLI: bd show ID --json

        Args:
            issue_id: Issue identifier (e.g., "bd-42")

        Returns:
            Result with BeadsIssue on success, BeadsError if not found
        """
        pass

    def list_issues(
        self,
        status: Optional[str] = None,
        priority: Optional[int] = None,
        assignee: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> Result[List[BeadsIssue], BeadsError]:
        """Query issues with filters.

        CLI: bd list --status STATUS --priority N --assignee USER --json

        Args:
            status: Filter by status (open|in_progress|closed)
            priority: Filter by exact priority (0-4)
            assignee: Filter by assignee username
            labels: Filter by labels (any match)

        Returns:
            Result with list of BeadsIssue on success, BeadsError on failure
        """
        pass

    def update_issue(
        self,
        issue_id: str,
        status: Optional[str] = None,
        priority: Optional[int] = None,
        assignee: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Result[BeadsIssue, BeadsError]:
        """Update issue fields.

        CLI: bd update ID --status STATUS --priority N --assignee USER --json

        Args:
            issue_id: Issue to update
            status: New status
            priority: New priority
            assignee: New assignee
            title: New title
            description: New description

        Returns:
            Result with updated BeadsIssue on success, BeadsError on failure
        """
        pass

    def close_issue(
        self, issue_id: str, reason: Optional[str] = None
    ) -> Result[bool, BeadsError]:
        """Close issue with optional reason.

        CLI: bd close ID --reason "text" --json

        Args:
            issue_id: Issue to close
            reason: Closing reason (added to audit log)

        Returns:
            Result with True on success, BeadsError on failure
        """
        pass

    def delete_issue(
        self,
        issue_id: str,
        force: bool = False,
        cascade: bool = False,
    ) -> Result[bool, BeadsError]:
        """Delete issue with dependency handling.

        CLI: bd delete ID [--force] [--cascade] --json

        Args:
            issue_id: Issue to delete
            force: Skip confirmation
            cascade: Delete dependents too

        Returns:
            Result with True on success, BeadsError on failure
        """
        pass

    def add_dependency(
        self, child_id: str, parent_id: str, dep_type: str = "blocks"
    ) -> Result[bool, BeadsError]:
        """Add dependency relationship.

        CLI: bd dep add CHILD PARENT --type TYPE --json

        Args:
            child_id: Dependent issue (blocked by parent)
            parent_id: Blocking issue
            dep_type: blocks|related|parent-child|discovered-from

        Returns:
            Result with True on success, BeadsError on failure
        """
        pass

    def remove_dependency(
        self, child_id: str, parent_id: str
    ) -> Result[bool, BeadsError]:
        """Remove dependency relationship.

        CLI: bd dep remove CHILD PARENT --json

        Args:
            child_id: Dependent issue
            parent_id: Blocking issue

        Returns:
            Result with True on success, BeadsError on failure
        """
        pass

    def get_dependency_tree(self, issue_id: str) -> Result[Dict, BeadsError]:
        """Get full dependency graph for issue.

        CLI: bd dep tree ID --json

        Args:
            issue_id: Root issue for tree

        Returns:
            Result with tree structure dict on success, BeadsError on failure
        """
        pass

    def get_ready_work(
        self,
        limit: Optional[int] = None,
        priority: Optional[int] = None,
        assignee: Optional[str] = None,
    ) -> Result[List[BeadsIssue], BeadsError]:
        """Find issues with no open blockers.

        CLI: bd ready --limit N --priority P --assignee USER --json

        Args:
            limit: Maximum results
            priority: Filter by priority
            assignee: Filter by assignee

        Returns:
            Result with list of unblocked issues on success, BeadsError on failure
        """
        pass

    def get_blocked_issues(self) -> Result[List[BeadsIssue], BeadsError]:
        """Find issues blocked by open dependencies.

        CLI: bd blocked --json

        Returns:
            Result with list of blocked issues on success, BeadsError on failure
        """
        pass

    def get_stats(self) -> Result[Dict, BeadsError]:
        """Get database statistics.

        CLI: bd stats --json

        Returns:
            Result with stats dict on success, BeadsError on failure
        """
        pass

    # Private methods

    def _run_command(
        self,
        args: List[str],
        timeout: Optional[int] = None,
    ) -> Result[Dict, BeadsError]:
        """Execute bd CLI command and parse JSON output.

        Args:
            args: Command arguments (e.g., ["create", "title", "--json"])
            timeout: Operation timeout in seconds

        Returns:
            Result with parsed JSON dict on success, BeadsError on failure
        """
        pass

    def _validate_issue_type(self, issue_type: str) -> bool:
        """Validate issue type is one of allowed values."""
        pass

    def _validate_priority(self, priority: int) -> bool:
        """Validate priority is in range 0-4."""
        pass

    def _validate_status(self, status: str) -> bool:
        """Validate status is one of allowed values."""
        pass

    def _validate_dep_type(self, dep_type: str) -> bool:
        """Validate dependency type is one of allowed values."""
        pass
```

## Dependencies

### Standard Library

- `subprocess`: Execute bd CLI commands
- `json`: Parse CLI JSON output
- `pathlib`: File and directory handling
- `typing`: Type hints
- `shutil`: Check for bd in PATH

### Internal Modules

- `models.py`: BeadsIssue, BeadsError, Result types
- `utils.prerequisites` (optional): Reuse safe_subprocess_call pattern

## Implementation Notes

### Error Mapping

```python
# Subprocess errors → BeadsError types
subprocess.FileNotFoundError → BeadsNotInstalledError
returncode == 1, "not initialized" in stderr → BeadsNotInitializedError
returncode != 0 → BeadsCLIError(cmd, returncode, stderr)
json.JSONDecodeError → BeadsParseError
subprocess.TimeoutExpired → BeadsTimeoutError
```

### CLI Command Construction

```python
def _build_create_command(self, title: str, **kwargs) -> List[str]:
    """Build bd create command with all options."""
    cmd = ["bd", "create", title]

    if kwargs.get("description"):
        cmd.extend(["-d", kwargs["description"]])

    if kwargs.get("issue_type"):
        cmd.extend(["-t", kwargs["issue_type"]])

    if kwargs.get("priority") is not None:
        cmd.extend(["-p", str(kwargs["priority"])])

    if kwargs.get("assignee"):
        cmd.extend(["-a", kwargs["assignee"]])

    if kwargs.get("labels"):
        cmd.extend(["-l", ",".join(kwargs["labels"])])

    if kwargs.get("explicit_id"):
        cmd.extend(["--id", kwargs["explicit_id"]])

    cmd.append("--json")  # Always use JSON mode
    return cmd
```

### JSON Parsing

```python
def _parse_issue_response(self, data: Dict) -> BeadsIssue:
    """Parse bd CLI JSON output into BeadsIssue."""
    # Handle envelope format
    if "success" in data:
        if not data["success"]:
            raise BeadsCLIError(
                cmd="unknown",
                returncode=1,
                stderr=data.get("error", "Unknown error"),
            )
        data = data["data"]

    # Parse issue object
    return BeadsIssue.from_json(data)
```

### Timeout Configuration

```python
# Per-operation timeouts (seconds)
OPERATION_TIMEOUTS = {
    "create": 5,
    "update": 5,
    "list": 10,
    "ready": 10,
    "show": 5,
    "close": 5,
    "delete": 10,
    "dep add": 5,
    "dep tree": 10,
    "compact": 120,  # AI operations take longer
    "stats": 5,
}
```

### Validation

```python
VALID_ISSUE_TYPES = {"bug", "feature", "task", "epic", "chore"}
VALID_PRIORITIES = {0, 1, 2, 3, 4}
VALID_STATUSES = {"open", "in_progress", "closed"}
VALID_DEP_TYPES = {"blocks", "related", "parent-child", "discovered-from"}
```

## Test Requirements

### Unit Tests (60%)

- ✅ is_installed() detects bd in PATH
- ✅ get_version() parses version string
- ✅ Command construction for all operations
- ✅ JSON parsing with valid responses
- ✅ Error mapping for all failure modes
- ✅ Validation for issue_type, priority, status, dep_type
- ✅ Timeout handling

### Integration Tests (30%)

- ✅ Full CRUD cycle (create → read → update → delete)
- ✅ Dependency operations (add, remove, tree)
- ✅ Ready work detection
- ✅ Blocked issues query
- ✅ Multi-issue operations
- ✅ Error recovery

### E2E Tests (10%)

- ✅ Initialize new project
- ✅ Create workflow of dependent issues
- ✅ Close issues in correct order
- ✅ Verify JSONL and SQLite consistency

## Usage Examples

### Basic Issue Creation

```python
from amplihack.beads import BeadsAdapter

adapter = BeadsAdapter()

if not adapter.is_installed():
    print("Please install beads: go install github.com/steveyegge/beads/cmd/bd@latest")
    exit(1)

if not adapter.is_initialized():
    result = adapter.init(prefix="amplihack")
    if result.is_err:
        print(f"Init failed: {result.error}")
        exit(1)

# Create issue
result = adapter.create_issue(
    title="Implement authentication",
    description="Add JWT-based auth",
    issue_type="feature",
    priority=1,
    labels=["security", "api"],
)

if result.is_ok:
    issue = result.value
    print(f"Created issue: {issue.id}")
else:
    print(f"Failed: {result.error}")
```

### Dependency Management

```python
# Create parent and child issues
parent = adapter.create_issue(
    title="Design API",
    issue_type="task",
    priority=0,
).unwrap()

child = adapter.create_issue(
    title="Implement API",
    issue_type="feature",
    priority=1,
).unwrap()

# Link dependency
adapter.add_dependency(
    child_id=child.id,
    parent_id=parent.id,
    dep_type="blocks",
).unwrap()

# Check ready work (child won't appear until parent closed)
ready = adapter.get_ready_work().unwrap()
print(f"Ready issues: {[i.id for i in ready]}")

# Close parent
adapter.close_issue(parent.id, reason="Design complete").unwrap()

# Now child is ready
ready = adapter.get_ready_work().unwrap()
assert child.id in [i.id for i in ready]
```

### Error Handling

```python
# Graceful error handling with Result type
result = adapter.get_issue("nonexistent-id")

if result.is_ok:
    issue = result.value
    print(f"Found: {issue.title}")
elif isinstance(result.error, BeadsNotFoundError):
    print("Issue does not exist")
elif isinstance(result.error, BeadsCLIError):
    print(f"CLI error: {result.error.stderr}")
else:
    print(f"Unexpected error: {result.error}")

# Or use unwrap_or for default values
issue = adapter.get_issue("maybe-exists").unwrap_or(None)
```

## Performance Considerations

- **Batch operations**: Use explicit_id to create multiple issues in parallel
- **Caching**: Beads caches in SQLite, repeated queries are fast
- **JSONL sync**: 5-second debounce means rapid creates don't spam git
- **Timeout tuning**: Increase timeout for large repos or slow disks

## Philosophy Compliance

- ✅ **Ruthless Simplicity**: Uses subprocess directly, no abstractions
- ✅ **Standard Library Only**: No dependencies beyond Python stdlib
- ✅ **Zero-BS**: All operations work or return explicit errors
- ✅ **Regeneratable**: Clear contract enables AI reconstruction
- ✅ **Bricks & Studs**: Self-contained module with clean public API
