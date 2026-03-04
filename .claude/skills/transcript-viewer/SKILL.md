---
name: transcript-viewer
version: 1.0.0
description: |
  Convert and browse JSONL session transcripts as HTML or Markdown using claude-code-log.
  Supports viewing the current session, a specific session by ID, agent background task
  output files, or all project sessions with optional date-range filtering.
auto_activate_keywords:
  - "view transcript"
  - "show transcript"
  - "browse transcript"
  - "read transcript"
  - "view session log"
  - "show session log"
  - "transcript viewer"
  - "convert jsonl"
  - "view jsonl"
  - "browse sessions"
  - "session history"
  - "agent output"
  - "background task output"
priority_score: 35.0
evaluation_criteria:
  frequency: MEDIUM
  impact: HIGH
  complexity: LOW
  reusability: HIGH
  philosophy_alignment: HIGH
  uniqueness: HIGH
dependencies:
  tools:
    - Bash
    - Glob
    - Read
  external:
    - claude-code-log (npm package, optional — falls back to npx)
maturity: production
---

# Transcript Viewer Skill

## Purpose

This skill wraps the `claude-code-log` CLI to convert JSONL session transcripts into
readable HTML or Markdown. It provides four browsing modes:

1. **Current session** — View the active session's transcript
2. **Specific session** — View a session by its ID
3. **Agent output** — View background task output files produced by subagents
4. **All sessions** — Browse all project sessions, with optional date-range filtering

## Tool Detection

Before running any command, check whether `claude-code-log` is available:

```bash
# Step 1: direct install check
which claude-code-log 2>/dev/null

# Step 2: npx fallback
npx --yes claude-code-log --version 2>/dev/null
```

Set `CCL` to the resolved command:

```bash
if which claude-code-log &>/dev/null; then
  CCL="claude-code-log"
elif npx --yes claude-code-log --version &>/dev/null 2>&1; then
  CCL="npx claude-code-log"
else
  CCL=""
fi
```

### Missing Tool — Graceful Error

If `CCL` is empty, display this message and stop:

```
claude-code-log is not installed.

To install it globally:
  npm install -g claude-code-log

Or run without installing (requires npx):
  npx claude-code-log --help

After installing, retry your request.
```

Do not attempt to install it automatically.

## Modes

### Mode 1: Current Session

**Trigger phrases**: "view current transcript", "show my current session", "current log"

**What to do**:

1. Find the most recently modified JSONL file under `.claude/projects/` or the path
   returned by:
   ```bash
   ls -t ~/.claude/projects/*/*.jsonl 2>/dev/null | head -1
   ```
2. Run:
   ```bash
   $CCL <path-to-jsonl> --format markdown
   ```
3. Display the Markdown output inline.

**Example output**:

```markdown
# Session: 2025-11-23 19:32
**Model**: claude-sonnet-4-6
**Messages**: 42

---

**User**: Fix the authentication bug in login.py
**Assistant**: I'll examine the file...
...
```

### Mode 2: Specific Session by ID

**Trigger phrases**: "view session <ID>", "show transcript <ID>", "open log <ID>"

**What to do**:

1. Search for the JSONL file matching the session ID:
   ```bash
   find ~/.claude/projects -name "*.jsonl" | xargs grep -l "<SESSION_ID>" 2>/dev/null | head -1
   ```
   Or, if the ID looks like a filename fragment, use:
   ```bash
   ls ~/.claude/projects/*/ | grep "<SESSION_ID>"
   ```
2. Run:
   ```bash
   $CCL <path-to-jsonl> --format markdown
   ```
3. Display the output. If no file matches, report:
   ```
   No session found with ID: <SESSION_ID>
   Available sessions: run "view all sessions" to list them.
   ```

### Mode 3: Agent Background Task Output

**Trigger phrases**: "view agent output", "show background task output", "agent log"

**What to do**:

1. Find `.log` or `.jsonl` files created by background agent tasks. These are
   typically written to the current working directory or a temp path with a name
   matching `.agent-step-*.log` or similar:
   ```bash
   ls -t .agent-step-*.log 2>/dev/null
   ls -t /tmp/*.agent*.log 2>/dev/null
   ```
2. For each `.jsonl` file found, run `$CCL <file> --format markdown`.
3. For plain `.log` files (non-JSONL), display them directly with `cat`.
4. If no agent output files are found:
   ```
   No agent background task output files found in the current directory.
   Background agents write their output to files named .agent-step-<ID>.log.
   ```

### Mode 4: All Sessions (Browse)

**Trigger phrases**: "browse all sessions", "list transcripts", "view all sessions",
"show session history"

**What to do**:

1. List all JSONL files under `~/.claude/projects/`:
   ```bash
   find ~/.claude/projects -name "*.jsonl" -printf "%T@ %p\n" 2>/dev/null \
     | sort -rn | awk '{print $2}'
   ```
2. For each file, extract the session date and first user message:
   ```bash
   $CCL <file> --format markdown --summary
   # If --summary flag is not supported, just show filename and date
   head -1 <file> | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('timestamp',''))"
   ```
3. Print a summary table:
   ```
   Available Sessions
   ==================
   #   Date                  File
   1   2025-11-23 19:32:36   ~/.claude/projects/foo/abc123.jsonl
   2   2025-11-22 14:10:05   ~/.claude/projects/foo/def456.jsonl
   ...
   ```
4. Offer to open a specific session: "Enter a number to view that session."

#### Date-Range Filtering

When the user specifies a date range (e.g., "last 7 days", "between 2025-11-01 and 2025-11-30"):

```bash
# Filter by modification time (last N days)
find ~/.claude/projects -name "*.jsonl" -mtime -7

# Filter by date range using find -newer
find ~/.claude/projects -name "*.jsonl" \
  -newer /tmp/start_date_ref \
  ! -newer /tmp/end_date_ref
```

Create the reference files with `touch -d`:
```bash
touch -d "2025-11-01" /tmp/start_date_ref
touch -d "2025-11-30" /tmp/end_date_ref
```

## Output Formats

### Markdown (default)

Pass `--format markdown` to `claude-code-log`. The output is printed inline in the
conversation. Best for quick reading in the terminal or Claude Code.

### HTML

Pass `--format html` to `claude-code-log`. Write the output to a file and open it:

```bash
$CCL <file> --format html > /tmp/transcript-view.html
open /tmp/transcript-view.html 2>/dev/null \
  || xdg-open /tmp/transcript-view.html 2>/dev/null \
  || echo "HTML saved to /tmp/transcript-view.html — open it in your browser."
```

The user can request HTML explicitly: "view transcript as HTML" or "export to HTML".

## Full Workflow

When the user invokes this skill, follow this decision tree:

```
1. Detect CCL (which claude-code-log / npx fallback)
   → If missing: show install instructions and STOP

2. Determine mode from user message:
   - mentions "current" or no session specified → Mode 1 (Current Session)
   - mentions a session ID or hash             → Mode 2 (Specific Session)
   - mentions "agent" or "background"          → Mode 3 (Agent Output)
   - mentions "all", "browse", "list"          → Mode 4 (All Sessions)

3. Determine output format:
   - "as HTML" or "export HTML" → html
   - default                    → markdown

4. Execute the appropriate mode and display results.
```

## Error Handling

| Situation | Response |
|-----------|----------|
| `claude-code-log` not installed | Show install instructions, stop |
| JSONL file not found | "No session file found at <path>" |
| Session ID not found | "No session with ID <ID>. Run 'browse all sessions' to list available ones." |
| No agent output files | "No agent background task output found in current directory." |
| Empty JSONL file | "Session file is empty — no messages to display." |
| Date range produces no results | "No sessions found between <start> and <end>." |
| `claude-code-log` returns non-zero exit | Display stderr and suggest `--help` |

## Implementation Notes

### Detecting Session IDs

Claude Code session IDs are UUID-like strings. If the user writes something like
"view session abc123" or "show log def456", treat the last word as the session ID
and search for matching JSONL filenames.

### JSONL Structure

Claude Code session JSONL files contain one JSON object per line:

```json
{"type":"user","message":{"role":"user","content":[{"type":"text","text":"..."}]},"timestamp":"...","sessionId":"..."}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"..."}]},"timestamp":"..."}
```

`claude-code-log` handles parsing; this skill does not re-implement it.

### Philosophy Alignment

- **Thin wrapper**: This skill delegates to `claude-code-log` — no re-implementation of parsing
- **Graceful degradation**: Clear error messages when the tool is missing
- **Single responsibility**: Only views/converts transcripts, never modifies them
- **No hidden state**: All file paths are shown to the user

## Limitations

- Requires `claude-code-log` (npm) or `npx` to convert JSONL to HTML/Markdown
- Cannot view transcripts from remote machines
- Date filtering relies on filesystem modification times, not session timestamps
- `--summary` flag availability depends on `claude-code-log` version

## Quick Reference

| User says | Mode | Command |
|-----------|------|---------|
| "view current transcript" | Current session | `$CCL <latest.jsonl> --format markdown` |
| "show session abc123" | Specific session | `$CCL <abc123.jsonl> --format markdown` |
| "view agent output" | Agent output | `cat .agent-step-*.log` or `$CCL *.jsonl` |
| "browse all sessions" | All sessions | list + summarize all `~/.claude/projects/**/*.jsonl` |
| "view transcript as HTML" | Any + HTML | `$CCL <file> --format html > /tmp/view.html` |
| "last 7 days" (with browse) | Date filter | `find ... -mtime -7` |
