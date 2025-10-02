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

## Implementation

The actual implementation is in `/Users/ryan/src/hackathon/MicrosoftHackathon2025-AgenticCoding/.claude/commands/transcripts.py`

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

This command provides amplihack-style transcript management, ensuring that conversation context and original requirements are never lost, even during context compaction events.
