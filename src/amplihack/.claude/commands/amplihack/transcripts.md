---
name: amplihack:transcripts
version: 1.0.0
description: Manage and analyze conversation transcripts
triggers:
  - "View conversation history"
  - "Restore session context"
  - "Search past conversations"
  - "Find original request"
---

# /transcripts - Conversation Transcript Management

**Purpose**: amplihack-style transcript management for context preservation and restoration.

**Usage**: `/transcripts [action] [session_id]`

## Description

The `/transcripts` command provides conversation history management, implementing amplihack's "Never lose context again" approach. It handles automatic exports, restoration, and search across conversation transcripts.

## Actions

### `/transcripts` (default: list)

Shows recent conversation transcripts and original requests.

### `/transcripts list [count]`

Lists recent session transcripts with summaries.

- `count`: Number of sessions to show (default: 10)

### `/transcripts restore [session_id]`

Restores complete conversation context from a specific session.

- `session_id`: Target session (default: latest)

### `/transcripts search <query>`

Searches across all transcripts for specific content.

- `query`: Search term or phrase

### `/transcripts original [session_id]`

Shows the original request and requirements for a session.

- `session_id`: Target session (default: current)

## What To Do

When this command is invoked, use the `transcript_manager` tool to handle the request:

### List Sessions (No Args or "list")

```python
from transcript_manager import TranscriptManager, list_transcripts, get_transcript_summary

# List all available sessions
sessions = list_transcripts()

# Display formatted list with summaries
manager = TranscriptManager()
for i, session_id in enumerate(sessions[:10], 1):  # Show latest 10
    summary = get_transcript_summary(session_id)
    print(manager.format_summary_display(summary, i))
```

### Restore Latest Session ("latest")

```python
from transcript_manager import list_transcripts, restore_transcript, TranscriptManager

sessions = list_transcripts()
if sessions:
    context = restore_transcript(sessions[0])
    manager = TranscriptManager()
    print(manager.format_context_display(context))
```

### Restore Specific Session (<session_id>)

```python
from transcript_manager import restore_transcript, TranscriptManager

context = restore_transcript(session_id)
manager = TranscriptManager()
print(manager.format_context_display(context))
# Display:
# - Original user request
# - Conversation summary
# - Full transcript location
# - Compaction events (if any)
```

### Save Checkpoint ("save")

```python
from transcript_manager import save_checkpoint, TranscriptManager
from datetime import datetime

session_id = save_checkpoint()
manager = TranscriptManager()
checkpoint_count = manager.get_checkpoint_count(session_id)

# Display success message with:
# - Session ID
# - Checkpoint location
# - Checkpoint number
# - Timestamp
print(f"✅ Session checkpoint created!")
print(f"📄 Session ID: {session_id}")
print(f"🔖 Checkpoint #{checkpoint_count}")
print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
```

## Implementation

All transcript functionality is provided by the `transcript_manager` tool:

**Tool**: `~/.amplihack/.claude/tools/amplihack/transcript_manager.py`

This command provides instructions on how to use the tool. No Python code is executed directly by this command - Claude interprets the instructions and calls the tool.

## Examples

### List Recent Sessions

```
/transcripts list 5

📚 Recent Conversation Transcripts (Latest 5)
═════════════════════════════════════════════════════════════

🎯💬📦 **20250923_143022** - 2025-09-23 14:30:22
   Target: Context preservation system for original user requirements
   Messages: 47, Compactions: 2

🎯💬 **20250923_120815** - 2025-09-23 12:08:15
   Target: Fix CI pipeline authentication issues
   Messages: 23, Compactions: 0

📝 **20250923_094512** - 2025-09-23 09:45:12
   Target: General development task
   Messages: 8, Compactions: 0
```

### Restore Session Context

```
/transcripts restore 20250923_143022

🔄 Restored Session: 20250923_143022
📅 Timestamp: 2025-09-23 14:30:22

🎯 **Original Request**:
**Target**: Context preservation system for original user requirements
**Requirements**: 4 items
**Constraints**: 1 items

✅ Original request restored
✅ Conversation transcript available

📖 **Full Transcript**: .claude/runtime/logs/20250923_143022/CONVERSATION_TRANSCRIPT.md
   Use Read tool to view complete conversation history
```

### Search Transcripts

```
/transcripts search "amplihack"

🔍 Search Results for: 'amplihack'
Found 2 matches across sessions
═════════════════════════════════════════════════════════════

📄 **20250923_143022** - 2025-09-23 14:30:22
   File: ORIGINAL_REQUEST.md
   Preview: ...preservation for amplihack. Target: Context preservation system for...

📄 **20250922_211458** - 2025-09-22 21:14:58
   File: CONVERSATION_TRANSCRIPT.md
   Preview: ...amplihack's proven approach. Based on amplihack: - PreCompact Hook...
```

## Integration Notes

- **Automatic Export**: PreCompact hook automatically exports transcripts
- **Session Logging**: Session start hook preserves original requests
- **Context Restoration**: Enables full context recovery after compaction
- **Search Capability**: Find past conversations and decisions
- **Requirement Tracking**: Never lose original user requirements

## Benefits

1. **Never Lose Context**: Complete conversation history preserved
2. **Requirement Preservation**: Original user goals always accessible
3. **Easy Restoration**: Quick context recovery with `/transcripts restore`
4. **Searchable History**: Find past decisions and implementations
5. **Compaction Safe**: Automatic export before context loss

## Philosophy Alignment

- **Ruthless Simplicity**: Command is markdown instructions only, no Python code
- **Separation of Concerns**: Command provides instructions, tool implements business logic
- **Zero-BS**: All tool functions work completely, no stubs or placeholders
- **Brick Philosophy**: transcript_manager.py is a self-contained, regeneratable brick

## Resources

- **Tool**: `~/.amplihack/.claude/tools/amplihack/transcript_manager.py` (business logic)
- **Command**: `~/.amplihack/.claude/commands/amplihack/transcripts.md` (instructions only)
- **PreCompact Hook**: `~/.amplihack/.claude/tools/amplihack/hooks/pre_compact.py` (automatic export)

This command provides amplihack-style transcript management through a clean, reusable tool. The tool can be called from commands, skills, and hooks. It ensures that conversation context and original requirements are never lost, even during context compaction events.

**Key Takeaway**: Business logic lives in `transcript_manager.py`, this command just tells you how to use it.
