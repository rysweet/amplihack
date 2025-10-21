# Beads Integration - Architectural Decisions

## Decision Record Format

**What was decided | Why | Alternatives considered**

---

## Decision 1: CLI-First, Not MCP Server

**Decision**: Use `bd` CLI via subprocess wrapper instead of MCP server integration.

**Why**:

1. **Simplicity**: Subprocess calls are standard library, well-understood
2. **Stability**: MCP server has known routing bugs in multi-workstream scenarios
3. **Prerequisites**: MCP requires additional setup (server registration, config)
4. **Testing**: CLI integration easier to test (mock subprocess vs network)
5. **Philosophy**: Start simple, add complexity only when justified

**Alternatives Considered**:

- **MCP Server**: Would provide native protocol integration but adds complexity and requires beads fixes
- **Direct SQLite Access**: Would bypass beads entirely but loses git-distribution and audit trail
- **REST API**: No API exists in beads currently

**Trade-offs**:

- ✅ Simple, testable, standard library only
- ✅ Works immediately with existing beads installation
- ✅ No additional beads modifications needed
- ❌ Subprocess overhead (~50-100ms per call)
- ❌ JSON parsing required for all outputs
- ❌ No streaming or real-time updates

**Future Path**: Consider MCP in Phase 3 after beads 1.0 fixes routing bugs.

---

## Decision 2: Result Type for Error Handling

**Decision**: Use explicit `Result[T, E]` type for all beads operations instead of exceptions.

**Why**:

1. **Railway-Oriented Programming**: Forces explicit error handling at call site
2. **No Silent Failures**: Can't accidentally ignore errors (unlike swallowed exceptions)
3. **Type Safety**: Mypy can verify error handling paths
4. **Zero-BS Principle**: Makes success/failure explicit in code
5. **Composability**: Easy to chain operations with error propagation

**Alternatives Considered**:

- **Exceptions**: Python-idiomatic but allows silent failures via swallowed try/catch
- **Optional + Logging**: Loses error context, harder to debug
- **Status Codes**: Less type-safe, requires documentation

**Implementation**:

```python
@dataclass
class Result:
    value: Optional[Any]
    error: Optional[Exception]

    @property
    def is_ok(self) -> bool:
        return self.error is None

    def unwrap(self) -> Any:
        if self.is_err:
            raise self.error
        return self.value

    def unwrap_or(self, default: Any) -> Any:
        return self.value if self.is_ok else default
```

**Trade-offs**:

- ✅ Explicit error handling, no silent failures
- ✅ Type-safe, mypy can verify
- ✅ Composable with functional patterns
- ❌ More verbose than exceptions
- ❌ Requires discipline to check .is_ok before accessing .value

---

## Decision 3: Memory Provider Protocol

**Decision**: Extend MemoryManager with optional provider interface instead of replacing it.

**Why**:

1. **Backward Compatibility**: Existing code continues to work without beads
2. **Optional Integration**: Beads provider is opt-in, not required
3. **Local-First**: SQLite remains source of truth, beads is sync layer
4. **Graceful Degradation**: System works without beads if not installed
5. **Testability**: Can test memory system without beads dependency

**Alternatives Considered**:

- **Replace MemoryManager**: Would break existing integrations
- **Dual Storage**: Write to both SQLite and beads always (complexity, failure modes)
- **Beads-Only**: Requires beads installation, no fallback

**Implementation**:

```python
class MemoryManager:
    def __init__(
        self,
        db_path: Optional[Path] = None,
        session_id: Optional[str] = None,
        provider: Optional[MemoryProvider] = None,  # NEW
    ):
        self.db = MemoryDatabase(db_path)  # Local SQLite
        self.provider = provider  # Optional beads provider

    def store(self, ...) -> str:
        # Store locally first (always succeeds)
        memory_id = self.db.store_memory(memory)

        # Sync to provider if configured (best effort)
        if self.provider:
            result = self.provider.store_memory(...)
            if result.is_err:
                logger.warning(f"Provider sync failed: {result.error}")

        return memory_id
```

**Trade-offs**:

- ✅ Backward compatible with existing code
- ✅ Optional beads integration, graceful fallback
- ✅ Local SQLite remains fast source of truth
- ❌ Potential sync inconsistencies if provider fails
- ❌ Two storage systems to maintain (SQLite + beads)

**Mitigation**: Provider errors are logged but don't fail the operation. Local SQLite is authoritative.

---

## Decision 4: Single Workstream for MVP

**Decision**: Limit MVP to single workstream per project, defer multi-workstream to Phase 2.

**Why**:

1. **Alpha Limitation**: Beads has known data duplication bugs in multi-workstream scenarios
2. **Risk Mitigation**: Avoid hitting known beads issues during MVP
3. **Simplicity**: Single workstream is simpler to reason about and test
4. **Most Use Cases**: 90% of amplihack usage is single-workstream
5. **Wait for 1.0**: Beads maintainers targeting multi-workstream fix in 1.0

**Alternatives Considered**:

- **Multi-Workstream Now**: Would hit known bugs, require workarounds
- **Custom Workarounds**: Would add complexity to work around alpha bugs
- **Separate Beads DBs**: Would fragment knowledge across databases

**Implementation**:

```python
class BeadsMemoryProvider:
    def __init__(
        self,
        adapter: BeadsAdapter,
        workstream: str = "main",  # Single workstream
    ):
        if workstream != "main":
            logger.warning("Multi-workstream support limited in MVP")
        self.workstream = workstream
```

**Trade-offs**:

- ✅ Avoids known alpha bugs
- ✅ Simpler implementation and testing
- ✅ Aligns with amplihack's typical usage
- ❌ Doesn't support multi-project workflows
- ❌ Requires Phase 2 work for full capability

**Future Path**: Add multi-workstream support in Phase 2 after beads 1.0 release.

---

## Decision 5: Label-Based Session Tracking

**Decision**: Use beads labels (e.g., `session:20251018_143052`) for session organization instead of custom metadata.

**Why**:

1. **Built-in Support**: Beads has native label filtering in `bd list --label`
2. **Query Efficiency**: Labels are indexed in SQLite, fast queries
3. **Git-Friendly**: Labels are part of JSONL, survive git operations
4. **Composability**: Can combine multiple label filters
5. **Human-Readable**: Easy to see session in `bd list` output

**Alternatives Considered**:

- **Custom Metadata Field**: Not indexed, requires full scan
- **Issue Title Prefix**: Pollutes titles with metadata
- **Separate Session Table**: Would require custom beads modifications

**Implementation**:

```python
def _build_labels(
    self,
    agent_id: str,
    memory_type: str,
    tags: Optional[List[str]],
) -> List[str]:
    return [
        f"session:{self.session_id}",
        f"agent:{agent_id}",
        f"memory:{memory_type}",
    ] + (tags or [])

# Query by session
issues = adapter.list_issues(labels=[f"session:{session_id}"])
```

**Trade-offs**:

- ✅ Leverages beads' built-in indexing
- ✅ Fast queries, git-friendly
- ✅ Human-readable in CLI
- ❌ Label namespace could conflict with user labels
- ❌ Requires parsing to extract session ID

**Mitigation**: Use consistent prefix format (`session:`, `agent:`, `memory:`) to avoid conflicts.

---

## Decision 6: Importance → Priority Mapping

**Decision**: Map MemoryManager's importance (1-10) to beads priority (0-4) with intentional information loss.

**Why**:

1. **Beads Constraint**: Priority is 0-4, can't store 10 levels
2. **Semantic Mapping**: Most users think in High/Medium/Low, not 1-10 scale
3. **Lossy But Acceptable**: 1-10 granularity not critical for memory prioritization
4. **Reversible**: Can map back to approximate importance

**Alternatives Considered**:

- **Store in Metadata**: Would preserve exact value but priority field wouldn't reflect it
- **Use Description**: Would pollute description with metadata
- **Custom Field**: Would require beads modifications

**Implementation**:

```python
IMPORTANCE_TO_PRIORITY = {
    10: 0, 9: 0,        # Critical → 0
    8: 1, 7: 1,         # High → 1
    6: 2, 5: 2, 4: 2,   # Medium → 2
    3: 3, 2: 3,         # Low → 3
    1: 4,               # Very Low → 4
}

# Reverse mapping (to midpoint)
PRIORITY_TO_IMPORTANCE = {
    0: 9, 1: 7, 2: 5, 3: 3, 4: 1
}
```

**Trade-offs**:

- ✅ Uses beads priority field semantically correctly
- ✅ Preserves high-level importance classification
- ✅ No custom modifications needed
- ❌ Loses exact importance value (8 vs 7 becomes same priority)
- ❌ Not bijective (can't recover exact original)

**Acceptable**: Exact importance granularity not critical for memory system use cases.

---

## Decision 7: Git Sync Coordination

**Decision**: Hook beads sync into amplihack's git workflow, don't manage git operations directly.

**Why**:

1. **Separation of Concerns**: Beads handles JSONL sync, amplihack handles git
2. **User Control**: Never auto-commit or auto-push on user's behalf
3. **Workflow Integration**: Amplihack already has git workflow (Step 9)
4. **Trust Beads**: Beads' 5-second debounce handles frequent writes
5. **Security**: No automatic git operations reduces risk

**Alternatives Considered**:

- **Auto-Commit JSONL**: Would commit without user permission
- **Git Hooks**: Would require installing hooks in every repo
- **Beads Watch Mode**: No such mode exists

**Implementation**:

```python
class BeadsSyncCoordinator:
    def before_commit(self) -> Result[bool, SyncError]:
        """Ensure beads JSONL is current before git commit.

        Called by workflow before Step 9 (Commit and Push).
        Checks if JSONL has pending writes, waits for debounce.
        """
        # Check if .beads/issues.jsonl has uncommitted changes
        # If so, wait up to 5 seconds for beads' auto-sync
        pass

    def after_pull(self) -> Result[bool, SyncError]:
        """Trigger beads import after git pull.

        Beads auto-imports JSONL changes, just verify it happened.
        """
        pass
```

**Trade-offs**:

- ✅ User always in control of git operations
- ✅ No surprise commits or pushes
- ✅ Leverages amplihack's existing workflow
- ❌ User must follow workflow for sync to work
- ❌ Can't prevent user from committing mid-sync

**Acceptable**: Workflow guidance ensures users follow correct process.

---

## Decision 8: Standard Library Only for Core Modules

**Decision**: adapter.py, models.py, sync.py use only Python stdlib, no external dependencies.

**Why**:

1. **Philosophy**: Core utilities should have zero dependencies
2. **Circular Deps**: Avoids dependency cycles with memory system
3. **Regeneratable**: Simpler to regenerate with AI
4. **Testability**: No mocking of external libraries needed
5. **Bootstrap**: Works immediately after Python install

**Alternatives Considered**:

- **Use requests**: Not needed, subprocess handles CLI
- **Use pydantic**: Nice validation but adds dependency
- **Use rich**: Pretty output but not core requirement

**Implementation**:

```python
# adapter.py - Only stdlib
import subprocess
import json
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass

# No external dependencies
```

**Trade-offs**:

- ✅ Zero dependency risk
- ✅ Fast imports, no installation needed
- ✅ Easy to vendor or copy to other projects
- ❌ More verbose than using libraries (e.g., dataclasses vs pydantic)
- ❌ Can't use rich for pretty CLI output

**Future**: Can add optional dependencies (e.g., rich) with graceful fallback.

---

## Decision 9: Close vs Delete for Memory Cleanup

**Decision**: "Delete" memories by closing beads issues, not deleting them.

**Why**:

1. **Audit Trail**: Beads preserves closed issues in JSONL, maintains history
2. **Undo**: Closed issues can be reopened, deleted issues are gone
3. **Git History**: Closing is a new JSONL entry, deleting rewrites history
4. **Conflicts**: Closing conflicts easier to resolve than deletion conflicts
5. **Philosophy**: Preserve information, don't destroy data

**Alternatives Considered**:

- **bd delete**: Would remove from JSONL, loses audit trail
- **Custom "deleted" Label**: Would clutter label namespace
- **Hide in UI Only**: Would still query closed issues

**Implementation**:

```python
def delete_memory(self, memory_id: str) -> Result[bool, ProviderError]:
    """Delete memory (close beads issue).

    Closes the beads issue rather than deleting to preserve audit trail.
    """
    result = self.adapter.close_issue(
        issue_id=memory_id,
        reason="Memory deleted by user",
    )
    return result
```

**Trade-offs**:

- ✅ Preserves full audit trail
- ✅ Undoable (can reopen)
- ✅ Git-friendly (append-only log)
- ❌ Closed issues still in database (use beads compact to clean)
- ❌ Not "true" deletion, just status change

**Acceptable**: Beads' compaction feature handles cleanup of old closed issues.

---

## Decision 10: JSON-Only CLI Mode

**Decision**: Always use `--json` flag for all bd CLI calls, never parse text output.

**Why**:

1. **Stability**: JSON schema is part of beads' API contract
2. **Parsing**: JSON parsing is standard library, reliable
3. **Type Safety**: JSON maps directly to dataclasses
4. **Future-Proof**: Text output format may change, JSON won't
5. **Error Handling**: JSON envelope has structured error info

**Alternatives Considered**:

- **Text Parsing**: Fragile, breaks on format changes
- **Mix JSON + Text**: Inconsistent, harder to test
- **Custom Protocol**: Would require beads modifications

**Implementation**:

```python
def _run_command(self, args: List[str]) -> Result[Dict, BeadsError]:
    """Execute bd CLI command and parse JSON output."""
    # Always append --json flag
    args.append("--json")

    result = subprocess.run(
        ["bd"] + args,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        return Result(value=None, error=BeadsCLIError(...))

    # Parse JSON
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return Result(value=None, error=BeadsParseError(str(e)))

    return Result(value=data, error=None)
```

**Trade-offs**:

- ✅ Stable, well-defined interface
- ✅ Easy to parse and validate
- ✅ Type-safe conversion to dataclasses
- ❌ Slightly more verbose output (JSON overhead)
- ❌ Requires JSON parsing for every call

**Acceptable**: JSON parsing overhead negligible compared to subprocess call.

---

## Decision 11: Timeout Strategy

**Decision**: Use operation-specific timeouts with safe defaults, configurable per-call.

**Why**:

1. **Responsiveness**: Prevents hanging on stuck operations
2. **Operation Variability**: Different ops have different expected durations
3. **User Control**: Allow override for slow environments
4. **Fail-Fast**: Better to timeout and retry than hang forever
5. **Testing**: Makes tests predictable and fast

**Alternatives Considered**:

- **No Timeouts**: Would hang indefinitely on issues
- **Fixed Global Timeout**: Too short for some ops, too long for others
- **Async with Cancel**: More complex, not needed for MVP

**Implementation**:

```python
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

def _run_command(
    self,
    args: List[str],
    timeout: Optional[int] = None,
) -> Result[Dict, BeadsError]:
    """Execute with timeout."""
    actual_timeout = timeout or self.default_timeout

    try:
        result = subprocess.run(
            ["bd"] + args,
            timeout=actual_timeout,
            ...
        )
    except subprocess.TimeoutExpired:
        return Result(
            value=None,
            error=BeadsTimeoutError(f"Command timed out after {actual_timeout}s"),
        )
```

**Trade-offs**:

- ✅ Prevents hanging on issues
- ✅ Operation-specific allows optimization
- ✅ Configurable for different environments
- ❌ Might timeout on legitimate slow operations
- ❌ Requires tuning based on usage

**Future**: Add retry with exponential backoff for transient timeouts.

---

## Summary of Key Decisions

| Decision              | Rationale                               | Risk Mitigation                           |
| --------------------- | --------------------------------------- | ----------------------------------------- |
| CLI-First             | Simplicity, stability                   | Phase 3: Consider MCP after beads 1.0     |
| Result Types          | Explicit errors, no silent failures     | Type system enforces checking             |
| Provider Protocol     | Optional integration, graceful fallback | Local SQLite remains authoritative        |
| Single Workstream     | Avoid alpha bugs                        | Phase 2: Multi-workstream after beads 1.0 |
| Label-Based Sessions  | Leverages beads indexing                | Namespace prefixes avoid conflicts        |
| Importance → Priority | Semantic mapping, lossy but acceptable  | Store exact value in metadata if needed   |
| Git Sync Hooks        | User control, trust beads               | Workflow guidance ensures correctness     |
| Stdlib Only           | Zero dependencies, regeneratable        | Optional rich deps with fallback          |
| Close vs Delete       | Preserve audit trail                    | Beads compact for cleanup                 |
| JSON-Only             | Stable API, easy parsing                | Always use --json flag                    |
| Operation Timeouts    | Fail-fast, responsive                   | Configurable, operation-specific          |

## Compliance with Amplihack Philosophy

All decisions align with amplihack's core principles:

- ✅ **Ruthless Simplicity**: CLI wrapper, no complex abstractions
- ✅ **Zero-BS Implementation**: All operations work or return explicit errors
- ✅ **Bricks & Studs**: Self-contained modules with clear public interfaces
- ✅ **Standard Library Only**: Core modules have no external dependencies
- ✅ **Regeneratable**: Clear specifications enable AI reconstruction
- ✅ **Trust in Emergence**: Simple components, complex system emerges
- ✅ **User Control**: Never auto-commit or modify git without permission

## Open Questions for Future Phases

1. **Multi-Workstream Support**: How to handle when beads fixes routing bugs?
2. **Compaction Integration**: Should amplihack expose beads' memory decay features?
3. **Cross-Project Memory**: How to share knowledge across different amplihack projects?
4. **Vector Search**: Should we add semantic search on top of beads full-text search?
5. **Real-Time Updates**: Would SSE or websockets improve UX for multi-user scenarios?
6. **Beads MCP Server**: When should we migrate from CLI to MCP server integration?

These questions deferred to Phase 2 and Phase 3 based on MVP learnings and beads maturity.
