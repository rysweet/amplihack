# Beads Memory System Integration Architecture

## Executive Summary

This document specifies the complete architecture for integrating the beads memory system into amplihack. Beads provides persistent, git-distributed agent memory through a hybrid SQLite+JSONL architecture, solving the "agent amnesia" problem where agents lose context between sessions.

**Critical Constraint**: User explicitly requested full beads integration with persistent agent memory, graph-based issue tracking, and git-distributed state. These requirements CANNOT be simplified away.

## Architecture Overview

### Design Philosophy Alignment

The beads integration follows amplihack's core principles:

1. **Ruthless Simplicity**: Start with CLI wrapper, defer MCP server to later phase
2. **Zero-BS Implementation**: All operations work or fail explicitly, no stubs
3. **Bricks & Studs**: Each module is self-contained with clear public interfaces
4. **Standard Library Only**: Core modules use subprocess for CLI calls, no heavy dependencies
5. **Regeneratable**: Clear specifications enable AI reconstruction

### Integration Strategy

**Phased Approach**:

- **Phase 1 (MVP)**: CLI adapter + memory provider + workflow integration
- **Phase 2**: Dependency management + ready work detection
- **Phase 3**: Advanced features (compaction, cross-project)

**Non-Goals for MVP**:

- MCP server implementation (beads has routing bugs)
- Multi-project support (alpha version limitation)
- Custom beads modifications (upstream dependency)

## System Components

### Component Hierarchy

```
amplihack/
├── beads/                          # New beads integration package
│   ├── __init__.py                # Public API exports
│   ├── adapter.py                 # CLI wrapper (Brick #1)
│   ├── provider.py                # Memory provider (Brick #2)
│   ├── models.py                  # Data classes (Brick #3)
│   ├── sync.py                    # Git coordination (Brick #4)
│   ├── workflow_integration.py    # Workflow hooks (Brick #5)
│   └── exceptions.py              # Error types
└── memory/                         # Existing memory system
    ├── manager.py                 # Updated to support providers
    └── providers/                  # New provider interface
        ├── __init__.py
        └── base.py                 # Provider protocol
```

### Data Flow Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Amplihack Session                        │
│                                                              │
│  ┌────────────┐      ┌─────────────┐     ┌──────────────┐  │
│  │  Agents    │ ───▶ │   Memory    │ ──▶ │   Beads      │  │
│  │ (architect,│      │   Manager   │     │   Provider   │  │
│  │  builder,  │ ◀─── │             │ ◀── │              │  │
│  │  reviewer) │      └─────────────┘     └──────────────┘  │
│  └────────────┘                                │            │
│                                                │            │
└────────────────────────────────────────────────│────────────┘
                                                 │
                                                 ▼
                                          ┌─────────────┐
                                          │    Beads    │
                                          │   Adapter   │
                                          └──────┬──────┘
                                                 │
                                                 ▼
                                          ┌─────────────┐
                                          │  bd CLI     │
                                          │  (Go)       │
                                          └──────┬──────┘
                                                 │
                         ┌───────────────────────┼───────────────────────┐
                         │                       │                       │
                         ▼                       ▼                       ▼
                  ┌────────────┐         ┌────────────┐         ┌────────────┐
                  │  SQLite    │ ◀───▶   │   JSONL    │ ───▶    │    Git     │
                  │  (.beads/  │  sync   │  (.beads/  │ commit  │ (remote)   │
                  │  *.db)     │         │  *.jsonl)  │         │            │
                  └────────────┘         └────────────┘         └────────────┘
                   Local cache           Source of truth        Distributed
                   (gitignored)          (committed)            sync
```

## Module Specifications

### Brick #1: BeadsAdapter (adapter.py)

**Purpose**: Safe abstraction over `bd` CLI with comprehensive error handling.

**Public Interface (Studs)**:

```python
class BeadsAdapter:
    """Safe subprocess wrapper for beads CLI operations.

    Philosophy:
    - Standard library only (subprocess)
    - All operations return explicit Result types
    - No exceptions for operational failures
    - JSON output mode for all commands
    """

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize adapter with optional project root."""

    def is_installed(self) -> bool:
        """Check if bd CLI is available."""

    def get_version(self) -> Optional[str]:
        """Get installed beads version."""

    def init(self, prefix: str = "bd") -> Result[bool, BeadsError]:
        """Initialize beads in project directory."""

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
        """Create new issue with full options."""

    def get_issue(self, issue_id: str) -> Result[BeadsIssue, BeadsError]:
        """Retrieve issue by ID."""

    def list_issues(
        self,
        status: Optional[str] = None,
        priority: Optional[int] = None,
        assignee: Optional[str] = None,
    ) -> Result[List[BeadsIssue], BeadsError]:
        """Query issues with filters."""

    def update_issue(
        self,
        issue_id: str,
        status: Optional[str] = None,
        priority: Optional[int] = None,
        assignee: Optional[str] = None,
    ) -> Result[BeadsIssue, BeadsError]:
        """Update issue fields."""

    def close_issue(
        self, issue_id: str, reason: Optional[str] = None
    ) -> Result[bool, BeadsError]:
        """Close issue with optional reason."""

    def add_dependency(
        self, child_id: str, parent_id: str, dep_type: str = "blocks"
    ) -> Result[bool, BeadsError]:
        """Add dependency relationship."""

    def get_ready_work(
        self,
        limit: Optional[int] = None,
        priority: Optional[int] = None,
        assignee: Optional[str] = None,
    ) -> Result[List[BeadsIssue], BeadsError]:
        """Find issues with no open blockers."""

    def get_blocked_issues(self) -> Result[List[BeadsIssue], BeadsError]:
        """Find issues blocked by open dependencies."""

    def get_dependency_tree(self, issue_id: str) -> Result[Dict, BeadsError]:
        """Get full dependency graph for issue."""
```

**Error Handling Strategy**:

- Uses `Result[T, E]` type (success/error) - no exceptions for operational failures
- Maps subprocess errors to BeadsError types:
  - `BeadsNotInstalledError`: bd CLI not found in PATH
  - `BeadsNotInitializedError`: .beads/ directory missing
  - `BeadsCLIError`: CLI returned non-zero exit code
  - `BeadsParseError`: JSON output parsing failed
  - `BeadsTimeoutError`: Command exceeded timeout

**Implementation Notes**:

- All CLI calls use `--json` flag for machine-readable output
- Timeout: 30 seconds default, configurable per operation
- Environment variables: `$BEADS_DB` for custom db path override
- Platform-agnostic: Works on macOS, Linux, WSL
- Subprocess wrapper from PATTERNS.md (safe_subprocess_call)

**Dependencies**:

- Python stdlib: subprocess, pathlib, json, dataclasses
- Internal: models.py (BeadsIssue, BeadsError types)

---

### Brick #2: BeadsMemoryProvider (provider.py)

**Purpose**: Bridge between amplihack's MemoryManager and beads issue tracking.

**Public Interface (Studs)**:

```python
class BeadsMemoryProvider:
    """Memory provider that stores agent memories as beads issues.

    Philosophy:
    - Implements memory provider protocol
    - Maps memory entries to beads issues
    - Maintains bidirectional sync
    - Handles session restoration

    Mapping Strategy:
    - MemoryEntry → BeadsIssue
    - session_id → beads workstream (via labels)
    - memory_type → issue labels
    - importance → priority (scale conversion)
    - tags → issue labels
    """

    def __init__(self, adapter: BeadsAdapter, workstream: str = "main"):
        """Initialize provider with beads adapter."""

    def store_memory(
        self,
        agent_id: str,
        title: str,
        content: str,
        memory_type: str,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
        importance: Optional[int] = None,
    ) -> Result[str, ProviderError]:
        """Store memory as beads issue."""

    def retrieve_memories(
        self,
        agent_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> Result[List[MemoryEntry], ProviderError]:
        """Retrieve memories from beads issues."""

    def restore_session(
        self, session_id: str
    ) -> Result[List[MemoryEntry], ProviderError]:
        """Restore all memories from previous session."""

    def get_session_context(self) -> Result[SessionContext, ProviderError]:
        """Get current session's memory context."""

    def mark_memory_accessed(self, memory_id: str) -> Result[bool, ProviderError]:
        """Update last accessed timestamp."""

    def link_memories(
        self, child_id: str, parent_id: str, relationship: str = "related"
    ) -> Result[bool, ProviderError]:
        """Create dependency link between memories."""
```

**Mapping Rules**:

```python
# Memory importance (1-10) → Beads priority (0-4)
IMPORTANCE_TO_PRIORITY = {
    (9, 10): 0,  # Critical
    (7, 8): 1,   # High
    (4, 6): 2,   # Medium (default)
    (2, 3): 3,   # Low
    (1, 1): 4,   # Very low
}

# Memory types → Beads issue types
MEMORY_TYPE_MAP = {
    "conversation": "task",
    "decision": "feature",
    "pattern": "chore",
    "context": "task",
    "learning": "chore",
    "artifact": "task",
}

# Session tracking via labels
# e.g., "session:20251018_143052", "agent:architect", "memory:decision"
```

**Implementation Notes**:

- Store beads issue ID in MemoryEntry.metadata["beads_issue_id"]
- Use issue description for memory content (supports markdown)
- Store metadata as JSON in issue metadata field
- Session restoration queries by session label + open status
- Batch operations for efficiency (create multiple issues in parallel)

**Dependencies**:

- adapter.py (BeadsAdapter)
- models.py (BeadsIssue, MemoryEntry conversions)
- amplihack.memory.models (MemoryEntry, MemoryType)

---

### Brick #3: Data Models (models.py)

**Purpose**: Type-safe data structures for beads integration.

**Public Interface (Studs)**:

```python
@dataclass
class BeadsIssue:
    """Beads issue with full metadata.

    Parsed from bd CLI --json output.
    """
    id: str
    title: str
    description: str
    issue_type: str  # bug, feature, task, epic, chore
    priority: int  # 0-4
    status: str  # open, in_progress, closed
    assignee: Optional[str]
    labels: List[str]
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
    blockers: List[str]  # Issue IDs blocking this
    dependents: List[str]  # Issue IDs depending on this
    audit_log: List[AuditEntry]

    @classmethod
    def from_json(cls, data: Dict) -> "BeadsIssue":
        """Parse from bd --json output."""

    def to_memory_entry(self, session_id: str) -> MemoryEntry:
        """Convert to MemoryEntry for amplihack."""

    def is_ready(self) -> bool:
        """Check if issue has no open blockers."""

@dataclass
class BeadsDependency:
    """Dependency relationship between issues."""
    from_id: str
    to_id: str
    dep_type: str  # blocks, related, parent-child, discovered-from
    created_at: datetime

@dataclass
class AuditEntry:
    """Single audit log entry."""
    timestamp: datetime
    action: str
    actor: str
    changes: Dict[str, Any]

@dataclass
class SessionContext:
    """Restored session context from beads."""
    session_id: str
    memories: List[MemoryEntry]
    active_agents: List[str]
    open_issues: List[BeadsIssue]
    ready_work: List[BeadsIssue]
    created_at: datetime
    last_accessed: datetime

# Error types
class BeadsError(Exception):
    """Base error for beads operations."""
    pass

class BeadsNotInstalledError(BeadsError):
    """bd CLI not found in PATH."""
    pass

class BeadsNotInitializedError(BeadsError):
    """Project not initialized with beads."""
    pass

class BeadsCLIError(BeadsError):
    """CLI command failed."""
    def __init__(self, cmd: str, returncode: int, stderr: str):
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr

class BeadsParseError(BeadsError):
    """Failed to parse CLI output."""
    pass

class BeadsTimeoutError(BeadsError):
    """Command exceeded timeout."""
    pass

# Result type for safe error handling
@dataclass
class Result:
    """Generic result type (like Rust Result<T, E>)."""
    value: Optional[Any]
    error: Optional[Exception]

    @property
    def is_ok(self) -> bool:
        return self.error is None

    @property
    def is_err(self) -> bool:
        return self.error is not None

    def unwrap(self) -> Any:
        """Get value or raise error."""
        if self.is_err:
            raise self.error
        return self.value

    def unwrap_or(self, default: Any) -> Any:
        """Get value or default."""
        return self.value if self.is_ok else default
```

**Implementation Notes**:

- All datetime fields use ISO 8601 format for JSON serialization
- BeadsIssue validates issue_type and priority on construction
- Audit log parsing handles nested JSON from CLI
- Result type enables Railway-Oriented Programming pattern

**Dependencies**:

- Python stdlib: dataclasses, datetime, typing, json

---

### Brick #4: Git Sync Coordinator (sync.py)

**Purpose**: Coordinate beads JSONL sync with git operations.

**Public Interface (Studs)**:

```python
class BeadsSyncCoordinator:
    """Coordinate beads state with git operations.

    Philosophy:
    - Hook into amplihack git workflow
    - Ensure JSONL committed before push
    - Pull triggers beads import
    - Handle merge conflicts gracefully
    """

    def __init__(self, adapter: BeadsAdapter, project_root: Path):
        """Initialize sync coordinator."""

    def before_commit(self) -> Result[bool, SyncError]:
        """Ensure beads JSONL is current before git commit."""

    def after_pull(self) -> Result[bool, SyncError]:
        """Trigger beads import after git pull."""

    def check_sync_status(self) -> SyncStatus:
        """Check if SQLite cache is in sync with JSONL."""

    def force_sync(self) -> Result[bool, SyncError]:
        """Force bidirectional sync (export + import)."""

    def detect_conflicts(self) -> List[ConflictInfo]:
        """Detect JSONL merge conflicts after git pull."""

    def get_sync_stats(self) -> SyncStats:
        """Get synchronization statistics."""

@dataclass
class SyncStatus:
    """Current sync status."""
    in_sync: bool
    last_export: Optional[datetime]
    last_import: Optional[datetime]
    pending_changes: int
    jsonl_path: Path

@dataclass
class ConflictInfo:
    """Information about a sync conflict."""
    file_path: Path
    conflict_lines: List[str]
    suggested_resolution: str

@dataclass
class SyncStats:
    """Sync performance metrics."""
    total_syncs: int
    successful_syncs: int
    failed_syncs: int
    avg_sync_time: float
    last_sync: Optional[datetime]
```

**Implementation Notes**:

- Beads auto-syncs with 5-second debounce on writes
- Read .beads/issues.jsonl to check for git conflicts
- Conflict resolution: append both versions, let beads dedupe
- Hook into amplihack's git workflow (Step 9: Commit and Push)
- No automatic git operations - only prepare for user's git commands

**Dependencies**:

- adapter.py (BeadsAdapter)
- Python stdlib: pathlib, datetime, subprocess (for git status)

---

### Brick #5: Workflow Integration (workflow_integration.py)

**Purpose**: Hook beads operations into amplihack DEFAULT_WORKFLOW.md.

**Public Interface (Studs)**:

```python
class BeadsWorkflowIntegration:
    """Integrate beads into amplihack workflow.

    Philosophy:
    - Auto-create beads issues at Step 2
    - Track workflow progress via issue status
    - Update dependencies as work progresses
    - Restore context on session startup
    """

    def __init__(self, provider: BeadsMemoryProvider):
        """Initialize workflow integration."""

    def create_workflow_issue(
        self,
        title: str,
        requirements: str,
        step: int,
    ) -> Result[BeadsIssue, WorkflowError]:
        """Create beads issue for workflow task (Step 2)."""

    def update_workflow_status(
        self,
        issue_id: str,
        step: int,
        status: str,
    ) -> Result[bool, WorkflowError]:
        """Update issue status as workflow progresses."""

    def discover_dependency(
        self,
        child_issue: str,
        parent_issue: str,
    ) -> Result[bool, WorkflowError]:
        """Record discovered dependency during implementation."""

    def get_workflow_context(
        self, issue_id: str
    ) -> Result[WorkflowContext, WorkflowError]:
        """Get full context for workflow issue."""

    def suggest_next_steps(
        self, current_step: int
    ) -> List[str]:
        """Suggest next workflow steps based on ready work."""

@dataclass
class WorkflowContext:
    """Full context for a workflow issue."""
    issue: BeadsIssue
    blockers: List[BeadsIssue]
    dependents: List[BeadsIssue]
    related_memories: List[MemoryEntry]
    current_step: int
    next_steps: List[str]
```

**Workflow Hook Points**:

```python
# Step 2: Create GitHub Issue → Also create beads issue
workflow.create_workflow_issue(
    title=github_issue.title,
    requirements=clarified_requirements,
    step=2,
)

# Step 4: Research and Design → Store as memory
provider.store_memory(
    agent_id="architect",
    title="Architecture Decision",
    content=design_doc,
    memory_type="decision",
    importance=8,
)

# Step 9: Commit and Push → Sync beads JSONL
sync.before_commit()  # Ensure JSONL is current

# Step 14: PR Mergeable → Close beads issue
adapter.close_issue(issue_id, reason="PR merged")

# Session Startup → Restore context
context = provider.restore_session(last_session_id)
```

**Implementation Notes**:

- Use beads labels to track workflow steps: "workflow:step-4"
- Link GitHub issue to beads issue via metadata
- Suggest next steps by querying ready work
- Auto-discover dependencies when agents link memories

**Dependencies**:

- provider.py (BeadsMemoryProvider)
- adapter.py (BeadsAdapter)
- models.py (WorkflowContext, BeadsIssue)

---

## Integration Points

### 1. Memory Manager Integration

**Extend MemoryManager to support providers**:

```python
# amplihack/memory/manager.py

class MemoryManager:
    def __init__(
        self,
        db_path: Optional[Path] = None,
        session_id: Optional[str] = None,
        provider: Optional[MemoryProvider] = None,  # NEW
    ):
        self.db = MemoryDatabase(db_path)
        self.session_id = session_id or self._generate_session_id()
        self.provider = provider  # NEW: Optional beads provider

    def store(self, ...) -> str:
        memory_id = self.db.store_memory(memory)

        # NEW: Sync to provider if configured
        if self.provider:
            result = self.provider.store_memory(...)
            if result.is_err:
                # Log warning but don't fail - local DB is source of truth
                logger.warning(f"Provider sync failed: {result.error}")

        return memory_id
```

**Provider Protocol**:

```python
# amplihack/memory/providers/base.py

class MemoryProvider(Protocol):
    """Protocol for external memory providers."""

    def store_memory(self, ...) -> Result[str, Exception]:
        """Store memory in external system."""

    def retrieve_memories(self, ...) -> Result[List[MemoryEntry], Exception]:
        """Retrieve memories from external system."""

    def restore_session(self, session_id: str) -> Result[List[MemoryEntry], Exception]:
        """Restore session from external system."""
```

### 2. Session Startup Integration

**Add beads context restoration to launcher**:

```python
# amplihack/launcher/core.py

def prepare_launch(self) -> bool:
    # Existing setup...

    # NEW: Check for beads and restore context
    if BeadsAdapter().is_installed():
        beads_integration = BeadsBootstrap()
        if beads_integration.is_initialized():
            context = beads_integration.restore_last_session()
            if context:
                print(f"Restored {len(context.memories)} memories from last session")
                print(f"Ready work: {len(context.ready_work)} issues")

    return True
```

### 3. Workflow Integration Hooks

**Insert beads operations at workflow checkpoints**:

```python
# .claude/commands/ultrathink.md or workflow coordinator

# At Step 2: Create GitHub Issue
github_issue = create_github_issue(...)
beads_issue = beads_workflow.create_workflow_issue(
    title=github_issue.title,
    requirements=requirements,
    step=2,
)
# Store mapping in metadata for cross-reference
github_issue.add_label(f"beads:{beads_issue.id}")

# At Step 4: Architecture Design
design = architect_agent.design(...)
beads_provider.store_memory(
    agent_id="architect",
    title=f"Design: {github_issue.title}",
    content=design,
    memory_type="decision",
    importance=8,
    tags=["architecture", f"issue-{github_issue.number}"],
)

# At Step 9: Before Commit
beads_sync.before_commit()  # Ensure JSONL current

# At Step 14: PR Merged
beads_workflow.update_workflow_status(
    issue_id=beads_issue.id,
    step=14,
    status="closed",
)
```

### 4. Agent Memory Access

**Agents use MemoryManager with beads provider**:

```python
# In agent execution context

memory_manager = MemoryManager(
    session_id=current_session_id,
    provider=BeadsMemoryProvider(BeadsAdapter()),
)

# Agent stores decision
memory_manager.store(
    agent_id="architect",
    title="API Design Decision",
    content="Chose REST over GraphQL because...",
    memory_type=MemoryType.DECISION,
    importance=8,
)

# Agent retrieves past decisions
past_decisions = memory_manager.retrieve(
    agent_id="architect",
    memory_type=MemoryType.DECISION,
    tags=["api-design"],
    limit=5,
)
```

## Prerequisites & Installation

### 1. Beads CLI Installation

**Detection & Bootstrap**:

```python
class BeadsBootstrap:
    """Handle beads installation and initialization."""

    def check_prerequisites(self) -> PrerequisiteResult:
        """Check if beads is installed and initialized."""
        results = []

        # Check Go installation
        go_check = check_tool("go", "--version")
        results.append(go_check)

        # Check bd CLI
        bd_check = check_tool("bd", "--version")
        results.append(bd_check)

        # Check .beads/ directory
        if bd_check.available:
            beads_init = check_beads_initialized()
            results.append(beads_init)

        return PrerequisiteResult(results)

    def install_beads(self) -> Result[bool, InstallError]:
        """Provide installation guidance."""
        platform = detect_platform()

        instructions = f"""
Beads CLI Installation:

Prerequisites:
  • Go 1.23 or later

Installation:
  go install github.com/steveyegge/beads/cmd/bd@latest

Verify installation:
  bd --version

Initialize in project:
  cd {project_root}
  bd init
"""
        print(instructions)

        # Never auto-install - user control
        return Result(value=False, error=None)
```

**Platform-Specific Installation**:

- macOS: `brew install go && go install github.com/steveyegge/beads/cmd/bd@latest`
- Linux: `apt install golang-go && go install github.com/steveyegge/beads/cmd/bd@latest`
- WSL: Same as Linux
- Windows: `winget install GoLang.Go && go install github.com/steveyegge/beads/cmd/bd@latest`

**Fallback Behavior**:

- If beads not installed: Gracefully degrade, use only local SQLite memory
- If beads not initialized: Prompt user to run `bd init`
- If beads commands fail: Log error, continue with local memory

### 2. Project Initialization

**Auto-initialization on first use**:

```python
def ensure_beads_initialized(project_root: Path) -> bool:
    adapter = BeadsAdapter(project_root)

    if not adapter.is_installed():
        print("Beads CLI not found. Install with: go install github.com/steveyegge/beads/cmd/bd@latest")
        return False

    beads_dir = project_root / ".beads"
    if not beads_dir.exists():
        print(f"Initializing beads in {project_root}...")
        result = adapter.init(prefix="amplihack")
        if result.is_ok:
            print("Beads initialized successfully")
            return True
        else:
            print(f"Beads initialization failed: {result.error}")
            return False

    return True
```

## Risk Mitigation Strategies

### 1. Alpha Version Instability

**Problem**: Beads is pre-1.0 with known data duplication bugs in multi-workstream scenarios.

**Mitigation**:

- **Constraint**: Limit MVP to single workstream per project
- **Validation**: Check for duplicate issues on session restore, dedupe by title+timestamp
- **Recovery**: Provide `bd delete --cascade` wrapper to clean duplicates
- **Documentation**: Warn users about alpha limitations in README
- **Future**: Add multi-workstream support in Phase 2 after beads 1.0

### 2. JSONL Merge Conflicts

**Problem**: Git merge conflicts in `.beads/issues.jsonl` when multiple users work simultaneously.

**Mitigation**:

- **Detection**: Check for conflict markers after `git pull`
- **Resolution Strategy**: Append-only log means both versions are valid
- **Auto-merge**: Concatenate both conflict sections, let beads dedupe on import
- **Manual Override**: Provide `beads sync --force-import` to rebuild from JSONL
- **Prevention**: Use short-lived feature branches (amplihack workflow already does this)

### 3. Performance Degradation

**Problem**: SQLite cache vs JSONL sync overhead slows operations.

**Mitigation**:

- **Async Operations**: All beads CLI calls use subprocess with timeout
- **Batch Operations**: Group multiple creates/updates into single CLI call
- **Cache Optimization**: Rely on beads' SQLite cache for queries
- **Lazy Sync**: Only sync JSONL on git operations, not every write
- **Monitoring**: Track sync times, alert if >5 seconds
- **Escape Hatch**: Allow disabling beads provider via env var

### 4. Cross-Platform Compatibility

**Problem**: beads CLI behavior differs on Windows vs Unix.

**Mitigation**:

- **Path Handling**: Use `pathlib.Path` for all file operations
- **Subprocess Encoding**: Force UTF-8 encoding on subprocess calls
- **Line Endings**: JSONL files use Unix line endings (LF) on all platforms
- **Testing**: Include WSL and Windows test matrix in CI
- **Known Issues**: Document Windows-specific beads bugs in README

### 5. CLI Timeout Issues

**Problem**: Long-running beads operations (compaction, large repos) hit timeouts.

**Mitigation**:

- **Operation-Specific Timeouts**:
  - `bd create/update`: 5 seconds
  - `bd list/ready`: 10 seconds
  - `bd compact`: 120 seconds
- **Retry Logic**: Exponential backoff for transient failures
- **Progress Indication**: Show "beads operation in progress..." for >2 second ops
- **Abort Handling**: Graceful cleanup on timeout, log for manual intervention
- **Configuration**: Allow user timeout overrides via env var

## Implementation Phases

### Phase 1: MVP (Week 1)

**Deliverables**:

1. ✅ BeadsAdapter with core CLI operations (create, list, update, close)
2. ✅ BeadsMemoryProvider implementing provider protocol
3. ✅ Data models (BeadsIssue, Result types, error hierarchy)
4. ✅ Prerequisites checking (Go, bd CLI, .beads/ init)
5. ✅ Workflow integration at Step 2 (auto-create issue)
6. ✅ Basic sync coordination (before_commit hook)
7. ✅ Session restoration (restore_last_session)

**Acceptance Criteria**:

- Beads issues created for workflow tasks
- Agent memories stored in beads
- Session context restored on startup
- JSONL synced before git commits
- All operations handle errors gracefully

**Testing**:

- Unit tests: 60% coverage (adapter, models, error handling)
- Integration tests: 30% coverage (provider, sync, workflow)
- E2E tests: 10% coverage (full workflow with beads)

### Phase 2: Dependency Management (Week 2)

**Deliverables**:

1. ✅ Dependency operations (add_dependency, get_ready_work, get_blocked)
2. ✅ Dependency tree visualization
3. ✅ Workflow integration: Auto-discover dependencies
4. ✅ Ready work detection integrated into workflow
5. ✅ Conflict detection and resolution
6. ✅ Performance optimization (batch operations, caching)

**Acceptance Criteria**:

- Workflow automatically links discovered dependencies
- Agents can query ready work
- Dependency trees visualized in CLI
- JSONL conflicts resolved automatically
- No performance regression vs baseline

### Phase 3: Advanced Features (Future)

**Potential Additions**:

1. Memory compaction integration (tier-1/tier-2 with Claude API)
2. Cross-project knowledge transfer
3. Multi-workstream support (after beads 1.0)
4. MCP server integration (when routing bugs fixed)
5. Advanced query capabilities (FTS, vector search)
6. Beads analytics dashboard

## Testing Strategy

### Unit Tests (60%)

**adapter.py**:

- CLI command construction
- JSON parsing from bd output
- Error mapping (subprocess → BeadsError)
- Timeout handling
- Platform-specific behavior

**provider.py**:

- Memory → Issue mapping
- Issue → Memory conversion
- Session restoration logic
- Batch operations

**models.py**:

- Data validation
- JSON serialization/deserialization
- Result type behavior
- Error hierarchy

### Integration Tests (30%)

**Adapter + CLI**:

- Full CRUD cycle (create, read, update, delete)
- Dependency operations
- Ready work detection
- Conflict scenarios

**Provider + Memory Manager**:

- Store and retrieve via provider
- Session restoration
- Multi-agent scenarios
- Provider failure fallback

**Workflow Integration**:

- End-to-end workflow with beads
- Git sync coordination
- Context restoration on startup

### E2E Tests (10%)

**Full Workflow**:

1. Initialize beads in test project
2. Create workflow issue (Step 2)
3. Architect stores design decision
4. Builder links implementation memory
5. Commit triggers JSONL sync
6. Pull in another worktree, restore context
7. Close issue on PR merge

**Test Environment**:

- Use temporary git repos
- Mock GitHub operations
- Real beads CLI (requires Go in CI)
- Clean .beads/ between tests

## Success Metrics

### Functional Metrics

- ✅ Beads issues created for 100% of workflow tasks
- ✅ Agent memories persist across sessions
- ✅ Session context restored in <5 seconds
- ✅ JSONL conflicts resolved automatically 95% of time
- ✅ Ready work detection identifies unblocked issues

### Performance Metrics

- CLI operations complete in <10 seconds (p95)
- Session restoration handles 1000+ memories in <5 seconds
- JSONL sync adds <1 second to git commits
- No memory leaks over 8-hour sessions
- Batch operations 10x faster than individual calls

### Quality Metrics

- 80%+ test coverage across all modules
- All public APIs documented with examples
- Zero-BS: No stubs or placeholder code
- Philosophy compliance: Ruthless simplicity maintained
- Regeneratable: Clear specs for all bricks

## Documentation Deliverables

### 1. Module Specifications (Specs/)

- beads-adapter-spec.md
- beads-provider-spec.md
- beads-models-spec.md
- beads-sync-spec.md
- beads-workflow-spec.md

### 2. Integration Guides

- BEADS_INTEGRATION.md (user-facing)
- BEADS_DEVELOPMENT.md (contributor guide)
- BEADS_TROUBLESHOOTING.md (common issues)

### 3. API Documentation

- BeadsAdapter API reference
- BeadsMemoryProvider API reference
- Workflow integration hooks

### 4. Examples

- examples/beads_basic_usage.py
- examples/beads_workflow_integration.py
- examples/beads_session_restoration.py

## Conclusion

This architecture provides a complete blueprint for integrating beads into amplihack while maintaining ruthless simplicity and zero-BS implementation. The phased approach ensures MVP delivers core value quickly, with clear paths for future enhancements.

**Key Design Decisions**:

1. CLI-first approach: Simplest integration, defer MCP to Phase 3
2. Provider pattern: Extends existing memory system without breaking changes
3. Explicit error handling: Result types prevent silent failures
4. Standard library: No heavy dependencies, easy to regenerate
5. Workflow integration: Seamless UX, beads operations invisible to users

The architecture is ready for builder agent implementation, with complete specifications for each module and clear integration points with existing amplihack systems.
