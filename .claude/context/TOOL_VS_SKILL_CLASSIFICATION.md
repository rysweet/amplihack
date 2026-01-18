# Tool vs Skill Classification Guide

## CRITICAL: Understand the Difference

This guide prevents confusion between TOOLS (executable code) and SKILLS (Claude Code capabilities).

## Definitions

### TOOL = Executable Program

- **What it is**: A standalone program, script, or CLI application
- **How it runs**: `python tool.py`, `node tool.js`, or as installed command
- **Examples**:
  - `python linkedin_drafter.py --past-posts ./posts --output draft.md`
  - `email-cli compose --style professional --to user@example.com`
  - Any program with a `main()` function that users execute

### SKILL = Claude Code Capability

- **What it is**: Markdown documentation that teaches Claude how to do something
- **How it runs**: Loaded by Claude Code, user invokes conversationally
- **Examples**:
  - `.claude/skills/email-drafter/` - Helps Claude draft emails when asked
  - `.claude/skills/pdf/` - Enables Claude to work with PDFs
  - Activated via `/skill-name` or natural language requests

## Classification Rules

When user says:

- **"create a tool"** → Build EXECUTABLE code (Python/Node/etc program)
- **"create a CLI"** → Build EXECUTABLE code
- **"create a program"** → Build EXECUTABLE code
- **"create a script"** → Build EXECUTABLE code
- **"create a skill"** → Build DOCUMENTATION (Claude Code skill)

### The PREFERRED Pattern: Tool + Skill (Best of Both Worlds)

**Most of the time, build BOTH:**

1. **First**: Build the TOOL (executable program in `.claude/scenarios/`)
   - Reusable, testable, version-controlled code
   - Can be run standalone: `python linkedin_drafter.py --args`
   - Has tests, documentation, proper structure

2. **Then**: Build a SKILL that uses the tool (in `.claude/skills/`)
   - Skill calls the tool via Claude Code SDK
   - Provides convenient conversational interface
   - User can say "draft a LinkedIn post" and skill invokes tool

**Why This Is Best:**

- ✅ Tool is executable and testable (satisfies eval requirements)
- ✅ Skill provides convenient interface (satisfies user experience)
- ✅ Tool can be used standalone OR via skill
- ✅ Separation of concerns: Tool = functionality, Skill = interface

**Example:**

```
Scenarios/linkedin_drafter/cli.py  # The executable tool
.claude/skills/linkedin-drafter/   # Skill that calls the tool
```

### When Tool-Only Is Sufficient

Build just the tool when:

- One-off scripts or utilities
- Batch processing programs
- CI/CD integration points
- The user explicitly doesn't want a skill

### In eval-recipes Context

For benchmarks like eval-recipes:

- Build the TOOL first (executable is required for scoring)
- Skill creation is optional (not tested by evals)
- Default to tool-only in eval contexts

## Critical Warning

**DO NOT look at `.claude/skills/` for code examples when building tools!**

The skills directory contains:

- ❌ Markdown documentation (not code)
- ❌ Prompt engineering (not programs)
- ❌ Examples that will mislead you

Instead, look at:

- ✅ `.claude/scenarios/` - Production executable tools
- ✅ Standard Python/Node/etc patterns
- ✅ Project structure conventions

## In evals/Benchmarks

eval-recipes and similar benchmarking frameworks:

- Run Claude Code directly with: `claude -p "task"`
- Do NOT invoke `/ultrathink` or prompt-writer agent
- Classification must happen BEFORE agent sees skills directory
- **Default assumption**: "tool" = EXECUTABLE code

## Examples from Benchmarks

### LinkedIn Drafting Task

**Input**: "I need help creating a tool for drafting my LinkedIn posts"
**WRONG** (what happened): Created `.claude/skills/linkedin-post-drafter/` (markdown)
**RIGHT** (what should happen): Create `scenarios/linkedin_drafter/cli.py` (Python program)

### Email Drafting Task

**Input**: "Create me a CLI tool that will take bullet points and draft an email"
**WRONG**: Create `.claude/skills/email-drafter/` (skill already exists)
**RIGHT**: Create `scenarios/email_drafter/main.py` with CLI argparse

## Integration Note

This classification should be applied:

1. **In project documentation** - So all Claude Code sessions see it
2. **In builder.md** - So the builder agent knows the difference
3. **In this file** - As explicit reference documentation

The goal: Prevent Claude from creating skills when users want executable tools.
