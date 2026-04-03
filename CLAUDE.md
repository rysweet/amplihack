<!-- amplihack-version: 0.9.0 -->

# CLAUDE.md

<!-- AMPLIHACK_CONTEXT_START -->

## 🎯 USER PREFERENCES (MANDATORY - MUST FOLLOW)

# User Preferences

**MANDATORY**: These preferences MUST be followed by all agents. Priority #2
(only explicit user requirements override).

## Autonomy

Work autonomously. Follow workflows without asking permission between steps.
Only ask when truly blocked on critical missing information.

## Core Preferences

| Setting             | Value                      |
| ------------------- | -------------------------- |
| Verbosity           | balanced                   |
| Communication Style | (not set)                  |
| Update Frequency    | regular                    |
| Priority Type       | balanced                   |
| Collaboration Style | autonomous and independent |
| Auto Update         | ask                        |
| Neo4j Auto-Shutdown | ask                        |
| Preferred Languages | (not set)                  |
| Coding Standards    | (not set)                  |

## Workflow Configuration

**Selected**: DEFAULT_WORKFLOW
(`@~/.amplihack/.claude/workflows/DEFAULT_WORKFLOW.md`) **Consensus Depth**:
balanced

Use CONSENSUS_WORKFLOW for: ambiguous requirements, architectural changes,
critical/security code, public APIs.

## Behavioral Rules

- **No sycophancy**: Be direct, challenge wrong ideas, point out flaws. Never
  use "Great idea!", "Excellent point!", etc. See
  `@~/.amplihack/.claude/context/TRUST.md`.
- **Quality over speed**: Always prefer complete, high-quality work over fast
  delivery.

## Learned Patterns

<!-- User feedback and learned behaviors are added here by /amplihack:customize learn -->

## Managing Preferences

Use `/amplihack:customize` to view or modify (`set`, `show`, `reset`, `learn`).

<!-- AMPLIHACK_CONTEXT_END -->

This file provides guidance to Claude Code when working with your codebase. It
configures the amplihack agentic coding framework - a development tool that uses
specialized AI agents to accelerate software development through intelligent
automation and collaborative problem-solving.

## Important Files to Import

When starting a session, import these files for context:

[@~/.amplihack/.claude/context/PHILOSOPHY.md](~/.amplihack/.claude/context/PHILOSOPHY.md)
[@~/.amplihack/.claude/context/PROJECT.md](~/.amplihack/.claude/context/PROJECT.md)
[@~/.amplihack/.claude/context/PATTERNS.md](~/.amplihack/.claude/context/PATTERNS.md)
[@~/.amplihack/.claude/context/TRUST.md](~/.amplihack/.claude/context/TRUST.md)
[@~/.amplihack/.claude/context/USER_PREFERENCES.md](~/.amplihack/.claude/context/USER_PREFERENCES.md)
[@~/.amplihack/.claude/context/USER_REQUIREMENT_PRIORITY.md](~/.amplihack/.claude/context/USER_REQUIREMENT_PRIORITY.md)

## MANDATORY: Workflow Classification at Topic Boundaries

**CRITICAL**: You MUST classify at topic boundaries (new conversation topics)
and follow the corresponding workflow BEFORE taking action. No exceptions.

### When to Classify

Classify when the user:

- **Starts a new topic** (different domain/goal from current work)
- **First message of the session** (no prior context)
- **Explicitly changes direction** ("Now let's...", "Next I want...", "Different
  question...")
- **Switches request type** (question → implementation, investigation → coding)

### When NOT to Re-Classify

Do NOT re-classify when the user:

- **Asks follow-ups** ("Also...", "What about...", "And...")
- **Provides clarifications** ("I meant...", "To clarify...")
- **Requests related additions** ("Add logout too", "Also update the tests")
- **Checks status** ("How's it going?", "What's the progress?")

**Detection rule**: If the request is about the same goal/domain as the last 3
turns, it's the same topic. Continue in the current workflow.

### Quick Classification (3 seconds max)

```mermaid
flowchart TD
    MSG[New User Message] --> TB{Topic Boundary?}
    TB -->|"same goal/domain as last 3 turns"| CONTINUE[Continue current workflow]
    TB -->|"new topic / first message / direction change"| CLASS{Classify Task Type}

    CLASS --> QA{Edits code files?}
    QA -->|"no + Q&A keywords"| QA_ACT[Respond directly]
    QA -->|"no + ops keywords"| OPS_ACT[Respond directly]

    CLASS -->|"investigation keywords"| INV_ACT[Invoke /dev]
    CLASS -->|"development keywords"| DEV_ACT[Invoke /dev]
    QA -->|"yes - ANY code file edit"| DEV_ACT

    CLASS -->|"ambiguous"| DEV_ACT
```

| Task Type         | Action                      | When to Use                                            |
| ----------------- | --------------------------- | ------------------------------------------------------ |
| **Q&A**           | Respond directly            | Simple questions, single-turn answers, no code changes |
| **Operations**    | Respond directly            | Admin tasks, commands, disk cleanup, repo management   |
| **Investigation** | smart-orchestrator (`/dev`) | Understanding code, exploring systems, research        |
| **Development**   | smart-orchestrator (`/dev`) | Code changes, features, bugs, refactoring              |

### Code File Edit Rule (MANDATORY)

**If the task requires editing ANY code files (`.py`, `.yaml`, `.ts`, `.js`,
`.rs`, `.go`, `.json`, `.toml`, etc.), it MUST be classified as Development —
never Q&A or Operations, even if the change seems trivial.**

Examples of "trivial" changes that STILL require the Development workflow:

- Changing a default value in a config file
- Updating a version string
- Fixing a typo in a code comment
- Changing an import path

The only exception is editing `CLAUDE.md` itself or files in `.claude/context/`
— these are documentation/configuration, not code.

### Classification Pipeline (4 layers)

Classification happens through 4 layers, each reinforcing the others:

1. **`routing_prompt.txt`** — Injected every turn. Uses parallel signal
   evaluation (UNDERSTAND, IMPLEMENT, FILE_EDIT, SHELL_ONLY, QUESTION) with
   priority resolution. The authoritative per-turn classifier.
2. **`CLAUDE.md`** (this file) — Keywords and code-file-edit rule below.
3. **`workflow_classification_reminder.py`** — Topic boundary reinforcement.
4. **`dev-orchestrator/SKILL.md`** — Decomposition guidance when skill
   activates.

### Classification Keywords

- **Q&A**: "what is", "explain briefly", "quick question", "how do I run"
- **Operations**: "run command", "disk cleanup", "repo management", "git
  operations", "delete files", "cleanup", "organize"
- **Investigation**: "investigate", "understand", "analyze", "research",
  "explore", "how does X work"
- **Development**: "implement", "add", "fix", "create", "refactor", "update",
  "build"
- **Hybrid**: Both investigation AND implementation keywords present (e.g.,
  "investigate X then fix Y", "research how to do X then implement it")

### Required Announcement

State your classification before proceeding:

```
WORKFLOW: [Q&A | OPERATIONS | INVESTIGATION | DEVELOPMENT]
Reason: [Brief justification]
Action: [Respond directly | Respond directly | Invoke /dev | Invoke /dev]
```

### Workflow Execution

**Default Behavior**: Claude invokes dev-orchestrator for non-trivial
development and investigation tasks.

| Task Type         | Claude's Action   |
| ----------------- | ----------------- |
| **Q&A**           | Responds directly |
| **Operations**    | Responds directly |
| **Investigation** | Invokes /dev      |
| **Development**   | Invokes /dev      |

**Override**: Use explicit commands (/analyze, /improve) or request "without
orchestration" for direct implementation.

### Rules

1. **If keywords match multiple workflows**: Choose DEFAULT_WORKFLOW
2. **If uncertain**: Choose DEFAULT_WORKFLOW (never skip workflow)
3. **Q&A is for simple questions ONLY**: If answer needs exploration, use
   INVESTIGATION
4. **For Development tasks using /dev**: The smart-orchestrator recipe handles
   step ordering automatically via the recipe runner.

### Anti-Patterns (DO NOT)

- Answering without classifying first
- Starting implementation without reading DEFAULT_WORKFLOW.md
- Skipping Step 0 of DEFAULT_WORKFLOW
- Treating workflow as optional
- Classifying code file edits as Q&A to skip the workflow

## Working Philosophy

### Critical Operating Principles

- **Always think through a plan**: For any non-trivial task, think carefully,
  break it down into smaller tasks and use TodoWrite tool to manage a todo list.
- **ALWAYS classify into a workflow FIRST**: Every task gets classified BEFORE
  any action. Read the appropriate workflow file and follow all steps.
- **No workflow = No action**: If you haven't announced your workflow
  classification, you haven't started the task. Period.
- **ALWAYS use dev-orchestrator**: For non-trivial tasks, ALWAYS start with
  Skill(skill="dev-orchestrator") which classifies the task, decomposes into
  workstreams if needed, and executes via recipe runner.
- **Maximize agent usage**: Every workflow step should leverage specialized
  agents - delegate aggressively to agents in
  `~/.amplihack/.claude/agents/amplihack/*.md`
- **Operate Autonomously and Independently by default**: Determine the user's
  objective, then pursue it autonomously with the highest possible quality,
  without stopping, until it is achieved. Stopping to ask questions you can
  answer yourself wastes the user's time.
- **Ask for clarity only if really needed**: Use your best judgement; only stop
  to ask if really necessary or explicitly instructed to do so.
- **Check discoveries before problem-solving**: Retrieve recent discoveries from
  memory using `get_recent_discoveries()` from `amplihack.memory.discoveries`
- **Document learnings**: Store discoveries using `store_discovery()` from
  `amplihack.memory.discoveries`
- **Session Logs**: Log interactions in .claude/runtime/logs/<session_id>
- **Decision records**: Log decisions in
  .claude/runtime/logs/<session_id>/DECISIONS.md Format: What was decided | Why
  | Alternatives considered

### Extensibility Mechanisms and Composition Rules

Amplihack provides four extensibility mechanisms with clear invocation patterns:

| Mechanism    | Purpose                      | Invoked By                     | Invocation Method                         |
| ------------ | ---------------------------- | ------------------------------ | ----------------------------------------- |
| **Workflow** | Multi-step process blueprint | Commands, Skills, Agents       | `Read` workflow file, follow steps        |
| **Command**  | User-explicit entry point    | User, Commands, Skills, Agents | User types `/cmd` OR `SlashCommand` tool  |
| **Skill**    | Auto-discovered capability   | Claude auto-discovers          | Context triggers OR explicit `Skill` tool |
| **Subagent** | Specialized delegation       | Commands, Skills, Agents       | `Task` tool with `subagent_type`          |

**Key Invocation Patterns:**

- `SlashCommand(command="/dev Analyze architecture")` - programmatic command
  invocation
- `Skill(skill="mermaid-diagram-generator")` - explicit skill invocation
- `Task(subagent_type="architect", prompt="Design system...")` - subagent
  delegation
- `Read(file_path="~/.amplihack/.claude/workflow/DEFAULT_WORKFLOW.md")` -
  workflow reference

See `~/.amplihack/.claude/context/FRONTMATTER_STANDARDS.md` for complete
invocation metadata in frontmatter.

### CRITICAL: User Requirement Priority

**MANDATORY BEHAVIOR**: All agents must follow the priority hierarchy:

1. **EXPLICIT USER REQUIREMENTS** (HIGHEST PRIORITY - NEVER OVERRIDE)
2. **IMPLICIT USER PREFERENCES**
3. **PROJECT PHILOSOPHY**
4. **DEFAULT BEHAVIORS** (LOWEST PRIORITY)

**When user says "ALL files", "include everything", or provides specific
requirements in quotes, these CANNOT be optimized away by simplification
agents.** See USER_REQUIREMENT_PRIORITY.md for complete guidelines.

### Agent Delegation Strategy

**GOLDEN RULE**: You are an orchestrator, not an implementer. This means:

1. **Follow the workflow first** - Let DEFAULT_WORKFLOW.md determine the order
2. **Delegate within each step** - Use specialized agents to execute the work
3. **Coordinate, don't implement** - Your role is orchestration, not direct
   execution

ALWAYS delegate to specialized agents when possible. **DEFAULT TO PARALLEL
EXECUTION** by passing multiple tasks to the Task tool in a single call unless
dependencies require sequential order.

#### When to Use Agents (ALWAYS IF POSSIBLE)

**Immediate Delegation Triggers:**

- **System Design**: `architect.md` | **Implementation**: `builder.md`
- **Code Review**: `reviewer.md` | **Testing**: `tester.md`
- **API Design**: `api-designer.md` | **Performance**: `optimizer.md`
- **Security**: `security.md` | **Database**: `database.md`
- **Integration**: `integration.md` | **Cleanup**: `cleanup.md`
- **Pattern Recognition**: `patterns.md` | **Analysis**: `analyzer.md`
- **Ambiguity**: `ambiguity.md` | **Fix Workflows**: `fix-agent.md`

**Architect Variants**: `architect` (general), `amplifier-cli-architect` (CLI),
`philosophy-guardian` (compliance), `visualization-architect` (diagrams)

#### Development Workflow Agents

- **Pre-Commit Issues**: Use `pre-commit-diagnostic.md` — "Pre-commit failed",
  "Can't commit"
- **CI Issues**: Use `ci-diagnostic-workflow.md` — "CI failing", "Fix CI"
- **General Fixes**: Use `fix-agent.md` or `/fix [pattern] [scope]` — "Fix
  this", "Something's broken"

#### Creating Custom Agents

For repeated specialized tasks: create agent in
`~/.amplihack/.claude/agents/amplihack/specialized/`, define clear role and
boundaries, add to delegation triggers above.

### Parallel Execution

**PARALLEL BY DEFAULT**: Always execute operations in parallel unless
dependencies require sequential order. For detailed templates and decision
framework, read `~/.amplihack/.claude/context/PARALLEL_EXECUTION.md`.

**PARALLEL-READY Agents**: `analyzer`, `security`, `optimizer`, `patterns`,
`reviewer`, `architect`, `api-designer`, `database`, `tester`, `integration`,
`cleanup`, `ambiguity`

**SEQUENTIAL-REQUIRED Agents**: `architect` → `builder` → `reviewer`,
`pre-commit-diagnostic`, `ci-diagnostic-workflow`

## Project Structure

```
.claude/
├── context/          # Philosophy, patterns, project info
├── agents/           # Specialized AI agents
├── commands/         # Slash commands (/dev, /analyze, /improve)
├── scenarios/        # Production-ready user-facing tools
├── ai_working/       # Experimental tools under development
├── tools/            # Hooks and utilities
├── workflow/         # Default workflow definition
│   └── DEFAULT_WORKFLOW.md  # Customizable multi-step workflow
└── runtime/          # Logs, metrics, analysis

Specs/               # Module specifications
Makefile             # Easy access to scenario tools
```

## Key Commands

### /dev <task>

Default execution mode for all non-trivial tasks. The dev-orchestrator:

- Classifies task type (Q&A / Investigation / Development)
- Detects parallel workstreams automatically
- Executes via smart-orchestrator recipe (recipe runner)
- Reflects on goal achievement after completion

### /analyze <path>

Comprehensive code review for philosophy compliance

### /improve [target]

Self-improvement and learning capture

### /fix [pattern] [scope]

Intelligent fix dispatch. See
`~/.amplihack/.claude/context/COMMANDS_REFERENCE.md` for details.

### Fault Tolerance Commands

- `/amplihack:n-version <task>` — N-version programming for critical code (3-4x
  cost, 30-65% error reduction)
- `/amplihack:debate <question>` — Multi-agent debate for architectural
  decisions (2-3x cost)
- `/amplihack:cascade <task>` — Fallback cascade for resilient operations (95%+
  reliability)
- `/multitask` — Parallel independent tasks in subprocess isolation

See `~/.amplihack/.claude/context/COMMANDS_REFERENCE.md` for full usage.

### DDD, Investigation, Scenario Tools

For Document-Driven Development (`/amplihack:ddd:*`), Investigation Workflow,
Scenario Tools, and other utilities, see
`~/.amplihack/.claude/context/COMMANDS_REFERENCE.md`.

## Testing & Validation

After code changes:

1. Run tests if available
2. Check philosophy compliance
3. Verify module boundaries
4. Store learnings in memory via discoveries adapter

## Self-Improvement

- Track patterns in `~/.amplihack/.claude/context/PATTERNS.md`
- Store discoveries in memory for cross-session persistence
- Update agent definitions as needed
- Create new agents for repeated tasks

# tool vs skill

**PREFERRED PATTERN:** When user says "create a tool" → Build BOTH:

1. Executable tool in `~/.amplihack/.claude/scenarios/` (the program itself)
2. Skill in `~/.amplihack/.claude/skills/` that calls the tool (convenient
   interface)
