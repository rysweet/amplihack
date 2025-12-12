# Context Management Refactoring Architecture

**Date**: 2025-11-24
**Issue**: #1575
**Branch**: `refactor/issue-1575-simplify-profile-api-clean`

## Executive Summary

This document describes the refactored architecture for context management and transcript management in amplihack, following Claude Code skill best practices and the brick philosophy.

**Key Achievement**: Separated business logic from presentation layer, created reusable tools, and made skills/commands instruction-only.

## Problem Statement

The original context management implementation had several architectural issues:

1. **Skill contained business logic** - `.claude/skills/context_management/` had Python files with implementation
2. **Skill too large** - SKILL.md was 513 lines (should be < 500)
3. **Command was Python code** - `transcripts.py` was executable Python (should be markdown)
4. **Hook had inline logic** - `post_tool_use.py` imported and inlined context automation
5. **Not extensible** - Hook was tightly coupled to context management only

## Solution Overview

### Architectural Principles

1. **Separation of Concerns**: Business logic in tools/, instructions in skills/ and commands/
2. **Brick Philosophy**: Self-contained, regeneratable modules with clear public APIs
3. **Extensibility**: Hook system supports multiple tools via registry pattern
4. **Best Practices**: Follows Claude Code skill guidelines (< 500 lines, instructions-only)

### New Architecture

```
.claude/
├── tools/amplihack/
│   ├── context_manager.py          # Context management brick (900+ lines)
│   ├── transcript_manager.py       # Transcript management brick (400+ lines)
│   ├── context_automation_hook.py  # Bridge between hook and context_manager
│   └── hooks/
│       ├── post_tool_use.py        # Refactored to use registry
│       └── tool_registry.py        # Extensible hook registration system
│
├── skills/context_management/
│   └── SKILL.md                    # Instructions only (395 lines, < 500 ✓)
│
└── commands/amplihack/
    └── transcripts.md              # Markdown instructions only
```

## Component Details

### 1. context_manager.py

**Location**: `.claude/tools/amplihack/context_manager.py`
**Lines**: ~900
**Purpose**: Self-contained context management brick with ONE clear responsibility

**Public API**:

```python
# Data Models
ContextStatus(current_tokens, max_tokens, percentage, threshold_status, recommendation)
ContextSnapshot(snapshot_id, name, timestamp, ...)

# Main Class
ContextManager(snapshot_dir, max_tokens, state_file)
  - check_status(current_tokens) -> ContextStatus
  - create_snapshot(conversation_data, name) -> ContextSnapshot
  - rehydrate(snapshot_id, level) -> str
  - list_snapshots() -> List[Dict]
  - run_automation(current_tokens, conversation_data) -> Dict

# Convenience Functions
check_context_status(current_tokens) -> ContextStatus
create_context_snapshot(conversation_data, name) -> ContextSnapshot
rehydrate_from_snapshot(snapshot_id, level) -> str
list_context_snapshots() -> List[Dict]
run_automation(current_tokens, conversation_data) -> Dict
```

**Philosophy**:

- Single responsibility: Monitor, extract, rehydrate context
- Standard library only (no external dependencies)
- Zero-BS implementation (all functions work completely)
- Self-contained and regeneratable

**Consolidates**:

- `token_monitor.py`
- `context_extractor.py`
- `context_rehydrator.py`
- `orchestrator.py`
- `automation.py`
- `models.py`

### 2. transcript_manager.py

**Location**: `.claude/tools/amplihack/transcript_manager.py`
**Lines**: ~400
**Purpose**: Self-contained transcript management brick

**Public API**:

```python
# Data Models
TranscriptSummary(session_id, timestamp, target, message_count, ...)

# Main Class
TranscriptManager(logs_dir)
  - list_sessions() -> List[str]
  - get_summary(session_id) -> TranscriptSummary
  - restore_context(session_id) -> Dict
  - save_checkpoint(session_id) -> str
  - get_current_session_id() -> str
  - format_summary_display(summary, index) -> str
  - format_context_display(context) -> str

# Convenience Functions
list_transcripts() -> List[str]
get_transcript_summary(session_id) -> TranscriptSummary
restore_transcript(session_id) -> Dict
save_checkpoint(session_id) -> str
get_current_session_id() -> str
```

**Philosophy**:

- Single responsibility: Save and restore conversation transcripts
- Standard library only
- Zero-BS implementation
- Self-contained and regeneratable

**Replaces**:

- `.claude/commands/transcripts.py` (343 lines of Python code)

### 3. tool_registry.py

**Location**: `.claude/tools/amplihack/hooks/tool_registry.py`
**Lines**: ~300
**Purpose**: Extensible hook registration system

**Public API**:

```python
# Data Models
HookResult(actions_taken, warnings, metadata, skip_remaining)

# Main Class
ToolRegistry()
  - register(hook) -> Callable
  - execute_hooks(input_data) -> List[HookResult]
  - clear() -> None
  - count() -> int

# Functions
register_tool_hook(func) -> Callable  # Decorator
get_global_registry() -> ToolRegistry
aggregate_hook_results(results) -> Dict
```

**Philosophy**:

- Single responsibility: Register and dispatch tool hooks
- Extensible for adding new tools
- Zero-BS implementation

**Key Feature**: Allows multiple tools to register handlers that run after tool use events, not just context management.

### 4. context_automation_hook.py

**Location**: `.claude/tools/amplihack/context_automation_hook.py`
**Lines**: ~150
**Purpose**: Bridge between hook system and context_manager

**Public API**:

```python
context_management_hook(input_data) -> HookResult
register_context_hook() -> None
```

**Philosophy**:

- Single responsibility: Bridge between hook system and context_manager
- Standard library only
- Automatic registration via decorator

**Key Feature**: Registered automatically with `@register_tool_hook` decorator.

### 5. Refactored post_tool_use.py

**Location**: `.claude/tools/amplihack/hooks/post_tool_use.py`
**Changes**:

- Removed direct imports of `automation.py`
- Added `_setup_tool_hooks()` method
- Uses `tool_registry` for extensibility
- Calls `get_global_registry().execute_hooks(input_data)`
- Aggregates results from all registered hooks

**Before** (tight coupling):

```python
from context_management.automation import run_automation
# ... inline logic to call run_automation
```

**After** (extensible):

```python
from tool_registry import get_global_registry, aggregate_hook_results

def _setup_tool_hooks(self):
    from context_automation_hook import register_context_hook
    register_context_hook()  # Registers with global registry

def process(self, input_data):
    registry = get_global_registry()
    hook_results = registry.execute_hooks(input_data)
    aggregated = aggregate_hook_results(hook_results)
    # ... handle aggregated results
```

### 6. Refactored SKILL.md

**Location**: `.claude/skills/context_management/SKILL.md`
**Lines**: 395 (< 500 ✓)
**Changes**:

- Removed implementation details
- Kept instructions only
- Points to `context_manager.py` for implementation
- Shows how to call the tool's public API

**Before**: 513 lines with detailed implementation explanations
**After**: 395 lines with clear usage instructions

### 7. Refactored transcripts.md

**Location**: `.claude/commands/amplihack/transcripts.md`
**Type**: Markdown (not Python)
**Changes**:

- Converted from `.py` to `.md`
- Shows how to call `transcript_manager.py`
- Instructions only, no executable code in the command file

**Before**: `transcripts.py` with 343 lines of Python code
**After**: `transcripts.md` with markdown instructions that call the tool

## Integration Flow

### Context Management Flow

```
User request
    ↓
Skills/context_management/SKILL.md (instructions)
    ↓
[Imports]
    ↓
.claude/tools/amplihack/context_manager.py (business logic)
    ↓
[Executes logic, returns results]
    ↓
Skills presents results to user
```

### Automatic Hook Flow

```
Tool use event
    ↓
.claude/tools/amplihack/hooks/post_tool_use.py
    ↓
get_global_registry().execute_hooks(input_data)
    ↓
[For each registered hook:]
    context_automation_hook.context_management_hook(input_data)
        ↓
    .claude/tools/amplihack/context_manager.py
        run_automation(tokens, conversation_data)
            ↓
        [Automatic monitoring, snapshots, rehydration]
            ↓
        Returns HookResult
    ↓
Aggregate all HookResults
    ↓
Return to post_tool_use.py for logging
```

### Transcript Command Flow

```
User: /transcripts latest
    ↓
.claude/commands/amplihack/transcripts.md (instructions)
    ↓
[Claude interprets markdown, imports tool]
    ↓
from transcript_manager import restore_transcript, TranscriptManager
    ↓
.claude/tools/amplihack/transcript_manager.py (business logic)
    ↓
context = restore_transcript(sessions[0])
manager = TranscriptManager()
print(manager.format_context_display(context))
    ↓
[Results displayed to user]
```

## Benefits

### 1. Separation of Concerns

- **Business logic** in `.claude/tools/amplihack/` (reusable, testable)
- **Presentation logic** in `.claude/skills/` and `.claude/commands/` (instructions)
- **Clear boundaries** between what does the work vs what tells you how to use it

### 2. Extensibility

- Adding new tool hooks is easy:

  ```python
  # new_tool_hook.py
  @register_tool_hook
  def my_hook(input_data):
      return HookResult(actions_taken=["something"])

  # post_tool_use.py
  from new_tool_hook import register_my_hook
  register_my_hook()  # Done!
  ```

### 3. Best Practices Compliance

- ✅ Skills < 500 lines
- ✅ Instructions only in skills/commands
- ✅ Business logic in separate tools
- ✅ Standard library only for core tools
- ✅ Self-contained, regeneratable modules

### 4. Testability

- Tools have CLI interfaces for testing
- Unit tests can test tools directly
- Integration tests can test hook system
- E2E tests can test skills/commands

### 5. Maintainability

- Single source of truth for business logic
- Easy to find and fix bugs (in one place)
- Easy to add features (extend tools)
- Easy to regenerate components (modular)

## Migration Notes

### Old Files (Deprecated)

These files are no longer needed and can be removed after migration period:

```
.claude/skills/context_management/
├── automation.py
├── core.py
├── orchestrator.py
├── token_monitor.py
├── context_extractor.py
├── context_rehydrator.py
└── models.py

.claude/commands/
└── transcripts.py  # Now transcripts.md
```

### New Files (Active)

```
.claude/tools/amplihack/
├── context_manager.py          # ✅ Consolidates all context management logic
├── transcript_manager.py       # ✅ Consolidates all transcript logic
├── context_automation_hook.py  # ✅ Bridge to hook system
└── hooks/
    ├── tool_registry.py        # ✅ Extensible hook registration
    └── post_tool_use.py        # ✅ Refactored to use registry

.claude/skills/context_management/
└── SKILL.md                    # ✅ Refactored to 395 lines, instructions only

.claude/commands/amplihack/
└── transcripts.md              # ✅ Markdown instructions only
```

### Backward Compatibility

- **Skills**: Old imports like `from context_management import check_status` still work (convenience functions)
- **Commands**: `/transcripts` command works the same from user perspective
- **Hooks**: Context automation happens automatically as before
- **Breaking changes**: Only for code that directly imported old skill modules

## Testing Strategy

### Unit Tests

- `context_manager.py` - Test all public functions
- `transcript_manager.py` - Test all public functions
- `tool_registry.py` - Test registration and execution

### Integration Tests

- Hook system - Test hook registration and execution
- Context automation - Test automatic snapshot creation
- Transcript restoration - Test full workflow

### E2E Tests

- Skills - Test user-facing functionality
- Commands - Test command invocation
- Hooks - Test automatic behavior

### CLI Testing

All tools have CLI interfaces for quick testing:

```bash
# Context manager
python .claude/tools/amplihack/context_manager.py status 500000
python .claude/tools/amplihack/context_manager.py list

# Transcript manager
python .claude/tools/amplihack/transcript_manager.py list
python .claude/tools/amplihack/transcript_manager.py current

# Tool registry
python .claude/tools/amplihack/hooks/tool_registry.py
```

## Future Enhancements

### Additional Tool Hooks

The registry system makes it easy to add new hooks:

- **Code quality hook**: Run linters/formatters after file operations
- **Testing hook**: Auto-run tests after code changes
- **Documentation hook**: Update docs after API changes
- **Security hook**: Scan for security issues after tool use

### Enhanced Context Management

- **Smart compression**: Better context extraction algorithms
- **Semantic search**: Find snapshots by content, not just name
- **Auto-cleanup**: Delete old snapshots based on age/size
- **Sharing**: Export/import snapshots between sessions

### Enhanced Transcript Management

- **Search**: Search across all transcripts for specific content
- **Analysis**: Analyze patterns in conversation history
- **Export**: Export transcripts in different formats (PDF, HTML)
- **Tagging**: Tag sessions for better organization

## Conclusion

This refactoring achieves:

✅ **Separation of concerns** - Business logic separated from presentation
✅ **Best practices compliance** - Follows Claude Code guidelines
✅ **Extensibility** - Easy to add new tool hooks
✅ **Maintainability** - Single source of truth for logic
✅ **Testability** - CLI interfaces and modular design
✅ **Philosophy alignment** - Ruthless simplicity, brick design, zero-BS

The new architecture provides a solid foundation for future enhancements while maintaining backward compatibility and following established best practices.

## References

- **Claude Code Skill Best Practices**: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- **Amplihack Philosophy**: `.claude/context/PHILOSOPHY.md`
- **Amplihack Patterns**: `.claude/context/PATTERNS.md`
- **Issue #1575**: Context management refactoring

---

**Document Version**: 1.0
**Last Updated**: 2025-11-24
**Author**: Claude (via amplihack ultrathink workflow)
