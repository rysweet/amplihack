# Module: TodoWrite Phase Grouping Enhancement

## Problem Statement

During long-running Ultra-Think sessions, users cannot easily tell:
- Which workflow phase they're in
- How much progress has been made
- What's coming next
- Why tasks happen in a specific order

The current TodoWrite implementation shows a flat list of tasks without workflow context.

## Solution Analysis

### Option 1: Client-Side Display Enhancement (RECOMMENDED)
**Approach**: Enhance `_format_todos_for_terminal()` to detect and group phase information from todo content
**Pros**:
- No SDK changes required
- Works immediately with existing TodoWrite calls
- Backward compatible
- Simple to implement and test

**Cons**:
- Requires convention in todo content (e.g., "Phase N:" prefix)
- Phase detection is pattern-based

### Option 2: Extended TodoWrite Schema
**Approach**: Extend todo items with phase metadata fields
**Pros**:
- Explicit phase information
- Type-safe phase tracking

**Cons**:
- Requires SDK changes (out of scope)
- Breaks existing TodoWrite callers
- Complex migration path

### Option 3: Separate Phase Tracking Tool
**Approach**: Create new tool for phase tracking alongside TodoWrite
**Pros**:
- Separate concerns
- No TodoWrite changes

**Cons**:
- Fragmented state (todos + phases separate)
- Requires multiple tool calls
- More complexity

## Recommendation: Option 1

Enhance the display layer to extract phase information from todo content using conventions. This is the simplest, most pragmatic approach that delivers value immediately without breaking changes.

## Architecture Design

### Phase 1: Enhanced Display Layer

**Module**: `auto_mode._format_todos_for_terminal()`

**Purpose**: Transform flat todo list into phase-grouped display with progress indicators

**Contract**:
- **Input**: `list[dict]` - todo items with content, status, activeForm
- **Output**: `str` - formatted string with phase grouping and progress
- **Side Effects**: None (pure formatting function)

**Detection Strategy**:

Todos can opt into phase grouping by using this content format:
```
"PHASE N: [Phase Name] - [Task Description]"
```

Example:
```python
{
    "content": "PHASE 2: DESIGN - Use architect agent to design solution",
    "status": "in_progress",
    "activeForm": "Using architect agent to design solution"
}
```

**Display Format**:

```
📋 WORKFLOW PROGRESS

🎯 PHASE 1: REQUIREMENTS [✅ COMPLETED - 2/2 tasks]
  ✓ Clarify requirements with prompt-writer agent
  ✓ Analyze existing implementation

🎯 PHASE 2: DESIGN [⏳ IN PROGRESS - 1/3 tasks]
  ✓ Create worktree and branch
  ⏳ Use architect agent to design solution (ACTIVE)
  ○ Use api-designer for API contracts

🎯 PHASE 3: IMPLEMENTATION [○ PENDING - 0/5 tasks]
  ○ Use builder agent to implement changes
  ○ Use tester agent for test coverage
  ...

Overall Progress: 3/10 tasks complete (30%)
```

### Implementation Specification

#### 1. Phase Detection Function

```python
def _extract_phase_info(todo: dict) -> tuple[Optional[int], Optional[str], str]:
    """Extract phase information from todo content.

    Args:
        todo: Todo item with content field

    Returns:
        Tuple of (phase_number, phase_name, task_description)
        Returns (None, None, original_content) if no phase pattern found
    """
    content = todo.get("content", "")

    # Pattern: "PHASE N: [Phase Name] - [Task]"
    import re
    match = re.match(r'^PHASE\s+(\d+):\s*([^-]+?)\s*-\s*(.+)$', content, re.IGNORECASE)

    if match:
        phase_num = int(match.group(1))
        phase_name = match.group(2).strip()
        task_desc = match.group(3).strip()
        return (phase_num, phase_name, task_desc)

    return (None, None, content)
```

#### 2. Phase Grouping Function

```python
def _group_todos_by_phase(todos: list) -> dict:
    """Group todos by phase and calculate progress.

    Args:
        todos: List of todo items

    Returns:
        {
            'phases': {
                1: {'name': 'REQUIREMENTS', 'tasks': [...], 'completed': N, 'total': M},
                2: {'name': 'DESIGN', 'tasks': [...], 'completed': N, 'total': M},
                ...
            },
            'ungrouped': [...],  # Todos without phase info
            'total_completed': N,
            'total_tasks': M
        }
    """
    phases = {}
    ungrouped = []
    total_completed = 0
    total_tasks = len(todos)

    for todo in todos:
        phase_num, phase_name, task_desc = _extract_phase_info(todo)

        if phase_num is not None:
            if phase_num not in phases:
                phases[phase_num] = {
                    'name': phase_name,
                    'tasks': [],
                    'completed': 0,
                    'total': 0
                }

            # Create task item with extracted description
            task_item = {
                'description': task_desc,
                'status': todo['status'],
                'activeForm': todo.get('activeForm', task_desc)
            }

            phases[phase_num]['tasks'].append(task_item)
            phases[phase_num]['total'] += 1

            if todo['status'] == 'completed':
                phases[phase_num]['completed'] += 1
                total_completed += 1
        else:
            ungrouped.append(todo)
            if todo['status'] == 'completed':
                total_completed += 1

    return {
        'phases': phases,
        'ungrouped': ungrouped,
        'total_completed': total_completed,
        'total_tasks': total_tasks
    }
```

#### 3. Enhanced Formatting Function

```python
def _format_todos_for_terminal(self, todos: list) -> str:
    """Format todo list for terminal display with phase grouping.

    Args:
        todos: List of todo items

    Returns:
        Formatted string with phase grouping and progress indicators
    """
    if not todos:
        return ""

    # ANSI color codes
    BOLD = "\033[1m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    RESET = "\033[0m"

    # Group todos by phase
    grouped = self._group_todos_by_phase(todos)

    lines = []

    # If we have phase-grouped todos, show structured format
    if grouped['phases']:
        lines.append(f"\n{BOLD}📋 WORKFLOW PROGRESS{RESET}\n")

        # Show each phase
        for phase_num in sorted(grouped['phases'].keys()):
            phase = grouped['phases'][phase_num]

            # Determine phase status
            if phase['completed'] == phase['total']:
                phase_icon = f"{GREEN}✅{RESET}"
                phase_status = "COMPLETED"
            elif phase['completed'] > 0:
                phase_icon = f"{YELLOW}⏳{RESET}"
                phase_status = "IN PROGRESS"
            else:
                phase_icon = f"{BLUE}○{RESET}"
                phase_status = "PENDING"

            # Phase header
            lines.append(
                f"\n{BOLD}🎯 PHASE {phase_num}: {phase['name'].upper()}{RESET} "
                f"[{phase_icon} {phase_status} - {phase['completed']}/{phase['total']} tasks]"
            )

            # Phase tasks
            for task in phase['tasks']:
                status = task['status']

                if status == "completed":
                    indicator = f"{GREEN}✓{RESET}"
                    text = task['description']
                elif status == "in_progress":
                    indicator = f"{YELLOW}⏳{RESET}"
                    text = f"{task['activeForm']} (ACTIVE)"
                else:  # pending
                    indicator = f"{BLUE}○{RESET}"
                    text = task['description']

                lines.append(f"  {indicator} {text}")

        # Show ungrouped tasks if any
        if grouped['ungrouped']:
            lines.append(f"\n{BOLD}📝 Other Tasks:{RESET}")
            for todo in grouped['ungrouped']:
                status = todo.get("status", "pending")
                content = todo.get("content", "")
                active_form = todo.get("activeForm", content)

                if status == "completed":
                    indicator = f"{GREEN}✓{RESET}"
                    text = content
                elif status == "in_progress":
                    indicator = f"{YELLOW}⟳{RESET}"
                    text = active_form
                else:
                    indicator = f"{BLUE}○{RESET}"
                    text = content

                lines.append(f"  {indicator} {text}")

        # Overall progress
        percentage = int((grouped['total_completed'] / grouped['total_tasks']) * 100) if grouped['total_tasks'] > 0 else 0
        lines.append(
            f"\n{BOLD}Overall Progress:{RESET} {grouped['total_completed']}/{grouped['total_tasks']} tasks ({percentage}%)\n"
        )
    else:
        # Fallback to original flat format if no phases detected
        lines.append(f"\n{BOLD}📋 Todo List:{RESET}")

        for todo in todos:
            status = todo.get("status", "pending")
            content = todo.get("content", "")
            active_form = todo.get("activeForm", content)

            if status == "completed":
                indicator = f"{GREEN}✓{RESET}"
                text = content
            elif status == "in_progress":
                indicator = f"{YELLOW}⟳{RESET}"
                text = active_form
            else:
                indicator = f"{BLUE}○{RESET}"
                text = content

            lines.append(f"  {indicator} {text}")

        lines.append("")

    return "\n".join(lines)
```

### Module Dependencies

- `re` module for pattern matching
- Existing ANSI color codes
- No new external dependencies

### Testing Requirements

#### Unit Tests

1. **Phase Detection Tests**:
   - Detect valid phase patterns
   - Handle invalid/missing phase patterns
   - Extract phase number, name, and task correctly
   - Handle edge cases (no dashes, extra spaces, etc.)

2. **Grouping Tests**:
   - Group tasks by phase number correctly
   - Calculate progress per phase
   - Handle mixed grouped/ungrouped todos
   - Handle empty todo lists

3. **Formatting Tests**:
   - Phase-grouped format renders correctly
   - Fallback to flat format when no phases
   - ANSI codes applied correctly
   - Overall progress calculation
   - Status indicators (✅ ⏳ ○) correct

#### Integration Tests

1. **Real TodoWrite Flow**:
   - Create todos with phase format
   - Verify display shows grouped format
   - Verify progress updates correctly

2. **Backward Compatibility**:
   - Old-style todos still work
   - Mixed old/new format handled gracefully

### Backward Compatibility

**Guaranteed**:
- Existing TodoWrite calls with no phase info will display in original flat format
- Phase detection is opt-in via content convention
- No breaking changes to existing code

## Implementation Plan

### Phase 1: Core Functions (TDD)
1. Write tests for `_extract_phase_info()`
2. Implement `_extract_phase_info()`
3. Write tests for `_group_todos_by_phase()`
4. Implement `_group_todos_by_phase()`

### Phase 2: Display Enhancement (TDD)
1. Write tests for enhanced `_format_todos_for_terminal()`
2. Implement enhanced formatting with phase grouping
3. Ensure fallback to original format works

### Phase 3: Integration & Testing
1. Test with real TodoWrite calls in auto mode
2. Verify ANSI rendering in terminal
3. Test mixed grouped/ungrouped scenarios

### Phase 4: Documentation & Examples
1. Update workflow to use phase-format todos
2. Add examples to ultrathink command
3. Document convention in CLAUDE.md

## Success Criteria

- Users can see which workflow phase is active
- Progress indicators show completion percentage
- Tasks are logically grouped by phase
- Backward compatible with existing todos
- All tests pass
- Zero-BS implementation (no stubs, no TODOs)

## Files to Modify

1. `/home/azureuser/src/MicrosoftHackathon2025-AgenticCoding/worktrees/feat/issue-1103-todowrite-enhancement/src/amplihack/launcher/auto_mode.py`
   - Add `_extract_phase_info()` method
   - Add `_group_todos_by_phase()` method
   - Enhance `_format_todos_for_terminal()` method

2. `/home/azureuser/src/MicrosoftHackathon2025-AgenticCoding/worktrees/feat/issue-1103-todowrite-enhancement/tests/unit/test_todowrite_phase_grouping.py` (NEW)
   - Unit tests for all three functions

3. `/home/azureuser/src/MicrosoftHackathon2025-AgenticCoding/worktrees/feat/issue-1103-todowrite-enhancement/tests/integration/test_todowrite_display.py` (NEW)
   - Integration tests for real TodoWrite flow

## Risk Mitigation

**Risk**: Pattern matching too rigid
**Mitigation**: Use flexible regex, document convention clearly

**Risk**: ANSI codes break in some terminals
**Mitigation**: Reuse existing ANSI code patterns that already work

**Risk**: Performance with large todo lists
**Mitigation**: Linear complexity, no performance concern for typical todo counts (<50)

## Philosophical Alignment

- **Ruthless Simplicity**: Convention over configuration, pattern-based detection
- **Zero-BS**: Pure functions, no stubs, complete implementation
- **Modular Design**: Clear separation (detection → grouping → formatting)
- **Backward Compatible**: Graceful fallback to original format
- **Regeneratable**: Clear spec allows complete rebuild
