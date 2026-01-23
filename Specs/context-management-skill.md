# Context Management Skill Specification

## Purpose

Proactive context management for Claude Code sessions via intelligent token monitoring, context extraction, and selective rehydration.

## Scope

**Handles**:

- Token usage monitoring and threshold detection
- Intelligent context extraction (key decisions, requirements, state)
- Selective context rehydration at configurable detail levels
- Context snapshot management and retrieval

**Does NOT handle**:

- Automatic compaction (handled by Claude Code + PreCompact hook)
- Full conversation transcript storage (handled by `/transcripts` command)
- Session logging (handled by existing session hooks)
- Background monitoring (on-demand invocation only)

## Philosophy Alignment

- ✅ **Ruthless Simplicity**: Four single-purpose bricks, on-demand invocation (no background processes)
- ✅ **Single Responsibility**: Each component has ONE job (monitor, extract, rehydrate, orchestrate)
- ✅ **No External Dependencies**: Pure Python standard library only
- ✅ **Regeneratable**: Yes, module can be rebuilt from this spec
- ✅ **Occam's Razor**: Simplest solution that solves the problem (user-initiated, not automatic)
- ✅ **Trust in Emergence**: User decides when to offload, not the system

## Public Interface (The "Studs")

### Main Skill Entry Point

```python
def context_management_skill(action: str, **kwargs) -> Dict[str, Any]:
    """Main entry point for the context-management skill.

    Args:
        action: One of 'status', 'snapshot', 'rehydrate', 'list'
        **kwargs: Action-specific parameters

    Returns:
        Dict with action results and recommendations

    Example:
        result = context_management_skill('status')
        result = context_management_skill('snapshot', name='feature-auth')
        result = context_management_skill('rehydrate', snapshot_id='20251116_123456', level='essential')
    """
```

### Token Monitor (Brick 1)

```python
class TokenMonitor:
    """Monitors token usage and calculates thresholds.

    Attributes:
        current_usage (int): Current token count
        max_tokens (int): Maximum context window size
        thresholds (Dict[str, float]): Named threshold percentages
    """

    def __init__(self, max_tokens: int = 1_000_000):
        """Initialize token monitor with context window size."""

    def check_usage(self, current_tokens: int) -> Dict[str, Any]:
        """Check current usage against thresholds.

        Args:
            current_tokens: Current token count from system

        Returns:
            Dict with usage stats, percentage, threshold status, recommendations
        """

    def get_recommendation(self, percentage: float) -> str:
        """Get action recommendation based on usage percentage.

        Returns one of: 'ok', 'consider_snapshot', 'snapshot_recommended', 'snapshot_urgent'
        """
```

### Context Extractor (Brick 2)

```python
class ContextExtractor:
    """Extracts essential context for snapshot preservation.

    Focus on intelligent extraction, not full dumps:
    - Original user requirements
    - Key decisions and trade-offs
    - Current implementation state
    - Open questions and blockers
    """

    def extract_from_conversation(self, conversation_data: List[Dict]) -> Dict[str, Any]:
        """Extract essential context from conversation history.

        Args:
            conversation_data: List of conversation messages

        Returns:
            Dict with structured context components:
            - original_requirements: User's initial request
            - key_decisions: List of decisions with rationale
            - implementation_state: Current progress summary
            - open_items: Pending questions/blockers
            - tools_used: List of tools invoked
        """

    def create_snapshot(self, context: Dict[str, Any], name: str = None) -> Path:
        """Create a named context snapshot.

        Args:
            context: Extracted context dictionary
            name: Optional human-readable snapshot name

        Returns:
            Path to created snapshot file
        """
```

### Context Rehydrator (Brick 3)

```python
class ContextRehydrator:
    """Restores context from snapshots at configurable detail levels."""

    LEVELS = ['essential', 'standard', 'comprehensive']

    def rehydrate(self, snapshot_path: Path, level: str = 'standard') -> str:
        """Rehydrate context from snapshot.

        Args:
            snapshot_path: Path to snapshot file
            level: Detail level ('essential', 'standard', 'comprehensive')

        Returns:
            Formatted context string ready for Claude to process

        Level Behaviors:
        - essential: Original requirements + current state only
        - standard: + key decisions + open items
        - comprehensive: + full decision log + all tools used
        """

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """List all available context snapshots.

        Returns:
            List of snapshot metadata dicts with id, name, timestamp, size
        """
```

### Skill Orchestrator (Brick 4)

```python
class ContextManagementOrchestrator:
    """Coordinates token monitoring, extraction, and rehydration."""

    def __init__(self):
        """Initialize with all component bricks."""

    def handle_action(self, action: str, **kwargs) -> Dict[str, Any]:
        """Handle skill action by coordinating components.

        Args:
            action: One of 'status', 'snapshot', 'rehydrate', 'list'
            **kwargs: Action-specific parameters

        Returns:
            Dict with action results
        """
```

### Constants

- `DEFAULT_MAX_TOKENS`: 1_000_000 (Claude's context window)
- `THRESHOLDS`: {'ok': 0.5, 'consider': 0.7, 'recommended': 0.85, 'urgent': 0.95}
- `SNAPSHOT_DIR`: '.claude/runtime/context-snapshots/'
- `REHYDRATION_LEVELS`: ['essential', 'standard', 'comprehensive']

## Dependencies

### External

None - pure Python standard library only (json, pathlib, datetime, typing)

### Internal

- `.claude.tools.amplihack.utils.paths`: FrameworkPathResolver (for project root detection)

### Integration Points (Uses, Not Depends)

- Complements `/transcripts` command (transcripts = full history, snapshots = intelligent extraction)
- Works alongside PreCompact hook (hook = automatic export, skill = proactive management)
- Reads from `~/.amplihack/.claude/runtime/logs/` when creating snapshots

## Module Structure

```
.claude/skills/context-management/
├── SKILL.md                    # Claude Code skill definition (this spec)
├── README.md                   # User documentation
├── QUICK_START.md              # Quick reference guide
├── __init__.py                 # Exports via __all__
├── core.py                     # Main skill entry point
├── token_monitor.py            # TokenMonitor brick
├── context_extractor.py        # ContextExtractor brick
├── context_rehydrator.py       # ContextRehydrator brick
├── orchestrator.py             # ContextManagementOrchestrator
├── models.py                   # Data structures (ContextSnapshot, UsageStats)
├── tests/
│   ├── __init__.py
│   ├── test_token_monitor.py
│   ├── test_context_extractor.py
│   ├── test_context_rehydrator.py
│   ├── test_orchestrator.py
│   ├── test_integration.py
│   └── fixtures/
│       ├── sample_conversation.json
│       ├── sample_snapshot.json
│       └── high_token_usage.json
└── examples/
    ├── basic_usage.md          # Basic usage examples
    ├── proactive_workflow.md   # Proactive context management workflow
    └── rehydration_levels.md   # When to use each rehydration level
```

## Data Models

```python
@dataclass
class UsageStats:
    """Token usage statistics."""
    current_tokens: int
    max_tokens: int
    percentage: float
    threshold_status: str  # 'ok', 'consider', 'recommended', 'urgent'
    recommendation: str

@dataclass
class ContextSnapshot:
    """Context snapshot metadata and content."""
    snapshot_id: str  # Format: YYYYMMDD_HHMMSS
    name: Optional[str]
    timestamp: datetime
    original_requirements: str
    key_decisions: List[Dict[str, str]]  # [{decision, rationale, alternatives}]
    implementation_state: str
    open_items: List[str]
    tools_used: List[str]
    token_count: int  # Estimated tokens in snapshot
    file_path: Path
```

## Test Requirements

### Unit Tests

**TokenMonitor Tests:**

- ✅ Test threshold detection at 50%, 70%, 85%, 95%
- ✅ Test recommendation logic for each threshold
- ✅ Test with various token counts (low, medium, high)
- ✅ Test edge cases (0 tokens, max tokens, over max)

**ContextExtractor Tests:**

- ✅ Test extraction from sample conversation data
- ✅ Test original requirements identification
- ✅ Test key decision extraction from conversation
- ✅ Test tool usage tracking
- ✅ Test snapshot file creation and structure
- ✅ Test with empty conversation (edge case)

**ContextRehydrator Tests:**

- ✅ Test rehydration at each level (essential, standard, comprehensive)
- ✅ Test snapshot listing and metadata
- ✅ Test with missing snapshot file (error handling)
- ✅ Test with corrupted snapshot JSON
- ✅ Test formatting of rehydrated context

**Orchestrator Tests:**

- ✅ Test 'status' action integration
- ✅ Test 'snapshot' action workflow
- ✅ Test 'rehydrate' action with different levels
- ✅ Test 'list' action
- ✅ Test error handling for invalid actions
- ✅ Test component coordination

### Integration Tests

- ✅ Test end-to-end workflow: status → snapshot → rehydrate
- ✅ Test with real conversation data from test fixtures
- ✅ Test snapshot persistence and retrieval
- ✅ Test concurrent access (if multiple sessions)

### Coverage Target

85%+ line coverage

## Example Usage

### Basic Status Check

```python
from context_management import context_management_skill

# Check current token usage
result = context_management_skill('status')
# Returns:
# {
#   'status': 'ok',
#   'usage': {
#     'current_tokens': 45000,
#     'max_tokens': 1000000,
#     'percentage': 4.5,
#     'threshold_status': 'ok',
#     'recommendation': 'Context is healthy. No action needed.'
#   }
# }
```

### Create Context Snapshot

```python
# When tokens reach 70%+, create a snapshot
result = context_management_skill('snapshot', name='auth-feature-implementation')
# Returns:
# {
#   'status': 'success',
#   'snapshot': {
#     'snapshot_id': '20251116_143522',
#     'name': 'auth-feature-implementation',
#     'file_path': '.claude/runtime/context-snapshots/20251116_143522.json',
#     'token_count': 15000,
#     'components': ['requirements', 'decisions', 'state', 'open_items']
#   },
#   'recommendation': 'Snapshot created. You can now use /transcripts or let Claude compact naturally.'
# }
```

### Rehydrate Context (After Compaction)

```python
# After compaction, restore essential context
result = context_management_skill('rehydrate',
                                  snapshot_id='20251116_143522',
                                  level='essential')
# Returns formatted context string:
# """
# # Restored Context: auth-feature-implementation
#
# ## Original Requirements
# Implement JWT authentication for API endpoints...
#
# ## Current State
# - JWT validation completed
# - Middleware integration in progress
# - Tests: 12/15 passing
#
# ## Open Items
# - Refresh token rotation strategy needed
# - Error messages for expired tokens
# """
```

### List All Snapshots

```python
result = context_management_skill('list')
# Returns:
# {
#   'snapshots': [
#     {'id': '20251116_143522', 'name': 'auth-feature', 'timestamp': '2025-11-16 14:35:22', 'size': '15KB'},
#     {'id': '20251116_092315', 'name': 'database-migration', 'timestamp': '2025-11-16 09:23:15', 'size': '22KB'}
#   ],
#   'count': 2,
#   'total_size': '37KB'
# }
```

## Proactive Usage Workflow

1. **User monitors token usage**: Check periodically with `context_management_skill('status')`
2. **At 70-85% threshold**: Create snapshot with `context_management_skill('snapshot', name='task-name')`
3. **Continue working**: Let Claude Code compact naturally or use `/transcripts` for full history
4. **After compaction**: Rehydrate with `context_management_skill('rehydrate', snapshot_id='...', level='essential')`
5. **Resume work**: Claude now has essential context without full conversation history

## Integration Notes

### Relationship to Existing Systems

**vs. PreCompact Hook:**

- PreCompact: Automatic, full conversation export, triggered by Claude Code
- Context Skill: Manual, intelligent extraction, user-initiated

**vs. /transcripts Command:**

- /transcripts: Reactive restoration of full conversation history
- Context Skill: Proactive management with selective rehydration

**Philosophy:**

- PreCompact Hook = Safety net (never lose anything)
- /transcripts = Full recovery tool
- Context Skill = Proactive optimization

### Storage Location

- Snapshots: `~/.amplihack/.claude/runtime/context-snapshots/`
- Transcripts: `~/.amplihack/.claude/runtime/logs/<session_id>/CONVERSATION_TRANSCRIPT.md`
- **No conflicts**: Different directories, different purposes

## Regeneration Notes

This module can be rebuilt from this specification while maintaining:

- ✅ Public contract (all skill actions and signatures preserved)
- ✅ Dependencies (pure Python standard library)
- ✅ Test interface (same test requirements)
- ✅ Module structure (same file organization)
- ✅ Integration points (complements existing systems without replacement)

## Decision: No PostCompact Hook

**Rationale**: A PostCompact hook is **NOT needed** because:

1. **Redundancy**: PreCompact already saves everything before compaction
2. **Timing**: After compaction, context is already gone (too late)
3. **Complexity**: Adds unnecessary automation without clear benefit
4. **Philosophy**: Trust in emergence - user controls when to snapshot/rehydrate

**Alternative**: User-initiated rehydration via this skill is simpler and more aligned with amplihack principles.

## Success Criteria

A successful implementation will:

- [ ] Allow users to check token usage on-demand
- [ ] Create intelligent context snapshots (not full dumps)
- [ ] Restore context at configurable detail levels
- [ ] Integrate seamlessly with existing transcript system
- [ ] Require no background processes or hooks
- [ ] Follow brick philosophy (4 independent components)
- [ ] Use only Python standard library
- [ ] Be regeneratable from this specification
- [ ] Enable proactive context management without automatic behavior

## Next Steps for Builder

1. Implement each brick independently (token_monitor, context_extractor, context_rehydrator, orchestrator)
2. Create data models (UsageStats, ContextSnapshot)
3. Implement main skill entry point
4. Write comprehensive tests
5. Create SKILL.md following Claude Code skill format
6. Add examples and documentation
7. Integration test with real conversation data
8. Verify against this specification
