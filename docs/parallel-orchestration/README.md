# Parallel Task Orchestration Documentation

Complete documentation fer the Parallel Task Orchestrator - a system fer coordinatin' multiple Claude Code agents workin' in parallel on independent sub-tasks.

## Quick Links

- **[User Guide](USER_GUIDE.md)** - When and how to use parallel orchestration (start here!)
- **[Command Reference](.claude/commands/amplihack/parallel-orchestrate.md)** - Complete command documentation
- **[Skill Documentation](.claude/skills/parallel-task-orchestrator/SKILL.md)** - Technical skill details
- **[Technical Reference](TECHNICAL_REFERENCE.md)** - API contracts, protocols, schemas
- **[Examples](EXAMPLES.md)** - Real-world case studies and patterns

## What Is Parallel Task Orchestration?

Deploy multiple Claude Code agents simultaneously to work on independent sub-tasks from a master GitHub issue. Each agent operates in isolation, creates its own PR, and coordinates through simple file-based status updates.

**Validated at Scale**: 5 agents produced 4,000+ lines of code with 100% success rate (SimServ migration, Issue #1783)

## Quick Start

```bash
# Basic usage
/amplihack:parallel-orchestrate <issue-number>

# With options
/amplihack:parallel-orchestrate 1234 --max-workers 5 --timeout 1800
```

**Requirements**:
1. Master GitHub issue with numbered or checkmarked sub-tasks
2. Sub-tasks must be independent (different files/modules)
3. At least 3-5 sub-tasks (overhead not worth it for fewer)

## Documentation Structure

### For Users

**New to Parallel Orchestration?**
1. Read [User Guide](USER_GUIDE.md) - Comprehensive introduction
2. Review [Examples](EXAMPLES.md) - Learn from real cases
3. Try `/amplihack:parallel-orchestrate --dry-run` - Validate before running

**Regular Users?**
- [Command Reference](.claude/commands/amplihack/parallel-orchestrate.md) - Quick command lookup
- [Examples](EXAMPLES.md) - Pattern library for common scenarios

### For Developers

**Implementing or Extending?**
1. [Technical Reference](TECHNICAL_REFERENCE.md) - API specs, protocols
2. [Skill Documentation](.claude/skills/parallel-task-orchestrator/SKILL.md) - Architecture details
3. [Orchestration Infrastructure](../../../.claude/tools/amplihack/orchestration/README.md) - Core infrastructure

**Troubleshooting?**
- [User Guide - Troubleshooting Section](USER_GUIDE.md#troubleshooting-guide)
- [Command Reference - Troubleshooting](../../.claude/commands/amplihack/parallel-orchestrate.md#troubleshooting)

## Documentation Files

| File | Purpose | Audience |
|------|---------|----------|
| [USER_GUIDE.md](USER_GUIDE.md) | When/how to use parallel orchestration | Users |
| [parallel-orchestrate.md](../../.claude/commands/amplihack/parallel-orchestrate.md) | Complete command reference | Users |
| [SKILL.md](../../.claude/skills/parallel-task-orchestrator/SKILL.md) | Skill architecture and workflow | Users & Developers |
| [TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md) | API contracts, protocols, schemas | Developers |
| [EXAMPLES.md](EXAMPLES.md) | Real-world case studies | Users |
| [README.md](README.md) | This file - documentation index | Everyone |

## Core Concepts

### Independence

**Critical Requirement**: Sub-tasks MUST be independent
- Different files/modules (minimal overlap)
- No sequential dependencies (A doesn't require B's output)
- Can be tested independently
- Can be merged independently

### File-Based Coordination

**Ruthlessly Simple**: Agents coordinate through JSON status files
- No message queues
- No distributed consensus
- No complex synchronization
- Just files: `.claude/runtime/parallel/{issue}/agent-{id}.status.json`

### Partial Success

**Resilient Execution**: System continues despite individual failures
- Success threshold: >= 80% completion
- Failed tasks → Diagnostic follow-up issues
- Retry mechanism for recovery
- No single point of failure

### 9-Step Workflow

1. **Parse Master Issue** - Extract sub-tasks
2. **Validate Independence** - Check for conflicts
3. **Create Sub-Issues** - GitHub sub-issues per task
4. **Deploy Agents** - Spawn parallel Claude Code agents
5. **Monitor Progress** - Track via status files
6. **Handle Failures** - Resilient partial success
7. **Aggregate Results** - Collect PR numbers, metrics
8. **Create Summary** - Generate report
9. **Update Master Issue** - Post results comment

## When to Use

### ✅ Perfect Use Cases

- **Modular features**: E-commerce cart (data/API/UI/tests/docs modules)
- **Multi-service bugs**: 10 bugs across microservices
- **Directory refactoring**: TypeScript migration (one directory per agent)
- **API documentation**: Document independent endpoints
- **Plugin development**: Independent extension modules

### ❌ Poor Use Cases

- **Sequential dependencies**: A → B → C pipeline
- **Shared files**: All tasks modify same config file
- **Integration-heavy**: Features need tight coordination
- **< 3 tasks**: Orchestration overhead > time savings
- **Complex testing**: Requires full integration before split

## Performance Expectations

| Sub-Tasks | Sequential | Parallel | Speedup |
|-----------|------------|----------|---------|
| 3 | 45 min | 15 min | 3x |
| 5 | 75 min | 20 min | 3.75x |
| 10 | 150 min | 35 min | 4.3x |

*Assumes balanced complexity, 80%+ success rate*

## Architecture Summary

```
Master Issue
     ↓
Parse Sub-Tasks → Validate Independence
     ↓
Create Sub-Issues (GitHub)
     ↓
Deploy Agents (Parallel)
     ↓
Monitor via Status Files (.agent_status.json)
     ↓
Aggregate Results (PRs, metrics)
     ↓
Update Master Issue (Summary comment)
```

**Key Components**:
- **Issue Parser**: Extracts tasks from markdown
- **Independence Validator**: Checks for conflicts
- **Agent Deployer**: Spawns parallel Claude Code processes
- **Status Monitor**: File-based progress tracking
- **Result Aggregator**: Combines outputs, generates summary

## Integration with Amplihack

### With DEFAULT_WORKFLOW

Parallel orchestration happens WITHIN workflow steps:

```markdown
## Step 4: Implement Feature

**Option A**: Sequential (default)
**Option B**: Parallel orchestration (for complex features)

Use /amplihack:parallel-orchestrate if feature has 5+ independent sub-tasks
```

### With Document-Driven Development (DDD)

```bash
# Phase 1: Write docs
/amplihack:ddd:2-docs

# Phase 2: Parallel implementation
/amplihack:parallel-orchestrate <issue>
# Each agent implements against docs

# Phase 3: Cleanup
/amplihack:ddd:5-finish
```

### With Other Commands

```bash
# Pre-orchestration analysis
/amplihack:analyze src/ --check-dependencies

# Post-orchestration fixes
/fix import  # Fix import errors across agents
```

## Philosophy Alignment

### Ruthless Simplicity

- **File-based coordination**: No complex infrastructure
- **Direct subprocess spawning**: Leverages existing orchestration
- **Simple status protocol**: JSON files, not distributed systems
- **Trust in emergence**: Agents coordinate naturally through files

### Modular Design (Bricks & Studs)

**Bricks** (Self-contained modules):
- Issue Parser
- Agent Deployer
- Status Monitor
- Result Aggregator

**Studs** (Public contracts):
- `.agent_status.json` schema
- Sub-issue template format
- Agent prompt specification

### Zero-BS Implementation

- **No stubs**: Every function works
- **No mocks**: Real GitHub API, real agents
- **No dead code**: All paths tested
- **Real logging**: Complete traceability

## Getting Help

### Common Questions

**Q: How many agents can I run?**
A: Default 5, configurable via `--max-workers`. Limited by system resources and GitHub API rate limits.

**Q: What if an agent fails?**
A: System continues with others. Creates diagnostic issue for investigation. Retry mechanism available.

**Q: Can I retry failed tasks?**
A: Yes! Use `--retry` flag to retry previously failed tasks from same issue.

**Q: How do I know if my tasks are independent?**
A: Use `--dry-run` to validate. Checks file overlap, dependencies, resource availability.

**Q: What about merge conflicts?**
A: PRs created in parallel but should be reviewed and merged carefully. Independent tasks minimize conflicts.

### Support Resources

- **Documentation**: This folder (start with USER_GUIDE.md)
- **Examples**: EXAMPLES.md has 7 real-world case studies
- **Troubleshooting**: USER_GUIDE.md Troubleshooting section
- **Technical Details**: TECHNICAL_REFERENCE.md
- **Validation Study**: Issue #1783 (SimServ migration)

### Reporting Issues

Found a bug or have a suggestion?

1. Check existing documentation first
2. Review EXAMPLES.md for similar scenarios
3. Create GitHub issue with:
   - Master issue number
   - Command used
   - Expected vs actual behavior
   - Relevant logs from `.claude/runtime/logs/`

## Metrics & Validation

### Proven Performance (Issue #1783)

- **Sub-Tasks**: 5 independent modules
- **Agents Deployed**: 5
- **Success Rate**: 100% (5/5)
- **Total LOC**: 4,127 lines
- **Duration**: 31 minutes (vs ~150 min sequential)
- **Speedup**: 4.8x
- **PRs Created**: 5 (all merged successfully)

### Success Criteria

- **Success Rate**: >= 80% agents complete
- **Time Savings**: >= 3x speedup over sequential
- **Quality**: PRs mergeable without major rework
- **Reliability**: Resilient to partial failures

## Future Enhancements

**Not Yet Implemented** (Trust in Emergence):
- Dynamic load balancing between agents
- Intelligent retry with different strategies
- Cross-agent learning
- Automatic dependency detection from code analysis
- Cost optimization per task complexity

## Contributing

### Improving Documentation

Documentation follows [Eight Rules](../../.claude/skills/documentation-writing/reference.md):

1. All docs in `docs/` directory
2. Every doc linked from index
3. Plain language, ruthlessly simple
4. Real examples, tested code
5. One Diataxis type per file
6. Scannable headings
7. Relative links with context
8. Current, no temporal info

### Updating Examples

When adding examples to EXAMPLES.md:

- Use real issue numbers
- Include actual output (anonymize if needed)
- Show both successes and failures
- Document lessons learned
- Test all code snippets

---

**Ready to parallelize yer work?** Start with the [User Guide](USER_GUIDE.md) and set sail fer faster development! ⚓