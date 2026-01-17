# Command Selection Guide

**User Reference**: This guide helps you choose the right slash command for your workflow.

## Quick Command Finder

**Decision Tree**:

```
What do you need to do?
├─ DEVELOPMENT WORKFLOWS
│  ├─ Quick fix (< 5 min)? → /fix
│  ├─ Build new module? → /modular-build
│  ├─ Full feature development? → /ultrathink
│  └─ Autonomous external loop? → /auto
│     └─ Note: /auto runs in subprocess, /ultrathink in current session
│
├─ DECISION MAKING
│  ├─ Need discussion/debate? → /debate
│  │  └─ Interactive facilitated discussion converging to consensus
│  └─ Need expert voting? → /expert-panel
│     └─ Independent reviews with weighted voting
│
├─ FAULT TOLERANCE
│  ├─ Need reliability/fallbacks? → /cascade
│  ├─ Need critical correctness? → /n-version
│  └─ Need decision consensus? → /debate
│
└─ INVESTIGATION & IMPROVEMENT
   ├─ Understand codebase? → /investigate
   ├─ Session reflection? → /reflect
   └─ Philosophy compliance? → /analyze
```

## Quick Reference Table

| Task Type            | Command                  | When to Use                                    |
| -------------------- | ------------------------ | ---------------------------------------------- |
| Quick fixes          | `/fix [pattern] [scope]` | Error blocking you, need rapid resolution      |
| Module building      | `/modular-build`         | Creating new self-contained module (brick)     |
| Feature development  | `/ultrathink`            | Multi-step feature with workflow orchestration |
| Autonomous work      | `/auto`                  | Long-running task in external subprocess       |
| Debate decision      | `/debate <question>`     | Need facilitated discussion to consensus       |
| Expert consensus     | `/expert-panel <topic>`  | Need independent expert votes                  |
| Fallback resilience  | `/cascade <task>`        | Need graceful degradation (API calls, etc.)    |
| Critical correctness | `/n-version <task>`      | Security code, core algorithms (3-4x cost)     |
| Code understanding   | `/investigate <path>`    | Deep dive into codebase structure              |
| Session analysis     | `/reflect`               | Review session and create improvement issues   |
| Philosophy check     | `/analyze <path>`        | Validate code against amplihack principles     |
| Multi-model AI       | `amplihack amplifier`    | Use Amplifier with Claude, GPT-4, etc.         |

## Key Distinctions

### `/ultrathink` vs `/auto`

- **`/ultrathink`**: Runs in current Claude Code session (internal orchestration)
- **`/auto`**: Spawns external subprocess with autonomous loop
- **Use `/ultrathink` for**: Interactive development, want to see progress
- **Use `/auto` for**: Hands-off background work, long-running tasks

### `/debate` vs `/expert-panel`

- **`/debate`**: Interactive discussion with back-and-forth, facilitated convergence
- **`/expert-panel`**: Independent reviews without cross-talk, then voting
- **Use `/debate` for**: Exploring trade-offs, need discussion
- **Use `/expert-panel` for**: Clear decision with expert consensus

### `/ultrathink` vs `/modular-build`

- **`/ultrathink`**: General-purpose development workflow
- **`/modular-build`**: Specialized for module creation (progressive pipeline)
- **Use `/ultrathink` for**: Features, bug fixes, general development
- **Use `/modular-build` for**: Specifically creating new bricks (self-contained modules)

## Command Integration Examples

### Quick Workflow: Fix → Build → Review

```bash
/fix import                    # Fix import errors
/modular-build auth-module     # Build new module
/analyze .                     # Check philosophy compliance
```

### Complex Decision Workflow: Debate → N-Version → Reflect

```bash
/debate "Should we use REST or GraphQL?"
/n-version "Implement chosen API approach"
/reflect                       # Analyze decisions made
```

### Investigation Workflow: Investigate → Ultrathink

```bash
/investigate ./src/core        # Understand existing code
/ultrathink "Add new feature to core"  # Build on understanding
```

## All Available Commands

### Development Commands

- `/fix` - Quick error resolution with pattern detection
- `/modular-build` - Create self-contained modules (bricks)
- `/ultrathink` - Full development workflow
- `/auto` - Autonomous external subprocess

### Decision Making Commands

- `/debate` - Facilitated multi-agent discussion
- `/expert-panel` - Independent expert review with voting

### Fault Tolerance Commands

- `/cascade` - Graceful degradation with fallbacks
- `/n-version` - N-version programming for critical code

### Investigation Commands

- `/investigate` - Deep codebase exploration
- `/analyze` - Philosophy compliance check
- `/reflect` - Session analysis and improvement

### Document-Driven Development (DDD)

- `/ddd:0-help` - DDD workflow guide
- `/ddd:prime` - Load DDD context
- `/ddd:1-plan` - Planning phase
- `/ddd:2-docs` - Documentation retcon
- `/ddd:3-code-plan` - Code planning
- `/ddd:4-code` - Implementation
- `/ddd:5-finish` - Cleanup and finalize
- `/ddd:status` - Check DDD progress

### Utility Commands

- `/customize` - Manage user preferences
- `/skill-builder` - Create new Claude Code skills
- `/knowledge-builder` - Build knowledge bases
- `/socratic` - Generate Socratic questions
- `/transcripts` - Manage conversation transcripts
- `/lock` / `/unlock` - Continuous work mode
- `/install` / `/uninstall` - System setup

## When in Doubt

Start with `/ultrathink` - it will orchestrate the appropriate workflow for most tasks.

For quick questions or simple tasks, just ask directly without commands.

---

**See Also**:

- `.claude/context/AGENT_SELECTION_GUIDE.md` - Which agent to use (AI context)
- `CLAUDE.md` - Complete project documentation
- `.claude/commands/` - Individual command documentation
