# Claude Agent SDK Skill

## Overview

Comprehensive skill providing Claude with deep knowledge of the Claude Agent SDK for building production-ready autonomous agents.

**Version**: 1.0.0
**Created**: 2025-11-15
**Status**: Active

## What This Skill Provides

This skill enables Claude to:

- Guide users in building agents with the Claude Agent SDK
- Design tool architectures and implement custom tools
- Implement hooks for observability and validation
- Use MCP (Model Context Protocol) servers
- Apply production patterns for agent design
- Debug and optimize agent implementations
- Integrate SDK with existing systems like Amplihack

## File Structure

```
agent-sdk/
├── SKILL.md                    # Main entry point (~2,100 tokens)
│   └── Core concepts, quick start, navigation guide
├── reference.md                # Complete API reference (~3,900 tokens)
│   └── Architecture, tools, hooks, permissions, MCP, skills
├── examples.md                 # Working code examples (~3,200 tokens)
│   └── Basic agents, tool implementations, hooks, advanced patterns
├── patterns.md                 # Production patterns (~2,950 tokens)
│   └── Agent loop patterns, context management, security, anti-patterns
├── drift-detection.md          # Update mechanism (~2,000 tokens)
│   └── Drift detection strategy, update workflow, validation
├── .metadata/
│   └── versions.json           # Version tracking and content hashes
└── scripts/
    └── check_drift.py          # Drift detection script
```

**Total Token Budget**: ~14,150 tokens (within Claude's context limits)

## Activation

**Auto-activates** when user message contains:

- agent sdk
- claude agent
- sdk tools
- agent hooks
- mcp server
- subagent
- agent loop
- agent permissions
- agent skill

**Manual activation**:

```python
# In Claude Code conversations
@.claude/skills/agent-sdk/SKILL.md
```

## Usage Patterns

### Quick Reference

Start with `SKILL.md` for:

- Overview and when to use Agent SDK
- Quick start guide
- Core concepts summary
- Common patterns
- Navigation to other files

### Deep Dive

Refer to supporting files for:

- `reference.md` - Complete API documentation
- `examples.md` - Working code examples
- `patterns.md` - Production best practices
- `drift-detection.md` - How to keep skill current

### Progressive Disclosure

The skill follows a progressive disclosure pattern:

1. SKILL.md provides complete working knowledge
2. Supporting files available when deeper knowledge needed
3. Claude references appropriate file based on user needs

## Source Documentation

This skill synthesizes information from 5 authoritative sources:

1. **Claude Agent SDK Overview** (docs.claude.com)
   - Official architecture and setup documentation
   - Core concepts and API reference

2. **Engineering Blog** (anthropic.com/engineering)
   - Agent loop patterns and design philosophy
   - Production insights from Anthropic team

3. **Skills Documentation** (docs.claude.com)
   - Skills system implementation guide
   - YAML format and activation logic

4. **Tutorial Repository** (github.com/kenneth-liao)
   - Practical examples and learning path
   - Real-world implementation patterns

5. **Medium Article** (Production Integration)
   - Integration strategies and common pitfalls
   - Advanced patterns and best practices

## Drift Detection

### What is Drift?

Drift occurs when source documentation changes but skill content remains stale, potentially causing Claude to provide outdated guidance.

### Detection Mechanism

The skill includes automated drift detection:

- Content hashing (SHA-256) of all source URLs
- Version tracking in `.metadata/versions.json`
- Automated checking via `scripts/check_drift.py`

### Running Drift Detection

```bash
cd .claude/skills/agent-sdk

# Check for drift
python scripts/check_drift.py

# Check and update metadata
python scripts/check_drift.py --update

# JSON output for automation
python scripts/check_drift.py --json
```

### Recommended Schedule

- **Weekly**: Automated drift checks
- **Monthly**: Manual review even if no drift
- **On-demand**: After SDK version releases
- **User-reported**: When inconsistencies found

## Token Budget Compliance

| File               | Words      | Est. Tokens | Budget     | Status |
| ------------------ | ---------- | ----------- | ---------- | ------ |
| SKILL.md           | 1,616      | 2,100       | 4,500      | ✓ 47%  |
| reference.md       | 3,006      | 3,900       | 6,000      | ✓ 65%  |
| examples.md        | 2,452      | 3,200       | 4,000      | ✓ 80%  |
| patterns.md        | 2,268      | 2,950       | 3,500      | ✓ 84%  |
| drift-detection.md | 1,541      | 2,000       | 2,000      | ✓ 100% |
| **Total**          | **10,883** | **14,150**  | **20,000** | ✓ 71%  |

Token calculation: words × 1.3 (conservative estimate)

## Quality Assurance

### Validation Checklist

- [x] All required sections present in each file
- [x] Token budgets not exceeded
- [x] Internal markdown links functional
- [x] Code examples syntactically valid (Python)
- [x] YAML frontmatter valid
- [x] All 5 sources incorporated
- [x] Drift detection mechanism implemented
- [x] No contradictions between files

### Content Coverage

**SKILL.md**:

- ✓ Overview and when to use
- ✓ Quick start (Python & TypeScript)
- ✓ Core concepts (agent loop, context, tools, permissions, hooks)
- ✓ Common patterns
- ✓ Navigation guide
- ✓ Integration with Amplihack

**reference.md**:

- ✓ Architecture (agent loop internals)
- ✓ Setup & configuration (Python & TypeScript)
- ✓ Tools system (built-in catalog, custom creation)
- ✓ Permissions & security
- ✓ Hooks reference (all 4 types)
- ✓ Skills system
- ✓ MCP integration

**examples.md**:

- ✓ Basic agent examples
- ✓ Tool implementations (file ops, code exec, web search, DB, MCP)
- ✓ Hook implementations (logging, validation, rate limiting, cost tracking)
- ✓ Advanced patterns (subagents, search, verification, error recovery)
- ✓ Integration examples

**patterns.md**:

- ✓ Agent loop patterns (Gather, Act, Verify, Iterate)
- ✓ Context management (subagents, compaction, state, memory)
- ✓ Tool design (SRP, idempotency, error handling, composition)
- ✓ Security patterns (validation, permissions, sensitive data, audit)
- ✓ Performance (token budget, parallel, caching)
- ✓ Anti-patterns (god agent, context pollution, brittleness, over-engineering)

**drift-detection.md**:

- ✓ Drift detection strategy
- ✓ Detection implementation
- ✓ Update workflow (6 steps)
- ✓ Self-validation mechanisms

## Post-Deployment Setup

**IMPORTANT**: After deploying this skill, complete these setup steps:

### 1. Initialize Content Hashes (Required)

The skill ships with placeholder content hashes. Generate real hashes:

```bash
cd .claude/skills/agent-sdk
python scripts/check_drift.py --update
```

This updates `.metadata/versions.json` with actual SHA-256 hashes from source URLs.

### 2. Verify Dependencies

The drift detection script requires the `requests` library:

```bash
pip install requests
```

Or handle gracefully - the script provides clear error messages if missing.

### 3. Test Skill Activation

Verify the skill activates correctly:

```bash
# Query Claude with SDK keywords
echo "How do I use agent sdk tools?" | claude
```

The skill should auto-load and provide guidance from SKILL.md.

### 4. Weekly Drift Detection (Optional)

Set up automated drift detection in CI/CD:

```yaml
# .github/workflows/drift-check.yml
name: Agent SDK Skill Drift Check

on:
  schedule:
    - cron: "0 0 * * 0" # Weekly on Sunday
  workflow_dispatch:

jobs:
  check-drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check for drift
        run: |
          cd .claude/skills/agent-sdk
          python scripts/check_drift.py
```

### Troubleshooting

**Issue**: "requests module not found"
**Solution**: `pip install requests` or install via requirements.txt

**Issue**: "Permission denied" when running check_drift.py
**Solution**: Script should be executable (chmod +x). Already set to 755.

**Issue**: Skill doesn't auto-activate
**Solution**: Verify YAML frontmatter in SKILL.md is valid and `auto_activate: true`

## Maintenance

### Update Workflow

When drift is detected:

1. **Verify Drift**: Run `check_drift.py` to identify changed sources
2. **Fetch Content**: Get updated documentation
3. **Analyze Changes**: Assess impact (minor, major, breaking)
4. **Update Files**: Modify affected skill files
5. **Validate**: Run self-validation checks
6. **Update Metadata**: Run `check_drift.py --update`, increment version

### Version Numbering

- **Patch** (1.0.0 → 1.0.1): Minor documentation updates, bug fixes
- **Minor** (1.0.0 → 1.1.0): New SDK features, new patterns
- **Major** (1.0.0 → 2.0.0): Breaking API changes, restructuring

### Contributing

To improve this skill:

1. Identify gaps or inaccuracies
2. Reference authoritative sources
3. Update relevant files
4. Validate token budgets
5. Update version metadata
6. Document changes in version history

## Integration with Amplihack

This skill integrates with the Amplihack framework:

**Agent Creation**:

```python
# Use Agent SDK patterns in Amplihack specialized agents
from claude_agents import Agent

def create_specialized_agent():
    return Agent(
        model="claude-sonnet-4-5-20250929",
        system="<amplihack_agent_role>",
        tools=[...],
        hooks=[AmplihackLoggingHook()]
    )
```

**MCP in Amplihack**:

```python
# Integrate MCP servers into Amplihack workflows
from claude_agents.mcp import MCPClient

mcp = MCPClient("npx", ["-y", "@modelcontextprotocol/server-filesystem"])
agent = Agent(mcp_clients=[mcp])
```

**Observability**:

```python
# Log agent actions to Amplihack runtime logs
class AmplihackLoggingHook(PreToolUseHook):
    async def execute(self, context):
        log_to_amplihack_runtime(...)
        return context
```

## Future Enhancements

Planned improvements:

- [ ] Automated weekly drift detection via CI/CD
- [ ] Smart diff analysis showing exact changes
- [ ] Automated partial updates for minor drifts
- [ ] Integration with Anthropic SDK changelog
- [ ] Community contribution process for patterns
- [ ] Performance benchmarks and optimization guide
- [ ] Advanced subagent orchestration patterns
- [ ] Error recovery decision trees

## Support

For questions or issues:

1. Check `SKILL.md` for quick reference
2. Review appropriate supporting file
3. Check `drift-detection.md` if information seems outdated
4. Consult source documentation URLs in `.metadata/versions.json`
5. Run drift detection to verify skill is current

## License

This skill synthesizes publicly available documentation from Anthropic and community sources. All original source material copyright © Anthropic and respective authors.

---

**Last Updated**: 2025-11-15
**Skill Version**: 1.0.0
**Maintained By**: Amplihack Framework
