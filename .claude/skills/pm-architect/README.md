# PM Architect Skill

**Expert project manager for complex software projects.**

## Overview

PM Architect is a Claude Code skill that enables Claude to act as an expert project manager, coordinating multiple software projects through roadmap management, backlog curation, workstream coordination, and delegation to coding agents.

## When This Skill Activates

PM Architect automatically activates when you:

- Mention managing projects, coordinating work, or tracking tasks
- Ask about priorities or what to work on next
- Want to delegate work to coding agents
- Need help organizing multiple projects or features
- Say "I'm losing track of my projects" or similar

## Key Capabilities

### 1. Roadmap Management

Track project goals, milestones, and strategic direction. Ensure work aligns with objectives.

### 2. Backlog Curation

Maintain prioritized backlog with multi-criteria scoring (40% priority, 30% blocking impact, 20% ease, 10% goal alignment).

### 3. Work Delegation

Create rich delegation packages with comprehensive context for coding agents (builder, reviewer, tester).

### 4. Workstream Coordination

Manage up to 5 concurrent workstreams per project, detect dependencies, identify conflicts, monitor for stalls.

### 5. Autonomous Operation (Phase 4)

Operate independently with periodic decision cycles, transparent logging, and appropriate oversight.

## Quick Start

```
User: Help me manage my-cli-tool project

PM: I'll initialize PM Architect for my-cli-tool. A few questions:
1. What type of project? (cli-tool, web-service, library, other)
2. What are your 3-5 primary goals?
3. Quality bar? (strict/balanced/relaxed)

[After initialization, you can:]
- "Add backlog item: implement config parser"
- "What should I work on next?"
- "Start work on BL-001"
- "What's the status?"
- "Enable autonomous mode"
```

## File Structure

```
.claude/skills/pm-architect/
├── SKILL.md              # Main skill file (525 lines, ~2.5K tokens)
├── REFERENCE.md          # Detailed algorithms (809 lines, ~4K tokens)
├── EXAMPLES.md           # Usage scenarios (938 lines, ~4.5K tokens)
├── README.md             # This file
└── scripts/
    ├── README.md
    ├── analyze_backlog.py       # Multi-criteria scoring
    ├── create_delegation.py     # Rich delegation packages
    ├── coordinate.py            # Workstream coordination
    └── manage_state.py          # State file operations
```

## State Management

PM Architect maintains a `.pm/` directory for each project:

```
.pm/
├── config.yaml           # Project configuration
├── roadmap.md           # Goals and milestones
├── backlog/
│   └── items.yaml       # Prioritized work items
├── workstreams/
│   ├── ws-001.yaml      # Active workstream tracking
│   └── ...
├── logs/                # Decision logs and history
└── context.yaml         # Project metadata
```

## Token Efficiency

**Pre-load cost**: ~50 tokens (YAML frontmatter only)

**On activation**:

- SKILL.md loads: ~2,500 tokens (core guidance)
- REFERENCE.md loads as needed: ~4,000 tokens (algorithms)
- EXAMPLES.md loads as needed: ~4,500 tokens (scenarios)
- Scripts execute externally: 0 tokens until output

**Progressive disclosure**: Start with SKILL.md, load additional files only when needed.

## Philosophy Alignment

### Ruthless Simplicity

- File-based state (YAML, no database)
- Standard library + PyYAML only
- Simple scoring formulas
- Direct file operations

### Single Responsibility

- PM focuses on coordination, not implementation
- Delegates work to specialized agents
- Maintains state, doesn't execute code

### Zero-BS Implementation

- All scripts work completely (no stubs)
- All state files are valid YAML
- All recommendations have clear rationale

### Trust in Emergence

- User decides when to delegate
- User approves autonomous actions
- PM suggests, user directs

## Multi-Criteria Scoring

PM Architect uses weighted scoring to prioritize work:

```
Score = (Priority × 40%) + (Blocking × 30%) + (Ease × 20%) + (Goals × 10%)

Where:
- Priority: HIGH=1.0, MEDIUM=0.6, LOW=0.3
- Blocking: Normalized count of items unblocked
- Ease: Simple=1.0, Medium=0.6, Complex=0.3
- Goals: Alignment with project primary goals
```

See REFERENCE.md for detailed algorithms.

## Integration with ClaudeProcess

When orchestration is available, PM Architect integrates with ClaudeProcess:

```python
from orchestration.claude_process import ClaudeProcess

# PM creates delegation package
package = create_delegation_package(backlog_id="BL-001")

# Start process with agent
process = ClaudeProcess(
    agent_path=".claude/agents/amplihack/core/builder.md",
    context=package,
    project_root=Path.cwd()
)
result = process.execute()
```

## Common Usage Patterns

### Morning Check-In

```
User: How are my projects?

PM: [Checks all .pm/ directories]
- my-cli-tool: 2 workstreams active, on track
- api-gateway: 1 stalled (needs attention)
- mobile-app: CI failing (CRITICAL)

Priority: Fix mobile-app CI immediately
```

### Adaptive Prioritization

```
User: Deadline moved up for auth feature!

PM: [Reprioritizes]
- Paused lower-priority work
- Elevated auth to HIGH priority
- Started auth workstream
- Timeline: Meets deadline
```

### Cross-Project Coordination

```
User: Work on both projects today

PM: [Detects shared patterns]
- Both need authentication
- Implement in api-gateway first
- Reuse pattern in mobile-app
- Saves 2 hours
```

## Success Criteria

PM Architect successfully helps users:

- ✓ Manage multiple projects simultaneously
- ✓ Prioritize work based on clear criteria
- ✓ Delegate effectively to coding agents
- ✓ Track progress across workstreams
- ✓ Coordinate dependencies and conflicts
- ✓ Operate with appropriate autonomy
- ✓ Maintain alignment with goals

## Tips for Effective Usage

1. **Initialize early**: Set up PM before backlog grows
2. **Update regularly**: Keep backlog and priorities current
3. **Trust the scoring**: Multi-criteria formula is well-calibrated
4. **Delegate liberally**: Let PM coordinate, agents execute
5. **Review outcomes**: PM learns from completed workstreams
6. **Grant autonomy gradually**: Start supervised, increase trust

## Resources

- **SKILL.md**: Core PM guidance and workflows
- **REFERENCE.md**: Detailed algorithms and patterns
- **EXAMPLES.md**: Complete usage scenarios with dialogue
- **scripts/**: Utility scripts for analysis and coordination

## Version

**Version**: 1.0
**Created**: 2025-11-21
**Architecture**: Skill (not slash commands)

## License

See project LICENSE for terms.

---

**Remember**: PM Architect makes Claude BE the PM, not use a PM tool. Claude thinks strategically, acts pragmatically, and communicates clearly as your project manager.
