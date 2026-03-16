# Transcript Viewer

View and browse session transcripts from **Claude Code** and **GitHub Copilot CLI**.

## Quick Start

Just ask naturally:

```
Show me my current session transcript
Browse all sessions
View copilot session abc123
Show transcript as HTML
```

The skill auto-activates on keywords like "transcript", "session log", "copilot session", etc.

## Supported Tools

| Tool                   | Log Location                              | Format                           |
| ---------------------- | ----------------------------------------- | -------------------------------- |
| **Claude Code**        | `~/.claude/projects/*/*.jsonl`            | JSONL (one JSON object per line) |
| **GitHub Copilot CLI** | `~/.copilot/session-state/*/events.jsonl` | JSONL (one JSON object per line) |

Both use JSONL format and are parsed by `claude-code-log`.

## Modes

### 1. Current Session

View the most recent session transcript.

```
View current transcript
Show my current copilot session
```

### 2. Specific Session

View a session by ID (supports partial ID matching).

```
Show session abc123
View copilot session def456
```

### 3. Agent Output

View background task output files from subagents.

```
Show agent output
View background task logs
```

### 4. Browse All Sessions

List all available sessions with date filtering.

```
Browse all sessions
List sessions from last 7 days
Show copilot session history
```

## Auto-Detection

The skill automatically detects which tool you're using:

1. **Directory check** (most reliable): looks for `~/.copilot/session-state/` and `~/.claude/projects/`
2. **Environment variables** (fallback): checks `CLAUDE_CODE_SESSION`, `GITHUB_COPILOT_TOKEN`, etc.
3. **Default**: Claude Code (safe fallback for most users)

When both tools have sessions, you'll be asked to choose.

## Output Formats

- **Markdown** (default) — displayed inline in the terminal
- **HTML** — saved to `/tmp/transcript-view.html` and opened in browser

```
View transcript as HTML
Export session to HTML
```

## Prerequisites

- **claude-code-log** (npm package) — required for JSONL→Markdown/HTML conversion
  ```bash
  npm install -g claude-code-log
  ```
  Or use via npx (no install needed): `npx claude-code-log --help`

## Copilot Session Structure

Each Copilot session directory contains:

```
~/.copilot/session-state/{session-id}/
├── events.jsonl     # Session history (JSONL)
├── workspace.yaml   # Session metadata
├── plan.md          # Implementation plan
└── checkpoints/     # Compaction history
```

## Limitations

- Requires `claude-code-log` or `npx` for JSONL conversion
- Date filtering uses filesystem modification times, not session timestamps
- Legacy Copilot sessions (`~/.copilot/history-session-state/`) require explicit path
- Cannot view transcripts from remote machines
