# Context Management Skill

Proactive context window management for Claude Code sessions via intelligent token monitoring, context extraction, and selective rehydration.

**Version 3.0** - Now with predictive budget monitoring, context health indicators, and priority-based retention.

## What This Skill Does

This skill helps you proactively manage Claude's context window by:

1. **Monitoring token usage** against configurable thresholds
2. **Extracting essential context** (requirements, decisions, state) into snapshots
3. **Restoring context** at appropriate detail levels after compaction
4. **Managing snapshots** with list, create, and retrieve operations
5. **Predicting capacity limits** before they're reached (v3.0)
6. **Providing health indicators** for statusline integration (v3.0)
7. **Prioritizing content retention** for efficient snapshots (v3.0)

## Quick Start

```python
from context_management import context_management_skill

# Check current token usage
result = context_management_skill('status', current_tokens=750000)
# Returns: {'status': 'consider', 'usage': {...}}

# Create a snapshot
result = context_management_skill(
    'snapshot',
    conversation_data=messages,
    name='my-feature'
)
# Returns: {'status': 'success', 'snapshot': {...}}

# Rehydrate context
result = context_management_skill(
    'rehydrate',
    snapshot_id='20251116_143522',
    level='essential'
)
# Returns: {'status': 'success', 'context': '# Restored Context...'}

# List all snapshots
result = context_management_skill('list')
# Returns: {'snapshots': [...], 'count': N}
```

## Installation

This skill uses only Python standard library - no external dependencies required.

```bash
# The skill is ready to use immediately
# No installation needed
```

## Architecture

### Four Component Bricks

This skill follows the **brick philosophy** with four independent, single-responsibility components:

1. **TokenMonitor** (`token_monitor.py`)
   - Tracks token usage against thresholds (50%, 70%, 85%, 95%)
   - Provides recommendations based on usage percentage
   - Calculates tokens until next threshold

2. **ContextExtractor** (`context_extractor.py`)
   - Extracts original requirements from conversation
   - Identifies key decisions and rationales
   - Summarizes implementation state
   - Captures open items and questions
   - Tracks tools used during session
   - Creates snapshot files

3. **ContextRehydrator** (`context_rehydrator.py`)
   - Restores context from snapshot files
   - Provides three detail levels:
     - **Essential**: Requirements + current state
     - **Standard**: + decisions + open items
     - **Comprehensive**: + full details + metadata
   - Lists available snapshots
   - Formats context for Claude to process

4. **ContextManagementOrchestrator** (`orchestrator.py`)
   - Coordinates the three bricks
   - Handles skill action dispatch
   - Manages component lifecycle

### Public Interface

```python
# Main skill entry point
context_management_skill(action, **kwargs)

# Convenience functions
check_status(current_tokens)
create_snapshot(conversation_data, name=None)
rehydrate_context(snapshot_id, level='standard')
list_snapshots()
```

## Usage Patterns

### Pattern 1: Preventive Monitoring

```python
# Check token usage periodically
status = check_status(current_tokens=current)

if status['status'] == 'recommended':
    # Create snapshot before hitting limit
    snapshot = create_snapshot(messages, name='before-limit')
```

### Pattern 2: Progressive Rehydration

```python
# Start with minimal context
context = rehydrate_context(snapshot_id, level='essential')

# Upgrade if more detail needed
if need_more_context:
    context = rehydrate_context(snapshot_id, level='standard')

# Full context if necessary
if need_everything:
    context = rehydrate_context(snapshot_id, level='comprehensive')
```

### Pattern 3: Context Switching

```python
# Pause current work
snapshot_a = create_snapshot(messages, name='feature-a-paused')

# Work on something else
# [... new conversation ...]

# Resume previous work
context = rehydrate_context(snapshot_a_id, level='standard')
```

## Integration with Existing Tools

### PreCompact Hook (Safety Net)

- **What**: Automatically saves full conversation before compaction
- **When**: Triggered by Claude Code
- **Where**: `~/.amplihack/.claude/runtime/logs/<session_id>/CONVERSATION_TRANSCRIPT.md`
- **Relationship**: Safety net for complete recovery

### /transcripts Command (Reactive Recovery)

- **What**: Restores full conversation history after compaction
- **When**: User invoked after losing context
- **Where**: Reads from logs directory
- **Relationship**: Full recovery tool

### Context Management Skill (Proactive Optimization)

- **What**: Intelligent context extraction and selective rehydration
- **When**: User invoked at threshold warnings
- **Where**: `~/.amplihack/.claude/runtime/context-snapshots/*.json`
- **Relationship**: Proactive optimization tool

**All three are complementary, not competing.**

## Configuration

### Token Thresholds

Default thresholds (in `token_monitor.py`):

```python
THRESHOLDS = {
    'ok': 0.5,          # 0-50%: No action needed
    'consider': 0.7,    # 70%+: Consider snapshotting
    'recommended': 0.85, # 85%+: Snapshot recommended
    'urgent': 0.95      # 95%+: Snapshot urgent
}
```

### Snapshot Storage

Default location: `~/.amplihack/.claude/runtime/context-snapshots/`

Can be customized:

```python
result = context_management_skill(
    'snapshot',
    conversation_data=messages,
    snapshot_dir='/custom/path'
)
```

### Context Window Size

Default: 1,000,000 tokens (Claude's context window)

Can be customized:

```python
result = context_management_skill(
    'status',
    current_tokens=current,
    max_tokens=500_000  # Custom window size
)
```

## Testing

Comprehensive test suite with 85%+ coverage:

```bash
# Run all tests
pytest .claude/skills/context-management/tests/

# Run specific test file
pytest .claude/skills/context-management/tests/test_token_monitor.py

# Run with coverage
pytest --cov=context_management .claude/skills/context-management/tests/
```

Test organization:

- `test_token_monitor.py`: 25+ tests for TokenMonitor
- `test_context_extractor.py`: 20+ tests for ContextExtractor
- `test_context_rehydrator.py`: 25+ tests for ContextRehydrator
- `test_orchestrator.py`: 20+ tests for Orchestrator
- `test_integration.py`: 10+ end-to-end workflow tests

## Philosophy Alignment

### Ruthless Simplicity

- Four single-purpose bricks, no complex abstractions
- On-demand invocation, no background processes
- Pure Python standard library, zero external dependencies
- Clear contracts between components

### Single Responsibility

Each brick has ONE job:

- TokenMonitor: Track usage
- ContextExtractor: Extract and snapshot
- ContextRehydrator: Restore context
- Orchestrator: Coordinate components

### Zero-BS Implementation

- No stubs or placeholders
- All functions work completely
- Real file I/O, not simulated
- Actual token estimation

### Trust in Emergence

- User decides when to snapshot
- User chooses detail level
- No automatic behavior
- Proactive choice, not reactive automation

## File Structure

```
.claude/skills/context-management/
├── SKILL.md                    # Claude Code skill definition
├── README.md                   # This file
├── QUICK_START.md              # Quick reference guide
├── __init__.py                 # Public interface exports
├── core.py                     # Main skill entry point
├── models.py                   # Data models (UsageStats, ContextSnapshot)
├── token_monitor.py            # TokenMonitor brick
├── context_extractor.py        # ContextExtractor brick
├── context_rehydrator.py       # ContextRehydrator brick
├── orchestrator.py             # ContextManagementOrchestrator
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
    ├── basic_usage.md
    ├── proactive_workflow.md
    ├── proactive_management.md  # NEW in v3.0
    └── rehydration_levels.md
```

## Troubleshooting

### Snapshot not found

```python
result = rehydrate_context('invalid_id')
# Returns: {'status': 'error', 'error': 'Snapshot not found: invalid_id'}

# Solution: List snapshots to find valid IDs
snapshots = list_snapshots()
```

### Corrupted snapshot

If a snapshot JSON is corrupted, the skill will:

- Skip it in list operations
- Raise JSONDecodeError on rehydration

Solution: Create a new snapshot with fresh data.

### Token estimation inaccurate

Token estimation uses rough calculation: ~1 token per 4 characters.

This is intentional for simplicity. For exact counts, use Claude's token counter.

## Contributing

This skill follows amplihack's brick philosophy. When extending:

1. Keep bricks independent (single responsibility)
2. Use only standard library
3. Write comprehensive tests (85%+ coverage)
4. Update documentation
5. Follow existing patterns

## License

Part of the amplihack framework. See project LICENSE.

## Support

For issues, questions, or contributions:

- See: `~/.amplihack/.claude/context/PHILOSOPHY.md` for principles
- See: `Specs/context-management-skill.md` for specification
- See: `SKILL.md` for complete skill documentation
- See: `QUICK_START.md` for quick reference

## Version

3.0.0 - Proactive features

## Changelog

### 3.0.0 (2025-11-25)

- Added predictive budget monitoring (burn rate tracking)
- Added context health indicators for statusline integration
- Added priority-based context retention
- Added proactive_management.md example
- Updated SKILL.md with v3.0 features documentation
- Enhanced automation with smarter threshold adaptation

### 2.0.0 (2025-11-22)

- Refactored to use centralized context_manager.py tool
- Improved automation with adaptive checking frequency
- Added compaction detection and auto-rehydration

### 1.0.0 (2025-11-16)

- Initial implementation with four bricks
- Token monitoring with configurable thresholds
- Intelligent context extraction
- Three-level rehydration system
- Comprehensive test suite (85%+ coverage)
- Full documentation and examples
