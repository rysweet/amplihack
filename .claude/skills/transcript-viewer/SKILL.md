---
name: transcript-viewer
version: 1.1.0
description: |
  Convert and browse session transcripts as HTML or Markdown.
  Supports Claude Code JSONL logs (auto-saved to ~/.claude/projects/) and
  GitHub Copilot CLI markdown exports (created via /share markdown).
  Auto-detects log source based on file format and context.
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
  - "copilot transcript"
  - "copilot session"
  - "copilot log"
  - "view copilot"
  - "show copilot session"
  - "copilot history"
  - "copilot export"
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

This skill converts and browses session transcripts from two supported tools:

- **Claude Code** — JSONL logs auto-saved to `~/.claude/projects/`
- **GitHub Copilot CLI** — Markdown exports created via `/share markdown <file>`

It provides four browsing modes:

1. **Current session** — View the active session's transcript
2. **Specific session** — View a session by its ID
3. **Agent output** — View background task output files produced by subagents
4. **All sessions** — Browse all project sessions, with optional date-range filtering

## Tool Context Auto-Detection

Before browsing, detect which tool is active to set default log paths.
This uses the same env var markers as `src/amplihack/hooks/launcher_detector.py`:

```bash
if [[ -n "${CLAUDE_CODE_SESSION:-}${CLAUDE_SESSION_ID:-}${ANTHROPIC_API_KEY:-}" ]]; then
  TOOL_CONTEXT="claude-code"
  DEFAULT_LOG_DIR="$HOME/.claude/projects"
elif [[ -n "${GITHUB_COPILOT_TOKEN:-}${COPILOT_SESSION:-}" ]]; then
  # Note: GITHUB_TOKEN is intentionally excluded — it's too generic and
  # appears in non-Copilot CI contexts, causing false positives.
  # launcher_detector.py includes it but the skill omits it for safety.
  TOOL_CONTEXT="copilot"
  DEFAULT_LOG_DIR=""  # Copilot has no auto-saved logs; see Copilot section
else
  # Default to claude-code — safe fallback (most users)
  TOOL_CONTEXT="claude-code"
  DEFAULT_LOG_DIR="$HOME/.claude/projects"
fi
```

The user can always override with an explicit path.

## Log Format Auto-Detection

When given a file path, detect its format before processing:

```bash
detect_log_format() {
  local file="$1"
  if [[ "$file" == *.jsonl ]]; then
    echo "jsonl"
  elif [[ "$file" == *.md ]]; then
    # Check for Copilot /share export signature — specific header only
    # Note: do NOT match on "/share" alone (too generic — appears in docs, READMEs)
    if grep -q "Copilot Session Export\|copilot-session" "$file" 2>/dev/null; then
      echo "copilot-markdown"
    else
      echo "markdown"
    fi
  elif [[ "$file" == *.log ]]; then
    # .log files may be plain text or agent JSONL; check content
    local first_char
    first_char=$(head -c 1 "$file" 2>/dev/null)
    if [[ "$first_char" == "{" ]]; then
      echo "jsonl"
    else
      echo "plain-log"
    fi
  else
    # Inspect first byte for other extensions
    local first_char
    first_char=$(head -c 1 "$file" 2>/dev/null)
    if [[ "$first_char" == "{" ]]; then
      echo "jsonl"
    else
      echo "unknown"
    fi
  fi
}
```

| Format | Handler |
|--------|---------|
| `jsonl` | Pass to `claude-code-log` |
| `copilot-markdown` | Display inline (already readable Markdown) |
| `markdown` | Display inline |
| `unknown` | Warn and display raw |

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
2. For each file found, run `detect_log_format <file>` to classify it:
   - `jsonl` → run `$CCL <file> --format markdown`
   - `plain-log` → display directly with `cat`
3. This ensures JSONL-formatted `.log` files (rare but possible) are rendered properly.
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

## GitHub Copilot CLI Support

### Key Difference: No Automatic Log Persistence

GitHub Copilot CLI does **not** automatically save session transcripts to disk. Unlike
Claude Code (which auto-saves every session to `~/.claude/projects/*.jsonl`), Copilot CLI
keeps sessions **in memory only** during the session.

There is **no** `~/.copilot/logs/` or `~/.local/share/github-copilot-cli/` directory.
Copilot does not have a `log` or `transcript` subcommand.

### How to Export a Copilot Session

To preserve a Copilot session, use the `/share` command **within the Copilot CLI**:

```
# In Copilot CLI:
/share markdown ./my-session.md    # Export to a local markdown file
/share gist                        # Export to a GitHub gist
```

The exported file is plain Markdown with this structure:

```markdown
# Copilot Session Export

**Date**: 2025-11-23 19:32:36
**Session ID**: copilot-session-xyz789

---

**User**: Fix the authentication bug in login.py

**Copilot**: I'll examine the file and fix the authentication bug...

---
```

### Viewing a Copilot Export

When the user provides a `.md` file exported from Copilot:

1. Detect the format:
   ```bash
   if grep -q "Copilot Session Export\|copilot-session" "$FILE" 2>/dev/null; then
     FORMAT="copilot-markdown"
   fi
   ```
2. Display it directly (it is already human-readable Markdown — no `claude-code-log` needed):
   ```bash
   cat "$FILE"
   ```
3. Optionally extract a summary of turns:
   ```bash
   echo "=== Session Summary ==="
   grep -E "^\*\*User\*\*:|^\*\*Copilot\*\*:" "$FILE" | head -20
   ```

### Running Under Copilot — Guidance Message

If the skill detects `$GITHUB_COPILOT_TOKEN` or `$COPILOT_SESSION` is set (Copilot context)
and no explicit file path is given, display this guidance and stop:

```
GitHub Copilot CLI does not automatically save session transcripts.

To view a Copilot session:
1. While in Copilot CLI, export the session:
     /share markdown ./session.md
2. Then run:
     view transcript ./session.md

For sessions with full automatic archiving, use Claude Code instead:
  /amplihack:transcripts
```

## Full Workflow

When the user invokes this skill, follow this decision tree:

```
0. Detect tool context (uses launcher_detector.py env var conventions):
   - CLAUDE_CODE_SESSION / CLAUDE_SESSION_ID / ANTHROPIC_API_KEY set → claude-code
   - GITHUB_COPILOT_TOKEN / COPILOT_SESSION set → copilot (no auto-logs; guide to /share)
   - Neither set → default to claude-code (safe fallback)

1. Detect CCL (which claude-code-log / npx fallback)
   → If missing: show install instructions and STOP
   → Not needed for copilot-markdown files (skip CCL check for those)

2. If user provides an explicit file path:
   a. Detect its format (detect_log_format function above)
   b. copilot-markdown → display directly, skip CCL
   c. jsonl → pass to $CCL
   d. unknown → warn and display raw

3. Determine mode from user message:
   - mentions "current" or no session specified → Mode 1 (Current Session)
   - mentions a session ID or hash             → Mode 2 (Specific Session)
   - mentions "agent" or "background"          → Mode 3 (Agent Output)
   - mentions "all", "browse", "list"          → Mode 4 (All Sessions)
   - in Copilot context with no file → show /share guidance and STOP

4. Determine output format:
   - "as HTML" or "export HTML" → html
   - default                    → markdown

5. Execute the appropriate mode and display results.
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
| Copilot context, no file given | Show `/share` guidance and stop |
| Unknown file format | Warn user and display raw content |

## Implementation Notes

### Detecting Session IDs

Claude Code session IDs are UUID-like strings. If the user writes something like
"view session abc123" or "show log def456", treat the last word as the session ID
and search for matching JSONL filenames.

### JSONL Structure (Claude Code)

Claude Code session JSONL files contain one JSON object per line:

```json
{"type":"user","message":{"role":"user","content":[{"type":"text","text":"..."}]},"timestamp":"...","sessionId":"..."}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"..."}]},"timestamp":"..."}
```

`claude-code-log` handles parsing; this skill does not re-implement it.

### Copilot Markdown Structure

Copilot CLI `/share markdown` exports look like:

```markdown
# Copilot Session Export

**Date**: <timestamp>
**Session ID**: <id>

---

**User**: <user message>

**Copilot**: <assistant response>

---
```

Turns are separated by `---` horizontal rules. No external tool needed to read these.

### Philosophy Alignment

- **Thin wrapper**: Delegates to `claude-code-log` for JSONL; displays Markdown directly
- **Graceful degradation**: Clear error messages when tool is missing or Copilot has no logs
- **Single responsibility**: Only views/converts transcripts, never modifies them
- **No hidden state**: All file paths are shown to the user

## Limitations

- Requires `claude-code-log` (npm) or `npx` to convert Claude Code JSONL to HTML/Markdown
- Copilot CLI does not auto-save sessions; users must use `/share` to export first
- Cannot view transcripts from remote machines
- Date filtering relies on filesystem modification times, not session timestamps
- `--summary` flag availability depends on `claude-code-log` version

## Quick Reference

| User says | Tool | Mode | Command |
|-----------|------|------|---------|
| "view current transcript" | Claude Code | Current session | `$CCL <latest.jsonl> --format markdown` |
| "show session abc123" | Claude Code | Specific session | `$CCL <abc123.jsonl> --format markdown` |
| "view agent output" | Claude Code | Agent output | `cat .agent-step-*.log` or `$CCL *.jsonl` |
| "browse all sessions" | Claude Code | All sessions | list + summarize all `~/.claude/projects/**/*.jsonl` |
| "view transcript as HTML" | Claude Code | Any + HTML | `$CCL <file> --format html > /tmp/view.html` |
| "last 7 days" (with browse) | Claude Code | Date filter | `find ... -mtime -7` |
| "view copilot session ./s.md" | Copilot | Explicit file | `cat ./s.md` (already Markdown) |
| "show copilot transcript" | Copilot | No file | Show `/share` guidance and stop |
