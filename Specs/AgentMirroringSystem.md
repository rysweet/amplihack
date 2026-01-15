# Agent Mirroring System - Design Specification

**Version**: 1.0.0
**Status**: Design Phase
**Created**: 2026-01-15

## Overview

A system to automatically convert amplihack's `.claude/agents/` to `.github/agents/` for GitHub Copilot CLI compatibility, enabling amplihack users to leverage the same agent ecosystem across both Claude Code and Copilot CLI platforms.

## Problem Statement

amplihack has 37+ specialized agents in `.claude/agents/` that work with Claude Code's pull model (automatic discovery). GitHub Copilot CLI uses a push model (explicit `@` references) and expects agents in `.github/agents/` with a slightly different frontmatter format. Users want to use the same agents in both environments without manual duplication and synchronization overhead.

## Core Philosophy Alignment

- **Ruthless Simplicity**: Single-pass conversion, no complex state machines
- **Zero-BS Implementation**: No stubs, every function works or doesn't exist
- **Regeneratable**: Can rebuild `.github/agents/` from `.claude/agents/` at any time
- **Fail-Fast**: Validate agent structure before conversion, report all errors upfront

## Architecture

### Module: Agent Converter (Brick)

**Purpose**: Convert amplihack agents from Claude Code format to Copilot CLI format

**Location**: `src/amplihack/adapters/copilot_agent_converter.py`

**Contract**:
- **Inputs**: Path to `.claude/agents/` directory
- **Outputs**: Converted agents in `.github/agents/` directory, conversion report
- **Side Effects**: Creates `.github/agents/` directory structure, writes markdown files

**Public API (Studs)**:
```python
def convert_agents(
    source_dir: Path = Path(".claude/agents"),
    target_dir: Path = Path(".github/agents"),
    force: bool = False
) -> ConversionReport:
    """Convert all agents from source to target directory."""

def convert_single_agent(
    agent_path: Path,
    target_dir: Path
) -> AgentConversion:
    """Convert single agent file."""

def validate_agent(agent_path: Path) -> ValidationResult:
    """Validate agent structure before conversion."""

@dataclass
class ConversionReport:
    """Results of agent conversion operation."""
    total: int
    succeeded: int
    failed: int
    conversions: List[AgentConversion]
    errors: List[ConversionError]

@dataclass
class AgentConversion:
    """Single agent conversion result."""
    source_path: Path
    target_path: Path
    agent_name: str
    status: Literal["success", "skipped", "failed"]
    reason: Optional[str] = None
```

### Module: Agent Parser (Brick)

**Purpose**: Parse amplihack agent markdown files with frontmatter

**Location**: `src/amplihack/adapters/agent_parser.py`

**Contract**:
- **Inputs**: Agent markdown file path
- **Outputs**: Parsed agent structure (frontmatter + body)
- **Side Effects**: None (pure parsing)

**Public API (Studs)**:
```python
@dataclass
class AgentDocument:
    """Parsed agent document."""
    frontmatter: Dict[str, Any]
    body: str
    source_path: Path

def parse_agent(agent_path: Path) -> AgentDocument:
    """Parse agent markdown file with YAML frontmatter."""

def has_frontmatter(content: str) -> bool:
    """Check if content has YAML frontmatter."""
```

### Module: Agent Adapter (Brick)

**Purpose**: Adapt Claude Code agent instructions for Copilot CLI

**Location**: `src/amplihack/adapters/agent_adapter.py`

**Contract**:
- **Inputs**: Parsed agent document
- **Outputs**: Copilot-compatible agent document
- **Side Effects**: None (pure transformation)

**Public API (Studs)**:
```python
def adapt_agent_for_copilot(agent: AgentDocument) -> AgentDocument:
    """Adapt Claude agent for Copilot CLI compatibility."""

def adapt_frontmatter(frontmatter: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Claude frontmatter to Copilot format."""

def adapt_instructions(body: str) -> str:
    """Adapt agent instructions for Copilot CLI patterns."""
```

### Module: Agent Registry (Brick)

**Purpose**: Maintain manifest of converted agents for discovery

**Location**: `src/amplihack/adapters/agent_registry.py`

**Contract**:
- **Inputs**: List of converted agents
- **Outputs**: JSON registry manifest
- **Side Effects**: Writes `.github/agents/registry.json`

**Public API (Studs)**:
```python
@dataclass
class AgentRegistryEntry:
    """Single agent in registry."""
    name: str
    description: str
    category: Literal["core", "specialized", "workflow"]
    source_path: str
    target_path: str
    triggers: List[str]
    version: str

def create_registry(
    conversions: List[AgentConversion]
) -> Dict[str, Any]:
    """Create agent registry from conversions."""

def write_registry(
    registry: Dict[str, Any],
    output_path: Path
) -> None:
    """Write registry to JSON file."""
```

## Conversion Rules

### Frontmatter Transformation

**Claude Code Format** (`.claude/agents/`):
```yaml
---
name: architect
version: 1.0.0
description: General architecture and design agent
role: "System architect and problem decomposition specialist"
model: inherit
---
```

**Copilot CLI Format** (`.github/agents/`):
```yaml
---
name: architect
description: General architecture and design agent. System architect and problem decomposition specialist.
triggers:
  - architecture
  - design
  - system design
  - module specification
version: 1.0.0
---
```

**Transformation Rules**:
1. **name**: Copy directly
2. **description**: Combine `description` + `role` fields
3. **triggers**: Extract from description/role or use defaults based on name
4. **version**: Copy directly
5. **Remove**: `model` field (Copilot doesn't support this)

### Instruction Adaptation

**Claude-Specific Patterns** → **Copilot Equivalents**:

| Claude Pattern | Copilot Pattern | Rationale |
|----------------|-----------------|-----------|
| `Task tool` | `subagent invocation` | Copilot doesn't have Task tool |
| `TodoWrite` | `state file updates in .claude/runtime/` | Different state management |
| `@.claude/context/FILE.md` | `Include @.claude/context/FILE.md` | Explicit reference needed |
| `Skill tool` | `MCP server call` | Different capability invocation |
| `/command-name` | Reference to `.github/agents/` | Commands don't exist in Copilot |

**Adaptation Process**:
1. **Search and replace** Claude-specific tool references
2. **Add Copilot invocation examples** using `@` notation
3. **Preserve agent logic** - only change invocation patterns
4. **Keep context references** - just make them explicit with `@`

### Agent Categorization

Agents are categorized into three types based on their source path:

1. **Core Agents** (`.claude/agents/amplihack/core/*.md`)
   - architect, builder, reviewer, tester, optimizer, api-designer
   - Essential agents used in most workflows

2. **Specialized Agents** (`.claude/agents/amplihack/specialized/*.md`)
   - fix-agent, security, database, integration, analyzer, etc.
   - Domain-specific agents for particular tasks

3. **Workflow Agents** (`.claude/agents/amplihack/workflows/*.md`)
   - amplihack-improvement-workflow, prompt-review-workflow
   - Orchestrators for multi-step processes

**Registry Structure**:
```json
{
  "version": "1.0.0",
  "generated": "2026-01-15T10:30:00Z",
  "source": ".claude/agents",
  "target": ".github/agents",
  "categories": {
    "core": [
      {
        "name": "architect",
        "description": "System architecture and design specialist",
        "source_path": ".claude/agents/amplihack/core/architect.md",
        "target_path": ".github/agents/core/architect.md",
        "triggers": ["architecture", "design", "system design"],
        "version": "1.0.0"
      }
    ],
    "specialized": [...],
    "workflow": [...]
  },
  "usage_examples": {
    "architect": [
      "copilot -p \"Include @.github/agents/core/architect.md -- Design a REST API\"",
      "copilot -p \"/agent architect -- Design authentication system\""
    ]
  }
}
```

## Conversion Process Flow

### Step-by-Step Execution

**Step 1: Prerequisite Validation**
- Check `.claude/agents/` exists
- Check write permissions for `.github/`
- Verify YAML parser available
- Fail fast if any prerequisite missing

**Step 2: Agent Discovery**
- Glob all `.md` files in `.claude/agents/**/*.md`
- Filter out README.md files
- Validate each agent has frontmatter
- Report count of agents found

**Step 3: Agent Validation**
- For each agent:
  - Parse frontmatter
  - Validate required fields (name, description)
  - Check frontmatter format (YAML)
  - Report validation errors
- Stop if any validation fails (fail-fast)

**Step 4: Agent Conversion**
- For each validated agent:
  - Parse agent document
  - Adapt frontmatter
  - Adapt instructions
  - Determine target path (preserve directory structure)
  - Write to `.github/agents/`
  - Track conversion result

**Step 5: Registry Generation**
- Collect all successful conversions
- Categorize by source path
- Generate usage examples per agent
- Write registry to `.github/agents/registry.json`

**Step 6: Report Generation**
- Count succeeded/failed/skipped
- List all errors
- Show target directory structure
- Provide next steps

### Error Handling Strategy

**Fail-Fast Validation**:
- Validate ALL agents before converting ANY
- Report all validation errors at once
- Don't proceed with partial conversion

**Resilient Conversion**:
- If single agent conversion fails, continue with others
- Track all errors in conversion report
- Never lose progress - conversion is idempotent

**User-Friendly Errors**:
```python
# BAD - Cryptic error
raise ValueError("Invalid YAML")

# GOOD - Actionable error
raise ValueError(
    f"Invalid YAML in agent frontmatter: {agent_path}\n"
    f"Error: {yaml_error}\n"
    f"Line {yaml_error.line}: {yaml_error.context}\n"
    f"Fix: Ensure frontmatter has valid YAML between '---' markers"
)
```

## When Conversion Runs

### Trigger Conditions

1. **Manual Command**: `amplihack sync-agents`
   - User explicitly requests sync
   - Force sync with `--force` flag
   - Dry-run with `--dry-run` flag

2. **Setup Command**: `amplihack setup-copilot`
   - Part of Copilot CLI integration setup
   - Creates `.github/` structure
   - Runs agent conversion automatically

3. **Session Start Hook** (optional):
   - Check if `.github/agents/` is outdated
   - Outdated = any `.claude/agents/` file modified after `.github/agents/registry.json`
   - Ask user to run sync command
   - Never auto-sync without permission

### Sync Detection

**Efficient Staleness Check**:
```python
def is_agents_synced() -> bool:
    """Check if .github/agents/ is in sync with .claude/agents/."""
    registry_path = Path(".github/agents/registry.json")

    if not registry_path.exists():
        return False  # Never synced

    registry_mtime = registry_path.stat().st_mtime

    # Check if any source agent is newer than registry
    for agent_path in Path(".claude/agents").rglob("*.md"):
        if agent_path.name == "README.md":
            continue
        if agent_path.stat().st_mtime > registry_mtime:
            return False  # Source newer than target

    return True  # In sync
```

## Implementation Plan

### Module Dependencies

```
agent_parser.py (no dependencies)
    ↓
agent_adapter.py (depends on agent_parser)
    ↓
agent_converter.py (depends on adapter + parser)
    ↓
agent_registry.py (depends on converter)
```

**Build Order**: parser → adapter → converter → registry

### File Structure

```
src/amplihack/adapters/
├── __init__.py                 # Public API exports
├── copilot_agent_converter.py # Main conversion logic
├── agent_parser.py             # Markdown + frontmatter parsing
├── agent_adapter.py            # Claude → Copilot transformation
├── agent_registry.py           # Registry generation
├── README.md                   # Module documentation
└── tests/
    ├── test_converter.py       # Conversion tests
    ├── test_parser.py          # Parsing tests
    ├── test_adapter.py         # Adaptation tests
    ├── test_registry.py        # Registry tests
    └── fixtures/
        ├── claude_agents/      # Sample Claude agents
        └── expected_copilot/   # Expected Copilot output
```

### CLI Command Integration

**Location**: `src/amplihack/cli/commands/sync_agents.py`

```python
@click.command()
@click.option('--dry-run', is_flag=True, help='Show what would be converted')
@click.option('--force', is_flag=True, help='Overwrite existing agents')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed output')
def sync_agents(dry_run: bool, force: bool, verbose: bool):
    """Sync .claude/agents/ to .github/agents/ for Copilot CLI."""

    # Step 1: Check prerequisites
    checker = PrerequisiteChecker()
    if not checker.check_agents_conversion_ready():
        return 1

    # Step 2: Convert agents
    report = convert_agents(
        source_dir=Path(".claude/agents"),
        target_dir=Path(".github/agents"),
        force=force
    )

    # Step 3: Display report
    if dry_run:
        print_dry_run_report(report)
    else:
        print_conversion_report(report)

    return 0 if report.failed == 0 else 1
```

### Testing Strategy (TDD Pyramid)

**Unit Tests (60%)**:
- `test_parse_agent_with_frontmatter()`
- `test_parse_agent_without_frontmatter()`
- `test_adapt_frontmatter_core_fields()`
- `test_adapt_frontmatter_triggers()`
- `test_adapt_instructions_task_tool()`
- `test_adapt_instructions_todowrite()`
- `test_categorize_agent_by_path()`

**Integration Tests (30%)**:
- `test_convert_single_agent_end_to_end()`
- `test_convert_all_agents_with_errors()`
- `test_registry_generation_complete()`
- `test_sync_detection_staleness()`

**E2E Tests (10%)**:
- `test_amplihack_sync_agents_command()`
- `test_amplihack_setup_copilot_integration()`
- `test_copilot_cli_discovers_converted_agents()` (requires Copilot CLI installed)

## Security Considerations

**File Operations**:
- Validate all file paths before writing
- Use Path.resolve() to prevent directory traversal
- Check write permissions before starting conversion
- Never overwrite without explicit `--force` flag

**Content Sanitization**:
- YAML parsing with safe_load (no code execution)
- Validate agent names (alphanumeric + hyphen only)
- Prevent path injection in target directory

**Error Disclosure**:
- Never expose full file system paths in public errors
- Sanitize error messages for external display
- Log full details securely for debugging

## Performance Characteristics

**Expected Performance**:
- Parse agent: < 10ms per file
- Adapt agent: < 5ms per file
- Write agent: < 20ms per file
- Total for 37 agents: < 1.5 seconds

**Optimization Strategies**:
- Parallel conversion (multiprocessing) - optional for > 100 agents
- Caching of parsed agents (in-memory)
- Skip unchanged agents (compare mtimes)

**Memory Usage**:
- < 10MB for 37 agents
- Lazy loading of agent content
- No global state retention

## Failure Modes and Recovery

### Failure Scenarios

**1. Source Directory Missing**
```
Error: Source directory not found: .claude/agents/
Fix: Ensure you're in an amplihack project directory
     Run 'amplihack init' to create project structure
```

**2. Target Directory Permission Denied**
```
Error: Cannot write to .github/agents/
Fix: Check directory permissions: chmod +w .github/
     Or run with sudo (not recommended)
```

**3. Invalid YAML Frontmatter**
```
Error: Invalid YAML in .claude/agents/core/architect.md
Line 3: mapping values are not allowed here
Fix: Ensure frontmatter has valid YAML between '---' markers
     Common issue: unquoted colons in description
```

**4. Conversion Interrupted**
```
Error: Conversion interrupted (SIGINT)
Status: 15/37 agents converted
Fix: Re-run 'amplihack sync-agents' to complete
      Previous conversions are preserved (idempotent)
```

### Recovery Strategy

**Idempotent Operations**:
- Conversion is idempotent - safe to re-run
- Existing files overwritten only with `--force`
- Registry regenerated on every run

**Partial Completion**:
- Track conversions in real-time
- Report partial progress on failure
- Allow continuation without reprocessing succeeded agents

**Rollback** (if needed):
```bash
# Rollback is simply deleting target directory
rm -rf .github/agents/
# Re-run conversion when ready
amplihack sync-agents
```

## Documentation Plan

### User Documentation

**Location**: `docs/github-copilot-agent-mirroring.md`

**Contents**:
1. Overview - What is agent mirroring
2. When to use - Copilot CLI integration
3. How it works - Conversion process
4. Commands - sync-agents, setup-copilot
5. Troubleshooting - Common errors
6. FAQ - Frequently asked questions

### Developer Documentation

**Location**: `src/amplihack/adapters/README.md`

**Contents**:
1. Architecture - Module design
2. API Reference - Public functions
3. Extension Guide - Adding new adaptations
4. Testing - How to test conversions
5. Contributing - Guidelines for changes

## Success Criteria

**Functional Requirements**:
- ✅ Convert all 37 agents from `.claude/agents/` to `.github/agents/`
- ✅ Preserve agent semantics and instructions
- ✅ Generate registry with categories and usage examples
- ✅ Fail-fast validation before conversion
- ✅ Idempotent conversion (safe to re-run)

**Non-Functional Requirements**:
- ✅ Complete in < 2 seconds for 37 agents
- ✅ Clear error messages with actionable fixes
- ✅ No manual intervention required
- ✅ Works on all platforms (Linux, macOS, Windows)
- ✅ Test coverage > 80%

**User Experience**:
- ✅ Single command: `amplihack sync-agents`
- ✅ Dry-run mode: `amplihack sync-agents --dry-run`
- ✅ Progress indication during conversion
- ✅ Summary report with errors
- ✅ Staleness detection at session start

## Future Enhancements (Out of Scope)

**Phase 2** (not in this design):
- Two-way sync (`.github/` → `.claude/`)
- Watch mode (auto-sync on file change)
- Selective sync (specific agents only)
- Conflict resolution (both changed)

**Phase 3** (not in this design):
- MCP server for agent invocation
- Copilot CLI workflow orchestration
- State management adapters
- Hook conversion system

**Philosophy Note**: Start minimal, add complexity only when justified by real usage. These enhancements are hypothetical until users request them.

## Open Questions

**For User Feedback**:
1. Should sync run automatically at session start? (Privacy concern)
2. Should we support custom trigger generation? (Complexity vs control)
3. Should registry include agent performance metrics? (Useful but complex)

**For Implementation**:
1. Handle agents without frontmatter? (Skip or error?)
2. Preserve comments in frontmatter? (YAML library dependent)
3. Handle agents with duplicate names? (Error or suffix with number?)

## References

- **GitHub Copilot CLI Documentation**: [@.claude/skills/github-copilot-cli-expert/README.md](../.claude/skills/github-copilot-cli-expert/README.md)
- **Philosophy**: [@.claude/context/PHILOSOPHY.md](../.claude/context/PHILOSOPHY.md)
- **Patterns**: [@.claude/context/PATTERNS.md](../.claude/context/PATTERNS.md)
- **Agent Example**: [@.claude/agents/amplihack/core/architect.md](../.claude/agents/amplihack/core/architect.md)

---

**Design Status**: Ready for review and feedback
**Next Step**: Get user approval before implementation
**Implementation Estimate**: 1-2 days for core + tests + docs
