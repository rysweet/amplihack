<!-- TOC -->

- [PM Architect - User Guide](#pm-architect---user-guide)
  - [Phase 1: Foundation](#phase-1-foundation)
  - [Quick Start](#quick-start)
  - [Core Concepts](#core-concepts)
    - [Project Structure](#project-structure)
    - [Backlog Items](#backlog-items)
    - [Workstreams](#workstreams)
  - [Commands](#commands)
    - [/pm:init - Initialize PM](#pminit---initialize-pm)
    - [/pm:add - Add Backlog Item](#pmadd---add-backlog-item)
    - [/pm:start - Start Workstream](#pmstart---start-workstream)
    - [/pm:status - View Status](#pmstatus---view-status)
  - [File Structure](#file-structure)
  - [Workflow](#workflow)
  - [Phase 1 Limitations](#phase-1-limitations)
  - [Philosophy](#philosophy)
  - [Troubleshooting](#troubleshooting)
  <!-- TOC -->

# PM Architect - User Guide

PM Architect is a file-based project management system for AI-assisted development. It manages backlog items, orchestrates AI agents through workstreams, and tracks project progress—all through simple slash commands and YAML files.

## Phase 1: Foundation

**Current Capabilities:**

- Single workstream management (one task at a time)
- File-based state (no database required)
- AI agent delegation via ClaudeProcess
- Simple CLI commands

**Coming in Future Phases:**

- Multiple concurrent workstreams
- Progress tracking and metrics
- Roadmap visualization
- Advanced reporting

## Quick Start

```bash
# 1. Initialize PM in your project
/pm:init

# 2. Add items to backlog
/pm:add "Implement authentication" --priority HIGH --estimated-hours 8
/pm:add "Write user documentation" --priority MEDIUM

# 3. Start working on an item
/pm:start BL-001 --agent builder

# 4. Check status
/pm:status              # Project overview
/pm:status ws-001       # Workstream details
```

## Core Concepts

### Project Structure

PM Architect creates a `.pm/` directory in your project root:

```
.pm/
├── config.yaml          # Project configuration
├── roadmap.md           # Project roadmap (editable)
├── context.yaml         # Project metadata
├── backlog/
│   └── items.yaml       # All backlog items
├── workstreams/
│   ├── ws-001.yaml      # Active/completed workstreams
│   └── ws-002.yaml
└── logs/
    └── pm-builder-001.log  # Agent execution logs
```

### Backlog Items

Backlog items represent work to be done. Each item has:

- **ID**: Auto-generated (BL-001, BL-002, ...)
- **Title**: Short description
- **Description**: Detailed requirements (optional)
- **Priority**: HIGH, MEDIUM, LOW
- **Estimated Hours**: Time estimate
- **Status**: READY, IN_PROGRESS, DONE, BLOCKED
- **Tags**: Categorization (optional)

### Workstreams

A workstream is an active work session where an AI agent works on a backlog item.

**Properties:**

- **ID**: Auto-generated (ws-001, ws-002, ...)
- **Backlog ID**: Source backlog item
- **Agent**: AI agent role (builder, reviewer, tester)
- **Status**: RUNNING, PAUSED, COMPLETED, FAILED
- **Process ID**: ClaudeProcess identifier
- **Progress Notes**: Activity log

**Phase 1 Limitation**: Only one active workstream at a time.

## Commands

### /pm:init - Initialize PM

Initialize PM Architect in the current project.

**Interactive prompts:**

- Project name
- Project type (cli-tool, web-service, library, other)
- Primary goals
- Quality bar (strict, balanced, relaxed)

**Creates:**

- `.pm/` directory structure
- Initial configuration
- Roadmap template

### /pm:add - Add Backlog Item

Add a new item to the backlog.

**Arguments:**

```bash
/pm:add "Item title" [options]

Options:
  --priority HIGH|MEDIUM|LOW    # Default: MEDIUM
  --description "details"       # Default: empty
  --estimated-hours N           # Default: 4
  --tags "tag1,tag2"           # Default: none
```

**Examples:**

```bash
/pm:add "Implement JWT auth" --priority HIGH --estimated-hours 8
/pm:add "Fix bug in parser" --priority MEDIUM --description "Handle edge case"
/pm:add "Update README" --priority LOW --tags "docs,cleanup"
```

### /pm:start - Start Workstream

Start a new workstream to work on a backlog item.

**Arguments:**

```bash
/pm:start <backlog-id> [options]

Options:
  --agent builder|reviewer|tester  # Default: builder
  --timeout SECONDS                # Optional timeout
```

**Agent Roles:**

- **builder**: Implements features, writes code
- **reviewer**: Reviews code for quality and philosophy compliance
- **tester**: Writes tests and verifies behavior

**Examples:**

```bash
/pm:start BL-001                      # Start with builder agent
/pm:start BL-002 --agent reviewer     # Start with reviewer agent
/pm:start BL-003 --agent tester       # Start with tester agent
```

**Process:**

1. Validates no active workstream exists (Phase 1 limitation)
2. Creates delegation package with context
3. Spawns ClaudeProcess with agent instructions
4. Updates workstream state as work progresses

### /pm:status - View Status

View project overview or workstream details.

**Project Overview:**

```bash
/pm:status
```

Shows:

- Project name and type
- Active workstreams (if any)
- Backlog summary (ready items)
- Project health indicator

**Workstream Details:**

```bash
/pm:status ws-001
```

Shows:

- Workstream title and status
- Elapsed time and progress estimate
- Progress notes
- Process ID and log location

## File Structure

### config.yaml

```yaml
version: "1.0"
project_name: "my-project"
project_type: "cli-tool"
primary_goals:
  - "Create fast, user-friendly CLI"
  - "Excellent documentation"
quality_bar: "balanced"
initialized_at: "2025-11-20T10:30:00Z"
```

### backlog/items.yaml

```yaml
items:
  - id: "BL-001"
    title: "Implement config parser"
    description: "Parse YAML/TOML config files"
    priority: "HIGH"
    estimated_hours: 4
    status: "READY"
    created_at: "2025-11-20T10:35:00Z"
    tags: ["core", "config"]
```

### workstreams/ws-001.yaml

```yaml
id: "ws-001"
backlog_id: "BL-001"
title: "Implement config parser"
status: "RUNNING"
agent: "builder"
started_at: "2025-11-20T10:40:00Z"
completed_at: null
process_id: "pm-builder-001"
elapsed_minutes: 30
progress_notes:
  - "Generated module spec"
  - "Implemented YAML parser"
```

## Workflow

**Typical workflow:**

1. **Plan**: Initialize PM and add items to backlog

   ```bash
   /pm:init
   /pm:add "Feature 1" --priority HIGH
   /pm:add "Feature 2" --priority MEDIUM
   /pm:add "Feature 3" --priority LOW
   ```

2. **Execute**: Start workstream for highest priority item

   ```bash
   /pm:start BL-001 --agent builder
   ```

3. **Monitor**: Check progress

   ```bash
   /pm:status ws-001
   ```

4. **Iterate**: After completion, start next item
   ```bash
   /pm:start BL-002 --agent builder
   ```

## Phase 1 Limitations

**Single Workstream Only:**

- Only one workstream can be active at a time
- Must complete or stop current workstream before starting another
- Simplifies state management and avoids concurrency issues

**No Workstream Pause/Resume:**

- Workstreams run to completion
- To stop: wait for agent to finish or manually terminate

**Basic Status Tracking:**

- Simple elapsed time tracking
- Rough progress estimates
- No detailed metrics or analytics

**These limitations will be addressed in future phases.**

## Philosophy

PM Architect follows the amplihack philosophy:

**Ruthless Simplicity:**

- File-based state (no database)
- Simple YAML files (human-readable, git-trackable)
- Direct commands (no complex workflows)

**Zero-BS Implementation:**

- Every function works (no stubs)
- Real ClaudeProcess integration
- Functional from day one

**Modular Design:**

- Clear module boundaries
- Self-contained components
- Regeneratable from specs

## Troubleshooting

**PM not initialized error:**

```bash
❌ PM not initialized. Run /pm:init first.
```

**Solution:** Run `/pm:init` to initialize PM in your project.

**Active workstream exists error:**

```bash
❌ Active workstream exists: ws-001 - Implement auth
```

**Solution:** Check workstream status with `/pm:status ws-001`. Wait for completion or manually stop it.

**Backlog item not found:**

```bash
❌ Backlog item BL-005 not found
```

**Solution:** Run `/pm:status` to see available backlog items. Verify the ID is correct.

**File permission errors:**

- Ensure you have write permissions in the project directory
- Check that `.pm/` directory is not locked or read-only

**Agent process errors:**

- Check log files in `.pm/logs/` for detailed error messages
- Verify ClaudeProcess is configured correctly
- Check for network issues if using remote Claude API

---

For more examples, see `EXAMPLES.md`.

For implementation details, see source code in `.claude/tools/amplihack/pm/`.
